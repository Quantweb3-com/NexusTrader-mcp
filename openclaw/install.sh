#!/usr/bin/env bash
# =============================================================================
# NexusTrader MCP — 一键安装脚本
# =============================================================================
# 执行顺序（每步先检查，已完成则跳过）：
#
#   1. 检查 / 安装 uv
#   2. 同步项目依赖 (uv sync)
#   3. 初始化配置 (nexustrader-mcp setup)  ← 如已有 config.yaml 则跳过
#   4. 安装 OpenClaw Skill 文件
#   5. 注册 BOOT.md 状态检查
#   6. 注册 exec 执行授权
#   7. 注册 TOOLS.md 快捷指令
#   8. 验证安装
#   9. 启动服务器（如未运行）
#
# 用法:
#   bash openclaw/install.sh [--yes] [--uninstall]
#
#   --yes        跳过所有确认提示（uv 安装除外，需网络下载）
#   --uninstall  移除 OpenClaw Skill 相关文件（不删除项目或 config.yaml）
# =============================================================================

set -euo pipefail

# ── 颜色 ──────────────────────────────────────────────────────────────────────
_green()  { printf '\033[0;32m%s\033[0m\n' "$*"; }
_red()    { printf '\033[0;31m%s\033[0m\n' "$*"; }
_yellow() { printf '\033[0;33m%s\033[0m\n' "$*"; }
_blue()   { printf '\033[0;34m%s\033[0m\n' "$*"; }
_bold()   { printf '\033[1m%s\033[0m\n' "$*"; }

# ── 路径 ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
CONFIG_PATH="${PROJECT_DIR}/config.yaml"

SKILL_DIR="${HOME}/.openclaw/skills/nexustrader"
OPENCLAW_WORKSPACE="${HOME}/.openclaw/workspace"
BOOT_MD="${OPENCLAW_WORKSPACE}/BOOT.md"
TOOLS_MD="${OPENCLAW_WORKSPACE}/TOOLS.md"
BOOT_MARKER="# NexusTrader Boot Check"
TOOLS_MARKER="## NexusTrader"

MCP_HOST="127.0.0.1"
MCP_PORT="18765"

# ── 解析参数 ──────────────────────────────────────────────────────────────────
ARG_YES=false
COMMAND="install"
for arg in "$@"; do
    case "${arg}" in
        --yes|-y) ARG_YES=true ;;
        --uninstall|uninstall) COMMAND="uninstall" ;;
        --help|-h) COMMAND="help" ;;
    esac
done

# ── 帮助 ──────────────────────────────────────────────────────────────────────
cmd_help() {
    cat <<EOF
NexusTrader MCP — 一键安装脚本

用法:
  bash openclaw/install.sh [--yes]          完整安装（含 uv、依赖、配置、服务启动）
  bash openclaw/install.sh --uninstall      卸载 OpenClaw Skill
  bash openclaw/install.sh --help           显示帮助

选项:
  --yes    跳过确认提示，非交互模式

说明:
  每步先检查是否已完成，已完成则跳过。
  setup 步骤需要交互式填写 API 密钥，无法跳过。
EOF
}

# ── 确认提示 ──────────────────────────────────────────────────────────────────
confirm() {
    local msg="${1:-继续？[y/N] }"
    if [[ "${ARG_YES}" == "true" ]]; then return 0; fi
    printf "%s" "${msg}"
    read -r reply
    case "${reply}" in
        y|Y|yes|YES) return 0 ;;
        *) _yellow "已取消。"; exit 0 ;;
    esac
}

