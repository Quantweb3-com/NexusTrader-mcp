# NexusTrader MCP Server — 设计文档

## 1. 概述

NexusTrader MCP Server 是一个 **Model Context Protocol（模型上下文协议）** 服务器，它封装了 NexusTrader 交易引擎，将其账户/持仓查询、行情数据和交易功能以 MCP **Tools** 和 **Resources** 的形式暴露出去。通过 **stdio** 传输方式在本地运行，兼容 **Claude Code** 和 **Cursor**。

---

## 2. 架构

```
┌──────────────────────────────────────────────────────────────────┐
│  AI 客户端 (Claude Code / Cursor)                                 │
│  ┌────────────────────────────────────────┐                      │
│  │ MCP Client  ←── stdio ──→  MCP Server  │                      │
│  └────────────────────────────────────────┘                      │
└──────────────────────────────────────────────────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    │  NexusTrader MCP       │
                    │  (Python 进程)         │
                    │                        │
                    │  ┌──────────────────┐  │
                    │  │  FastMCP Server   │  │
                    │  │  (stdio 传输)     │  │
                    │  └────────┬─────────┘  │
                    │           │             │
                    │  ┌────────▼─────────┐  │
                    │  │  NexusTrader      │  │
                    │  │  Engine           │  │
                    │  │  ┌─────────────┐  │  │
                    │  │  │ MCPStrategy  │  │  │
                    │  │  │ (被动模式)    │  │  │
                    │  │  └─────────────┘  │  │
                    │  │  ┌─────────────┐  │  │
                    │  │  │ Cache       │  │  │
                    │  │  │ Connectors  │  │  │
                    │  │  │ EMS / OMS   │  │  │
                    │  │  └─────────────┘  │  │
                    │  └──────────────────┘  │
                    └───────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    │  交易所 (WebSocket)     │
                    │  Binance / Bybit / OKX │
                    │  Bitget / HyperLiquid  │
                    └───────────────────────┘
```

### 核心设计决策

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 语言 | Python | NexusTrader 本身是 Python；同进程运行避免 IPC 开销 |
| MCP SDK | `fastmcp`（封装了 `mcp`） | 基于装饰器，自动生成 JSON Schema，生产就绪 |
| 传输方式 | stdio | Claude Code 和 Cursor 本地 MCP 所需 |
| 集成方式 | Engine + MCPStrategy | 复用 NexusTrader 的全部基础设施 |
| 运行时 | asyncio（单事件循环） | FastMCP 和 NexusTrader 都是异步原生 |
| 配置 | 极简 YAML + 自动推导凭证 | 复用 NexusTrader 已有的 `.keys/.secrets.toml`，用户零重复配置 |

### 工作原理

1. 用户运行 `nexustrader-mcp setup` 交互式生成配置并写入 AI 客户端（或手写 3 行 YAML）
2. `nexustrader-mcp` 启动一个带有特殊 `MCPStrategy` 的 NexusTrader `Engine`
3. Engine 连接交易所，订阅行情数据，初始化账户状态
4. FastMCP 服务器在 stdio 上启动，注册所有工具
5. AI 客户端（Claude Code / Cursor）调用 MCP 工具，委托给 MCPStrategy / Cache 处理
6. 响应被序列化为 JSON 并返回给 AI

---

## 3. 项目结构

```
NexusTrader-mcp/
├── pyproject.toml              # 包配置、依赖
├── README.md                   # 使用文档
│
├── nexustrader_mcp/
│   ├── __init__.py
│   ├── __main__.py             # 入口：python -m nexustrader_mcp
│   ├── server.py               # FastMCP 服务器定义与工具注册
│   ├── config.py               # 配置加载与校验
│   ├── engine_manager.py       # NexusTrader Engine 生命周期管理
│   ├── mcp_strategy.py         # MCPStrategy（被动 Strategy 子类）
│   ├── cli.py                  # CLI 命令：setup / run
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── account.py          # 账户与余额工具
│   │   ├── position.py         # 持仓查询工具
│   │   ├── market.py           # 行情数据工具
│   │   ├── trading.py          # 下单 / 撤单工具
│   │   └── info.py             # 交易所信息与合约工具
│   └── serializers.py          # msgspec Struct → dict 转换器
│
└── tests/
    ├── test_config.py
    ├── test_tools_account.py
    ├── test_tools_market.py
    └── test_tools_trading.py
```

