# 发布到 Read the Docs

## 已准备好的内容

这个仓库现在已经包含一套最小可发布的 Read the Docs 结构：

- `.readthedocs.yaml`
- `docs/conf.py`
- `docs/requirements.txt`
- `docs/index.md`

这意味着你可以直接把当前仓库导入 Read the Docs。

## 用户如何操作

### 1. 推送代码到 GitHub

确保这些文件已经在默认分支上：

- `README.md`
- `CHANGELOG.md`
- `docs/`
- `.readthedocs.yaml`

### 2. 在 Read the Docs 导入仓库

操作路径：

1. 登录 Read the Docs
2. 点击 `Import a Project`
3. 选择 GitHub 仓库 `Quantweb3-com/NexusTrader-mcp`
4. 确认默认分支

### 3. 让 Read the Docs 读取配置

Read the Docs 会自动识别根目录下的 `.readthedocs.yaml`，并按以下方式构建：

- Python 3.11
- `docs/conf.py`
- `docs/requirements.txt`

### 4. 首次构建后检查

重点检查：

- 首页能否打开
- 侧边栏目录是否正常
- Markdown 页面链接是否有效
- 中文是否显示正常

## 推荐给团队的发布流程

### 日常更新

1. 修改根目录 `README.md`
2. 修改 `docs/` 里的详细文档
3. 在 `CHANGELOG.md` 添加本次 release notes
4. 推送到仓库
5. 等待 Read the Docs 自动重建

### 对外推广

建议把链接分成三层：

- GitHub 首页：`README.md`
- 文档站：首页与操作说明
- 上游产品页：[NexusTrader](https://github.com/Quantweb3-com/NexusTrader)

这种结构便于交叉营销：

- `NexusTrader` 负责讲底层交易能力
- `NexusTrader MCP` 负责讲 AI 接入能力

## 常见发布问题

### 构建失败：缺少依赖

先检查 `docs/requirements.txt` 是否包含：

- `sphinx`
- `myst-parser`
- `furo`

### 构建成功但页面为空

通常是 `docs/conf.py` 或 `index.md` 的 `toctree` 配置有误。

### 链接可点但 404

检查：

- 文件名是否和 `toctree` 一致
- 相对链接是否指向存在的页面

### 中文显示异常

优先检查文档文件是否为 UTF-8 编码。
