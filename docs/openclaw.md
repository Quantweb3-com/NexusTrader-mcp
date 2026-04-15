# OpenClaw 使用指南

## OpenClaw 集成包含什么

仓库中的 `openclaw/` 目录提供了完整的 OpenClaw 集成层：

- `SKILL.md`：OpenClaw 对 NexusTrader 的技能说明
- `bridge.py`：OpenClaw 和本地 MCP server 之间的桥接层
- `nexustrader_daemon.sh`：Linux/macOS 下的辅助管理脚本
- `BOOT.md`：启动阶段检查说明

## 推荐安装方式

在 `NexusTrader-mcp` 根目录执行：

```bash
uv run nexustrader-mcp setup
```

如果当前环境是 Linux，向导会询问是否安装 OpenClaw skill，并将其写入：

```text
~/.openclaw/skills/nexustrader/
```

## OpenClaw 的工作方式

OpenClaw 并不直接访问交易所。

它的调用链是：

1. 用户向 OpenClaw 发出自然语言请求。
2. OpenClaw 根据 `SKILL.md` 调用 `bridge.py`。
3. `bridge.py` 连接本机 `NexusTrader MCP` 服务。
4. `NexusTrader MCP` 再调用 NexusTrader 执行查询或交易。

这意味着：

- OpenClaw 的问题，很多时候本质上是本地 MCP 服务没有起来。
- `bridge.py` 能通，通常说明 OpenClaw skill 没问题。
- `bridge.py` 不通，优先查服务状态、端口和凭证。

## 日常操作

### 启动服务

```bash
uv run nexustrader-mcp start
```

### 查看状态

```bash
uv run nexustrader-mcp status
```

### 查看日志

```bash
uv run nexustrader-mcp logs
```

### 直接测试 bridge

```bash
python ~/.openclaw/skills/nexustrader/bridge.py status
python ~/.openclaw/skills/nexustrader/bridge.py list_tools
python ~/.openclaw/skills/nexustrader/bridge.py get_all_balances
```

如果这些命令能跑通，而 OpenClaw UI 中仍不可用，问题通常在 OpenClaw 侧的 skill 读取或会话刷新。

## OpenClaw 复杂问题处理

### 问题 1：OpenClaw 看不到 skill

检查：

1. `~/.openclaw/skills/nexustrader/` 是否存在。
2. 目录下是否包含 `SKILL.md`、`bridge.py`、`.env`。
3. 是否重启过 OpenClaw 或重新加载过 skills。

处理方式：

- 重新执行 `uv run nexustrader-mcp setup`
- 重新安装 OpenClaw skill
- 重启 OpenClaw 进程

### 问题 2：skill 存在，但请求时报 server offline

检查：

```bash
uv run nexustrader-mcp status
```

如果状态不是 `ONLINE`：

- 先执行 `uv run nexustrader-mcp start`
- 再执行 `uv run nexustrader-mcp logs`

重点排查：

- API key 是否有效
- 是否能访问交易所 API
- 端口 `18765` 是否被占用

### 问题 3：OpenClaw 能发请求，但 bridge 超时

常见原因：

- NexusTrader 引擎首次启动较慢
- 交易所网络不可达
- 测试网或实盘凭证填写错误

处理建议：

1. 用 `uv run nexustrader-mcp logs 100` 看最后 100 行日志。
2. 等待 30 到 90 秒后再次测试。
3. 先减少订阅 symbol 数量，缩短初始化时间。
4. 先只连接一个交易所做最小验证。

### 问题 4：OpenClaw 自动启动 daemon 失败

默认情况下，OpenClaw skill 禁用了自动启动。

`.env` 中默认值是：

```text
NEXUSTRADER_NO_AUTOSTART=1
```

这意味着：

- 更安全
- 更适合商业环境
- 更容易定位问题

建议先保持默认，手动启动服务，等联调稳定后再评估是否开启自动启动。

### 问题 5：端口冲突

如果日志显示 `18765` 被占用：

- 停掉已有服务：`uv run nexustrader-mcp stop`
- 或修改 OpenClaw `.env` 中的：
  - `NEXUSTRADER_MCP_PORT`
  - `NEXUSTRADER_MCP_URL`

修改后重启服务和 OpenClaw。

### 问题 6：实盘与测试网切换混乱

建议做法：

- 演示环境始终用 `TESTNET` 或 `DEMO`
- 生产环境单独维护一套 `config.yaml`
- 实盘和测试网不要混用同一套说明文档与会话环境

## 适合交付给用户的操作建议

- 先教用户看 `status`
- 再教用户看 `logs`
- 最后才让用户排查 `.env` 和 `.secrets.toml`

这样支持团队可以快速把问题分成：

- OpenClaw 问题
- MCP 服务问题
- 交易所连接问题
- 凭证问题
