---
description: 执行交易下单。用法：/trade <symbol> <buy|sell> <amount> [price] [market|limit]
---

⚠️ **此命令将执行真实交易，请仔细确认参数后再操作。**

解析 `$ARGUMENTS`，格式为：`<symbol> <side> <amount> [price] [type]`

**参数解析规则：**
- `symbol`：交易对，如 `BTCUSDT-PERP.BINANCE`
- `side`：`buy` 或 `sell`（大小写不敏感）
- `amount`：数量，如 `0.01`
- `price`：价格（可选，省略则使用市价单）
- `type`：`limit`（默认）或 `market`

**下单前必做：**
1. 调用 `get_ticker(symbol)` 获取当前价格
2. 调用 `get_balance(exchange, account_type)` 确认可用余额充足
3. 调用 `get_market_info(symbol)` 验证数量/价格精度和最小下单量
4. 向用户展示完整订单摘要，等待确认：
   ```
   ─── 下单确认 ───
   交易对：{symbol}
   方向：{side}
   类型：{type}
   数量：{amount}
   价格：{price}（当前市价：{current_price}，偏差：{deviation}%）
   预估成本：{cost} USDT
   ────────────────
   确认下单？(yes/no)
   ```
5. 用户确认后调用 `create_order(symbol, side, type, amount, price)`
6. 展示订单结果（订单 ID、状态）

**安全限制：**
- 价格偏离当前市价超过 5% 时发出警告
- market 类型订单始终显示额外警告

参数：$ARGUMENTS
