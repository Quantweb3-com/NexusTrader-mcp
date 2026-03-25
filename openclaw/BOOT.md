# NexusTrader Boot Check

Run silently on every boot:

`exec ~/.openclaw/skills/nexustrader/bridge.py status`

- Output contains `"online"` → stay silent, reply NO_REPLY
- File not found → tell user to install: `git clone https://github.com/Quantweb3-com/NexusTrader-mcp.git` then `bash openclaw/install.sh` then `uv run nexustrader-mcp start`
- Output contains `"offline"` → tell user: `cd NexusTrader-mcp && uv run nexustrader-mcp start`
