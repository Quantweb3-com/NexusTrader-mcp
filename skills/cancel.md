---
description: 撤销订单。用法：/cancel <symbol> [order_id|all]
---

⚠️ **此命令将撤销真实订单，请确认后操作。**

解析 `$ARGUMENTS`：
- `/cancel BTCUSDT-PERP.BINANCE all` — 撤销该交易对所有挂单
- `/cancel BTCUSDT-PERP.BINANCE <order_id>` — 撤销指定订单

**执行步骤：**
1. 先调用 `get_open_orders(symbol=...)` 显示当前挂单
2. 展示将要撤销的订单列表，请求用户确认
3. 确认后执行：
   - 单笔：`cancel_order(symbol, oid)`
   - 全部：`cancel_all_orders(symbol)`
4. 展示撤单结果

参数：$ARGUMENTS
