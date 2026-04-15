# 故障排查

## 一条最快的排查路径

出现问题时，建议按这个顺序处理：

1. 看服务是否在线：`uv run nexustrader-mcp status`
2. 看最近日志：`uv run nexustrader-mcp logs`
3. 看凭证文件：`.keys/.secrets.toml`
4. 看端口和 URL：`127.0.0.1:18765`
5. 再看客户端本身是否重启或刷新过配置

## 服务启动失败

常见原因：

- `config.yaml` 不存在
- `.keys/.secrets.toml` 未填写
- 网络无法访问交易所 API
- 端口被占用

处理方法：

```bash
uv run nexustrader-mcp setup
uv run nexustrader-mcp start
uv run nexustrader-mcp logs 100
```

## AI 客户端看不到工具

重点检查：

- 服务是否已经启动
- 客户端是否已重启
- 客户端配置是否指向正确 URL

默认 URL：

- SSE: `http://127.0.0.1:18765/sse`
- Codex: `http://127.0.0.1:18765/mcp`

## Windows 下的常见问题

### Conda 环境污染

不要在 `Anaconda Prompt` 中运行。

推荐：

- PowerShell
- Windows Terminal
- VS Code / Cursor 内置终端

如果环境变量污染 Python：

```powershell
$env:PYTHONPATH=""
uv run nexustrader-mcp start
```

### UTF-8 或终端乱码

如果终端不是 UTF-8，部分中文输出可能显示异常。

可尝试：

```powershell
$env:PYTHONUTF8="1"
uv run nexustrader-mcp setup
```

## OpenClaw 专项故障

OpenClaw 复杂问题请优先查看：

- [OpenClaw 使用指南](./openclaw.md)

特别建议先用 `bridge.py` 独立验证：

```bash
python ~/.openclaw/skills/nexustrader/bridge.py status
python ~/.openclaw/skills/nexustrader/bridge.py list_tools
```

## 商业环境建议

- 生产和演示环境分开
- API key 权限最小化
- 文档中明确标注测试网和实盘的区别
- 先交付查询能力，再逐步开放交易能力
