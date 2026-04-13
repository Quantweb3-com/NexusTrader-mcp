"""交易相关 MCP 工具（下单 / 撤单 / 改单）。"""

from __future__ import annotations

import asyncio
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Optional

from nexustrader.constants import ExchangeType, OrderSide, OrderType, TimeInForce

from nexustrader_mcp.serializers import serialize_order

if TYPE_CHECKING:
    from nexustrader_mcp.engine_manager import EngineManager

ORDER_SIDE_MAP = {e.value: e for e in OrderSide}
ORDER_TYPE_MAP = {e.value: e for e in OrderType}

_ORDER_WAIT_TIMEOUT = 10


def register(mcp, engine: EngineManager):
    @mcp.tool()
    async def create_order(
        symbol: str,
        side: str,
        type: str,
        amount: str,
        price: Optional[str] = None,
        reduce_only: bool = False,
    ) -> dict:
        """【真实交易】下单。将在交易所执行真实交易，请谨慎操作。

        Args:
            symbol: 交易对，如 BTCUSDT-PERP.BINANCE
            side: 方向，BUY 或 SELL
            type: 订单类型，LIMIT / MARKET / POST_ONLY
            amount: 数量（字符串，如 "0.01"）
            price: 价格（限价单必填，字符串如 "68000"）
            reduce_only: 是否仅减仓，默认 False
        """
        order_side = ORDER_SIDE_MAP.get(side.upper())
        if order_side is None:
            return {"error": f"无效的 side: {side}。可选: BUY, SELL"}

        order_type = ORDER_TYPE_MAP.get(type.upper())
        if order_type is None:
            return {"error": f"无效的 type: {type}。可选: {', '.join(ORDER_TYPE_MAP.keys())}"}

        try:
            dec_amount = Decimal(amount)
        except InvalidOperation:
            return {"error": f"无效的 amount: {amount}"}

        dec_price = None
        if price is not None:
            try:
                dec_price = Decimal(price)
            except InvalidOperation:
                return {"error": f"无效的 price: {price}"}

        if (order_type.is_limit or order_type.is_post_only) and dec_price is None:
            return {"error": "限价单/POST_ONLY 必须提供 price 参数"}

        event = asyncio.Event()
        strategy = engine.strategy

        oid = strategy.create_order(
            symbol=symbol,
            side=order_side,
            type=order_type,
            amount=dec_amount,
            price=dec_price,
            reduce_only=reduce_only,
        )

        strategy.register_order_event(oid, event)

        try:
            await asyncio.wait_for(event.wait(), timeout=_ORDER_WAIT_TIMEOUT)
        except asyncio.TimeoutError:
            strategy.pop_order_result(oid)
            return {"oid": oid, "status": "PENDING", "message": "下单已提交，但等待确认超时"}

        order = strategy.pop_order_result(oid)
        if order:
            return serialize_order(order)
        return {"oid": oid, "status": "PENDING"}

    @mcp.tool()
    async def cancel_order(symbol: str, oid: str) -> dict:
        """撤销一个挂单。

        Args:
            symbol: 交易对，如 BTCUSDT-PERP.BINANCE
            oid: 订单 ID
        """
        event = asyncio.Event()
        strategy = engine.strategy

        strategy.register_order_event(oid, event)
        strategy.cancel_order(symbol=symbol, oid=oid)

        try:
            await asyncio.wait_for(event.wait(), timeout=_ORDER_WAIT_TIMEOUT)
        except asyncio.TimeoutError:
            strategy.pop_order_result(oid)
            return {"oid": oid, "status": "CANCELING", "message": "撤单已提交，但等待确认超时"}

        order = strategy.pop_order_result(oid)
        if order:
            return serialize_order(order)
        return {"oid": oid, "status": "CANCELING"}

    @mcp.tool()
    async def cancel_all_orders(symbol: str) -> dict:
        """撤销指定交易对的所有挂单。

        Args:
            symbol: 交易对，如 BTCUSDT-PERP.BINANCE
        """
        strategy = engine.strategy
        cache = strategy.cache

        try:
            oids = list(cache.get_open_orders(symbol=symbol))
        except Exception as e:
            return {"error": str(e)}

        if not oids:
            return {"symbol": symbol, "status": "NO_OPEN_ORDERS", "cancelled": 0}

        events: dict[str, asyncio.Event] = {}
        for oid in oids:
            event = asyncio.Event()
            strategy.register_order_event(oid, event)
            events[oid] = event
            try:
                strategy.cancel_order(symbol=symbol, oid=oid)
            except Exception as e:
                strategy.pop_order_result(oid)
                events.pop(oid, None)

        if not events:
            return {"error": "所有撤单提交均失败"}

        try:
            await asyncio.wait_for(
                asyncio.gather(*[e.wait() for e in events.values()]),
                timeout=_ORDER_WAIT_TIMEOUT,
            )
        except asyncio.TimeoutError:
            for oid in list(events):
                strategy.pop_order_result(oid)
            return {
                "symbol": symbol,
                "status": "CANCEL_ALL_SUBMITTED",
                "message": "撤单已提交，但等待确认超时",
                "order_count": len(events),
            }

        results = []
        for oid in list(events):
            order = strategy.pop_order_result(oid)
            if order:
                results.append(serialize_order(order))

        return {"symbol": symbol, "status": "CANCELLED", "cancelled": len(results), "orders": results}

    @mcp.tool()
    async def modify_order(
        symbol: str,
        oid: str,
        price: str,
        amount: str,
        side: Optional[str] = None,
    ) -> dict:
        """修改一个挂单的价格和数量。

        Args:
            symbol: 交易对
            oid: 要修改的订单 ID
            price: 新价格
            amount: 新数量
            side: 新方向（可选，不提供则保持原方向）
        """
        strategy = engine.strategy
        existing = strategy.cache.get_order(oid)

        if side:
            order_side = ORDER_SIDE_MAP.get(side.upper())
            if order_side is None:
                return {"error": f"无效的 side: {side}"}
        elif existing and existing.side:
            order_side = existing.side
        else:
            return {"error": "无法确定订单方向，请提供 side 参数"}

        event = asyncio.Event()

        strategy.register_order_event(oid, event)
        strategy.modify_order(
            symbol=symbol,
            oid=oid,
            side=order_side,
            price=Decimal(price),
            amount=Decimal(amount),
        )

        try:
            await asyncio.wait_for(event.wait(), timeout=_ORDER_WAIT_TIMEOUT)
        except asyncio.TimeoutError:
            strategy.pop_order_result(oid)
            return {"oid": oid, "status": "PENDING", "message": "改单已提交，但等待确认超时"}

        order = strategy.pop_order_result(oid)
        if order:
            return serialize_order(order)
        return {"oid": oid, "status": "PENDING"}

    @mcp.tool()
    def get_open_orders(
        symbol: Optional[str] = None,
        exchange: Optional[str] = None,
    ) -> list:
        """获取所有挂单。必须提供 symbol 或 exchange 之一。

        Args:
            symbol: 交易对，如 BTCUSDT-PERP.BINANCE
            exchange: 交易所名称，如 binance
        """
        cache = engine.strategy.cache
        try:
            if symbol:
                oids = cache.get_open_orders(symbol=symbol)
            elif exchange:
                ex = ExchangeType(exchange.lower())
                oids = cache.get_open_orders(exchange=ex)
            else:
                return {"error": "必须提供 symbol 或 exchange 参数"}
        except Exception as e:
            return {"error": str(e)}

        results = []
        for oid in oids:
            order = cache.get_order(oid)
            if order:
                results.append(serialize_order(order))
        return results

    @mcp.tool()
    def get_order(oid: str) -> dict:
        """获取指定订单的详细信息。

        Args:
            oid: 订单 ID
        """
        order = engine.strategy.cache.get_order(oid)
        if order is None:
            return {"error": f"未找到订单: {oid}"}
        return serialize_order(order)
