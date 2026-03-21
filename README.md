# NexusTrader MCP Server

让 AI 直接操控你的加密货币交易账户。

NexusTrader MCP 是一个 [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) 服务器，将 [NexusTrader](https://github.com/Quantweb3-com/NexusTrader) 的账户查询、实时行情和交易功能暴露给 AI 客户端。通过 **SSE (HTTP)** 传输方式在本地运行，支持 **Cursor** 和 **Claude Code**。

> **SSE 模式说明**：服务器作为后台守护进程持续运行，AI 客户端通过 HTTP URL（`http://127.0.0.1:18765/sse`）连接。这比 stdio 模式更稳定，且多个 AI 客户端可共享同一个服务器实例。

### 平台兼容性

| 平台 | Cursor | Claude Code |
|------|--------|-------------|
| **Windows** | ✅ 支持 | ⚠️ 需手动启动服务器 |
| **Linux** | ✅ 支持 | ✅ 支持 |
| **macOS** | ✅ 支持 | ✅ 支持 |

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

### 使用流程概览

```
1. uv run nexustrader-mcp setup     # 配置并安装（只需一次）
2. nexustrader-mcp daemon start     # 每次使用前启动服务器
3. 打开 Cursor / Claude Code        # AI 自动通过 SSE 连接
```

> 服务器需要在 AI 客户端连接前保持运行状态。

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

然后自动询问是否写入 Cursor 和 Claude Code 的配置文件（写入 SSE URL），并提供立即启动服务器的选项。

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

#### 2. 启动 SSE 服务器

```bash
# 后台启动（推荐）
nexustrader-mcp daemon start

# 或前台运行（调试用）
uv run nexustrader-mcp serve --config config.yaml
```

#### 3. 配置 AI 客户端（见下方章节）

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
      "url": "http://127.0.0.1:18765/sse"
    }
  }
}
```

> **使用前必须先启动服务器**：`nexustrader-mcp daemon start`

重启 Cursor 后，在 Agent 模式下即可使用 NexusTrader 工具。

---

## 对接 Claude Code

### 自动写入

```bash
uv run nexustrader-mcp setup
# 向导最后会询问是否写入 Claude Code 配置，选 Y 即可
```

### 手动配置

编辑 `~/.claude.json`（用户主目录下，不是 `~/.claude/settings.json`）：

```json
{
  "mcpServers": {
    "nexustrader": {
      "url": "http://127.0.0.1:18765/sse"
    }
  }
}
```

> **使用前必须先启动服务器**：`nexustrader-mcp daemon start`

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
# 交互式配置 + 写入 AI 客户端（SSE 模式）
uv run nexustrader-mcp setup

# 只生成 config.yaml，不写入客户端
uv run nexustrader-mcp setup --config-only

# 已有 config.yaml，只写入客户端配置
uv run nexustrader-mcp setup --install-only

# ── 守护进程管理 ──

# 后台启动 SSE 服务器
nexustrader-mcp daemon start

# 停止服务器
nexustrader-mcp daemon stop

# 重启服务器
nexustrader-mcp daemon restart

# 查看运行状态
nexustrader-mcp daemon status

# 实时查看日志（Ctrl+C 退出）
nexustrader-mcp daemon logs

# ── 前台运行（调试用）──

# 前台 SSE 模式（日志直接输出到终端）
uv run nexustrader-mcp serve --config path/to/config.yaml

# 前台 stdio 模式（供调试，AI 客户端一般不直接调用此命令）
uv run nexustrader-mcp run --config path/to/config.yaml

# 使用 MCP Inspector 调试
npx @modelcontextprotocol/inspector uv run nexustrader-mcp serve
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

通常是交易所 WebSocket 连接问题。排查步骤：
1. 检查网络是否能访问交易所 API（可能需要代理）
2. 确认 API 凭证正确（`.keys/.secrets.toml`）
3. 确认没有其他进程占用同一 API Key 的 WebSocket 连接
4. 测试网用户确认 `account_type` 包含 `TESTNET` 或 `DEMO`

**Q: Windows 下 Claude Code 无法使用？**

目前 Claude Code 在 Windows 下启动 MCP 子进程存在兼容性问题，暂不支持。Windows 用户请使用 **Cursor**，或在 **WSL (Windows Subsystem for Linux)** 中运行 Claude Code。

**Q: Claude Code 中 MCP 服务器启动报错 / uv 环境冲突？**

请确保你 **没有在 Anaconda Prompt 中启动 Claude Code**。详见下方「Anaconda 用户注意事项」。

**Q: Cursor / Claude Code 里看不到 NexusTrader 工具？**

1. 确认服务器正在运行：`nexustrader-mcp daemon status`
2. 如果未运行，先启动：`nexustrader-mcp daemon start`
3. 确认配置文件已写入 SSE URL（`~/.cursor/mcp.json` 或 `~/.claude.json`），内容应为 `{"url": "http://127.0.0.1:18765/sse"}`
4. 重启客户端（Cursor 重启 IDE，Claude Code 重启终端）

---

## Anaconda 用户注意事项

如果你的系统安装了 Anaconda / Miniconda，运行 `uv run` 时可能遇到以下问题：

### ⚠️ 不要在 Anaconda Prompt 中运行 Claude Code

**这是最常见的问题。** 在 Anaconda Prompt（或任何已激活 Conda 环境的终端）中启动 Claude Code 会导致 Conda 的环境变量（`PYTHONPATH`、`PYTHONHOME`、`CONDA_PREFIX` 等）被继承到 Claude Code 的子进程中，使得 `uv` 创建的虚拟环境与 Conda 环境发生冲突，MCP 服务器无法正常启动。

**正确做法：**
- 使用 **普通的 PowerShell**、**CMD**、**Windows Terminal** 或 **VS Code / Cursor 内置终端** 来启动 Claude Code
- 确保启动终端时 **没有** 自动激活 Conda 环境（检查 prompt 前面是否有 `(base)` 等标识）

**如果你的终端默认会激活 Conda**（prompt 前有 `(base)`），可以先关闭自动激活：

```bash
conda config --set auto_activate_base false
```

然后重新打开终端再启动 Claude Code。

---

### 问题一：`AttributeError: module '_thread' has no attribute 'daemon_threads_allowed'`

**现象：**

```
Could not import runpy module
...
File "H:\ProgramData\Anaconda3\Lib\threading.py", line 36, in <module>
    _daemon_threads_allowed = _thread.daemon_threads_allowed