---

## 4. 配置（简化设计）

### 4.1 设计原则

原来的方案需要用户同时维护 YAML + .env，步骤繁琐。简化后的核心思路：

1. **直接复用 NexusTrader 已有凭证**：用户使用 NexusTrader 时已经配置好了 `.keys/.secrets.toml`，MCP 直接读取，无需重复配置
2. **最小化配置**：只需填写"用哪个交易所 + 什么账户类型"，其余全部自动推导
3. **提供交互式 `setup` 命令**：一问一答生成配置 + 写入客户端，一条命令搞定
4. **合理默认值**：不填 symbols 则不预订阅行情（按需通过工具拉取即可）

### 4.2 极简配置文件（`config.yaml`）

**最简形式 — 只需 3 行：**

```yaml
exchanges:
  binance:
    account_type: USD_M_FUTURE_TESTNET
```

含义：使用 Binance U 本位合约测试网，凭证自动从 NexusTrader 的 `.keys/.secrets.toml` 中读取。

**多交易所示例：**

```yaml
exchanges:
  binance:
    account_type: USD_M_FUTURE
    # 凭证自动从 .keys/.secrets.toml 读取（settings_key: "BINANCE.LIVE"）
    # 也可以用环境变量覆盖：BINANCE_API_KEY / BINANCE_SECRET
    
  bybit:
    account_type: LINEAR_TESTNET

  okx:
    account_type: DEMO
```

**完整配置（高级用户）：**

```yaml
# 可选全局设置
strategy_id: "mcp_agent"    # 默认 "nexus_mcp"
user_id: "default"           # 默认 "mcp_user"

exchanges:
  binance:
    account_type: USD_M_FUTURE_TESTNET
    
    # 凭证来源（优先级从高到低，全部可省略）：
    # 1. 直接填写
    # api_key: "xxx"
    # secret: "yyy"
    # 2. 环境变量前缀
    # env_prefix: "BINANCE"       → 读取 BINANCE_API_KEY, BINANCE_SECRET
    # 3. Dynaconf settings_key
    # settings_key: "BINANCE.DEMO" → 读取 .keys/.secrets.toml 中的 [BINANCE.DEMO]
    # 4. 全部不填 → 自动推导 settings_key（见下方说明）

    # 可选：启动时预订阅的行情（不填则不预订阅，按需通过工具拉取）
    symbols:
      - "BTCUSDT-PERP.BINANCE"
      - "ETHUSDT-PERP.BINANCE"
    subscribe:
      - bookl1       # 最优买卖价
```

### 4.3 凭证自动推导规则

当用户不显式指定凭证来源时，系统按以下规则自动推导：

```
account_type 含 "TESTNET" / "DEMO" → settings_key = "{EXCHANGE}.DEMO"
account_type 不含                   → settings_key = "{EXCHANGE}.LIVE"

示例：
  binance + USD_M_FUTURE_TESTNET → BasicConfig(settings_key="BINANCE.DEMO", testnet=True)
  binance + USD_M_FUTURE         → BasicConfig(settings_key="BINANCE.LIVE", testnet=False)
  okx     + DEMO                 → BasicConfig(settings_key="OKX.DEMO", testnet=True)
  bybit   + LINEAR               → BasicConfig(settings_key="BYBIT.LIVE", testnet=False)
```

这与 NexusTrader 示例代码中 `settings.BINANCE.DEMO.API_KEY` 的使用方式完全一致。

### 4.4 一条命令完成所有配置（`nexustrader-mcp setup`）

`init` 和 `install` 合为一个 `setup` 命令——生成配置后直接询问是否写入 AI 客户端，用户确认即写入，全程不中断：

