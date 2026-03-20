#!/usr/bin/env bash
# =============================================================================
# NexusTrader MCP Server — Daemon Manager
# =============================================================================
# 用法:
#   bash nexustrader_daemon.sh start    # 启动后台服务（首次使用时自动调用）
#   bash nexustrader_daemon.sh stop     # 停止服务
#   bash nexustrader_daemon.sh restart  # 重启
#   bash nexustrader_daemon.sh status   # 查看状态
#   bash nexustrader_daemon.sh logs     # 查看日志
#   bash nexustrader_daemon.sh follow   # 实时跟踪日志（Ctrl+C 退出）
# =============================================================================
# 注意：本脚本由 `nexustrader-mcp setup` 自动安装，.env 由其自动生成，
#       无需手动配置。
# =============================================================================

set -euo pipefail

# ── 自动加载 .env（由 setup 命令自动生成，包含所有路径）────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env"
if [[ -f "${ENV_FILE}" ]]; then
    set -a
    # shellcheck source=/dev/null
    source "${ENV_FILE}"
    set +a
fi

# ── 配置（.env 中已预填，此处为兜底默认值）───────────────────────────────────
PROJECT_DIR="${NEXUSTRADER_PROJECT_DIR:-}"
MCP_CONFIG="${NEXUSTRADER_MCP_CONFIG:-}"
MCP_PORT="${NEXUSTRADER_MCP_PORT:-18765}"
MCP_HOST="${NEXUSTRADER_MCP_HOST:-127.0.0.1}"
LOG_DIR="${NEXUSTRADER_LOG_DIR:-${SCRIPT_DIR}/logs}"
PID_FILE="${LOG_DIR}/server.pid"
LOG_FILE="${LOG_DIR}/server.log"
STARTUP_TIMEOUT=90

# ── 颜色输出 ─────────────────────────────────────────────────────────────────
_green()  { printf '\033[0;32m%s\033[0m\n' "$*"; }
_red()    { printf '\033[0;31m%s\033[0m\n' "$*"; }
_yellow() { printf '\033[0;33m%s\033[0m\n' "$*"; }
_blue()   { printf '\033[0;34m%s\033[0m\n' "$*"; }