AttributeError: module '_thread' has no attribute 'daemon_threads_allowed'
```

**原因：** Anaconda 将自己的 `Lib` 目录写入了系统 `PYTHONPATH` 环境变量，导致 uv 创建的虚拟环境在启动时加载了 Anaconda 的标准库（与 venv 的 Python 版本不匹配）。

**解决方法：**

方法 A — 运行时临时清除（快速验证）：

```bash
# Linux / macOS
PYTHONPATH="" uv run nexustrader-mcp setup

# Windows (PowerShell)
$env:PYTHONPATH=""; uv run nexustrader-mcp setup

# Windows (CMD)
set PYTHONPATH= && uv run nexustrader-mcp setup
```

方法 B — 永久修复（推荐）：

在系统/用户环境变量中删除 Anaconda 对 `PYTHONPATH` 的设置。Anaconda 本身不需要 `PYTHONPATH`，这通常是安装时的残留配置。

> Windows 路径：控制面板 → 系统 → 高级系统设置 → 环境变量，找到 `PYTHONPATH` 删除或清空。

---

### 问题二：`uv sync` 使用了 Anaconda 的 Python 而非独立 CPython

**现象：** `uv sync` 成功，但运行时仍报错，且 `.venv/Scripts/python.exe` 指向 Anaconda。

**原因：** 未指定 Python 版本时，uv 可能优先发现系统 PATH 中的 Anaconda Python。

**解决方法：** 在项目根目录固定 Python 版本，强制 uv 使用独立管理的 CPython：

```bash
echo "3.11" > .python-version
rm -rf .venv
uv sync
```

本项目已包含 `.python-version` 文件，`uv sync` 会自动使用 CPython 3.11（uv 自行管理，与 Anaconda 隔离）。

---

### 问题三：Windows 终端 emoji 乱码（`UnicodeEncodeError`）

**现象：**

```
UnicodeEncodeError: 'gbk' codec can't encode character '\u2705'
```

**原因：** Windows 默认终端编码为 GBK，无法显示 `✅` `🎉` 等 emoji。

**解决方法：** 本项目已在 `cli.py` 启动时自动将 stdout/stderr 切换为 UTF-8。如仍遇到此问题，可在运行前设置：

```bash
# PowerShell
$env:PYTHONUTF8="1"; uv run nexustrader-mcp setup

# 或在 Windows Terminal 中将默认编码设为 UTF-8
chcp 65001
```

---

## License

MIT