```bash
$ uv run nexustrader-mcp setup

🚀 NexusTrader MCP 配置向导
───────────────────────────

[1/5] 选择要连接的交易所（空格选择，回车确认）：
  ◉ Binance
  ◯ Bybit
  ◯ OKX
  ◯ Bitget
  ◯ HyperLiquid

[2/5] Binance 账户类型：
  ◯ SPOT              （现货）
  ◉ USD_M_FUTURE      （U本位合约）
  ◯ COIN_M_FUTURE     （币本位合约）

[3/5] 使用测试网？ (Y/n): Y

[4/5] 预订阅行情的交易对（可跳过，逗号分隔）：
  > BTCUSDT-PERP.BINANCE, ETHUSDT-PERP.BINANCE

[5/5] 凭证来源：
  ◉ 自动读取 .keys/.secrets.toml （推荐，已有 NexusTrader 配置）
  ◯ 使用环境变量
  ◯ 手动输入

✅ 配置已生成：config.yaml

─── 安装到 AI 客户端 ───

? 检测到 Cursor，是否写入 ~/.cursor/mcp.json？ (Y/n): Y
✅ 已写入 Cursor MCP 配置

? 是否写入 Claude Code ~/.claude/settings.json？ (Y/n): Y
✅ 已写入 Claude Code MCP 配置

🎉 全部完成！重启 Cursor / Claude Code 即可使用 NexusTrader MCP。
```

**也支持非交互式用法（CI / 脚本场景）：**

```bash
# 跳过交互，直接用已有 config.yaml 写入客户端配置
uv run nexustrader-mcp setup --install-only

# 只生成 config.yaml，不写入客户端
uv run nexustrader-mcp setup --config-only
```

### 4.5 配置加载优先级

```
命令行参数 --config path/to/config.yaml
    ↓ 未指定
当前目录 ./config.yaml
    ↓ 不存在
~/.nexustrader-mcp/config.yaml
    ↓ 不存在
报错提示运行 `nexustrader-mcp setup`
```

### 4.7 配置内部加载逻辑

```python
# 伪代码
1. 找到并加载 config.yaml
2. 遍历每个交易所：
   a. 从 account_type 判断 testnet 标志
   b. 解析凭证（直接填写 → env_prefix 环境变量 → settings_key → 自动推导 settings_key）
   c. 构建 BasicConfig
   d. 从 account_type 自动构建 PublicConnectorConfig + PrivateConnectorConfig
   e. 如有 symbols + subscribe，构建行情订阅
3. 构建 NexusTrader Config 对象
4. 创建 Engine 并启动
```

---

## 5. MCP 工具设计

### 5.1 账户工具

| 工具名称 | 描述 | 参数 | 返回值 |
|----------|------|------|--------|
| `get_balance` | 获取指定交易所/账户的余额 | `exchange: str`, `account_type: str` | `{balances: {asset: {free, locked}}, total, free, locked}` |
| `get_all_balances` | 获取所有已配置账户的余额 | — | `[{exchange, account_type, balances...}]` |

### 5.2 持仓工具

| 工具名称 | 描述 | 参数 | 返回值 |
|----------|------|------|--------|
| `get_position` | 获取指定交易对的持仓信息 | `symbol: str` | `{symbol, side, signed_amount, entry_price, unrealized_pnl, realized_pnl}` |
| `get_all_positions` | 获取所有持仓，可按交易所过滤 | `exchange?: str` | `[{symbol, side, ...}]` |

### 5.3 行情工具

| 工具名称 | 描述 | 参数 | 返回值 |
|----------|------|------|--------|
| `get_ticker` | 获取指定交易对的最新行情 | `symbol: str` | `{last_price, volume, volume_currency}` |
| `get_all_tickers` | 获取指定账户类型的所有行情 | `exchange: str`, `account_type: str` | `[{symbol, last_price, ...}]` |
| `get_orderbook` | 获取缓存中的最优买卖价（L1） | `symbol: str` | `{bid, ask, bid_size, ask_size, spread, mid}` |
| `get_klines` | 获取历史K线数据 | `symbol: str`, `interval: str`, `limit?: int` | `[{open, high, low, close, volume, timestamp}]` |
| `get_funding_rate` | 获取资金费率 | `symbol: str` | `{rate, next_funding_time}` |
| `get_mark_price` | 获取标记价格 | `symbol: str` | `{price, timestamp}` |
| `get_index_price` | 获取指数价格 | `symbol: str` | `{price, timestamp}` |

