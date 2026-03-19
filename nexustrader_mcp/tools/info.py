"""交易所信息与合约查询 MCP 工具。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from nexustrader.constants import ExchangeType

from nexustrader_mcp.serializers import serialize_market

if TYPE_CHECKING:
    from nexustrader_mcp.engine_manager import EngineManager


def register(mcp, engine: EngineManager):
    @mcp.tool()
    def get_exchange_info() -> list:
        """获取已配置的交易所及其连接状态。"""
        results = []
        for ex_type, ex_mgr in engine.strategy._exchanges.items():
            account_types = []
            for at in engine.strategy._public_connectors:
                if hasattr(at, "exchange_id") and at.exchange_id == ex_type.value:
                    account_types.append(str(at.value) if hasattr(at, "value") else str(at))
            results.append({
                "exchange": ex_type.value,
                "account_types": account_types,
            })
        return results

    @mcp.tool()
    def get_symbols(
        exchange: str,
        instrument_type: Optional[str] = None,
    ) -> list:
        """列出交易所可用交易对。

        Args:
            exchange: 交易所名称，如 binance / bybit / okx
            instrument_type: 可选，过滤合约类型：linear / spot / inverse
        """
        ex_type = ExchangeType(exchange.lower())
        ex_mgr = engine.strategy._exchanges.get(ex_type)
        if ex_mgr is None:
            return {"error": f"交易所 {exchange} 未配置"}

        try:
            match (instrument_type or "").lower():
                case "linear" | "perp" | "futures":
                    return ex_mgr.linear()
                case "spot":
                    return ex_mgr.spot()
                case "inverse":
                    return ex_mgr.inverse()
                case _:
                    return ex_mgr.linear() + ex_mgr.spot()
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_market_info(symbol: str) -> dict:
        """获取指定交易对的市场详情（精度、最小数量等）。

        Args:
            symbol: 交易对，如 BTCUSDT-PERP.BINANCE
        """
        try:
            market = engine.strategy.market(symbol)
            return serialize_market(market)
        except Exception as e:
            return {"error": str(e)}
