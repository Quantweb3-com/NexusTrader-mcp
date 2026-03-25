# NexusTrader MCP 状态检查

每次 OpenClaw gateway 启动时，执行以下**只读状态检查**（不自动启动任何进程）：

## 步骤 — 检查 SSE 服务器是否在线

```bash
python3 ~/.openclaw/skills/nexustrader/bridge.py status
```

## 如果返回 ONLINE

正常，无需任何操作。

## 如果返回 OFFLINE

**告知用户**（不要静默启动进程）：

> ⚠️ **NexusTrader MCP 服务器当前未运行。**
>
> 请在终端中手动启动（约需 30–60 秒初始化）：
>
> ```bash
> uv run nexustrader-mcp start
> ```
>
> 启动后重新发送您的请求即可。

## 注意事项

- 本检查仅读取服务器状态，**不执行任何写操作，不启动任何后台进程**
- 服务器由用户手动启动和停止，OpenClaw 不会自动管理其生命周期
- SKILL_DIR = `~/.openclaw/skills/nexustrader`
- SSE URL   = `http://127.0.0.1:18765/sse`