### 5.4 交易工具

| 工具名称 | 描述 | 参数 | 返回值 |
|----------|------|------|--------|
| `create_order` | 下单 | `symbol: str`, `side: str`, `type: str`, `amount: str`, `price?: str`, `reduce_only?: bool` | `{oid: str, status: str}` |
| `cancel_order` | 撤单 | `symbol: str`, `oid: str` | `{oid: str, status: str}` |
| `cancel_all_orders` | 撤销指定交易对的所有订单 | `symbol: str` | `{symbol: str, status: str}` |
| `modify_order` | 修改订单 | `symbol: str`, `oid: str`, `price?: str`, `amount?: str` | `{oid: str, status: str}` |
| `get_open_orders` | 获取所有挂单，可按条件过滤 | `symbol?: str`, `exchange?: str` | `[{oid, symbol, side, type, price, amount, filled, status}]` |
| `get_order` | 获取指定订单详情 | `oid: str` | `{oid, symbol, side, type, price, amount, filled, status, ...}` |

### 5.5 信息工具

| 工具名称 | 描述 | 参数 | 返回值 |
|----------|------|------|--------|
| `get_exchange_info` | 获取已配置交易所及其状态 | — | `[{exchange, account_types, connected}]` |
| `get_symbols` | 列出交易所可用交易对 | `exchange: str`, `instrument_type?: str` | `[str]` |
| `get_market_info` | 获取市场信息（精度、限制等） | `symbol: str` | `{precision, limits, ...}` |

---

## 6. 工具实现细节

### 6.1 交易工具安全性

交易工具涉及真实资金，安全措施如下：

1. **确认性描述**：每个交易工具的 docstring 明确声明将执行真实交易
2. **数量验证**：在提交前根据市场的最小/最大限制校验数量
3. **价格验证**：对比当前市场价进行合理性检查（可配置最大偏差）
4. **订单类型约束**：默认使用 `LIMIT` 限价单，防止以不良价格意外执行市价单
5. **日志记录**：所有订单操作均记录完整详情

### 6.2 异步桥接

NexusTrader 的 `create_order`、`cancel_order` 等是同步方法（它们将请求入队到 EMS）。对于需要确认订单状态的 MCP 工具，我们需要异步桥接：

```python
async def create_order_and_wait(self, symbol, side, type, amount, price, timeout=10):
    """下单并等待初始状态更新。"""
    oid = self.strategy.create_order(symbol, side, type, amount, price)
    
    # 等待缓存中的订单状态更新（pending → accepted/filled/failed）
    status = await self._wait_for_order_status(oid, timeout)
    return {"oid": oid, "status": status}
```

### 6.3 数据序列化

NexusTrader 所有数据模型使用 `msgspec.Struct`。MCP 工具返回 JSON 可序列化的 dict：

```python
def serialize_position(pos: Position) -> dict:
    return {
        "symbol": pos.symbol,
        "exchange": pos.exchange.value,
        "side": pos.side.value,
        "signed_amount": str(pos.signed_amount),
        "entry_price": str(pos.entry_price),
        "unrealized_pnl": str(pos.unrealized_pnl),
        "realized_pnl": str(pos.realized_pnl),
    }
```

---

## 7. MCPStrategy 设计

`MCPStrategy` 是一个轻量级的 `Strategy` 子类：
- **不主动交易**（`on_bookl1`、`on_trade` 等回调中没有交易逻辑）
- 在 `on_start()` 中订阅配置文件指定的行情数据流
- 将继承的方法（`create_order`、`cancel_order`、`cache.*`）暴露给 MCP 服务器
- 通过回调跟踪订单状态更新，支持异步桥接

```python
class MCPStrategy(Strategy):
    def __init__(self):
        super().__init__()
        self._order_events: Dict[str, asyncio.Event] = {}
        self._subscriptions = []  # 从配置中填充
    
    def on_start(self):
        """订阅所有配置的行情数据流。"""
        for sub in self._subscriptions:
            match sub["type"]:
                case "bookl1":
                    self.subscribe_bookl1(sub["symbols"])
                case "trade":
                    self.subscribe_trade(sub["symbols"])
                case "kline":
                    self.subscribe_kline(sub["symbols"], sub["interval"])
    
    def on_accepted_order(self, order: Order):
        self._notify_order(order)
    
    def on_filled_order(self, order: Order):
        self._notify_order(order)
    
    def on_failed_order(self, order: Order):
        self._notify_order(order)
    
    # ... 其他订单回调
    
    def _notify_order(self, order: Order):
        if event := self._order_events.get(order.oid):
            event.set()
```

