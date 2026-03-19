"""MCPStrategy — a passive Strategy subclass that exposes NexusTrader capabilities to MCP tools."""

from __future__ import annotations

import asyncio
import threading
from typing import Any, Dict, List, Optional

from nexustrader.schema import Order
from nexustrader.strategy import Strategy


class MCPStrategy(Strategy):
    """Passive strategy: subscribes to market data, but never trades on its own.

    Order callbacks notify asyncio Events so MCP tools can await order status.
    """

    def __init__(self):
        super().__init__()
        self._order_events: Dict[str, asyncio.Event] = {}
        self._order_results: Dict[str, Order] = {}
        self._lock = threading.Lock()
        self._subscriptions: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_start(self):
        for sub in self._subscriptions:
            sub_type = sub["type"]
            symbols = sub["symbols"]
            match sub_type:
                case "bookl1":
                    self.subscribe_bookl1(symbols)
                case "trade":
                    self.subscribe_trade(symbols)
                case "kline":
                    self.subscribe_kline(symbols, sub["interval"])
                case "funding_rate":
                    self.subscribe_funding_rate(symbols)
                case "mark_price":
                    self.subscribe_mark_price(symbols)
                case "index_price":
                    self.subscribe_index_price(symbols)

    # ------------------------------------------------------------------
    # Order event tracking
    # ------------------------------------------------------------------

    def register_order_event(self, oid: str, event: asyncio.Event):
        with self._lock:
            self._order_events[oid] = event

    def pop_order_result(self, oid: str) -> Optional[Order]:
        with self._lock:
            self._order_events.pop(oid, None)
            return self._order_results.pop(oid, None)

    def _notify_order(self, order: Order):
        with self._lock:
            self._order_results[order.oid] = order
            event = self._order_events.get(order.oid)
        if event:
            event.set()

    # ------------------------------------------------------------------
    # Order callbacks
    # ------------------------------------------------------------------

    def on_pending_order(self, order: Order):
        self._notify_order(order)

    def on_accepted_order(self, order: Order):
        self._notify_order(order)

    def on_partially_filled_order(self, order: Order):
        self._notify_order(order)

    def on_filled_order(self, order: Order):
        self._notify_order(order)

    def on_canceling_order(self, order: Order):
        self._notify_order(order)

    def on_canceled_order(self, order: Order):
        self._notify_order(order)

    def on_failed_order(self, order: Order):
        self._notify_order(order)

    def on_cancel_failed_order(self, order: Order):
        self._notify_order(order)