# ── 步骤 1：检查 / 安装 uv ────────────────────────────────────────────────────
check_uv() {
    _blue "[1/9] 检查 uv..."
    # Add common install locations to PATH
    export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:${PATH}"

    if command -v uv &>/dev/null; then
        _green "  ✓ uv 已安装: $(uv --version)"
        return 0
    fi

    _yellow "  uv 未找到，准备安装..."
    confirm "  安装 uv (https://astral.sh/uv)？[y/N] "

    if command -v curl &>/dev/null; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
    elif command -v wget &>/dev/null; then
        wget -qO- https://astral.sh/uv/install.sh | sh
    else
        _red "  ✗ 未找到 curl 或 wget，无法自动安装 uv"
        _red "  请手动安装: https://docs.astral.sh/uv/getting-started/installation/"
        exit 1
    fi

    # Reload PATH
    export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:${PATH}"

    if command -v uv &>/dev/null; then
        _green "  ✓ uv 安装成功: $(uv --version)"
    else
        _red "  ✗ uv 安装后仍无法找到，请重新打开终端后再运行本脚本"
        exit 1
    fi
}

# ── 步骤 2：同步项目依赖 ───────────────────────────────────────────────────────
check_deps() {
    _blue "[2/9] 检查项目依赖..."
    if [[ -d "${PROJECT_DIR}/.venv" ]]; then
        _green "  ✓ 依赖已同步 (.venv 存在)"
        return 0
    fi
    _yellow "  正在同步依赖 (uv sync)..."
    uv --directory "${PROJECT_DIR}" sync
    _green "  ✓ 依赖同步完成"
}

# ── 步骤 3：初始化配置 ────────────────────────────────────────────────────────
check_setup() {
    _blue "[3/9] 检查配置文件..."
    if [[ -f "${CONFIG_PATH}" ]]; then
        _green "  ✓ config.yaml 已存在，跳过 setup"
        return 0
    fi

    echo ""
    _yellow "  config.yaml 不存在，需要运行初始化配置。"
    echo "  此步骤需要您填写交易所名称和账户类型（不会询问 API 密钥）。"
    echo "  API 密钥单独填写到 ${PROJECT_DIR}/.keys/.secrets.toml"
    echo ""
    confirm "  运行 nexustrader-mcp setup？[y/N] "

    uv --directory "${PROJECT_DIR}" run nexustrader-mcp setup

    if [[ -f "${CONFIG_PATH}" ]]; then
        _green "  ✓ setup 完成，config.yaml 已生成"
    else
        _red "  ✗ setup 未生成 config.yaml，请检查错误并重新运行"
        exit 1
    fi
}

# ── 步骤 4：安装 Skill 文件 ───────────────────────────────────────────────────
install_skill_files() {
    _blue "[4/9] 安装 Skill 文件..."
    mkdir -p "${SKILL_DIR}/logs"

    for f in bridge.py nexustrader_daemon.sh SKILL.md; do
        src="${SCRIPT_DIR}/${f}"
        if [[ -f "${src}" ]]; then
            cp -f "${src}" "${SKILL_DIR}/${f}"
            _green "  ✓ ${SKILL_DIR}/${f}"
        else
            _yellow "  ⚠ 源文件不存在，跳过: ${src}"
        fi
    done
    chmod +x "${SKILL_DIR}/nexustrader_daemon.sh" 2>/dev/null || true
    chmod +x "${SKILL_DIR}/bridge.py" 2>/dev/null || true

    # Write .env only if not already present (preserve user edits)
    ENV_FILE="${SKILL_DIR}/.env"
    if [[ ! -f "${ENV_FILE}" ]]; then
        cat > "${ENV_FILE}" <<EOF
NEXUSTRADER_PROJECT_DIR=${PROJECT_DIR}
NEXUSTRADER_MCP_CONFIG=${CONFIG_PATH}
NEXUSTRADER_MCP_PORT=${MCP_PORT}
NEXUSTRADER_MCP_HOST=${MCP_HOST}
NEXUSTRADER_MCP_URL=http://${MCP_HOST}:${MCP_PORT}/sse
NEXUSTRADER_LOG_DIR=${SKILL_DIR}/logs
EOF
        _green "  ✓ ${ENV_FILE}  (新建)"
    else
        _yellow "  ↷ ${ENV_FILE}  (已存在，跳过)"
    fi

    # Update skills index.json
    INDEX="${HOME}/.openclaw/skills/index.json"
    python3 - <<PYEOF
import json, pathlib, datetime
p = pathlib.Path("${INDEX}")
data = json.loads(p.read_text()) if p.is_file() else {}
skills = data.setdefault("skills", [])
entry = {
    "id": "nexustrader",
    "name": "NexusTrader 量化交易助手",
    "path": "${SKILL_DIR}",
    "skill_file": "${SKILL_DIR}/SKILL.md",
    "installed_at": datetime.datetime.now().isoformat(),
}
idx = next((i for i, s in enumerate(skills) if s.get("id") == "nexustrader"), None)
if idx is not None:
    skills[idx] = entry
else:
    skills.append(entry)
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
PYEOF
    _green "  ✓ ${HOME}/.openclaw/skills/index.json"
}