---

## 8. 引擎管理器

`EngineManager` 负责管理 NexusTrader Engine 的生命周期：

```python
class EngineManager:
    """在后台线程中管理 NexusTrader Engine。"""
    
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.strategy: MCPStrategy = None
        self.engine: Engine = None
        self._thread: Thread = None
        self._ready = asyncio.Event()
    
    async def start(self):
        """解析配置，构建 Engine，在后台线程中启动。"""
        yaml_config = load_yaml_config(self.config_path)
        nexus_config = build_nexus_config(yaml_config, self.strategy)
        self.engine = Engine(nexus_config)
        
        self._thread = Thread(target=self.engine.start, daemon=True)
        self._thread.start()
        
        # 等待引擎就绪
        await self._wait_ready()
    
    async def stop(self):
        """优雅关闭引擎。"""
        self.engine.dispose()
```

---

## 9. 客户端集成

### 9.1 一键配置（推荐）

```bash
# 交互式生成配置 + 自动写入 AI 客户端
uv run nexustrader-mcp setup

# 已有 config.yaml，只写入客户端配置
uv run nexustrader-mcp setup --install-only
```

### 9.2 Cursor 手动配置

文件路径：`~/.cursor/mcp.json`

```json
{
  "mcpServers": {
    "nexustrader": {
      "command": "uv",
      "args": [
        "--directory", "/path/to/NexusTrader-mcp",
        "run", "nexustrader-mcp"
      ]
    }
  }
}
```

> 注意：凭证已在 NexusTrader 的 `.keys/.secrets.toml` 中配置，无需在此重复填写。
> 如需通过环境变量覆盖，可添加 `"env": {"BINANCE_API_KEY": "xxx"}` 字段。

### 9.3 Claude Code 手动配置

文件路径：`~/.claude/settings.json`

```json
{
  "mcpServers": {
    "nexustrader": {
      "command": "uv",
      "args": [
        "--directory", "/path/to/NexusTrader-mcp",
        "run", "nexustrader-mcp"
      ]
    }
  }
}
```

### 9.4 命令行使用（用于测试）

```bash
# 直接启动 MCP 服务器
uv run nexustrader-mcp

# 指定配置文件
uv run nexustrader-mcp --config path/to/config.yaml

# 使用 MCP Inspector 调试
npx @modelcontextprotocol/inspector uv run nexustrader-mcp
```

---

## 10. 依赖

```toml
[project]
name = "nexustrader-mcp"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastmcp>=2.0",
    "nexustrader",        # 本地路径依赖
    "pyyaml>=6.0",
    "pydantic>=2.0",      # 用于配置校验
    "click>=8.0",         # CLI 框架（setup 命令）
    "inquirer>=3.0",      # 交互式选择菜单
]

[project.scripts]
nexustrader-mcp = "nexustrader_mcp.cli:main"

[tool.uv.sources]
nexustrader = { path = "../NexusTrader", editable = true }
```

---

## 11. 启动流程

### 首次使用（一次性）

```
1. uv run nexustrader-mcp setup  → 交互式生成 config.yaml + 写入 AI 客户端配置
2. 重启 Cursor / Claude Code，即可使用
```

### 每次运行（AI 客户端自动触发）

