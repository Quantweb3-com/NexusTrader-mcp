---
description: 查询行情数据。用法：/market <symbol> [klines|orderbook|funding]
---

根据 `$ARGUMENTS` 解析交易对和查询类型：

**参数格式示例：**
- `/market BTCUSDT-PERP.BINANCE` — 综合行情（ticker + orderbook + funding）
- `/market BTCUSDT-PERP.BINANCE klines` — K线数据（默认最近 24 根 1h）
- `/market BTCUSDT-PERP.BINANCE orderbook` — 最优买卖价
- `/market BTCUSDT-PERP.BINANCE funding` — 资金费率

**综合行情（默认）依次调用：**
1. `get_ticker(symbol)` — 最新成交价、24h 成交量
2. `get_orderbook(symbol)` — 最优买卖价、价差
3. `get_mark_price(symbol)` — 标记价格
4. `get_funding_rate(symbol)` — 资金费率（仅合约）

**K线查询：**
- 调用 `get_klines(symbol, interval="1h", limit=24)`
- 以简洁表格展示 OHLCV，并计算涨跌幅

**输出要求：**
- 价格数字对齐，保留合适精度
- 资金费率显示年化（费率 × 3 × 365）

参数：$ARGUMENTS
