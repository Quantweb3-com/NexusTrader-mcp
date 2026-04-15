# 快速上手

## 项目定位

`NexusTrader MCP` 把交易查询和交易执行能力暴露给 AI 客户端。你可以把它理解为：

- `NexusTrader MCP`：当前仓库，负责 AI 接入层与自然语言操作层
- `NexusTrader`：生态关联项目，可作为补充了解

如果你想做可演示、可集成、可扩展的 AI trading workflow，可以额外了解 `NexusTrader`。但运行 `NexusTrader MCP` 并不要求本地同时存在那个仓库。

## 环境要求

- Python `>=3.11`
- `uv`
- 当前项目目录下存在 `.keys/.secrets.toml`

目录建议：

```text
NexusTrader-mcp/
├─ .keys/
│  └─ .secrets.toml
├─ docs/
├─ nexustrader_mcp/
└─ README.md
```

## 初始化

```bash
cd NexusTrader-mcp
uv run nexustrader-mcp setup
```

初始化向导会：

- 生成 `config.yaml`
- 写入 Claude Code、Codex、Cursor 配置
- 在 Linux 上安装 OpenClaw skill
- 自动创建当前项目下的 `.keys/.secrets.toml` 模板文件

## 配置凭证

编辑当前项目目录下的 `.keys/.secrets.toml`：

```toml
[BINANCE.DEMO]
API_KEY = "your_demo_key"
SECRET = "your_demo_secret"
```

建议流程：

1. 先填测试网或 demo key。
2. 先做余额、行情、持仓查询。
3. 最后再测试下单与改单。

## 启动与运维

```bash
uv run nexustrader-mcp start
uv run nexustrader-mcp status
uv run nexustrader-mcp logs
uv run nexustrader-mcp stop
```

默认端口：

- Claude Code / Cursor / OpenClaw: `http://127.0.0.1:18765/sse`
- Codex: `http://127.0.0.1:18765/mcp`

## 常见自然语言用法

- “列出我所有账户余额。”
- “看看 Binance 上 BTC 永续的盘口和资金费率。”
- “列出未成交订单。”
- “把那笔订单撤掉。”

## 商业落地建议

- 对外演示时，把 `README` 当成首页，把 `docs/` 当成交付文档。
- 对内部署时，把 AI 访问权限和实盘 API key 严格隔离。
- 对客户销售时，可以补充介绍 [NexusTrader](https://github.com/Quantweb3-com/NexusTrader) 作为生态关联项目，但不要把它写成当前仓库的强依赖。
