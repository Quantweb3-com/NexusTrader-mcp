# Release Notes

## v0.1.1 - 2026-04-15

这是一个更适合外部推广与用户交付的文档化版本。

- 重写 `README.md`，从开发说明升级为可商业推广的产品首页。
- 新增 `docs/` 文档体系，适配 Read the Docs 发布。
- 新增 OpenClaw 专项文档，覆盖安装、运行机制、常见复杂问题与处理方法。
- 新增 Read the Docs 发布说明，方便团队把文档站点直接上线。
- 明确 `NexusTrader` 与 `NexusTrader MCP` 的交叉营销关系，方便对外展示完整方案。

## Earlier Work Included In v0.1.1

根据近期提交历史，当前版本已经累计包含以下能力与修复：

- 新增 Codex 支持。
- 新增 OpenClaw 集成与多轮迭代修复。
- 提供 SSE server 与 `/mcp` 兼容入口。
- 增加后台服务管理命令：`start`、`stop`、`status`、`logs`。
- 完成 Windows 兼容性修复。
- 补充部署与测试相关说明。
- 完成交易操作联调验证。

## Upgrade Notes

- 现有用户无需修改核心代码。
- 如果你之前只依赖根目录 `README.md`，现在建议同步使用 `docs/` 目录中的完整文档。
- 如果你要发布到 Read the Docs，请按 `docs/publishing.md` 与 `.readthedocs.yaml` 配置导入。
