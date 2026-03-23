# NexusTrader MCP Server

让 AI 直接操控你的加密货币交易账户。

NexusTrader MCP 是一个 [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) 服务器，将 [NexusTrader](https://github.com/Quantweb3-com/NexusTrader) 的账户查询、实时行情和交易功能暴露给 AI 客户端，在本地运行并同时提供 SSE 与 Streamable HTTP 两种接入方式。

| 平台 | Claude Code | Cursor | Codex | OpenClaw |
|------|:-----------:|:------:|:-----:|:--------:|
| Linux | ✅ | — | ✅ | ✅ |
| Windows | ✅ | ✅ | ✅ | — |

支持交易所：**Binance** / **Bybit** / **OKX** / **Bitget** / **HyperLiquid**

---

## 前置条件

- Python >= 3.11，[uv](https://docs.astral.sh/uv/) 包管理器
- NexusTrader 源码与本项目**同级目录**（`../NexusTrader`），API 凭证已配置（`.keys/.secrets.toml`）

```
your-workspace/
├── NexusTrader/
│   └── .keys/.secrets.toml
└── NexusTrader-mcp/
```

---

## 安装与启动

整体流程：**setup（一次性）→ 配置凭证 → 启动服务器**

### 第一步：运行配置向导

#### Linux

```bash
cd NexusTrader-mcp
uv run nexustrader-mcp setup
```

#### Windows

> **必须使用普通 PowerShell 或 Windows Terminal，不要用 Anaconda Prompt。**
> Conda 环境变量会与 uv 虚拟环境冲突导致启动失败，详见 [Anaconda 用户注意事项](#anaconda-用户注意事项)。

```powershell
cd NexusTrader-mcp
uv run nexustrader-mcp setup
```

`setup` 会自动检测虚拟环境，首次运行时自动执行 `uv sync` 安装所有依赖，无需手动操作。

向导会依次询问：交易所、账户类型、是否测试网、预订阅交易对；随后会分别询问是否安装各 AI 客户端配置：

- **Claude Code**：写入项目内 `.claude/mcp.json`，并安装 `.claude/commands/nexustrader/` 技能
- **Codex**：写入用户级 `~/.codex/config.toml`
- **Cursor（Windows）**：写入用户级 `~/.cursor/mcp.json`
- **OpenClaw（Linux）**：安装 OpenClaw Skill

---

### 第二步：填写 API 凭证

`setup` 完成后，**必须先填写凭证，再启动服务器**。

打开 `.keys/.secrets.toml`，将对应交易所的 `API_KEY` / `SECRET` 替换为真实值：

```toml
[BINANCE.DEMO]
API_KEY = "your_binance_testnet_api_key"   # ← 替换这里
SECRET  = "your_binance_testnet_secret"    # ← 替换这里
```

> 如果文件不存在，`setup` 会从模板自动创建；也可手动复制 `.keys/.secrets.toml.template`。

---

### 第三步：启动服务器

#### Linux（systemd，开机自动启动）

首次安装 systemd 服务（仅需运行一次）：

```bash
bash openclaw/install.sh
```

之后用 systemctl 管理：

```bash
systemctl --user start nexustrader-mcp-sse    # 启动
systemctl --user stop nexustrader-mcp-sse     # 停止
systemctl --user restart nexustrader-mcp-sse  # 重启
systemctl --user status nexustrader-mcp-sse   # 查看状态
```

服务已设置为开机自动启动（`default.target`），无需每次手动启动。

#### Windows（前台运行）

```powershell
uv run nexustrader-mcp serve
```

> **保持该终端窗口开启。** 服务器在前台运行，关闭窗口即停止服务，AI 将断开连接。
> 如需同时执行其他命令，请另开一个终端窗口。

服务器启动后会同时提供两个端点：

- `http://127.0.0.1:18765/sse`：供 **Claude Code / Cursor / OpenClaw**
- `http://127.0.0.1:18765/mcp`：供 **Codex**

---

### 第四步：重启 AI 客户端

服务器启动后，**重启你使用的 AI 客户端**，使其重新加载 MCP 配置并连接到服务器：

- **Claude Code**：退出后重新启动
- **OpenClaw Gateway**：在 OpenClaw 中重新加载或重启 Gateway
- **Cursor**：重启 Cursor 编辑器
- **Codex**：重启 Codex

> 如果客户端已在服务器启动前打开，必须重启才能识别到 NexusTrader 工具。

---

## 常用命令

| 命令 | 说明 |
|------|------|
| `uv run nexustrader-mcp setup` | 交互式配置向导，生成 `config.yaml` 并按提示安装 Claude / Codex / Cursor / OpenClaw 配置（**首次必须运行**） |
| `uv run nexustrader-mcp setup --install-only` | 已有 `config.yaml`，仅重新安装 AI 客户端配置 |
| `uv run nexustrader-mcp setup --config-only` | 仅重新生成 config.yaml，不写入客户端 |
| `uv run nexustrader-mcp serve` | 启动 HTTP MCP 服务器，前台运行，同时提供 `/sse` 与 `/mcp` |
| `uv run nexustrader-mcp serve --config path/to/config.yaml` | 指定配置文件路径启动 |
| `bash openclaw/install.sh` | 安装 systemd user service（**Linux 首次运行**） |
| `systemctl --user start nexustrader-mcp-sse` | 启动服务（**Linux**） |
| `systemctl --user status nexustrader-mcp-sse` | 查看服务状态（**Linux**） |

---

## 功能一览

| 类别 | 工具 |
|------|------|
| 账户 | `get_balance` / `get_all_balances` |
| 持仓 | `get_position` / `get_all_positions` |
| 行情 | `get_ticker` / `get_orderbook` / `get_klines` / `get_funding_rate` / `get_mark_price` / `get_index_price` |
| 交易 | `create_order` / `cancel_order` / `cancel_all_orders` / `modify_order` / `get_open_orders` / `get_order` |
| 信息 | `get_exchange_info` / `get_symbols` / `get_market_info` |

---

## AI 使用示例

配置完成、服务器运行后，在 Cursor、Claude Code 或 Codex 中直接用自然语言操作，无需记住工具名。

<details>
<summary>查看完整示例（19 个场景）</summary>

如需使用 `get_orderbook` / `get_funding_rate` / `get_mark_price` / `get_index_price` 等缓存行情，请先在 `config.yaml` 中开启预订阅：

```yaml
exchanges:
  binance:
    account_type: USD_M_FUTURE_TESTNET
    symbols:
      - BTCUSDT-PERP.BINANCE
    subscribe:
      - bookl1
      - funding_rate
      - mark_price
      - index_price
```

**查询类**

> 先告诉我现在 MCP 连上了哪些交易所和账户类型
> → `get_exchange_info`

> 列出 Binance 可交易的永续合约，先给我前 20 个
> → `get_symbols(exchange="binance", instrument_type="linear")`

> 查看 `BTCUSDT-PERP.BINANCE` 的最小下单量、价格精度和手续费
> → `get_market_info(symbol="BTCUSDT-PERP.BINANCE")`

> 把我所有账户的余额汇总一下
> → `get_all_balances`

> 我现在 `BTCUSDT-PERP.BINANCE` 有持仓吗
> → `get_position(symbol="BTCUSDT-PERP.BINANCE")`

> 列出 Binance 全部持仓，按盈亏排序
> → `get_all_positions(exchange="binance")`

**行情类**

> 查一下 `ETHUSDT-PERP.BINANCE` 最新价格
> → `get_ticker(symbol="ETHUSDT-PERP.BINANCE")`

> 看 `BTCUSDT-PERP.BINANCE` 的最优买一卖一和点差
> → `get_orderbook(symbol="BTCUSDT-PERP.BINANCE")`

> 拉取 `BTCUSDT-PERP.BINANCE` 最近 200 根 1 小时 K 线，总结趋势
> → `get_klines(symbol="BTCUSDT-PERP.BINANCE", interval="1h", limit=200)`

> 帮我看 `BTCUSDT-PERP.BINANCE` 资金费率、标记价格和指数价格
> → 组合调用 `get_funding_rate` / `get_mark_price` / `get_index_price`

**交易类**

> 在 `BTCUSDT-PERP.BINANCE` 挂一个 0.01 BTC 的限价买单，价格 68000
> → `create_order(symbol="BTCUSDT-PERP.BINANCE", side="BUY", type="LIMIT", amount="0.01", price="68000")`

> 把我 `ETHUSDT-PERP.BINANCE` 多头市价减仓 25%，只减仓不开新仓
> → 先 `get_position`，再 `create_order(..., type="MARKET", reduce_only=true)`

> 列出 Binance 所有未成交挂单
> → `get_open_orders(exchange="binance")`

> 帮我查订单 `mcp-xxx-001` 的状态
> → `get_order(oid="mcp-xxx-001")`

> 把订单 `mcp-xxx-001` 改价到 68150，数量改成 0.02
> → `modify_order(..., oid="mcp-xxx-001", price="68150", amount="0.02")`

> 撤掉 `BTCUSDT-PERP.BINANCE` 上的订单 `mcp-xxx-001`
> → `cancel_order(symbol="BTCUSDT-PERP.BINANCE", oid="mcp-xxx-001")`

> 把 `BTCUSDT-PERP.BINANCE` 的所有挂单全撤了
> → `cancel_all_orders(symbol="BTCUSDT-PERP.BINANCE")`

**多步组合**

> 先看 Binance 合约账户的 USDT 余额，再查 `BTCUSDT-PERP.BINANCE` 的最新价和盘口，如果价格离 68000 很近就挂一个 0.01 BTC 的 post-only 买单
> → AI 自动按顺序组合 `get_balance` → `get_ticker` → `get_orderbook` → `create_order(type="POST_ONLY", ...)`

</details>

---

## 交易对格式

```
{BASE}{QUOTE}-{TYPE}.{EXCHANGE}
```

| 示例 | 含义 |
|------|------|
| `BTCUSDT-PERP.BINANCE` | Binance BTC/USDT 永续合约 |
| `ETHUSDT-PERP.BYBIT` | Bybit ETH/USDT 永续合约 |
| `BTCUSDT.BINANCE` | Binance BTC/USDT 现货 |
| `BTC-PERP.HYPERLIQUID` | HyperLiquid BTC 永续合约 |

不确定时可先问 AI：「列出 Binance 可用的永续合约交易对」，AI 会调用 `get_symbols`。

---

## 支持的 account_type

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

## 安全注意事项

- API 密钥仅在本地读取，不会记录到日志或返回给 AI
- HTTP MCP 服务器默认绑定 `127.0.0.1`，只有本机可访问
- 交易工具执行**真实交易**，请确认 AI 的操作后再继续
- 建议先用**测试网**验证功能

---

## 常见问题

**Q: 提示找不到 config.yaml？**

运行 `uv run nexustrader-mcp setup` 生成配置。

**Q: 引擎启动超时？**

通常是网络或凭证问题：检查能否访问交易所 API（可能需代理）、确认 `.keys/.secrets.toml` 正确、确认没有其他进程占用同一 API Key 的连接。

**Q: AI 客户端里看不到 NexusTrader 工具？**

1. 确认 `serve` 终端窗口未关闭
2. 确认 AI 客户端配置了正确的本地 URL（运行 `setup` 可自动写入）：
   - Claude Code / Cursor / OpenClaw：`http://127.0.0.1:18765/sse`
   - Codex：`http://127.0.0.1:18765/mcp`
3. 重启 AI 客户端

**Q: 重新换了交易所或账户类型，如何更新客户端配置？**

重新运行 `uv run nexustrader-mcp setup`，或只更新客户端配置（保留已有 config.yaml）：

```bash
uv run nexustrader-mcp setup --install-only
```

**Q: Windows 下凭证读取失败？**

检查 `.keys/.secrets.toml` 中的 key 格式，或通过环境变量覆盖：

```powershell
$env:BINANCE_API_KEY="xxx"; $env:BINANCE_SECRET="yyy"; uv run nexustrader-mcp serve
```

---

## 凭证说明

MCP 服务器自动从 NexusTrader 的 `.keys/.secrets.toml` 读取凭证，无需重复配置。

| account_type | 读取的 key |
|---|---|
| 含 `TESTNET` 或 `DEMO` | `[{EXCHANGE}.DEMO]` |
| 其他 | `[{EXCHANGE}.LIVE]` |

---

## Anaconda 用户注意事项

<details>
<summary>展开查看</summary>

### 不要在 Anaconda Prompt 中运行 Claude Code

在已激活 Conda 环境的终端中启动 Claude Code，会导致 Conda 的 `PYTHONPATH`、`PYTHONHOME`、`CONDA_PREFIX` 等环境变量污染 uv 虚拟环境，MCP 服务器无法启动。

**正确做法**：使用普通 PowerShell、CMD、Windows Terminal 或 VS Code/Cursor 内置终端，确认 prompt 前无 `(base)` 标识。

如需关闭 Conda 自动激活：

```bash
conda config --set auto_activate_base false
```

### 问题一：`AttributeError: module '_thread' has no attribute 'daemon_threads_allowed'`

Anaconda 将自己的 `Lib` 目录写入了 `PYTHONPATH`，导致 uv 虚拟环境加载了版本不匹配的标准库。

**解决：** 临时清除 `PYTHONPATH`：

```powershell
# PowerShell
$env:PYTHONPATH=""; uv run nexustrader-mcp serve
```

永久修复：在系统环境变量中删除 `PYTHONPATH`（控制面板 → 系统 → 高级系统设置 → 环境变量）。

### 问题二：uv 使用了 Anaconda 的 Python

本项目已包含 `.python-version` 文件，`uv sync` 会自动使用独立管理的 CPython 3.11。如遇问题：

```bash
rm -rf .venv && uv sync
```

### 问题三：Windows 终端 emoji 乱码（`UnicodeEncodeError`）

`cli.py` 启动时已自动切换 UTF-8，如仍遇到：

```powershell
$env:PYTHONUTF8="1"; uv run nexustrader-mcp setup
```

</details>

---

## License

MIT
