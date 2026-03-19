"""行情数据相关 MCP 工具。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from nexustrader.constants import KlineInterval

from nexustrader_mcp.serializers import (
    serialize_bookl1,
    serialize_funding_rate,
    serialize_index_price,
    serialize_kline,
    serialize_mark_price,
    serialize_ticker,
)

if TYPE_CHECKING:
    from nexustrader_mcp.engine_manager import EngineManager

INTERVAL_MAP = {e.value: e for e in KlineInterval if e != KlineInterval.VOLUME}


def register(mcp, engine: EngineManager):
    @mcp.tool()
    def get_ticker(symbol: str) -> dict:
        """获取指定交易对的最新行情（REST 请求，非缓存）。

        Args:
            symbol: 交易对，如 BTCUSDT-PERP.BINANCE
        """
        try:
            ticker = engine.strategy.request_ticker(symbol)
            return serialize_ticker(ticker)
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_orderbook(symbol: str) -> dict:
        """获取缓存中的最优买卖价（L1 盘口）。需要先预订阅 bookl1。

        Args:
            symbol: 交易对，如 BTCUSDT-PERP.BINANCE
        """
        bl1 = engine.strategy.cache.bookl1(symbol)
        if bl1 is None:
            return {"error": f"未找到 {symbol} 的 L1 盘口数据，可能未订阅 bookl1"}
        return serialize_bookl1(bl1)

    @mcp.tool()
    def get_klines(
        symbol: str,
        interval: str = "1h",
        limit: int = 100,
    ) -> list:
        """获取历史 K 线数据（REST 请求）。

        Args:
            symbol: 交易对，如 BTCUSDT-PERP.BINANCE
            interval: K 线周期，可选 1m/5m/15m/30m/1h/4h/1d 等
            limit: 返回条数，默认 100
        """
        kline_interval = INTERVAL_MAP.get(interval)
        if kline_interval is None:
            return {"error": f"无效的 interval: {interval}。可选: {', '.join(INTERVAL_MAP.keys())}"}
        try:
            klines = engine.strategy.request_klines(
                symbol=symbol, interval=kline_interval, limit=limit
            )
            return [serialize_kline(k) for k in klines]
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_funding_rate(symbol: str) -> dict:
        """获取缓存中的资金费率。需要先预订阅 funding_rate。

        Args:
            symbol: 交易对，如 BTCUSDT-PERP.BINANCE
        """
        fr = engine.strategy.cache.funding_rate(symbol)
        if fr is None:
            return {"error": f"未找到 {symbol} 的资金费率数据"}
        return serialize_funding_rate(fr)

    @mcp.tool()
    def get_mark_price(symbol: str) -> dict:
        """获取缓存中的标记价格。需要先预订阅 mark_price。

        Args:
            symbol: 交易对，如 BTCUSDT-PERP.BINANCE
        """
        mp = engine.strategy.cache.mark_price(symbol)
        if mp is None:
            return {"error": f"未找到 {symbol} 的标记价格数据"}
        return serialize_mark_price(mp)

    @mcp.tool()
    def get_index_price(symbol: str) -> dict:
        """获取缓存中的指数价格。需要先预订阅 index_price。

        Args:
            symbol: 交易对，如 BTCUSDT-PERP.BINANCE
        """
        ip = engine.strategy.cache.index_price(symbol)
        if ip is None:
            return {"error": f"未找到 {symbol} 的指数价格数据"}
        return serialize_index_price(ip)
