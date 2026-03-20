# NexusTrader 量化交易助手

> 连接 NexusTrader MCP Server，让 AI 实时查询加密货币账户余额、持仓、行情，并执行交易操作。
> 支持 Binance、Bybit、OKX、Bitget、HyperLiquid。

---

## 自动启动（on_startup）

每次 OpenClaw 激活本 Skill 时，自动检查并拉起后台 MCP 服务器：

```bash
bash "${SKILL_DIR}/nexustrader_daemon.sh" start
```

服务器启动需要约 30–60 秒完成交易引擎初始化，之后所有工具调用均实时响应。
如果服务器已在运行，此命令立即返回，不会重复启动。

---

## 工具调用

所有工具通过以下命令调用，结果自动格式化为 Markdown 表格：

```bash
python "${SKILL_DIR}/bridge.py" <tool_name> [--arg=value ...]
```

### 可用工具速查表

| 工具名 | 用途 | 示例 |
|--------|------|------|
| `status` | 检查服务器是否在线 | `bridge.py status` |
| `list_tools` | 列出所有可用工具 | `bridge.py list_tools` |
| `get_all_balances` | 所有账户余额 | `bridge.py get_all_balances` |
| `get_balance` | 指定账户余额 | `bridge.py get_balance --exchange=binance --account_type=USD_M_FUTURE_TESTNET` |
| `get_all_positions` | 所有持仓 | `bridge.py get_all_positions` |
| `get_all_positions` | 指定交易所持仓 | `bridge.py get_all_positions --exchange=binance` |
| `get_position` | 单个持仓 | `bridge.py get_position --symbol=BTCUSDT-PERP.BINANCE` |
| `get_ticker` | 实时行情 | `bridge.py get_ticker --symbol=BTCUSDT-PERP.BINANCE` |
| `get_klines` | K线历史 | `bridge.py get_klines --symbol=BTCUSDT-PERP.BINANCE --interval=1h --limit=24` |
| `get_orderbook` | 买卖盘 | `bridge.py get_orderbook --symbol=BTCUSDT-PERP.BINANCE` |
| `get_open_orders` | 当前挂单 | `bridge.py get_open_orders --exchange=binance` |
| `get_exchange_info` | 已连接交易所 | `bridge.py get_exchange_info` |
| `get_symbols` | 交易对列表 | `bridge.py get_symbols --exchange=binance --instrument_type=linear` |
| `get_market_info` | 合约详情 | `bridge.py get_market_info --symbol=BTCUSDT-PERP.BINANCE` |
| `create_order` | ⚠️ 下单 | `bridge.py create_order --symbol=BTCUSDT-PERP.BINANCE --side=BUY --order_type=MARKET --amount=0.001` |
| `cancel_order` | ⚠️ 撤单 | `bridge.py cancel_order --symbol=BTCUSDT-PERP.BINANCE --order_id=123` |
| `cancel_all_orders` | ⚠️ 全部撤单 | `bridge.py cancel_all_orders --symbol=BTCUSDT-PERP.BINANCE` |
| `modify_order` | ⚠️ 改单 | `bridge.py modify_order --symbol=BTCUSDT-PERP.BINANCE --order_id=123 --price=65000` |

---

## AI 使用指南

### 交易对格式

永续合约：`{BASE}{QUOTE}-PERP.{EXCHANGE}`，例如 `BTCUSDT-PERP.BINANCE`
现货：`{BASE}{QUOTE}-SPOT.{EXCHANGE}`，例如 `ETHUSDT-SPOT.BYBIT`

交易所名称一律小写：`binance` / `bybit` / `okx` / `bitget` / `hyperliquid`

---

### 自然语言意图识别

**查询持仓**（`get_all_positions`）
> "我买了什么" / "我的仓位" / "当前持仓" / "开了什么单" / "做多了什么" / "BTC 持仓多少"

**查询余额**（`get_all_balances`）
> "有多少钱" / "账户余额" / "有多少 USDT" / "可用资金" / "钱包余额"

**投资组合总览**（`get_all_balances` + `get_all_positions`）
> "现在赚了吗" / "整体盈亏" / "总览" / "资产组合" / "给我报告一下"

**实时行情**（`get_ticker`）
> "BTC 现在多少钱" / "ETH 最新价格" / "BTCUSDT 行情"

**K 线走势**（`get_klines`）
> "BTC 近期走势" / "ETH 1小时K线" / "最近24小时数据"

**下单**（`create_order` — 必须二次确认）
> "帮我买 BTC" / "开 0.01 BTC 多单" / "做空 ETH"

**撤单**（`cancel_order` — 必须二次确认）
> "撤单" / "取消所有挂单" / "把 BTC 的限价单撤了"

---

### 盈亏计算流程

当用户问 "现在赚了吗" / "盈亏如何" 时，按以下步骤：

1. `get_all_positions` → 读取每个持仓的 `unrealized_pnl` 字段
2. `get_all_balances` → 读取账户总资产
3. 汇总计算，用人话回答：

```
你目前有 2 个持仓：
- BTCUSDT 多单：未实现盈利 +$234.50 ✅
- ETHUSDT 空单：未实现亏损 -$45.20 ❌

合计浮盈：+$189.30
账户余额：1,234.56 USDT（可用 1,100.00）
```

---

### 下单安全流程

涉及真实交易（`create_order` / `cancel_order` / `modify_order`）时，**必须**先向用户展示确认信息：

```
⚠️ 确认下单

- 交易对: BTCUSDT-PERP.BINANCE
- 方向: 做多 (BUY)
- 类型: 市价单 (MARKET)
- 数量: 0.00152 BTC（约 100 USDT）
- 当前价: ~$65,800

请回复"确认"后执行，或说明修改意见。
```

用户明确确认后，再调用 `bridge.py create_order ...`。

---

### 错误处理

- 工具返回 `error` 字段 → 用中文解释原因，给出解决建议
- 服务器离线 → 提示用户：
  ```
  MCP 服务器未响应，正在尝试重启...
  bash ~/.openclaw/skills/nexustrader/nexustrader_daemon.sh restart
  ```
- API Key 无效 → 提示填写 `.keys/.secrets.toml`（路径由 `SKILL_DIR` 下的 `.env` 记录）

---

## 故障排查

```bash
# 查看服务器状态
bash ~/.openclaw/skills/nexustrader/nexustrader_daemon.sh status

# 查看启动日志
bash ~/.openclaw/skills/nexustrader/nexustrader_daemon.sh logs

# 重启服务器
bash ~/.openclaw/skills/nexustrader/nexustrader_daemon.sh restart
```
