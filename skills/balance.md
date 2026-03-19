---
description: 查询账户余额。用法：/balance [exchange] [account_type]
---

使用 `get_all_balances` 工具获取所有已配置账户的余额。

如果用户在 `$ARGUMENTS` 中提供了交易所名称（如 `binance`），则改用 `get_balance(exchange, account_type)` 精确查询，account_type 从上下文或配置推断。

输出要求：
- 按交易所分组展示
- 显示总资产、可用余额、冻结余额
- 对 USDT/USDC 等稳定币保留 2 位小数，其他币种保留 6 位小数
- 如有多个账户类型（现货/合约），分别列出

参数：$ARGUMENTS