# ── 步骤 5：注册 BOOT.md ──────────────────────────────────────────────────────
install_boot_md() {
    _blue "[5/9] 注册 BOOT.md..."
    mkdir -p "${OPENCLAW_WORKSPACE}"

    if [[ -f "${BOOT_MD}" ]] && grep -qF "${BOOT_MARKER}" "${BOOT_MD}"; then
        _yellow "  ↷ BOOT.md 已包含 NexusTrader 块，跳过"
        return 0
    fi

    { echo ""; cat "${SCRIPT_DIR}/BOOT.md"; } >> "${BOOT_MD}"
    _green "  ✓ 已追加到 ${BOOT_MD}"
}

# ── 步骤 6：注册 exec 执行授权 ────────────────────────────────────────────────
install_exec_approvals() {
    _blue "[6/9] 注册 exec 执行授权..."
    APPROVALS_FILE="${HOME}/.openclaw/exec-approvals.json"
    if [[ ! -f "${APPROVALS_FILE}" ]]; then
        _yellow "  ↷ exec-approvals.json 不存在，跳过"
        return 0
    fi

    python3 - <<PYEOF
import json, pathlib, uuid
p = pathlib.Path("${APPROVALS_FILE}")
data = json.loads(p.read_text())

defaults = data.setdefault("defaults", {})
defaults.setdefault("security", "allowlist")
defaults.setdefault("ask", "on-miss")
defaults.setdefault("askFallback", "deny")

agents = data.setdefault("agents", {})
main = agents.setdefault("main", {})
main.setdefault("security", "allowlist")
main.setdefault("ask", "on-miss")
main.setdefault("askFallback", "deny")
main["autoAllowSkills"] = True

allowlist = main.setdefault("allowlist", [])
pattern = "~/.openclaw/skills/nexustrader/bridge.py"
if not any(e.get("pattern") == pattern for e in allowlist):
    allowlist.append({"id": str(uuid.uuid4()).upper(), "pattern": pattern})
    print("  Added bridge.py to exec allowlist")
else:
    print("  bridge.py already in exec allowlist")

p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
PYEOF
    _green "  ✓ ${APPROVALS_FILE}"
}

