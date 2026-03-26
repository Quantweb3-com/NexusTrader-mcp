---
name: nexustrader
description: NexusTrader trading assistant. Query crypto balances, positions, prices, and place orders on Binance, Bybit, OKX, Bitget, HyperLiquid.
metadata:
  openclaw:
    requires:
      bins: ["python3", "uv"]
      python_packages: ["fastmcp"]
    credentials:
      - name: NEXUSTRADER_API_KEYS
        description: "Exchange API keys stored in NexusTrader-mcp project at .keys/.secrets.toml"
        scope: "local_file"
    network:
      - "127.0.0.1:18765 (local MCP server via SSE)"
    side_effects:
      - "May auto-start nexustrader-mcp background daemon (set NEXUSTRADER_NO_AUTOSTART=1 to disable)"
---

# NexusTrader

Use the **exec** tool to run bridge.py. Do not write code or call external HTTP APIs directly.
bridge.py communicates with a local MCP server at 127.0.0.1:18765 (SSE).

**Get all balances:**
`exec {baseDir}/bridge.py get_all_balances`

**Get all positions:**
`exec {baseDir}/bridge.py get_all_positions`

**Get balance for one exchange:**
`exec {baseDir}/bridge.py get_balance --exchange=okx`

**Get ticker:**
`exec {baseDir}/bridge.py get_ticker --symbol=BTCUSDT-PERP.BINANCE`

**Get klines:**
`exec {baseDir}/bridge.py get_klines --symbol=BTCUSDT-PERP.BINANCE --interval=1h --limit=24`

**Get open orders:**
`exec {baseDir}/bridge.py get_open_orders --exchange=okx`

**Get position for one symbol:**
`exec {baseDir}/bridge.py get_position --symbol=BTCUSDT-PERP.OKX`

**Place order (confirm first):**
`exec {baseDir}/bridge.py create_order --symbol=BTCUSDT-PERP.BINANCE --side=BUY --order_type=MARKET --amount=0.001`

**Cancel order (confirm first):**
`exec {baseDir}/bridge.py cancel_order --symbol=BTCUSDT-PERP.BINANCE --order_id=123`

Symbol format: `BTCUSDT-PERP.OKX` / `ETHUSDT-SPOT.BYBIT`. Exchange names lowercase.

If exec returns `{"error": ...}` → explain in Chinese.
If server not running → tell user: `cd NexusTrader-mcp && uv run nexustrader-mcp start`

For orders, always confirm with user before calling create_order/cancel_order/modify_order.
