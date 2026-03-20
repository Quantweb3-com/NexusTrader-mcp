# NexusTrader MCP Server

让 AI 直接操控你的加密货币交易账户。

NexusTrader MCP 是一个 [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) 服务器，将 [NexusTrader](https://github.com/Quantweb3-com/NexusTrader) 的账户查询、实时行情和交易功能暴露给 AI 客户端。通过 **stdio** 传输方式在本地运行，支持 **Cursor** 和 **Claude Code**。

### 平台兼容性

| 平台 | Cursor | Claude Code |
|------|--------|-------------|
| **Windows** | ✅ 支持 | ❌ 暂不支持 |
| **Linux** | ✅ 支持 | ✅ 支持 |
| **macOS** | ✅ 支持 | ✅ 支持 |

> **Windows 用户注意**：Claude Code 在 Windows 下启动 MCP 子进程时存在兼容性问题，建议使用 Cursor 或 WSL 环境下的 Claude Code。

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

然后自动询问是否写入 Cursor 和 Claude Code 的配置文件。确认后重启客户端即可使用。

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
        "run", "--python", "3.11",
        "nexustrader-mcp",
        "--config", "/path/to/NexusTrader-mcp/config.yaml"
      ],
      "env": {
        "PYTHONPATH": "",
        "PYTHONHOME": "",
        "CONDA_PREFIX": "",
        "CONDA_DEFAULT_ENV": "",
        "CONDA_SHLVL": "0",
        "UV_PYTHON_PREFERENCE": "only-managed",
        "UV_PYTHON": "cpython-3.11"
      }
    }
  }
}
```

> 将 `/path/to/NexusTrader-mcp` 替换为本项目的实际绝对路径。`env` 部分用于隔离 Anaconda 等外部 Python 环境的干扰。

重启 Cursor 后，在 Agent 模式下即可使用 NexusTrader 工具。

---

## 对接 Claude Code

> ⚠️ **仅支持 Linux / macOS**。Windows 下的 Claude Code 暂不支持，建议 Windows 用户使用 Cursor 或在 WSL 中运行 Claude Code。

### 自动写入

```bash
uv run nexustrader-mcp setup
# 向导最后会询问是否写入 Claude Code 配置，选 Y 即可
```

### 手动配置

编辑 `~/.claude.json`（注意：是用户主目录下的 `.claude.json`，不是 `~/.claude/settings.json`）：

```json
{
  "mcpServers": {
    "nexustrader": {
      "command": "uv",
      "args": [
        "--directory", "/path/to/NexusTrader-mcp",
        "run", "--python", "3.11",
        "nexustrader-mcp",
        "--config", "/path/to/NexusTrader-mcp/config.yaml"
      ],
      "env": {
        "PYTHONPATH": "",
        "PYTHONHOME": "",
        "CONDA_PREFIX": "",
        "CONDA_DEFAULT_ENV": "",
        "CONDA_SHLVL": "0",
        "UV_PYTHON_PREFERENCE": "only-managed",
        "UV_PYTHON": "cpython-3.11"
      }
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

配置完成后，你可以在 Cursor 或 Claude Code 中直接用自然语言让 AI 调用 MCP 工具。

如果你希望 AI 能查询 `get_orderbook` / `get_funding_rate` / `get_mark_price` / `get_index_price` 这类**缓存行情**，请先在 `config.yaml` 中为对应交易对开启预订阅：

```yaml
exchanges:
  binance:
    account_type: USD_M_FUTURE_TESTNET
    symbols:
      - BTCUSDT-PERP.BINANCE
      - ETHUSDT-PERP.BINANCE
    subscribe:
      - bookl1
      - funding_rate
      - mark_price
      - index_price
```

下面是一组尽量覆盖全部功能的对话示例：

### 1. 查看已连接的交易所

> **你**：先告诉我现在 MCP 连上了哪些交易所和账户类型

AI 会调用 `get_exchange_info`。

### 2. 查看可用交易对

> **你**：列出 Binance 可交易的永续合约交易对，先给我前 20 个

AI 会调用 `get_symbols(exchange="binance", instrument_type="linear")`。

### 3. 查询交易规则

> **你**：查看 `BTCUSDT-PERP.BINANCE` 的最小下单数量、价格精度和手续费

AI 会调用 `get_market_info(symbol="BTCUSDT-PERP.BINANCE")`。

### 4. 查看所有账户余额

> **你**：把我当前所有已配置账户的余额都汇总一下

AI 会调用 `get_all_balances`。

### 5. 查看单个账户余额

> **你**：查看我的 Binance `USD_M_FUTURE_TESTNET` 余额

AI 会调用 `get_balance(exchange="binance", account_type="USD_M_FUTURE_TESTNET")`。

### 6. 查看单个持仓

> **你**：我现在 `BTCUSDT-PERP.BINANCE` 有持仓吗

AI 会调用 `get_position(symbol="BTCUSDT-PERP.BINANCE")`。

### 7. 查看全部持仓

> **你**：列出我在 Binance 的全部持仓，并按盈亏排序

AI 会调用 `get_all_positions(exchange="binance")`。

### 8. 查询最新成交价

> **你**：查一下 `ETHUSDT-PERP.BINANCE` 最新价格

AI 会调用 `get_ticker(symbol="ETHUSDT-PERP.BINANCE")`。

### 9. 查询 L1 盘口

> **你**：看一下 `BTCUSDT-PERP.BINANCE` 现在的最优买一卖一和点差

AI 会调用 `get_orderbook(symbol="BTCUSDT-PERP.BINANCE")`。

### 10. 查询历史 K 线

> **你**：拉取 `BTCUSDT-PERP.BINANCE` 最近 200 根 1 小时 K 线，顺便总结一下趋势

AI 会调用 `get_klines(symbol="BTCUSDT-PERP.BINANCE", interval="1h", limit=200)`。

### 11. 查询资金费率、标记价格、指数价格

> **你**：帮我看 `BTCUSDT-PERP.BINANCE` 当前资金费率、标记价格和指数价格

AI 会组合调用：

- `get_funding_rate(symbol="BTCUSDT-PERP.BINANCE")`
- `get_mark_price(symbol="BTCUSDT-PERP.BINANCE")`
- `get_index_price(symbol="BTCUSDT-PERP.BINANCE")`

### 12. 下单

> **你**：在 `BTCUSDT-PERP.BINANCE` 挂一个 0.01 BTC 的限价买单，价格 68000

AI 会调用 `create_order(symbol="BTCUSDT-PERP.BINANCE", side="BUY", type="LIMIT", amount="0.01", price="68000")`。

### 13. 市价减仓

> **你**：把我 `ETHUSDT-PERP.BINANCE` 当前多头市价减仓 25%，只减仓不要开新仓

AI 通常会先调用 `get_position` 确认仓位，再调用 `create_order(..., type="MARKET", reduce_only=true)`。

### 14. 查询当前挂单

> **你**：列出我在 Binance 现在所有未成交挂单

AI 会调用 `get_open_orders(exchange="binance")`。

也可以按交易对查询：

> **你**：查看 `BTCUSDT-PERP.BINANCE` 这个交易对当前有哪些挂单

AI 会调用 `get_open_orders(symbol="BTCUSDT-PERP.BINANCE")`。

### 15. 查询某个订单详情

> **你**：帮我查一下订单 `mcp-xxx-001` 的最新状态

AI 会调用 `get_order(oid="mcp-xxx-001")`。

### 16. 改单

> **你**：把订单 `mcp-xxx-001` 改成 68150，数量改成 0.02

AI 会调用 `modify_order(symbol="BTCUSDT-PERP.BINANCE", oid="mcp-xxx-001", price="68150", amount="0.02")`。

### 17. 撤销单个订单

> **你**：撤掉 `BTCUSDT-PERP.BINANCE` 上的订单 `mcp-xxx-001`

AI 会调用 `cancel_order(symbol="BTCUSDT-PERP.BINANCE", oid="mcp-xxx-001")`。

### 18. 一键撤销某交易对全部挂单

> **你**：把 `BTCUSDT-PERP.BINANCE` 的所有挂单全部撤掉

AI 会调用 `cancel_all_orders(symbol="BTCUSDT-PERP.BINANCE")`。

### 19. 让 AI 自动组合多步调用

> **你**：先检查我在 Binance 合约账户的 USDT 余额，再看 `BTCUSDT-PERP.BINANCE` 的最新价和盘口，如果价格离 68000 很近，就帮我挂一个 0.01 BTC 的 post-only 买单

AI 可能会按顺序组合调用：

- `get_balance`
- `get_ticker`
- `get_orderbook`
- `create_order(type="POST_ONLY", ...)`

也就是说，你通常不需要记住工具名，只要直接描述你的目标即可。

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

1. 确认配置文件已写入（`~/.cursor/mcp.json` 或 `~/.claude.json`）
2. 重启客户端（Cursor 重启 IDE，Claude Code 重启终端）
3. 确认 `uv` 在 PATH 中可用

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