# ── 检查进程是否存活 ──────────────────────────────────────────────────────────
_is_running() {
    [[ -f "${PID_FILE}" ]] || return 1
    local pid
    pid=$(cat "${PID_FILE}")
    [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null
}

# ── 等待 SSE 端点上线 ─────────────────────────────────────────────────────────
_wait_for_online() {
    local elapsed=0
    _yellow "等待 MCP Server 初始化（最多 ${STARTUP_TIMEOUT} 秒，交易引擎启动较慢属正常）..."
    while [[ ${elapsed} -lt ${STARTUP_TIMEOUT} ]]; do
        # 直接请求 SSE 端点，返回 200 即代表在线
        if curl -sf --max-time 2 "http://${MCP_HOST}:${MCP_PORT}/" >/dev/null 2>&1 \
            || curl -sf --max-time 2 "http://${MCP_HOST}:${MCP_PORT}/sse" >/dev/null 2>&1; then
            return 0
        fi
        sleep 3
        elapsed=$((elapsed + 3))
        printf '.'
    done
    printf '\n'
    return 1
}

# ── start ─────────────────────────────────────────────────────────────────────
cmd_start() {
    if _is_running; then
        local pid
        pid=$(cat "${PID_FILE}")
        _yellow "NexusTrader MCP 服务器已在运行（PID ${pid}）"
        return 0
    fi

    mkdir -p "${LOG_DIR}"

    # 验证 PROJECT_DIR
    if [[ -z "${PROJECT_DIR}" ]]; then
        _red "错误：NEXUSTRADER_PROJECT_DIR 未设置。"
        _red "请运行 uv run nexustrader-mcp setup 重新生成配置。"
        exit 1
    fi

    # 构造启动命令：uv run --directory <project> nexustrader-mcp serve
    local serve_cmd=(
        uv --directory "${PROJECT_DIR}"
        run --python 3.11
        nexustrader-mcp serve
        --host "${MCP_HOST}"
        --port "${MCP_PORT}"
    )
    if [[ -n "${MCP_CONFIG}" && -f "${MCP_CONFIG}" ]]; then
        serve_cmd+=(--config "${MCP_CONFIG}")
    fi

    _blue "启动 NexusTrader MCP Server（SSE 模式）..."
    _blue "项目目录: ${PROJECT_DIR}"
    _blue "监听地址: http://${MCP_HOST}:${MCP_PORT}"
    _blue "日志文件: ${LOG_FILE}"

    # 以后台方式运行，输出到日志文件
    nohup "${serve_cmd[@]}" >> "${LOG_FILE}" 2>&1 &
    local pid=$!
    echo "${pid}" > "${PID_FILE}"

    if _wait_for_online; then
        printf '\n'
        _green "✅ NexusTrader MCP Server 已上线！"
        _green "   SSE URL: http://${MCP_HOST}:${MCP_PORT}/sse"
    else
        printf '\n'
        _red "❌ 服务器在 ${STARTUP_TIMEOUT} 秒内未上线。"
        _red "   查看日志: bash ${SCRIPT_DIR}/nexustrader_daemon.sh logs"
        _red ""
        _red "   最后 20 行日志："
        tail -n 20 "${LOG_FILE}" 2>/dev/null || true
        exit 1
    fi
}

# ── stop ──────────────────────────────────────────────────────────────────────
cmd_stop() {
    if ! _is_running; then
        _yellow "NexusTrader MCP 服务器未在运行。"
        return 0
    fi

    local pid
    pid=$(cat "${PID_FILE}")
    _blue "正在停止服务器（PID ${pid}）..."
    kill "${pid}" 2>/dev/null || true

    local elapsed=0
    while kill -0 "${pid}" 2>/dev/null && [[ ${elapsed} -lt 10 ]]; do
        sleep 1
        elapsed=$((elapsed + 1))
    done

    if kill -0 "${pid}" 2>/dev/null; then
        kill -9 "${pid}" 2>/dev/null || true
    fi

    rm -f "${PID_FILE}"
    _green "✅ 服务器已停止。"
}

# ── restart ───────────────────────────────────────────────────────────────────
cmd_restart() {
    cmd_stop
    sleep 1
    cmd_start
}

# ── status ────────────────────────────────────────────────────────────────────
cmd_status() {
    if _is_running; then
        local pid
        pid=$(cat "${PID_FILE}")
        _green "● 服务器运行中（PID ${pid}）"
        _green "  URL: http://${MCP_HOST}:${MCP_PORT}/sse"
        _green "  日志: ${LOG_FILE}"
    else
        _red "○ 服务器未运行"
        if [[ -f "${LOG_FILE}" ]]; then
            _yellow "  最后日志："
            tail -n 3 "${LOG_FILE}" 2>/dev/null | sed 's/^/  /' || true
        fi
        _yellow "  启动: bash ${SCRIPT_DIR}/nexustrader_daemon.sh start"
    fi
}

# ── logs ──────────────────────────────────────────────────────────────────────
cmd_logs() {
    local lines="${1:-50}"
    if [[ ! -f "${LOG_FILE}" ]]; then
        _yellow "日志文件不存在：${LOG_FILE}"
        return 0
    fi
    _blue "最后 ${lines} 行日志（${LOG_FILE}）："
    tail -n "${lines}" "${LOG_FILE}"
}

# ── follow ────────────────────────────────────────────────────────────────────
cmd_follow() {
    if [[ ! -f "${LOG_FILE}" ]]; then
        _yellow "日志文件不存在，等待服务器启动..."
        while [[ ! -f "${LOG_FILE}" ]]; do sleep 1; done
    fi
    _blue "实时日志（Ctrl+C 退出）："
    tail -f "${LOG_FILE}"
}

# ── 入口 ──────────────────────────────────────────────────────────────────────
COMMAND="${1:-help}"
shift || true

case "${COMMAND}" in
    start)   cmd_start           ;;
    stop)    cmd_stop            ;;
    restart) cmd_restart         ;;
    status)  cmd_status          ;;
    logs)    cmd_logs "${1:-50}" ;;
    follow)  cmd_follow          ;;
    help|--help|-h)
        cat <<'EOF'
NexusTrader MCP Server — 守护进程管理

用法:
  nexustrader_daemon.sh <命令>

命令:
  start     后台启动 MCP 服务器（OpenClaw on_startup 自动调用）
  stop      停止服务器
  restart   重启
  status    查看运行状态
  logs [N]  查看最后 N 行日志（默认 50）
  follow    实时跟踪日志（Ctrl+C 退出）

配置路径（由 nexustrader-mcp setup 自动生成）:
  .env 文件: ~/.openclaw/skills/nexustrader/.env
EOF
        ;;
    *)
        _red "未知命令: ${COMMAND}"
        echo "运行 nexustrader_daemon.sh help 查看帮助"
        exit 1
        ;;
esac
