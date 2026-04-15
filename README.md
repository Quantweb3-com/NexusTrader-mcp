# NexusTrader MCP

让 AI 直接成为你的交易界面。

`NexusTrader MCP` 是一个面向交易团队、量化开发者与 AI 产品团队的 Model Context Protocol server。它把 `NexusTrader` 的账户、仓位、行情和交易能力安全地暴露给 Claude Code、Cursor、Codex 与 OpenClaw，让你可以直接用自然语言完成查询、分析与执行。

[查看 NexusTrader 主项目](https://github.com/Quantweb3-com/NexusTrader)  
[查看在线文档](https://nexustrader-mcp.readthedocs.io/)  
[查看 OpenClaw 集成说明](./docs/openclaw.md)  
[查看完整发布说明](./CHANGELOG.md)

## 为什么它适合商业推广

- 把交易接口直接接入 AI 工作流，减少人为切换终端、网页和脚本的成本。
- 兼容多交易所与多 AI 客户端，适合做内部交易助手、研究 Copilot、客服演示环境和策略运营后台。
- 本地读取 API 凭证，默认绑定 `127.0.0.1`，更适合机构内部部署与合规隔离。
- 同时提供 `/sse` 与 `/mcp` 两种入口，便于覆盖不同 MCP 客户端生态。

## 核心能力

- 账户查询：余额、全账户余额汇总。
- 仓位查询：单标的仓位、全仓位与持仓扫描。
- 行情查询：ticker、orderbook、K 线、funding rate、mark price、index price。
- 交易执行：下单、撤单、改单、查询未成交订单。
- 交易所信息：symbols、market info、exchange info。

支持交易所：

- Binance
- Bybit
- OKX
- Bitget
- HyperLiquid

支持客户端：

- Claude Code
- Cursor
- Codex
- OpenClaw

## 典型商业场景

- AI 交易助理：让运营、研究员或交易员直接问“我现在有哪些仓位风险”。
- 演示环境：为交易基础设施、量化 SaaS 或 AI Agent 产品提供可视化 Demo。
- 机构内控：让 AI 先完成查询和建议，再由人工确认交易。
- 研究协作：把行情、持仓和订单状态统一带入 Copilot 流程。

如果你正在评估 AI trading stack，可以同时了解生态关联项目 [NexusTrader](https://github.com/Quantweb3-com/NexusTrader)。但就 `NexusTrader MCP` 本身而言，使用和部署并不要求本地同时存在 `NexusTrader` 仓库。

## 快速开始

### 1. 准备项目目录

只需要当前仓库即可，API 凭证放在本项目目录下的 `.keys/.secrets.toml`：

```text
NexusTrader-mcp/
├─ .keys/
│  └─ .secrets.toml
├─ docs/
├─ nexustrader_mcp/
└─ README.md
```

### 2. 安装依赖

要求：

- Python `>=3.11`
- [uv](https://docs.astral.sh/uv/)

### 3. 运行初始化向导

```bash
cd NexusTrader-mcp
uv run nexustrader-mcp setup
```

`setup` 会完成这些工作：

- 生成 `config.yaml`
- 按需写入 Claude Code、Codex、Cursor 配置
- 在 Linux 环境下安装 OpenClaw skill
- 在缺少密钥文件时，从模板生成当前项目下的 `.keys/.secrets.toml`

### 4. 填写 API 凭证

编辑当前项目目录下的 `.keys/.secrets.toml`：

```toml
[BINANCE.DEMO]
API_KEY = "your_api_key"
SECRET = "your_secret"
```

建议先使用测试网或 demo 凭证。

### 5. 启动服务

```bash
uv run nexustrader-mcp start
uv run nexustrader-mcp status
uv run nexustrader-mcp logs
```

默认端点：

- SSE: `http://127.0.0.1:18765/sse`
- Codex MCP: `http://127.0.0.1:18765/mcp`

## 面向用户的自然语言体验

接入后，用户可以直接对 AI 说：

- “列出我所有交易所的余额，并按资产规模排序。”
- “看一下 `BTCUSDT-PERP.BINANCE` 最近 200 根 1 小时 K 线，总结趋势。”
- “检查 Binance 上是否有未成交订单。”
- “如果 BTC 价格接近 68000，就帮我挂一笔 0.01 BTC 的 post-only 买单。”

这类体验尤其适合产品演示、销售 PoC 和内部工作台。

## OpenClaw 用户

OpenClaw 在这个仓库里有单独集成层，包含：

- `openclaw/SKILL.md`
- `openclaw/bridge.py`
- `openclaw/nexustrader_daemon.sh`

建议直接阅读：

- [OpenClaw 安装与使用文档](./docs/openclaw.md)
- [OpenClaw 复杂问题排查](./docs/troubleshooting.md)

## 常用命令

```bash
uv run nexustrader-mcp setup
uv run nexustrader-mcp setup --install-only
uv run nexustrader-mcp start
uv run nexustrader-mcp stop
uv run nexustrader-mcp status
uv run nexustrader-mcp logs
uv run nexustrader-mcp serve
```

## 安全说明

- API 凭证从当前项目目录下的 `.keys/.secrets.toml` 读取，不会写入仓库。
- MCP 服务默认只监听 `127.0.0.1`。
- 下单、撤单、改单会触发真实交易行为。
- 商业环境建议默认启用测试网，验证完成后再切换实盘。

## 文档

- [在线文档站](https://nexustrader-mcp.readthedocs.io/)
- [快速上手](./docs/getting-started.md)
- [OpenClaw 使用指南](./docs/openclaw.md)
- [故障排查](./docs/troubleshooting.md)
- [Read the Docs 发布说明](./docs/publishing.md)
- [Release Notes](./CHANGELOG.md)

## License

MIT
