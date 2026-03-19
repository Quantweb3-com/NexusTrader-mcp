# NexusTrader MCP Server

让 AI 直接操控你的加密货币交易账户。

NexusTrader MCP 是一个 [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) 服务器，将 [NexusTrader](https://github.com/Quantweb3-com/NexusTrader) 的账户查询、实时行情和交易功能暴露给 AI 客户端。通过 **stdio** 传输方式在本地运行，支持 **Cursor** 和 **Claude Code**。

## 功能一览

| 类别 | 工具 | 说明 |
|------|------|------|
| **账户** | `get_balance` / `get_all_balances` | 查询单个或所有账户余额 |
| **持仓** | `get_position` / `get_all_positions` | 查询指定交易对或全部持仓 |
| **行情** | `get_ticker` / `get_orderbook` / `get_klines` / `get_funding_rate` / `get_mark_price` / `get_index_price` | 最新价格、盘口、K 线、资金费率等 |
| **交易** | `create_order` / `cancel_order` / `cancel_all_orders` / `modify_order` / `get_open_orders` / `get_order` | 下单、撤单、改单、查询订单 |
| **信息** | `get_exchange_info` / `get_symbols` / `get_market_info` | 交易所状态、可用交易对、合约精度 |

支持交易所：**Binance** / **Bybit** / **OKX** / **Bitget** / **HyperLiquid**

---

## 前置条件

- **Python >= 3.11**
- **[uv](https://docs.astral.sh/uv/)** 包管理器
- **NexusTrader** 源码（与本项目同级目录，即 `../NexusTrader`）
- NexusTrader 的 API 凭证已配置好（`.keys/.secrets.toml`），参考 [NexusTrader 文档](https://github.com/Quantweb3-com/NexusTrader)

目录结构示例：

```
your-workspace/
├── NexusTrader/          # NexusTrader 源码
│   └── .keys/
│       └── .secrets.toml # API 凭证
└── NexusTrader-mcp/      # 本项目
```

---

## 安装

```bash
cd NexusTrader-mcp
uv sync
```

> `uv sync` 会自动创建虚拟环境、安装所有依赖（包括通过本地路径引用的 NexusTrader）。

---

## 快速开始

### 方式一：一键配置（推荐）

运行交互式向导，生成配置文件并自动写入 AI 客户端：

```bash
uv run nexustrader-mcp setup
```

向导会依次询问：

1. 选择交易所（Binance / Bybit / OKX / Bitget / HyperLiquid）
2. 选择账户类型（现货、U 本位合约等）
3. 是否使用测试网
4. 预订阅的交易对（可跳过）
5. 确认凭证来源（默认读取 `.keys/.secrets.toml`）

然后自动询问是否写入 Cursor 和 Claude Code 的配置文件。确认后重启 IDE 即可使用。

### 方式二：手动配置

#### 1. 创建 `config.yaml`

最简配置只需 3 行：

```yaml
exchanges:
  binance:
    account_type: USD_M_FUTURE_TESTNET
```

多交易所示例：

```yaml
exchanges:
  binance:
    account_type: USD_M_FUTURE
  bybit:
    account_type: LINEAR_TESTNET
  okx:
    account_type: DEMO
```

完整配置（可选）：

```yaml
strategy_id: "mcp_agent"    # 默认 nexus_mcp
user_id: "default"           # 默认 mcp_user

exchanges:
  binance:
    account_type: USD_M_FUTURE_TESTNET
    # 可选：预订阅行情
    symbols:
      - "BTCUSDT-PERP.BINANCE"
      - "ETHUSDT-PERP.BINANCE"
    subscribe:
      - bookl1
```

#### 2. 配置 AI 客户端（见下方章节）

---

## 凭证说明

MCP 服务器 **不需要** 你重复配置 API Key。它会自动从 NexusTrader 已有的 `.keys/.secrets.toml` 中读取凭证。

自动推导规则：

| account_type | 推导出的 settings_key |
|---|---|
| 含 `TESTNET` 或 `DEMO` | `{EXCHANGE}.DEMO` |
| 其他 | `{EXCHANGE}.LIVE` |

例如：
- `binance` + `USD_M_FUTURE_TESTNET` → 读取 `.secrets.toml` 中的 `[BINANCE.DEMO]`
- `binance` + `USD_M_FUTURE` → 读取 `[BINANCE.LIVE]`

也可通过环境变量覆盖（如 `BINANCE_API_KEY` / `BINANCE_SECRET`）。

---

## 对接 Cursor

### 自动写入

```bash
uv run nexustrader-mcp setup
# 向导最后会询问是否写入 Cursor 配置，选 Y 即可
```

### 手动配置

编辑 `~/.cursor/mcp.json`：

```json
{
  "mcpServers": {
    "nexustrader": {
      "command": "uv",
      "args": [
        "--directory", "/path/to/NexusTrader-mcp",
        "run", "nexustrader-mcp",
        "--config", "/path/to/NexusTrader-mcp/config.yaml"
      ]
    }
  }
}
```

> 将 `/path/to/NexusTrader-mcp` 替换为本项目的实际绝对路径。

重启 Cursor 后，在 Agent 模式下即可使用 NexusTrader 工具。

---

## 对接 Claude Code

### 自动写入

```bash
uv run nexustrader-mcp setup
# 向导最后会询问是否写入 Claude Code 配置，选 Y 即可
```

### 手动配置

编辑 `~/.claude/settings.json`：

```json
{
  "mcpServers": {
    "nexustrader": {
      "command": "uv",
      "args": [
        "--directory", "/path/to/NexusTrader-mcp",
        "run", "nexustrader-mcp",
        "--config", "/path/to/NexusTrader-mcp/config.yaml"
      ]
    }
  }
}
```

重启 Claude Code 后即可使用。

---

## 支持的 account_type 列表

<details>
<summary>Binance</summary>

| account_type | 说明 |
|---|---|
| `SPOT` | 现货 |
| `SPOT_TESTNET` | 现货测试网 |
| `USD_M_FUTURE` | U 本位合约 |
| `USD_M_FUTURE_TESTNET` | U 本位合约测试网 |
| `COIN_M_FUTURE` | 币本位合约 |
| `COIN_M_FUTURE_TESTNET` | 币本位合约测试网 |

</details>

<details>
<summary>Bybit</summary>

| account_type | 说明 |
|---|---|
| `SPOT` | 现货 |
| `SPOT_TESTNET` | 现货测试网 |
| `LINEAR` | U 本位合约 |
| `LINEAR_TESTNET` | U 本位合约测试网 |
| `INVERSE` | 反向合约 |
| `INVERSE_TESTNET` | 反向合约测试网 |

</details>

<details>
<summary>OKX</summary>

| account_type | 说明 |
|---|---|
| `LIVE` | 实盘 |
| `DEMO` | 模拟盘 |

</details>

<details>
<summary>Bitget</summary>

| account_type | 说明 |
|---|---|
| `SPOT` | 现货 |
| `USDT_FUTURE` | U 本位合约 |

</details>

<details>
<summary>HyperLiquid</summary>

| account_type | 说明 |
|---|---|
| `MAINNET` | 主网 |
| `TESTNET` | 测试网 |

</details>

---

## 交易对格式

NexusTrader 使用统一的交易对格式：

```
{BASE}{QUOTE}-{TYPE}.{EXCHANGE}
```

示例：

| 交易对 | 含义 |
|---|---|
| `BTCUSDT-PERP.BINANCE` | Binance BTC/USDT 永续合约 |
| `ETHUSDT-PERP.BYBIT` | Bybit ETH/USDT 永续合约 |
| `BTCUSDT.BINANCE` | Binance BTC/USDT 现货 |
| `BTC-PERP.HYPERLIQUID` | HyperLiquid BTC 永续合约 |

不确定时可先调用 `get_symbols(exchange="binance")` 查看可用交易对。

---

## CLI 参考

```bash
# 交互式配置 + 写入 AI 客户端
uv run nexustrader-mcp setup

# 只生成 config.yaml，不写入客户端
uv run nexustrader-mcp setup --config-only

# 已有 config.yaml，只写入客户端配置
uv run nexustrader-mcp setup --install-only

# 启动 MCP 服务器（通常由 AI 客户端自动调用）
uv run nexustrader-mcp run

# 指定配置文件启动
uv run nexustrader-mcp run --config path/to/config.yaml

# 使用 MCP Inspector 调试
npx @modelcontextprotocol/inspector uv run nexustrader-mcp
```

---

## AI 使用示例

配置完成后，你可以在 Cursor 或 Claude Code 中这样与 AI 对话：

> **你**：查看我的 Binance 合约账户余额和当前 BTC 持仓

AI 会自动调用 `get_balance` 和 `get_position`，然后回复：

> 您的 Binance 合约账户余额为 $10,523.45（可用 $8,200）。
> 当前持有 0.5 BTC 多头仓位，入场价 $67,450.20，未实现盈亏 +$125.50。

> **你**：挂一个 0.1 BTC 的限价卖单，价格 68000

AI 会调用 `create_order`，然后回复：

> 限价卖单已挂出：0.1 BTC @ $68,000。订单 ID：mcp-xxx-001，状态：已接受。

---

## 安全注意事项

- API 密钥仅在本地读取，不会记录到日志或返回给 AI
- stdio 传输方式意味着只有本地 AI 客户端可以访问
- 交易工具会执行 **真实交易**，请确保你理解 AI 的操作再确认
- 建议先用 **测试网** 验证功能

---

## 常见问题

**Q: 提示找不到 config.yaml？**

运行 `uv run nexustrader-mcp setup` 生成配置，或通过 `--config` 指定路径。

**Q: 凭证读取失败？**

检查 NexusTrader 的 `.keys/.secrets.toml` 是否正确配置，或通过环境变量设置 `BINANCE_API_KEY` 等。

**Q: 引擎启动超时？**

通常是交易所连接问题，检查网络和 API 凭证。测试网用户确认 `account_type` 包含 `TESTNET` 或 `DEMO`。

**Q: Cursor / Claude Code 里看不到 NexusTrader 工具？**

1. 确认配置文件已写入（`~/.cursor/mcp.json` 或 `~/.claude/settings.json`）
2. 重启 IDE
3. 确认 `uv` 在 PATH 中可用

---

## License

MIT