```
1. AI 客户端启动 MCP 进程：nexustrader-mcp
   │
2. 按优先级查找 config.yaml（命令行 → 当前目录 → 用户目录）
   │
3. 加载配置，自动推导凭证（.keys/.secrets.toml → 环境变量 → 直接填写）
   │
4. 构建 MCPStrategy + NexusTrader Config
   │  → account_type 自动映射为 BasicConfig + ConnectorConfig
   │  → testnet 标志自动推导
   │
5. 创建 NexusTrader Engine(config)
   │
6. 在守护线程中启动 Engine
   │  → 连接交易所（REST + WebSocket）
   │  → 初始化余额和持仓（OMS）
   │  → 如有预订阅 symbols，订阅行情数据流
   │  → MCPStrategy.on_start() 执行
   │
7. 等待 Engine 就绪信号
   │
8. 向 FastMCP 注册所有 MCP 工具
   │
9. FastMCP.run(transport="stdio")
   │  → 监听来自 AI 客户端的工具调用
```

---

## 12. 错误处理

| 场景 | 处理方式 |
|------|---------|
| 交易所连接失败 | 在工具响应中返回错误，记录详细日志 |
| 无效交易对 | 根据交易所市场信息进行校验，返回友好错误提示 |
| 交易所拒绝订单 | 返回 OMS 中的拒绝原因 |
| 超出频率限制 | NexusTrader 内部处理频率限制 |
| 引擎未就绪 | 工具返回"引擎未就绪，请稍候" |
| 配置校验失败 | 启动时快速失败，给出清晰的错误信息 |
| 找不到配置文件 | 提示运行 `nexustrader-mcp setup` 生成配置 |
| 凭证缺失 | 明确提示从哪里读取失败，建议检查 `.keys/.secrets.toml` 或设置环境变量 |

---

## 13. 日志

- MCP 服务器日志输出到 **stderr**（stdout 保留给 MCP 协议通信）
- NexusTrader Engine 日志使用其内置的 Logger
- 日志级别可通过 config.yaml 或环境变量 `LOG_LEVEL` 配置

---

## 14. 未来扩展

| 功能 | 描述 |
|------|------|
| **Streamable HTTP 传输** | 支持远程访问（多客户端） |
| **MCP Resources** | 将实时行情数据作为 MCP Resources 暴露（实时订阅） |
| **止盈/止损订单** | 将 `create_tp_sl_order` 作为工具暴露 |
| **批量下单** | 将 `create_batch_orders` 作为工具暴露 |
| **策略参数** | 暴露 `param()` 的 get/set，用于运行时调优 |
| **历史数据导出** | 导出 K 线为 CSV/DataFrame 供 AI 分析 |
| **模拟模式** | 通过 MockConnectorConfig 启用模拟交易 |
| **多策略** | 支持多个策略实例 |

---

## 15. 安全考虑

1. **API 密钥**：不记录日志，不在工具响应中返回。通过环境变量或加密配置加载。
2. **仅本地访问**：stdio 传输方式意味着只有本地 AI 客户端可以访问服务器。
3. **不可修改配置**：MCP 工具无法修改服务器配置或重启引擎。
4. **频率限制**：NexusTrader 内置的频率限制器防止 API 滥用。
5. **订单确认**：交易工具返回订单 ID 和状态，便于审计追踪。

---

## 16. AI 交互示例

```
用户："查看我的 Binance 合约账户余额和当前 BTC 持仓"

AI 调用：get_balance(exchange="binance", account_type="USD_M_FUTURE")
→ 返回：{total: "10523.45", free: "8200.00", locked: "2323.45", 
         balances: {USDT: {free: "8200.00", locked: "2323.45"}}}

AI 调用：get_position(symbol="BTCUSDT-PERP.BINANCE")
→ 返回：{symbol: "BTCUSDT-PERP.BINANCE", side: "LONG", 
         signed_amount: "0.5", entry_price: "67450.2", 
         unrealized_pnl: "125.50"}

AI："您的 Binance 合约账户余额为 $10,523.45（可用 $8,200）。
     当前持有 0.5 BTC 多头仓位，入场价 $67,450.20，未实现盈亏 +$125.50。"

用户："挂一个 0.1 BTC 的限价卖单，价格 68000"

AI 调用：create_order(
    symbol="BTCUSDT-PERP.BINANCE",
    side="SELL", type="LIMIT",
    amount="0.1", price="68000"
)
→ 返回：{oid: "mcp-xxx-001", status: "ACCEPTED"}

AI："限价卖单已挂出：0.1 BTC，价格 $68,000。订单 ID：mcp-xxx-001，状态：已接受。"
```
