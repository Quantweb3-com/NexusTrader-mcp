---
name: nexustrader
description: NexusTrader trading assistant. Query crypto balances, positions, prices, and place orders on Binance, Bybit, OKX, Bitget, HyperLiquid.
metadata: {"openclaw":{"requires":{"bins":["python3"]}}}
---

# NexusTrader

Use the **exec** tool to run bridge.py. Do not write code or call any HTTP API.

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
