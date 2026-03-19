"""EngineManager — manages the NexusTrader Engine lifecycle in a background thread."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from nexustrader.engine import Engine
    from nexustrader_mcp.mcp_strategy import MCPStrategy
    from nexustrader_mcp.config import SubscriptionInfo


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
            if not self._ready.wait(timeout=60):
                raise RuntimeError("NexusTrader 引擎启动超时（60s），请检查网络和配置")
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
        try:
            # All heavy imports happen here, off the main thread
            from nexustrader_mcp.mcp_strategy import MCPStrategy
            from nexustrader.engine import Engine
            from nexustrader_mcp.config import (
                build_nexus_config,
                find_config_path,
                load_mcp_config,
            )

            self._strategy = MCPStrategy()
            path = find_config_path(config_path)
            mcp_cfg = load_mcp_config(path)

            nexus_config, self._subscriptions = build_nexus_config(
                mcp_cfg, self._strategy
            )
            self._strategy._subscriptions = self._subscriptions.items

            self.engine = Engine(nexus_config)
            self._run_engine()

        except BaseException as exc:
            self._error = exc
            self._ready.set()

    def _run_engine(self):
        """Run NexusTrader event loop until stopped."""
        try:
            self.engine._build()
            self.engine._loop.run_until_complete(self.engine._cache.start())

            async def _start_and_signal():
                await self.engine._sms.start()
                await self.engine._start_oms()
                await self.engine._start_ems()
                await self.engine._start_connectors()
                self.engine._strategy._on_start()
                self.engine._start_scheduler()
                self._ready.set()
                await self.engine._task_manager.wait()

            self.engine._loop.run_until_complete(_start_and_signal())
        except BaseException as exc:
            self._error = exc
            self._ready.set()
