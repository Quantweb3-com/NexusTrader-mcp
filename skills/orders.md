---
description: 查看挂单。用法：/orders [symbol] [exchange]
---

根据 `$ARGUMENTS` 查询挂单（必须提供 symbol 或 exchange 之一）：
- 无参数：先调用 `get_exchange_info()` 获取所有交易所，再逐一调用 `get_open_orders(exchange=...)` 汇总
- 参数是交易对：调用 `get_open_orders(symbol=...)`
- 参数是交易所名称：调用 `get_open_orders(exchange=...)`

输出格式（Markdown 表格）：

| 订单ID | 交易对 | 方向 | 类型 | 数量 | 已成交 | 挂单价 | 当前价 | 距市价% | 时间 |
|--------|--------|------|------|------|--------|--------|--------|---------|------|

- 订单ID 显示末尾 8 位即可
- 按交易所分组展示
- 底部显示挂单总数和总挂单价值（USDT 估算）
- 如无挂单，输出"当前没有未成交挂单"

参数：$ARGUMENTS
