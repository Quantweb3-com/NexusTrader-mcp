"""FastMCP 服务器定义与工具注册。"""

from __future__ import annotations

from fastmcp import FastMCP

from nexustrader_mcp.engine_manager import EngineManager
from nexustrader_mcp.tools import account, info, market, position, trading


def create_mcp_server(engine: EngineManager) -> FastMCP:
    mcp = FastMCP(
        name="NexusTrader",
        instructions=(
            "NexusTrader MCP 提供加密货币交易功能：\n"
            "- 账户余额与持仓查询\n"
            "- 实时行情与历史K线\n"
            "- 下单、撤单、改单\n"
            "- 交易所信息查询\n\n"
            "交易对格式: {base}{quote}-PERP.{EXCHANGE}，例如 BTCUSDT-PERP.BINANCE\n"
            "交易工具会执行真实交易，请务必确认后再操作。"
        ),
    )

    account.register(mcp, engine)
    position.register(mcp, engine)
    market.register(mcp, engine)
    trading.register(mcp, engine)
    info.register(mcp, engine)

    return mcp
