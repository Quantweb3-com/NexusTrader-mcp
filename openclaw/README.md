# NexusTrader — OpenClaw Skill

将 NexusTrader MCP 量化交易引擎包装为 **OpenClaw 常驻 Server 模式 Skill**。

---

## 安装（2步，与 MCP 配置体验完全一致）

### 步骤 1：运行 setup 向导

```bash
uv run nexustrader-mcp setup
```

向导会自动完成：
- 生成 `config.yaml`（交易所/账户类型配置）
- 写入 Cursor / Claude Code 的 `mcp.json`
- **安装 OpenClaw Skill** 到 `~/.openclaw/skills/nexustrader/`（自动生成含正确路径的 `.env`）

### 步骤 2：填写 API 凭证

```toml
# 文件：.keys/.secrets.toml（setup 命令已自动创建，直接替换占位符）

[BINANCE.DEMO]
API_KEY = "你的测试网 API Key"
SECRET  = "你的测试网 Secret"

[BINANCE.LIVE]
API_KEY = "你的实盘 API Key"
SECRET  = "你的实盘 Secret"
```

**就这两步！** OpenClaw 首次使用本 Skill 时，服务器会在后台自动启动。

---

## 工作原理

```
用户自然语言
     │
  OpenClaw
     │  读取 SKILL.md 中的指引
     │
  bridge.py  ──HTTP/SSE──►  nexustrader-mcp serve（常驻进程）
  (JSON→Markdown)                  │
                           NexusTrader 交易引擎
                                   │
                     Binance / Bybit / OKX / Bitget / HyperLiquid
```

- **`SKILL.md`** — AI 指引：工具列表 + 自然语言意图识别 + 安全规则
- **`bridge.py`** — 连接常驻 SSE Server，将 JSON 结果格式化为 Markdown 表格
- **`nexustrader_daemon.sh`** — 守护进程管理，OpenClaw `on_startup` 自动调用
- **`.env`** — 由 `setup` 自动生成，包含项目路径、端口等，**无需手动编辑**

---

## 目录结构

安装后：

```
~/.openclaw/skills/nexustrader/
├── SKILL.md                   # OpenClaw 读取：工具定义 + AI 指引
├── bridge.py                  # OpenClaw 工具调用桥接层
├── nexustrader_daemon.sh      # 守护进程管理（自动调用，也可手动）
├── .env                       # ✅ 自动生成，无需手动编辑
└── logs/
    ├── server.log             # 运行日志
    └── server.pid             # 进程 PID
```

---

## 服务器管理命令

以下命令 **Windows / Linux / macOS 均适用**，在项目目录下运行：

```bash
# 启动后台服务器（含进度等待）
uv run nexustrader-mcp start

# 查看是否在线
uv run nexustrader-mcp status

# 查看最后 50 行日志
uv run nexustrader-mcp logs

# 查看最后 100 行日志
uv run nexustrader-mcp logs 100

# 停止
uv run nexustrader-mcp stop

# 重启（修改 config.yaml 后）
uv run nexustrader-mcp stop && uv run nexustrader-mcp start
```

Linux / macOS 用户也可使用 daemon 脚本（功能相同，仅封装上述命令）：

```bash
bash ~/.openclaw/skills/nexustrader/nexustrader_daemon.sh start|stop|status|logs|follow
```

---

## 直接测试 bridge.py

```bash
# 服务器状态
python ~/.openclaw/skills/nexustrader/bridge.py status

# 列出工具
python ~/.openclaw/skills/nexustrader/bridge.py list_tools

# 查询持仓
python ~/.openclaw/skills/nexustrader/bridge.py get_all_positions

# 查询余额
python ~/.openclaw/skills/nexustrader/bridge.py get_all_balances

# 查询行情
python ~/.openclaw/skills/nexustrader/bridge.py get_ticker --symbol=BTCUSDT-PERP.BINANCE
```

---

## 常见问题

**Q: 首次使用需要等多久？**
A: 约 30–60 秒。NexusTrader 引擎启动时需要连接交易所并加载市场数据，属正常现象。

**Q: 如何切换到实盘？**
A: 修改 `config.yaml` 中的 `account_type`（去掉 `_TESTNET` 后缀），确保 `.keys/.secrets.toml` 中 `[EXCHANGE.LIVE]` 填有真实凭证，然后重启服务器。

**Q: 修改了 config.yaml，如何生效？**
A: `bash ~/.openclaw/skills/nexustrader/nexustrader_daemon.sh restart`

**Q: API Key 放在哪？**
A: 项目目录下的 `.keys/.secrets.toml`。OpenClaw Skill 和 MCP 共用同一个文件，只需填写一次。

**Q: 端口冲突怎么办？**
A: 编辑 `~/.openclaw/skills/nexustrader/.env`，修改 `NEXUSTRADER_MCP_PORT` 和 `NEXUSTRADER_MCP_URL`，重启服务器。

---

## 安全提示

- `.keys/.secrets.toml` 已在 `.gitignore` 中，永远不会被提交到版本控制
- 建议先用测试网验证（`account_type` 含 `TESTNET` 或 `DEMO`）
- 下单/撤单操作执行**真实交易**，AI 调用前会强制展示确认信息
- 服务器默认仅监听 `127.0.0.1`，不对外暴露