# ── 步骤 7：注册 TOOLS.md 快捷指令 ───────────────────────────────────────────
install_tools_md() {
    _blue "[7/9] 注册 TOOLS.md..."
    mkdir -p "${OPENCLAW_WORKSPACE}"

    if [[ -f "${TOOLS_MD}" ]] && grep -qF "${TOOLS_MARKER}" "${TOOLS_MD}"; then
        _yellow "  ↷ TOOLS.md 已包含 NexusTrader 块，跳过"
        return 0
    fi

    cat >> "${TOOLS_MD}" <<'EOF'

## NexusTrader

When the user asks about crypto balances, positions, prices, or orders — use the **exec** tool to run bridge.py. Do NOT call a tool named "nexustrader".

| Request | exec command |
|---------|--------------|
| all balances | `exec ~/.openclaw/skills/nexustrader/bridge.py get_all_balances` |
| balance for one exchange | `exec ~/.openclaw/skills/nexustrader/bridge.py get_balance --exchange=okx` |
| all positions | `exec ~/.openclaw/skills/nexustrader/bridge.py get_all_positions` |
| position for one symbol | `exec ~/.openclaw/skills/nexustrader/bridge.py get_position --symbol=BTCUSDT-PERP.OKX` |
| ticker price | `exec ~/.openclaw/skills/nexustrader/bridge.py get_ticker --symbol=BTCUSDT-PERP.BINANCE` |
| klines | `exec ~/.openclaw/skills/nexustrader/bridge.py get_klines --symbol=BTCUSDT-PERP.BINANCE --interval=1h --limit=24` |
| open orders | `exec ~/.openclaw/skills/nexustrader/bridge.py get_open_orders --exchange=okx` |
| connected exchanges | `exec ~/.openclaw/skills/nexustrader/bridge.py get_exchange_info` |
| ⚠️ place order | `exec ~/.openclaw/skills/nexustrader/bridge.py create_order --symbol=BTCUSDT-PERP.BINANCE --side=BUY --order_type=MARKET --amount=0.001` |
| ⚠️ cancel order | `exec ~/.openclaw/skills/nexustrader/bridge.py cancel_order --symbol=BTCUSDT-PERP.BINANCE --order_id=123` |

Symbol format: `BTCUSDT-PERP.OKX` / `ETHUSDT-SPOT.BYBIT`. Exchange names lowercase.
For ⚠️ actions, always ask the user to confirm before executing.
If exec fails → tell user: `bash <NexusTrader-mcp dir>/openclaw/install.sh`
EOF
    _green "  ✓ 已追加到 ${TOOLS_MD}"
}

# ── 步骤 8：验证安装 ──────────────────────────────────────────────────────────
verify_install() {
    _blue "[8/9] 验证安装..."
    local ok=true
    for f in bridge.py nexustrader_daemon.sh SKILL.md .env; do
        if [[ -f "${SKILL_DIR}/${f}" ]]; then
            _green "  ✓ ${SKILL_DIR}/${f}"
        else
            _red "  ✗ 缺失: ${SKILL_DIR}/${f}"
            ok=false
        fi
    done
    [[ "${ok}" == "true" ]] || { _red "  部分文件缺失，请重新运行"; exit 1; }
}

