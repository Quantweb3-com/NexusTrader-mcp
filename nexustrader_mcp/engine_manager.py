"""EngineManager — manages the NexusTrader Engine lifecycle in a background thread."""

from __future__ import annotations

import asyncio
import sys
import threading
import time
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from nexustrader.engine import Engine
    from nexustrader_mcp.mcp_strategy import MCPStrategy
    from nexustrader_mcp.config import SubscriptionInfo

# Timeout (seconds) for each startup phase
_PHASE_TIMEOUT = 60
# Total timeout (seconds) for the engine to be ready
_READY_TIMEOUT = 120


def _log(msg: str) -> None:
    """Write a timestamped startup log line to stderr."""
    ts = time.strftime("%H:%M:%S")
    print(f"[NexusTrader {ts}] {msg}", file=sys.stderr, flush=True)


class EngineManager:
    """Start / stop NexusTrader Engine in a daemon thread."""

    def __init__(self):
        self._strategy: Optional[MCPStrategy] = None
        self.engine: Optional[Engine] = None
        self._thread: Optional[threading.Thread] = None
        self._ready = threading.Event()
        self._error: Optional[BaseException] = None
        self._subscriptions: Optional[SubscriptionInfo] = None

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    @property
    def strategy(self) -> MCPStrategy:
        """Return strategy, blocking until engine is ready if startup is in progress."""
        if self._thread is not None:
            if not self._ready.wait(timeout=_READY_TIMEOUT):
                raise RuntimeError(
                    f"NexusTrader engine startup timeout ({_READY_TIMEOUT}s), check network and config"
                )
            if self._error:
                raise RuntimeError(f"NexusTrader 引擎启动失败: {self._error}")
        return self._strategy

    def start(self, config_path: Optional[str] = None):
        """Launch background thread for all startup work. Returns immediately."""
        self._thread = threading.Thread(
            target=self._run_all,
            args=(config_path,),
            daemon=True,
            name="nexustrader-engine",
        )
        self._thread.start()

    def stop(self):
        if self.engine:
            try:
                self.engine.dispose()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _run_all(self, config_path: Optional[str]):
        """Full startup in background: imports + config + engine. Sets _ready when done."""
        t0 = time.time()
        _log("importing modules...")
        try:
            # All heavy imports happen here, off the main thread
            from nexustrader_mcp.mcp_strategy import MCPStrategy
            from nexustrader.engine import Engine
            from nexustrader_mcp.config import (
                build_nexus_config,
                find_config_path,
                load_mcp_config,
            )
            import nexustrader as _nt
            _log(f"imports done ({time.time()-t0:.1f}s) | NexusTrader: {_nt.__file__}")

            # uvloop raises ValueError (not RuntimeError) from a non-main thread;
            # patch TaskManager to tolerate this before Engine is created.
            from nexustrader.core.entity import TaskManager as _TM
            _orig_setup = _TM._setup_signal_handlers
            def _safe_setup(self_tm):
                try:
                    _orig_setup(self_tm)
                except (NotImplementedError, RuntimeError, ValueError):
                    pass
            _TM._setup_signal_handlers = _safe_setup

            self._strategy = MCPStrategy()
            path = find_config_path(config_path)
            _log(f"config: {path}")
            mcp_cfg = load_mcp_config(path)

            nexus_config, self._subscriptions = build_nexus_config(
                mcp_cfg, self._strategy
            )
            self._strategy._subscriptions = self._subscriptions.items
            _log(f"config loaded ({time.time()-t0:.1f}s)")

            self.engine = Engine(nexus_config)
            self._run_engine(t0)

        except BaseException as exc:
            _log(f"startup failed: {exc}")
            self._error = exc
            self._ready.set()

    def _run_engine(self, t0: float):
        """Run NexusTrader event loop until stopped."""
        try:
            _log(f"building exchanges/connectors... ({time.time()-t0:.1f}s)")
            # _build() is synchronous — run it in a thread with timeout
            _build_done = threading.Event()
            _build_error: list[BaseException | None] = [None]

            def _do_build():
                try:
                    self.engine._build()
                except BaseException as exc:
                    _build_error[0] = exc
                finally:
                    _build_done.set()

            _t = threading.Thread(target=_do_build, daemon=True)
            _t.start()
            if not _build_done.wait(timeout=_PHASE_TIMEOUT):
                raise RuntimeError(
                    f"engine._build() timeout (>{_PHASE_TIMEOUT}s), check network"
                )
            if _build_error[0]:
                raise _build_error[0]

            _log(f"build done ({time.time()-t0:.1f}s), starting event loop...")

            try:
                self.engine._loop.run_until_complete(
                    asyncio.wait_for(self.engine._cache.start(), timeout=_PHASE_TIMEOUT)
                )
            except asyncio.TimeoutError:
                raise RuntimeError(
                    f"cache.start() timeout (>{_PHASE_TIMEOUT}s), check network"
                )
            _log(f"cache started ({time.time()-t0:.1f}s)")

            async def _start_and_signal():
                await _timed(self.engine._sms.start(), "SMS", t0)
                await _timed(self.engine._start_oms(), "OMS", t0)
                await _timed(self.engine._start_ems(), "EMS", t0)
                await _timed(self.engine._start_connectors(), "Connectors", t0)
                self.engine._strategy._on_start()
                self.engine._start_scheduler()
                _log(f"engine ready! total startup: {time.time()-t0:.1f}s")
                self._ready.set()
                await self.engine._task_manager.wait()

            self.engine._loop.run_until_complete(_start_and_signal())
        except BaseException as exc:
            _log(f"runtime error: {exc}")
            self._error = exc
            self._ready.set()


async def _timed(coro, name: str, t0: float) -> None:
    """Run a coroutine with per-phase timeout and timing log."""
    _log(f"  starting {name}...")
    try:
        await asyncio.wait_for(coro, timeout=_PHASE_TIMEOUT)
    except asyncio.TimeoutError:
        raise RuntimeError(
            f"{name} startup timeout (>{_PHASE_TIMEOUT}s), check network"
        )
    _log(f"  {name} ready ({time.time()-t0:.1f}s)")
