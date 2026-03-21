#!/usr/bin/env bash
# =============================================================================
# NexusTrader MCP — OpenClaw SSE Service Installer
# =============================================================================
# 安装内容：
#   1. systemd user service  (~/.config/systemd/user/nexustrader-mcp-sse.service)
#   2. OpenClaw BOOT.md      (~/.openclaw/workspace/BOOT.md，追加写入)
#   3. Skill 文件            (~/.openclaw/skills/nexustrader/)
#      - bridge.py（含自愈逻辑）
#      - nexustrader_daemon.sh
#      - SKILL.md
#      - .env（若尚未存在）
# =============================================================================
# 用法:
#   bash openclaw/install.sh
#   bash openclaw/install.sh --uninstall   # 卸载
# =============================================================================

set -euo pipefail

# ── 颜色 ─────────────────────────────────────────────────────────────
_green()  { printf '\033[0;32m%s\033[0m\n' "$*"; }
_red()    { printf '\033[0;31m%s\033[0m\n' "$*"; }
_yellow() { printf '\033[0;33m%s\033[0m\n' "$*"; }
_blue()   { printf '\033[0;34m%s\033[0m\n' "$*"; }
_bold()   { printf '\033[1m%s\033[0m\n' "$*"; }

# ── 路径 ─────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
CONFIG_PATH="${PROJECT_DIR}/config.yaml"

SKILL_DIR="${HOME}/.openclaw/skills/nexustrader"
SYSTEMD_DIR="${HOME}/.config/systemd/user"
SERVICE_NAME="nexustrader-mcp-sse"
SERVICE_FILE="${SYSTEMD_DIR}/${SERVICE_NAME}.service"
OPENCLAW_WORKSPACE="${HOME}/.openclaw/workspace"
BOOT_MD="${OPENCLAW_WORKSPACE}/BOOT.md"
BOOT_MARKER="# NexusTrader MCP 启动检查"   # used to detect existing block

MCP_HOST="127.0.0.1"
MCP_PORT="18765"

# ── 卸载 ─────────────────────────────────────────────────────────────
cmd_uninstall() {
    _blue "卸载 NexusTrader MCP SSE 服务..."

    # Stop & disable systemd service
    if systemctl --user is-active "${SERVICE_NAME}" &>/dev/null; then
        systemctl --user stop "${SERVICE_NAME}"
        _green "  已停止 systemd 服务"
    fi
    if systemctl --user is-enabled "${SERVICE_NAME}" &>/dev/null; then
        systemctl --user disable "${SERVICE_NAME}"
        _green "  已禁用 systemd 服务"
    fi
    rm -f "${SERVICE_FILE}"
    systemctl --user daemon-reload 2>/dev/null || true
    _green "  已删除 ${SERVICE_FILE}"

    # Remove BOOT.md block
    if [[ -f "${BOOT_MD}" ]] && grep -qF "${BOOT_MARKER}" "${BOOT_MD}"; then
        python3 - <<PYEOF
import re, pathlib
p = pathlib.Path("${BOOT_MD}")
txt = p.read_text()
txt = re.sub(r'\n*# NexusTrader MCP 启动检查.*?(?=\n# |\Z)', '', txt, flags=re.DOTALL)
p.write_text(txt.strip() + '\n' if txt.strip() else '')
PYEOF
        _green "  已从 BOOT.md 移除 NexusTrader 启动块"
    fi

    _green "卸载完成。Skill 文件保留在 ${SKILL_DIR}（如需删除请手动操作）"
}

# ── 安装辅助 ──────────────────────────────────────────────────────────

install_skill_files() {
    _blue "[1/4] 安装 Skill 文件..."
    mkdir -p "${SKILL_DIR}/logs"

    for f in bridge.py nexustrader_daemon.sh SKILL.md; do
        src="${SCRIPT_DIR}/${f}"
        if [[ -f "${src}" ]]; then
            cp -f "${src}" "${SKILL_DIR}/${f}"
        else
            _yellow "  警告: 源文件不存在，跳过: ${src}"
        fi
    done
    chmod +x "${SKILL_DIR}/nexustrader_daemon.sh" 2>/dev/null || true

    # Write .env only if not already present (preserve user edits)
    ENV_FILE="${SKILL_DIR}/.env"
    if [[ ! -f "${ENV_FILE}" ]]; then
        cat > "${ENV_FILE}" <<EOF
# NexusTrader MCP — OpenClaw Skill 配置
# 由 install.sh 自动生成，无需手动编辑

NEXUSTRADER_PROJECT_DIR=${PROJECT_DIR}
NEXUSTRADER_MCP_CONFIG=${CONFIG_PATH}
NEXUSTRADER_MCP_PORT=${MCP_PORT}
NEXUSTRADER_MCP_HOST=${MCP_HOST}
NEXUSTRADER_MCP_URL=http://${MCP_HOST}:${MCP_PORT}/sse
NEXUSTRADER_LOG_DIR=${SKILL_DIR}/logs
EOF
        _green "  已写入 ${ENV_FILE}"
    else
        _yellow "  .env 已存在，跳过（保留现有配置）"
    fi

    # Update skills index.json
    INDEX="${HOME}/.openclaw/skills/index.json"
    if command -v python3 &>/dev/null; then
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
        _green "  已更新 skills/index.json"
    fi

    _green "  Skill 文件已安装到 ${SKILL_DIR}"
}

