# NexusTrader MCP 启动检查

每次 OpenClaw gateway 启动时，请静默执行以下步骤（**不要向用户发送任何消息**，除非检测到错误）：

## 步骤 1 — 检查 SSE 服务器是否在线

```bash
python ~/.openclaw/skills/nexustrader/bridge.py status
```

## 步骤 2 — 如果离线，启动守护进程

如果 status 返回 OFFLINE，执行：

```bash
bash ~/.openclaw/skills/nexustrader/nexustrader_daemon.sh start
```

守护进程启动需要 30–90 秒完成交易引擎初始化，请耐心等待脚本返回。

## 步骤 3 — 验证

再次运行 `bridge.py status`，若仍为 OFFLINE，在日志中记录错误但**不要打断用户**：

```bash
bash ~/.openclaw/skills/nexustrader/nexustrader_daemon.sh logs 20
```

## 注意事项

- 若 systemd 服务 `nexustrader-mcp-sse.service` 已托管此进程（推荐），步骤 1 通常直接返回 ONLINE，步骤 2 会被跳过。
- SKILL_DIR = `~/.openclaw/skills/nexustrader`
- SSE URL = `http://127.0.0.1:18765/sse`
