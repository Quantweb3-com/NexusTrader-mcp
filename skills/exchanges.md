---
description: 查看已连接的交易所和可用交易对。用法：/exchanges [exchange] [instrument_type]
---

根据 `$ARGUMENTS`：
- 无参数：调用 `get_exchange_info()` 展示所有已配置交易所及连接状态
- 参数是交易所名称（如 `binance`）：调用 `get_symbols(exchange=...)` 列出可用交易对
- 参数含类型（如 `binance perp`）：调用 `get_symbols(exchange=..., instrument_type="perp")`

**交易所总览输出：**
| 交易所 | 账户类型 | 连接状态 | 测试网 |
|--------|----------|----------|--------|

**交易对列表输出：**
- 按品种分组（现货 / 合约 / 期权）
- 最多显示 20 个，超出时提示总数并说明可按类型过滤
- 支持模糊匹配：如参数含 `BTC` 则过滤显示 BTC 相关交易对

参数：$ARGUMENTS
