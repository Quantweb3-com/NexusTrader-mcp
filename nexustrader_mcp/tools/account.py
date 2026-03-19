"""账户与余额相关 MCP 工具。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from nexustrader_mcp.config import ACCOUNT_TYPE_MAP
from nexustrader_mcp.serializers import serialize_account_balance

if TYPE_CHECKING:
    from nexustrader_mcp.engine_manager import EngineManager


def register(mcp, engine: EngineManager):
    @mcp.tool()
    def get_balance(exchange: str, account_type: str) -> dict:
        """获取指定交易所/账户类型的余额。

        Args:
            exchange: 交易所名称，如 binance / bybit / okx
            account_type: 账户类型，如 USD_M_FUTURE_TESTNET / LINEAR
        """
        mapping = ACCOUNT_TYPE_MAP.get(exchange.lower())
        if not mapping:
            return {"error": f"不支持的交易所: {exchange}"}
        at = mapping.get(account_type)
        if at is None:
            return {"error": f"无效的 account_type: {account_type}"}

        try:
            ab = engine.strategy.cache.get_balance(at)
            return serialize_account_balance(ab)
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def get_all_balances() -> list:
        """获取所有已配置账户的余额。"""
        results = []
        cache = engine.strategy.cache
        for at, ab in cache._mem_account_balance.items():
            results.append({
                "account_type": str(at.value) if hasattr(at, "value") else str(at),
                "exchange": at.exchange_id if hasattr(at, "exchange_id") else "unknown",
                **serialize_account_balance(ab),
            })
        return results