# ── 步骤 9：启动服务器 ────────────────────────────────────────────────────────
start_server() {
    _blue "[9/9] 检查并启动服务器..."

    # Check current status
    STATUS=$(python3 "${SKILL_DIR}/bridge.py" status 2>/dev/null \
        | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','offline'))" 2>/dev/null \
        || echo "offline")

    if [[ "${STATUS}" == "online" ]]; then
        _green "  ✓ 服务器已在运行 (${MCP_HOST}:${MCP_PORT})"
        return 0
    fi

    _yellow "  服务器未运行，准备启动..."
    echo "  (初始化需要 30–60 秒，请稍候...)"
    echo ""

    # Start in background, redirect logs
    LOG_FILE="${SKILL_DIR}/logs/server.log"
    mkdir -p "${SKILL_DIR}/logs"
    nohup uv --directory "${PROJECT_DIR}" run nexustrader-mcp start \
        > "${LOG_FILE}" 2>&1 &
    SERVER_PID=$!

    # Wait up to 90s for server to come up
    local waited=0
    while [[ ${waited} -lt 90 ]]; do
        sleep 3
        waited=$((waited + 3))
        STATUS=$(python3 "${SKILL_DIR}/bridge.py" status 2>/dev/null \
            | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','offline'))" 2>/dev/null \
            || echo "offline")
        if [[ "${STATUS}" == "online" ]]; then
            _green "  ✓ 服务器启动成功 (${waited}s)"
            return 0
        fi
        printf "  等待中... %ds\r" "${waited}"
    done

    _yellow "  ⚠ 服务器未能在 90s 内完成启动"
    _yellow "  请查看日志: ${LOG_FILE}"
    _yellow "  或手动启动: uv --directory ${PROJECT_DIR} run nexustrader-mcp start"
}

# ── 卸载 ──────────────────────────────────────────────────────────────────────
cmd_uninstall() {
    _blue "卸载 NexusTrader MCP Skill..."

    # Remove BOOT.md block
    if [[ -f "${BOOT_MD}" ]] && grep -qF "${BOOT_MARKER}" "${BOOT_MD}"; then
        python3 - <<PYEOF
import re, pathlib
p = pathlib.Path("${BOOT_MD}")
txt = p.read_text()
txt = re.sub(r'\n*# NexusTrader Boot Check\b.*?(?=\n# |\Z)', '', txt, flags=re.DOTALL)
p.write_text(txt.strip() + '\n' if txt.strip() else '')
PYEOF
        _green "  已从 BOOT.md 移除"
    fi

    # Remove TOOLS.md block
    if [[ -f "${TOOLS_MD}" ]] && grep -qF "${TOOLS_MARKER}" "${TOOLS_MD}"; then
        python3 - <<PYEOF
import re, pathlib
p = pathlib.Path("${TOOLS_MD}")
txt = p.read_text()
txt = re.sub(r'\n*## NexusTrader\b.*?(?=\n## |\Z)', '', txt, flags=re.DOTALL)
p.write_text(txt.strip() + '\n' if txt.strip() else '')
PYEOF
        _green "  已从 TOOLS.md 移除"
    fi

    # Remove from skills index.json
    INDEX="${HOME}/.openclaw/skills/index.json"
    if [[ -f "${INDEX}" ]]; then
        python3 - <<PYEOF
import json, pathlib
p = pathlib.Path("${INDEX}")
data = json.loads(p.read_text())
data["skills"] = [s for s in data.get("skills", []) if s.get("id") != "nexustrader"]
p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
print("  已从 skills/index.json 移除")
PYEOF
    fi

    # Remove exec allowlist entry
    APPROVALS_FILE="${HOME}/.openclaw/exec-approvals.json"
    if [[ -f "${APPROVALS_FILE}" ]]; then
        python3 - <<PYEOF
import json, pathlib
p = pathlib.Path("${APPROVALS_FILE}")
data = json.loads(p.read_text())
pattern = "~/.openclaw/skills/nexustrader/bridge.py"
main = data.get("agents", {}).get("main", {})
before = len(main.get("allowlist", []))
main["allowlist"] = [e for e in main.get("allowlist", []) if e.get("pattern") != pattern]
if len(main.get("allowlist", [])) < before:
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print("  已从 exec allowlist 移除")
PYEOF
    fi

    _green "卸载完成。"
    _yellow "Skill 文件保留在 ${SKILL_DIR}（如需删除: rm -rf ${SKILL_DIR}）"
    _yellow "config.yaml 和 API 密钥未删除（保留在 ${PROJECT_DIR}）"
}

# ── 安装摘要 ──────────────────────────────────────────────────────────────────
print_summary() {
    echo ""
    _bold "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    _bold " 安装完成！"
    _bold "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "  项目目录  : ${PROJECT_DIR}"
    echo "  Skill 目录: ${SKILL_DIR}"
    echo "  SSE URL   : http://${MCP_HOST}:${MCP_PORT}/sse"
    echo "  API 密钥  : ${PROJECT_DIR}/.keys/.secrets.toml"
    echo ""
    echo "常用命令:"
    echo "  uv --directory ${PROJECT_DIR} run nexustrader-mcp status   # 状态"
    echo "  uv --directory ${PROJECT_DIR} run nexustrader-mcp logs     # 日志"
    echo "  uv --directory ${PROJECT_DIR} run nexustrader-mcp stop     # 停止"
    echo ""
    echo "卸载:"
    echo "  bash ${SCRIPT_DIR}/install.sh --uninstall"
    echo ""
}

# ── 入口 ──────────────────────────────────────────────────────────────────────
case "${COMMAND}" in
    help)
        cmd_help
        ;;
    uninstall)
        cmd_uninstall
        ;;
    install)
        _bold "NexusTrader MCP — 一键安装"
        echo ""
        check_uv
        check_deps
        check_setup
        install_skill_files
        install_boot_md
        install_exec_approvals
        install_tools_md
        verify_install
        start_server
        print_summary
        ;;
    *)
        echo "用法: bash install.sh [--yes] [--uninstall] [--help]"
        exit 1
        ;;
esac
