#!/usr/bin/env bash
# =============================================================================
# NexusTrader MCP — OpenClaw Skill Installer
# =============================================================================
# 安装内容（仅以下内容，无其他操作）：
#
#   1. Skill 文件     → ~/.openclaw/skills/nexustrader/
#      - bridge.py         HTTP 桥接层
#      - nexustrader_daemon.sh  服务器管理助手
#      - SKILL.md          AI 指引 + 工具定义
#      - .env              路径配置（仅含项目路径/端口，无密钥）
#
#   2. 启动检查规则  → ~/.openclaw/workspace/BOOT.md（追加，可卸载）
#      仅用于检测服务器是否在线，并在离线时提醒用户手动启动。
#      不会自动在后台启动任何进程。
#
#   3. OpenClaw 技能索引 → ~/.openclaw/skills/index.json
#
# 本安装脚本不会：
#   ✗ 安装 systemd / launchd / cron 等系统服务
#   ✗ 修改 shell 配置文件（~/.bashrc 等）
#   ✗ 自动在后台启动任何进程
#   ✗ 读取或写入 API 密钥（密钥保存在您的项目目录，不在 ~/.openclaw）
#
# 用法:
#   bash openclaw/install.sh [--yes] [--uninstall]
#
#   --yes        跳过确认提示，直接安装
#   --uninstall  移除已安装的文件和索引条目
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
BOOT_MARKER="# NexusTrader MCP 状态检查"

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
NexusTrader MCP — OpenClaw Skill Installer

用法:
  bash openclaw/install.sh [--yes]          安装
  bash openclaw/install.sh --uninstall      卸载
  bash openclaw/install.sh --help           显示帮助

选项:
  --yes    跳过确认提示，非交互模式安装

安装说明:
  本脚本仅将 Skill 文件复制到 ~/.openclaw/skills/nexustrader/，
  并在 BOOT.md 中添加服务器状态检查（离线时仅提醒，不自动启动）。
  不安装系统服务，不修改启动项，不读写 API 密钥。
EOF
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
txt = re.sub(r'\n*# NexusTrader MCP 状态检查.*?(?=\n# |\Z)', '', txt, flags=re.DOTALL)
p.write_text(txt.strip() + '\n' if txt.strip() else '')
PYEOF
        _green "  已从 BOOT.md 移除 NexusTrader 检查块"
    fi

    # Remove from index.json
    INDEX="${HOME}/.openclaw/skills/index.json"
    if [[ -f "${INDEX}" ]] && command -v python3 &>/dev/null; then
        python3 - <<PYEOF
import json, pathlib
p = pathlib.Path("${INDEX}")
if p.is_file():
    data = json.loads(p.read_text())
    skills = data.get("skills", [])
    data["skills"] = [s for s in skills if s.get("id") != "nexustrader"]
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print("  已从 skills/index.json 移除条目")
PYEOF
    fi

    _green "卸载完成。"
    _yellow "Skill 文件保留在 ${SKILL_DIR}（如需删除请手动运行: rm -rf ${SKILL_DIR}）"
    echo ""
    echo "如需停止 NexusTrader MCP 服务器:"
    echo "  uv --directory ${PROJECT_DIR} run nexustrader-mcp stop"
}

# ── 安装：显示清单 ─────────────────────────────────────────────────────────────
print_manifest() {
    echo ""
    _bold "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    _bold " NexusTrader MCP — OpenClaw Skill 安装清单"
    _bold "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "本安装脚本将写入以下文件（如已存在会被覆盖或追加，如下注明）："
    echo ""
    echo "  新建/覆盖："
    echo "    ${SKILL_DIR}/bridge.py"
    echo "    ${SKILL_DIR}/nexustrader_daemon.sh"
    echo "    ${SKILL_DIR}/SKILL.md"
    echo "    ${SKILL_DIR}/logs/          (目录)"
    echo ""
    echo "  新建（已存在则跳过，不覆盖）："
    echo "    ${SKILL_DIR}/.env           (路径配置，无 API 密钥)"
    echo ""
    echo "  追加（已存在相同内容则跳过）："
    echo "    ${BOOT_MD}"
    echo "    └─ 追加服务器状态检查规则（离线时提醒用户，不自动启动进程）"
    echo ""
    echo "  更新（JSON，追加或更新条目）："
    echo "    ${HOME}/.openclaw/skills/index.json"
    echo ""
    echo "本安装脚本不会执行以下操作："
    echo "  ✗ 安装 systemd / launchd / cron 任何系统服务"
    echo "  ✗ 修改 ~/.bashrc / ~/.zshrc 等 shell 配置"
    echo "  ✗ 在后台自动启动任何进程"
    echo "  ✗ 读取或写入您的 API 密钥"
    echo "    （密钥始终保存在您的项目目录: ${PROJECT_DIR}/.keys/）"
    echo ""
    echo "安装完成后，启动服务器请运行（您控制何时启动/停止）："
    echo "  uv --directory ${PROJECT_DIR} run nexustrader-mcp start"
    echo ""
    _bold "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# ── 确认提示 ──────────────────────────────────────────────────────────────────
confirm_install() {
    if [[ "${ARG_YES}" == "true" ]]; then
        return 0
    fi
    echo ""
    printf "继续安装？[y/N] "
    read -r reply
    case "${reply}" in
        y|Y|yes|YES) return 0 ;;
        *) _yellow "已取消。"; exit 0 ;;
    esac
}

