# NexusTrader MCP 接口测试报告

**测试时间**: 2026-03-20  
**交易所配置**: OKX (live)  
**订阅**: bookl1 (BTCUSDT.OKX, ETHUSDT.OKX, SOLUSDT.OKX)

## 测试总结

| 状态 | 数量 | 说明 |
|------|------|------|
| PASS | 14   | 正常可用 |
| WARN | 4    | 可调用但返回预期错误（需额外订阅配置） |
| SKIP | 3    | 交易类接口，跳过避免真实下单 |
| **总计** | **21** | |

## 详细结果

### 1. 交易所信息工具 (info)

| 工具 | 状态 | 说明 |
|------|------|------|
| `get_exchange_info` | **PASS** | 返回 `[{"exchange":"okx","account_types":["live"]}]` |
| `get_symbols[linear]` | **PASS** | 返回 270+ 永续合约交易对 (BTCUSDT-PERP.OKX 等) |
| `get_symbols[spot]` | **PASS** | 返回 700+ 现货交易对 |
| `get_market_info` | **PASS** | 返回 BTCUSDT-PERP.OKX 的精度/限额/费率等详情 |

### 2. 账户工具 (account)

| 工具 | 状态 | 说明 |
|------|------|------|
| `get_all_balances` | **PASS** | 返回 `[{"account_type":"live","exchange":"okx","balances":{}}]`（余额为空） |
| `get_balance` | **PASS** | 指定 exchange=okx, account_type=live 查询成功 |

### 3. 持仓工具 (position)

| 工具 | 状态 | 说明 |
|------|------|------|
| `get_all_positions` | **PASS** | 返回所有持仓列表 |
| `get_position` | **PASS** | 查询 BTCUSDT-PERP.OKX 返回 `{side: "FLAT", signed_amount: "0"}` |

### 4. 行情工具 (market)

| 工具 | 状态 | 说明 |
|------|------|------|
| `get_ticker` | **PASS** | REST 请求，返回最新价、成交量、时间戳 |
| `get_klines` | **PASS** | REST 请求，返回 K 线数组（interval=1h, limit=3） |
| `get_orderbook[SPOT]` | **PASS** | 使用 BTCUSDT.OKX (已订阅 bookl1)，返回 bid/ask/spread |
| `get_orderbook[PERP]` | **WARN** | BTCUSDT-PERP.OKX 未订阅 bookl1，返回错误 |
| `get_funding_rate` | **WARN** | config.yaml 未订阅 funding_rate，返回 "未找到资金费率数据" |
| `get_mark_price` | **WARN** | config.yaml 未订阅 mark_price，返回 "未找到标记价格数据" |
| `get_index_price` | **WARN** | config.yaml 未订阅 index_price，返回 "未找到指数价格数据" |

### 5. 交易工具 (trading)

| 工具 | 状态 | 说明 |
|------|------|------|
| `get_open_orders` | **PASS** | 按交易所查询挂单列表 |
| `get_order` | **PASS** | 查询不存在的订单正确返回 "未找到订单" |
| `cancel_all_orders` | **PASS** | 提交成功，返回 `{status: "CANCEL_ALL_SUBMITTED"}` |
| `create_order` | **SKIP** | 真实交易，需手动测试 |
| `cancel_order` | **SKIP** | 需要有效订单 ID |
| `modify_order` | **SKIP** | 需要有效订单 ID |

## 问题与建议

### 1. 订阅配置不完整

当前 `config.yaml` 只订阅了 `bookl1`，导致以下接口返回 "未找到" 错误：
- `get_funding_rate` → 需添加 `funding_rate`
- `get_mark_price` → 需添加 `mark_price`
- `get_index_price` → 需添加 `index_price`

**修复建议**：更新 config.yaml：

```yaml
exchanges:
  okx:
    account_type: live
    symbols:
    - BTCUSDT
    - ETHUSDT
    - SOLUSDT
    subscribe:
    - bookl1
    - funding_rate
    - mark_price
    - index_price
```

### 2. Symbol 格式问题

`get_orderbook` 使用 `BTCUSDT-PERP.OKX` 格式查询失败，但用 `BTCUSDT.OKX` 成功。
原因：config.yaml 中的 symbols 配置为 `BTCUSDT`，拼接后变成 `BTCUSDT.OKX`（非 PERP 格式）。
bookl1 订阅绑定的是 `BTCUSDT.OKX` 而不是 `BTCUSDT-PERP.OKX`。

**建议**：如果需要查询永续合约的 L1 盘口，symbols 应改为：

```yaml
symbols:
  - BTCUSDT-PERP
  - ETHUSDT-PERP
  - SOLUSDT-PERP
```

### 3. 引擎启动超时

独立运行测试脚本时，NexusTrader 引擎启动超时（`engine_manager.py` 硬编码 60s 超时）。
Cursor 中能正常使用是因为 MCP server 在 IDE 启动时已预热。

**建议**：考虑将 `engine_manager.py` 的启动超时改为可配置。
