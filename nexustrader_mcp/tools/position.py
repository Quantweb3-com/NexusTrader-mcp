"""持仓查询相关 MCP 工具。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from nexustrader.constants import ExchangeType

from nexustrader_mcp.serializers import serialize_position

if TYPE_CHECKING:
    from nexustrader_mcp.engine_manager import EngineManager


def register(mcp, engine: EngineManager):
    @mcp.tool()
    def get_position(symbol: str) -> dict:
        """获取指定交易对的持仓信息。

        Args:
            symbol: 交易对，如 BTCUSDT-PERP.BINANCE
        """
        pos = engine.strategy.cache.get_position(symbol)
        if pos is None:
            return {"symbol": symbol, "side": "FLAT", "signed_amount": "0"}
        return serialize_position(pos)

    @mcp.tool()
    def get_all_positions(exchange: Optional[str] = None) -> list:
        """获取所有持仓，可按交易所过滤。

        Args:
            exchange: 可选，交易所名称过滤，如 binance / bybit / okx
        """
        ex = ExchangeType(exchange.lower()) if exchange else None
        positions = engine.strategy.cache.get_all_positions(exchange=ex)
        return [serialize_position(p) for p in positions.values()]