# ── 安装：Skill 文件 ──────────────────────────────────────────────────────────
install_skill_files() {
    _blue "[1/3] 安装 Skill 文件..."
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

    # Write .env only if not already present (preserve user edits)
    ENV_FILE="${SKILL_DIR}/.env"
    if [[ ! -f "${ENV_FILE}" ]]; then
        cat > "${ENV_FILE}" <<EOF
# NexusTrader MCP — OpenClaw Skill 路径配置
# 由 install.sh 自动生成。此文件仅含路径和端口信息，不含任何 API 密钥。
# API 密钥保存在: ${PROJECT_DIR}/.keys/.secrets.toml（由您自己管理）

NEXUSTRADER_PROJECT_DIR=${PROJECT_DIR}
NEXUSTRADER_MCP_CONFIG=${CONFIG_PATH}
NEXUSTRADER_MCP_PORT=${MCP_PORT}
NEXUSTRADER_MCP_HOST=${MCP_HOST}
NEXUSTRADER_MCP_URL=http://${MCP_HOST}:${MCP_PORT}/sse
NEXUSTRADER_LOG_DIR=${SKILL_DIR}/logs
EOF
        _green "  ✓ ${ENV_FILE}  (新建，仅含路径/端口)"
    else
        _yellow "  ↷ ${ENV_FILE}  (已存在，跳过，保留现有配置)"
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
        _green "  ✓ ${INDEX}"
    fi
}

# ── 安装：BOOT.md 状态检查 ─────────────────────────────────────────────────────
install_boot_md() {
    _blue "[2/3] 注册 BOOT.md 状态检查..."

    mkdir -p "${OPENCLAW_WORKSPACE}"

    if [[ -f "${BOOT_MD}" ]] && grep -qF "${BOOT_MARKER}" "${BOOT_MD}"; then
        _yellow "  ↷ BOOT.md 已包含 NexusTrader 检查块，跳过"
        return 0
    fi

    {
        echo ""
        cat "${SCRIPT_DIR}/BOOT.md"
    } >> "${BOOT_MD}"
    _green "  ✓ 已追加状态检查到 ${BOOT_MD}"
    _green "    (仅离线时提醒用户，不自动启动进程)"
}

# ── 安装：验证 ────────────────────────────────────────────────────────────────
verify_install() {
    _blue "[3/3] 验证安装..."
    local ok=true

    for f in bridge.py nexustrader_daemon.sh SKILL.md .env; do
        if [[ -f "${SKILL_DIR}/${f}" ]]; then
            _green "  ✓ ${SKILL_DIR}/${f}"
        else
            _red "  ✗ 缺失: ${SKILL_DIR}/${f}"
            ok=false
        fi
    done

    if [[ "${ok}" == "true" ]]; then
        _green "  所有文件验证通过"
    else
        _red "  部分文件缺失，请重新运行安装脚本"
        exit 1
    fi
}

# ── 安装摘要 ──────────────────────────────────────────────────────────────────
print_summary() {
    echo ""
    _bold "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    _bold " 安装完成！"
    _bold "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "  Skill 目录  : ${SKILL_DIR}"
    echo "  SSE URL     : http://${MCP_HOST}:${MCP_PORT}/sse"
    echo "  API 密钥    : ${PROJECT_DIR}/.keys/.secrets.toml  ← 由您管理"
    echo ""
    echo "启动服务器（您手动控制）："
    echo ""
    echo "  uv --directory ${PROJECT_DIR} run nexustrader-mcp start"
    echo ""
    echo "其他命令："
    echo "  uv --directory ${PROJECT_DIR} run nexustrader-mcp status   # 状态"
    echo "  uv --directory ${PROJECT_DIR} run nexustrader-mcp logs     # 日志"
    echo "  uv --directory ${PROJECT_DIR} run nexustrader-mcp stop     # 停止"
    echo ""
    echo "连通性测试："
    echo "  python3 ${SKILL_DIR}/bridge.py status"
    echo ""
    echo "卸载："
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
        _bold "NexusTrader MCP — OpenClaw Skill Installer"

        # Pre-flight: config.yaml must exist
        if [[ ! -f "${CONFIG_PATH}" ]]; then
            _red "错误: 找不到 config.yaml (${CONFIG_PATH})"
            _red "请先运行: uv --directory ${PROJECT_DIR} run nexustrader-mcp setup"
            exit 1
        fi

        print_manifest
        confirm_install

        echo ""
        install_skill_files
        install_boot_md
        verify_install
        print_summary
        ;;
    *)
        echo "用法: bash install.sh [--yes] [--uninstall] [--help]"
        exit 1
        ;;
esac
