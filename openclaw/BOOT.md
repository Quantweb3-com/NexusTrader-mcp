# NexusTrader Boot Check

Run silently on every boot:

`exec ~/.openclaw/skills/nexustrader/bridge.py status`

- Output contains `"online"` → stay silent, reply NO_REPLY
- Any other result (offline / error / file not found) → tell user:
  服务未运行，请执行以下命令启动：
  `bash ~/NexusTrader-mcp/openclaw/install.sh`
  （脚本不会修改系统环境，不会自动填写 API 密钥）