install_systemd_service() {
    _blue "[2/4] 安装 systemd user service..."

    if ! command -v systemctl &>/dev/null; then
        _yellow "  跳过：未检测到 systemctl（非 systemd 系统）"
        return 0
    fi

    mkdir -p "${SYSTEMD_DIR}"

    # Substitute %h with actual HOME in the template
    sed "s|%h|${HOME}|g" "${SCRIPT_DIR}/nexustrader-mcp-sse.service" \
        > "${SERVICE_FILE}"

    systemctl --user daemon-reload
    systemctl --user enable "${SERVICE_NAME}"
    _green "  已安装并启用: ${SERVICE_FILE}"
    _green "  开机后将自动启动（跟随 default.target）"
}

install_boot_md() {
    _blue "[3/4] 更新 OpenClaw BOOT.md..."

    mkdir -p "${OPENCLAW_WORKSPACE}"

    if [[ -f "${BOOT_MD}" ]] && grep -qF "${BOOT_MARKER}" "${BOOT_MD}"; then
        _yellow "  BOOT.md 已包含 NexusTrader 启动块，跳过"
        return 0
    fi

    # Append our block (source BOOT.md from script dir)
    {
        echo ""
        cat "${SCRIPT_DIR}/BOOT.md"
    } >> "${BOOT_MD}"
    _green "  已追加到 ${BOOT_MD}"
}

start_service_now() {
    _blue "[4/4] 立即启动服务..."

    if ! command -v systemctl &>/dev/null; then
        _yellow "  跳过 systemd 启动，尝试 daemon.sh..."
        bash "${SKILL_DIR}/nexustrader_daemon.sh" start || true
        return 0
    fi

    if systemctl --user is-active "${SERVICE_NAME}" &>/dev/null; then
        _yellow "  服务已在运行，跳过启动"
        return 0
    fi

    systemctl --user start "${SERVICE_NAME}" || {
        _yellow "  systemd 启动失败，回退到 daemon.sh..."
        bash "${SKILL_DIR}/nexustrader_daemon.sh" start || true
        return 0
    }

    # Brief wait and status check
    sleep 5
    if systemctl --user is-active "${SERVICE_NAME}" &>/dev/null; then
        _green "  服务已启动（systemd 托管）"
    else
        _yellow "  服务启动中（交易引擎初始化需要 30–90 秒）"
        _yellow "  查看状态: systemctl --user status ${SERVICE_NAME}"
    fi
}

# ── 安装摘要 ──────────────────────────────────────────────────────────
print_summary() {
    echo ""
    _bold "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    _bold " NexusTrader MCP SSE 服务安装完成"
    _bold "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "  SSE URL    : http://${MCP_HOST}:${MCP_PORT}/sse"
    echo "  Skill 目录 : ${SKILL_DIR}"
    echo "  Service    : ${SERVICE_FILE}"
    echo "  BOOT.md    : ${BOOT_MD}"
    echo ""
    echo "常用命令:"
    echo "  systemctl --user status  ${SERVICE_NAME}   # 查看状态"
    echo "  systemctl --user restart ${SERVICE_NAME}   # 重启"
    echo "  journalctl --user -u ${SERVICE_NAME} -f    # 实时日志"
    echo "  python ${SKILL_DIR}/bridge.py status       # 连通性测试"
    echo ""
    echo "卸载:"
    echo "  bash ${SCRIPT_DIR}/install.sh --uninstall"
    echo ""
}

# ── 入口 ─────────────────────────────────────────────────────────────
COMMAND="${1:-install}"

case "${COMMAND}" in
    --uninstall|uninstall)
        cmd_uninstall
        ;;
    install|"")
        _bold "NexusTrader MCP — OpenClaw SSE Service Installer"
        echo ""

        # Pre-flight checks
        if [[ ! -f "${CONFIG_PATH}" ]]; then
            _red "错误: 找不到 config.yaml (${CONFIG_PATH})"
            _red "请先运行: uv run nexustrader-mcp setup"
            exit 1
        fi

        install_skill_files
        install_systemd_service
        install_boot_md
        start_service_now
        print_summary
        ;;
    *)
        echo "用法: bash install.sh [--uninstall]"
        exit 1
        ;;
esac
