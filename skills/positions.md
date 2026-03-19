---
description: 查询持仓。用法：/positions [exchange] 或 /positions [symbol]
---

根据 `$ARGUMENTS` 决定查询方式：
- 无参数：调用 `get_all_positions()` 获取全部持仓
- 参数是交易所名称（如 `binance`、`bybit`）：调用 `get_all_positions(exchange=...)` 按交易所过滤
- 参数是交易对（含 `.` 或 `-PERP`）：调用 `get_position(symbol=...)` 查询单个持仓

输出要求：
- 按交易所分组展示
- 每条持仓显示：交易对、方向（多/空/平仓）、数量、开仓均价、未实现盈亏（含百分比）、已实现盈亏
- 对平仓（FLAT）持仓不输出，除非明确要求
- 汇总显示总未实现盈亏

参数：$ARGUMENTS
