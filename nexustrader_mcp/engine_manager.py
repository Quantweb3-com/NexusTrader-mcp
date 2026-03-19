"""EngineManager — manages the NexusTrader Engine lifecycle in a background thread."""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path
from typing import Optional

from nexustrader.engine import Engine

from nexustrader_mcp.config import (
    SubscriptionInfo,
    build_nexus_config,
    find_config_path,
    load_mcp_config,
)
from nexustrader_mcp.mcp_strategy import MCPStrategy


class EngineManager:
    """Start / stop NexusTrader Engine in a daemon thread."""

    def __init__(self):
        self.strategy: MCPStrategy = MCPStrategy()
        self.engine: Optional[Engine] = None
        self._thread: Optional[threading.Thread] = None
        self._ready = threading.Event()
        self._error: Optional[Exception] = None
        self._subscriptions: Optional[SubscriptionInfo] = None

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def start(self, config_path: Optional[str] = None, timeout: float = 60):
        """Load config, build engine, start in background thread, block until ready."""
        path = find_config_path(config_path)
        mcp_cfg = load_mcp_config(path)

        nexus_config, self._subscriptions = build_nexus_config(
            mcp_cfg, self.strategy
        )

        self.strategy._subscriptions = self._subscriptions.items

        self.engine = Engine(nexus_config)

        self._thread = threading.Thread(
            target=self._run_engine, daemon=True, name="nexustrader-engine"
        )
        self._thread.start()

        if not self._ready.wait(timeout=timeout):
            print(
                "NexusTrader 引擎启动超时，请检查交易所连接和凭证配置。",
                file=sys.stderr,
            )
            sys.exit(1)

        if self._error:
            print(f"NexusTrader 引擎启动失败: {self._error}", file=sys.stderr)
            sys.exit(1)

    def stop(self):
        if self.engine:
            try:
                self.engine.dispose()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _run_engine(self):
        """Runs in the background thread."""
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
        except Exception as exc:
            self._error = exc
            self._ready.set()
