"""CLI 入口：setup / run。"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Optional

import click
import yaml

# Ensure stdout/stderr use UTF-8 on Windows (avoid GBK encoding errors)
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf8"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# ──────────────────────────────────────────────────────
# Account type definitions for the interactive wizard
# ──────────────────────────────────────────────────────

EXCHANGE_CHOICES = ["binance", "bybit", "okx", "bitget", "hyperliquid"]

ACCOUNT_TYPES = {
    "binance": {
        "SPOT": "现货",
        "USD_M_FUTURE": "U本位合约",
        "COIN_M_FUTURE": "币本位合约",
    },
    "bybit": {
        "SPOT": "现货",
        "LINEAR": "U本位合约",
        "INVERSE": "反向合约",
    },
    "okx": {
        "LIVE": "实盘",
    },
    "bitget": {
        "SPOT": "现货",
        "USDT_FUTURE": "U本位合约",
    },
    "hyperliquid": {
        "MAINNET": "主网",
    },
}

TESTNET_SUFFIX = {
    "binance": {"SPOT": "SPOT_TESTNET", "USD_M_FUTURE": "USD_M_FUTURE_TESTNET", "COIN_M_FUTURE": "COIN_M_FUTURE_TESTNET"},
    "bybit": {"SPOT": "SPOT_TESTNET", "LINEAR": "LINEAR_TESTNET", "INVERSE": "INVERSE_TESTNET"},
    "okx": {"LIVE": "DEMO"},
    "bitget": {},
    "hyperliquid": {"MAINNET": "TESTNET"},
}


def _pick(prompt: str, options: list[str], descriptions: list[str] | None = None) -> str:
    """Simple numbered selection (no dependency on inquirer)."""
    click.echo(f"\n{prompt}")
    for i, opt in enumerate(options, 1):
        desc = f"  ({descriptions[i - 1]})" if descriptions else ""
        click.echo(f"  {i}. {opt}{desc}")
    while True:
        raw = click.prompt("输入编号", type=int, default=1)
        if 1 <= raw <= len(options):
            return options[raw - 1]
        click.echo("无效编号，请重新输入")


def _multi_pick(prompt: str, options: list[str]) -> list[str]:
    click.echo(f"\n{prompt}")
    for i, opt in enumerate(options, 1):
        click.echo(f"  {i}. {opt}")
    click.echo("输入编号，用逗号分隔（如 1,3），直接回车跳过")
    raw = click.prompt("", default="", show_default=False)
    if not raw.strip():
        return []
    indices = [int(x.strip()) for x in raw.split(",") if x.strip().isdigit()]
    return [options[i - 1] for i in indices if 1 <= i <= len(options)]


def _generate_mcp_json(project_dir: str, config_path: str) -> dict:
    return {
        "command": "uv",
        "args": [
            "--directory", project_dir,
            "run", "--python", "3.11", "nexustrader-mcp",
            "--config", config_path,
        ],
        "env": {
            "PYTHONPATH": "",
            "PYTHONHOME": "",
            "CONDA_PREFIX": "",
            "CONDA_DEFAULT_ENV": "",
            "CONDA_SHLVL": "0",
            "UV_PYTHON_PREFERENCE": "only-managed",
            "UV_PYTHON": "cpython-3.11",
        },
    }



def _install_openclaw_skill(project_dir: str, skill_dir: Path, config_path: str) -> None:
    """将 OpenClaw Skill 文件安装到 ~/.openclaw/skills/nexustrader/。"""
    import datetime

    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "logs").mkdir(exist_ok=True)

    openclaw_src = Path(project_dir) / "openclaw"
    for fname in ["SKILL.md", "bridge.py", "nexustrader_daemon.sh"]:
        src = openclaw_src / fname
        if src.is_file():
            shutil.copy2(src, skill_dir / fname)

    # Make daemon script executable (Linux/macOS only; silently skip on Windows)
    daemon_sh = skill_dir / "nexustrader_daemon.sh"
    if daemon_sh.is_file():
        try:
            daemon_sh.chmod(0o755)
        except OSError:
            pass

    # Auto-generate .env with all paths pre-filled — user never needs to edit this
    env_content = (
        "# NexusTrader MCP — OpenClaw Skill 配置\n"
        "# 由 nexustrader-mcp setup 自动生成，无需手动编辑\n\n"
        f"NEXUSTRADER_PROJECT_DIR={project_dir}\n"
        f"NEXUSTRADER_MCP_CONFIG={config_path}\n"
        "NEXUSTRADER_MCP_PORT=18765\n"
        "NEXUSTRADER_MCP_HOST=127.0.0.1\n"
        "NEXUSTRADER_MCP_URL=http://127.0.0.1:18765/sse\n"
        f"NEXUSTRADER_LOG_DIR={skill_dir / 'logs'}\n"
    )
    (skill_dir / ".env").write_text(env_content, encoding="utf-8")

    # Register in ~/.openclaw/skills/index.json
    index_path = skill_dir.parent / "index.json"
    index_data: dict = {}
    if index_path.is_file():
        try:
            index_data = json.loads(index_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            index_data = {}
    skills = index_data.setdefault("skills", [])
    entry = {
        "id": "nexustrader",
        "name": "NexusTrader 量化交易助手",
        "path": str(skill_dir),
        "skill_file": str(skill_dir / "SKILL.md"),
        "installed_at": datetime.datetime.now().isoformat(),
    }
    existing_idx = next((i for i, s in enumerate(skills) if s.get("id") == "nexustrader"), None)
    if existing_idx is not None:
        skills[existing_idx] = entry
    else:
        skills.append(entry)
    index_path.write_text(json.dumps(index_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _install_skills(project_dir: str, target_dir: Path) -> list[str]:
    """Copy skills/*.md to target_dir/nexustrader/, return list of installed skill names."""
    skills_src = Path(project_dir) / "skills"
    if not skills_src.is_dir():
        return []
    dest = target_dir / "nexustrader"
    dest.mkdir(parents=True, exist_ok=True)
    installed = []
    for skill_file in sorted(skills_src.glob("*.md")):
        shutil.copy2(skill_file, dest / skill_file.name)
        installed.append(skill_file.stem)
    return installed


def _write_mcp_config(filepath: Path, server_entry: dict):
    """Merge nexustrader entry into an existing MCP JSON config file."""
    data = {}
    if filepath.is_file():
        try:
            data = json.loads(filepath.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}

    servers = data.setdefault("mcpServers", {})
    servers["nexustrader"] = server_entry
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")



# ──────────────────────────────────────────────────────
# OpenClaw daemon helpers (cross-platform start/stop/status)
# ──────────────────────────────────────────────────────

def _oc_skill_dir() -> Path:
    return Path.home() / ".openclaw" / "skills" / "nexustrader"


def _oc_pid_file() -> Path:
    return _oc_skill_dir() / "logs" / "server.pid"


def _oc_log_file() -> Path:
    return _oc_skill_dir() / "logs" / "server.log"


def _oc_load_env() -> dict:
    """Parse ~/.openclaw/skills/nexustrader/.env into a dict."""
    env_file = _oc_skill_dir() / ".env"
    result: dict = {}
    if not env_file.is_file():
        return result
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        result[key.strip()] = val.strip().strip("'\"")
    return result


def _oc_is_running() -> tuple[bool, int]:
    """Return (is_running, pid). pid=0 when not running."""
    pid_file = _oc_pid_file()
    if not pid_file.is_file():
        return False, 0
    try:
        pid = int(pid_file.read_text(encoding="utf-8").strip())
    except (ValueError, OSError):
        return False, 0
    try:
        os.kill(pid, 0)   # signal 0: existence check only
        return True, pid
    except OSError:
        return False, 0


def _oc_http_ok(host: str, port: int) -> bool:
    """Return True if the SSE server is responding."""
    for path in ("/", "/sse"):
        try:
            with urllib.request.urlopen(
                f"http://{host}:{port}{path}", timeout=2
            ) as r:
                if r.status < 500:
                    return True
        except Exception:
            pass
    return False


def _oc_launch(cmd: list[str], log_file: Path) -> int:
    """Start a detached background process. Returns PID."""
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_fh = open(log_file, "a", encoding="utf-8")  # kept open by child
    kwargs: dict = dict(stdout=log_fh, stderr=log_fh, stdin=subprocess.DEVNULL)
    if sys.platform == "win32":
        kwargs["creationflags"] = (
            subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        )
    else:
        kwargs["start_new_session"] = True
    proc = subprocess.Popen(cmd, **kwargs)
    return proc.pid


def _oc_kill(pid: int) -> None:
    """Terminate a process cross-platform."""
    if sys.platform == "win32":
        subprocess.call(
            ["taskkill", "/F", "/PID", str(pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        for sig in (15, 9):   # SIGTERM then SIGKILL
            try:
                os.kill(pid, sig)
            except OSError:
                break
            time.sleep(2)
            try:
                os.kill(pid, 0)
            except OSError:
                break   # process gone


# ──────────────────────────────────────────────────────
# CLI commands
# ──────────────────────────────────────────────────────

@click.group()
def main():
    """NexusTrader MCP Server — 让 AI 操控你的交易账户。"""
    pass


@main.command()
@click.option("--config-only", is_flag=True, help="只生成 config.yaml，不写入客户端配置")
@click.option("--install-only", is_flag=True, help="跳过交互，直接用已有 config.yaml 写入客户端配置")
def setup(config_only: bool, install_only: bool):
    """交互式配置 + 一键安装到 AI 客户端。"""
    project_dir = str(Path(__file__).resolve().parent.parent)
    config_path = os.path.join(project_dir, "config.yaml")

    if not install_only:
        click.echo("\n🚀 NexusTrader MCP 配置向导")
        click.echo("─" * 35)

        # 1. Select exchanges
        exchanges = _multi_pick(
            "[1/5] 选择要连接的交易所（输入编号，逗号分隔）：",
            EXCHANGE_CHOICES,
        )
        if not exchanges:
            click.echo("未选择任何交易所，退出。")
            return

        exchange_configs = {}
        for ex in exchanges:
            # 2. Account type
            at_options = list(ACCOUNT_TYPES.get(ex, {}).keys())
            at_descs = list(ACCOUNT_TYPES.get(ex, {}).values())
            if not at_options:
                click.echo(f"  {ex}: 使用默认账户类型")
                at = list(ACCOUNT_TYPES.get(ex, {"DEFAULT": ""}).keys())[0]
            else:
                at = _pick(f"[2/5] {ex} 账户类型：", at_options, at_descs)

            # 3. Testnet
            testnet_map = TESTNET_SUFFIX.get(ex, {})
            if at in testnet_map:
                use_testnet = click.confirm(f"[3/5] {ex} 使用测试网？", default=True)
                if use_testnet:
                    at = testnet_map[at]
            else:
                click.echo(f"  {ex}: 该账户类型不支持测试网")

            # 4. Symbols
            raw_symbols = click.prompt(
                f"[4/5] {ex} 预订阅的交易对（逗号分隔，直接回车跳过）",
                default="",
                show_default=False,
            )
            symbols = [s.strip() for s in raw_symbols.split(",") if s.strip()]

            cfg = {"account_type": at.lower()}
            if symbols:
                cfg["symbols"] = symbols
                cfg["subscribe"] = ["bookl1"]

            exchange_configs[ex] = cfg

        # 5. Credential source (informational)
        click.echo(
            "\n[5/5] 凭证将自动从 NexusTrader 的 .keys/.secrets.toml 读取。\n"
            "      也可通过环境变量覆盖（如 BINANCE_API_KEY）。"
        )

        yaml_data = {"exchanges": exchange_configs}
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(yaml_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        click.echo(f"\n✅ 配置已生成：{config_path}")

    if config_only:
        return

    # ── Install to AI clients ──
    if not Path(config_path).is_file():
        click.echo(f"找不到 {config_path}，请先运行 setup 生成配置。")
        return

    server_entry = _generate_mcp_json(project_dir, config_path)

    click.echo("\n─── 安装到 AI 客户端 ───")

    # ── Project-local configs (auto-updated, no confirmation) ──
    project_claude_path = Path(project_dir) / ".claude" / "mcp.json"
    _write_mcp_config(project_claude_path, server_entry)
    click.echo(f"✅ 已更新项目本地 Claude Code 配置：{project_claude_path}")

    project_cursor_path = Path(project_dir) / ".cursor" / "mcp.json"
    _write_mcp_config(project_cursor_path, server_entry)
    click.echo(f"✅ 已更新项目本地 Cursor 配置：{project_cursor_path}")

    # ── Install Claude Code skills ──
    skills_dest = Path(project_dir) / ".claude" / "commands"
    installed = _install_skills(project_dir, skills_dest)
    if installed:
        click.echo(f"✅ 已安装 {len(installed)} 个 Claude Code 技能：" + ", ".join(f"/{s}" for s in installed))

    # ── Bootstrap .secrets.toml from template ──
    secrets_path = Path(project_dir) / ".keys" / ".secrets.toml"
    secrets_template = Path(project_dir) / ".keys" / ".secrets.toml.template"
    if not secrets_path.is_file() and secrets_template.is_file():
        shutil.copy2(secrets_template, secrets_path)
        click.echo(f"\n📋 已创建 {secrets_path}")
        click.echo("   ⚠️  请打开该文件，将各交易所的 API_KEY / SECRET 替换为真实凭证后再启动服务器。")
    elif not secrets_path.is_file():
        click.echo(f"\n⚠️  未找到 {secrets_path}，请手动创建并填入 API 凭证。")

    # ── Global user configs (optional) ──
    try:
        cursor_path = Path.home() / ".cursor" / "mcp.json"
        if click.confirm(f"\n同时写入全局 Cursor 配置 ({cursor_path})？", default=False):
            _write_mcp_config(cursor_path, server_entry)
            click.echo("✅ 已写入全局 Cursor MCP 配置")

        claude_path = Path.home() / ".claude.json"
        if click.confirm(f"同时写入全局 Claude Code 配置 ({claude_path})？", default=False):
            _write_mcp_config(claude_path, server_entry)
            click.echo("✅ 已写入全局 Claude Code MCP 配置")
    except click.Abort:
        pass

    # ── Install OpenClaw Skill ──
    openclaw_src = Path(project_dir) / "openclaw"
    openclaw_installed = False
    if openclaw_src.is_dir():
        openclaw_skill_dir = Path.home() / ".openclaw" / "skills" / "nexustrader"
        try:
            if click.confirm(
                f"\n安装 OpenClaw Skill ({openclaw_skill_dir})？",
                default=True,
            ):
                _install_openclaw_skill(project_dir, openclaw_skill_dir, config_path)
                click.echo(f"✅ OpenClaw Skill 已安装：{openclaw_skill_dir}")
                openclaw_installed = True
        except click.Abort:
            pass

    # ── Final summary ──
    click.echo("\n" + "─" * 50)
    click.echo("🎉 配置完成！下一步：\n")
    click.echo(f"  1️⃣  填写 API 凭证（如尚未填写）：")
    click.echo(f"     {Path(project_dir) / '.keys' / '.secrets.toml'}\n")
    click.echo(f"  2️⃣  重启 Cursor / Claude Code 即可使用 MCP（stdio 模式）。\n")
    if openclaw_installed:
        click.echo(f"  3️⃣  OpenClaw SSE 服务器管理命令：")
        click.echo(f"       nexustrader-mcp start    # 启动后台服务器")
        click.echo(f"       nexustrader-mcp status   # 查看是否在线")
        click.echo(f"       nexustrader-mcp logs     # 查看启动日志")
        click.echo(f"       nexustrader-mcp stop     # 停止服务器\n")
        try:
            if click.confirm("  现在立即启动 OpenClaw SSE 服务器？", default=True):
                click.echo("")
                subprocess.run(
                    [sys.executable, "-m", "nexustrader_mcp", "start"],
                    check=False,
                )
        except (click.Abort, Exception):
            click.echo("  （跳过，稍后可运行 nexustrader-mcp start）")


class _StderrProxy:
    """Redirect print()/write() to stderr while keeping .buffer pointing at the
    real stdout so MCP's stdio transport (which uses sys.stdout.buffer directly)
    continues to work correctly.
    """

    def __init__(self, real_stdout):
        self._real = real_stdout
        # MCP's stdio_server does: anyio.wrap_file(TextIOWrapper(sys.stdout.buffer))
        # so .buffer must remain the real stdout binary stream.
        self.buffer = real_stdout.buffer

    def write(self, s):
        return sys.stderr.write(s)

    def writelines(self, lines):
        return sys.stderr.writelines(lines)

    def flush(self):
        sys.stderr.flush()

    def fileno(self):
        return self._real.fileno()

    @property
    def encoding(self):
        return self._real.encoding

    @property
    def errors(self):
        return self._real.errors

    @property
    def closed(self):
        return self._real.closed

    def isatty(self):
        return False


@main.command(name="run")
@click.option("--config", "config_path", default=None, help="配置文件路径")
def run_server(config_path: Optional[str]):
    """启动 MCP 服务器（通常由 AI 客户端自动调用）。"""
    # MCP uses stdio for JSON-RPC. Guard against any library printing to stdout,
    # which would corrupt the JSON-RPC stream in strict clients like Claude Code.
    # _StderrProxy redirects print()/write() to stderr, but keeps .buffer pointing
    # at real stdout so MCP's stdio transport continues writing JSON there.
    sys.stdout = _StderrProxy(sys.stdout)

    from nexustrader_mcp.engine_manager import EngineManager
    from nexustrader_mcp.server import create_mcp_server

    engine = EngineManager()
    mcp = create_mcp_server(engine, config_path=config_path)

    try:
        mcp.run(transport="stdio")
    except KeyboardInterrupt:
        pass


@main.command(name="serve")
@click.option("--host", default="127.0.0.1", show_default=True, help="绑定地址")
@click.option("--port", type=int, default=18765, show_default=True, help="监听端口")
@click.option("--config", "config_path", default=None, help="配置文件路径")
def serve_sse(host: str, port: int, config_path: Optional[str]):
    """以 SSE (HTTP) 模式启动 MCP 服务器，供 OpenClaw 等工具使用。"""
    from nexustrader_mcp.engine_manager import EngineManager
    from nexustrader_mcp.server import create_mcp_server

    engine = EngineManager()
    mcp = create_mcp_server(engine, config_path=config_path)

    click.echo(
        f"[NexusTrader MCP] SSE server listening on http://{host}:{port}",
        err=True,
    )
    try:
        try:
            mcp.run(transport="sse", host=host, port=port)
        except TypeError:
            # Fallback for older FastMCP versions
            os.environ.setdefault("HOST", host)
            os.environ.setdefault("PORT", str(port))
            mcp.run(transport="sse")
    except KeyboardInterrupt:
        pass


@main.command(name="start")
@click.option("--no-wait", "no_wait", is_flag=True,
              help="后台启动，不等待上线直接返回（用于 on_startup 等场景）")
def start_daemon(no_wait: bool):
    """后台启动 OpenClaw SSE 服务器（常驻进程，Windows/Linux/macOS 均可用）。"""
    env = _oc_load_env()
    mcp_port = int(env.get("NEXUSTRADER_MCP_PORT", "18765"))
    mcp_host = env.get("NEXUSTRADER_MCP_HOST", "127.0.0.1")
    mcp_config = env.get("NEXUSTRADER_MCP_CONFIG", "")

    # Already running?
    is_running, pid = _oc_is_running()
    if is_running:
        if _oc_http_ok(mcp_host, mcp_port):
            click.echo(f"✅ NexusTrader MCP Server 已在线（PID {pid}，http://{mcp_host}:{mcp_port}/sse）")
        else:
            click.echo(f"◔ 进程存在（PID {pid}），引擎正在初始化，请稍候...")
            click.echo(f"   查看进度：nexustrader-mcp logs")
        return

    # Build command: use current interpreter so packages are guaranteed available
    cmd = [sys.executable, "-m", "nexustrader_mcp", "serve",
           "--host", mcp_host, "--port", str(mcp_port)]
    if mcp_config and Path(mcp_config).is_file():
        cmd += ["--config", mcp_config]

    pid = _oc_launch(cmd, _oc_log_file())
    _oc_pid_file().parent.mkdir(parents=True, exist_ok=True)
    _oc_pid_file().write_text(str(pid), encoding="utf-8")
    click.echo(f"[NexusTrader MCP] 后台启动（PID {pid}）")
    click.echo(f"  日志：{_oc_log_file()}")

    if no_wait:
        click.echo("  服务器初始化中（约 30–60 秒），用 nexustrader-mcp status 查看状态。")
        return

    # Wait with progress dots
    click.echo("  等待引擎初始化（预计 30–60 秒）...", nl=False)
    for _ in range(30):   # 30 × 3s = 90s max
        time.sleep(3)
        click.echo(".", nl=False)
        if _oc_http_ok(mcp_host, mcp_port):
            click.echo(f"\n✅ 服务器已上线！http://{mcp_host}:{mcp_port}/sse")
            return
    click.echo(f"\n⚠️  90 秒内未响应，请检查日志：nexustrader-mcp logs")


@main.command(name="stop")
def stop_daemon():
    """停止后台 OpenClaw SSE 服务器。"""
    is_running, pid = _oc_is_running()
    if not is_running:
        click.echo("服务器未在运行。")
        return
    _oc_kill(pid)
    _oc_pid_file().unlink(missing_ok=True)
    click.echo(f"✅ 已停止（PID {pid}）")


@main.command(name="status")
def daemon_status():
    """查看 OpenClaw SSE 服务器的当前状态。"""
    env = _oc_load_env()
    mcp_port = int(env.get("NEXUSTRADER_MCP_PORT", "18765"))
    mcp_host = env.get("NEXUSTRADER_MCP_HOST", "127.0.0.1")

    is_running, pid = _oc_is_running()
    http_ok = _oc_http_ok(mcp_host, mcp_port)

    if is_running and http_ok:
        click.echo(f"● 运行中  PID {pid}")
        click.echo(f"  SSE URL : http://{mcp_host}:{mcp_port}/sse")
        click.echo(f"  日志    : {_oc_log_file()}")
        click.echo(f"  配置    : {env.get('NEXUSTRADER_MCP_CONFIG', '(未设置)')}")
    elif is_running:
        click.echo(f"◔ 启动中  PID {pid}（交易引擎初始化，约需 30–60 秒）")
        click.echo(f"  查看进度：nexustrader-mcp logs")
    else:
        click.echo("○ 未运行")
        log = _oc_log_file()
        if log.is_file():
            lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
            if lines:
                click.echo("  最后几行日志：")
                for line in lines[-4:]:
                    click.echo(f"    {line}")
        click.echo("  启动命令：nexustrader-mcp start")


@main.command(name="logs")
@click.argument("lines", default=50, type=int, required=False)
def daemon_logs(lines: int):
    """查看服务器日志（默认最后 50 行）。  用法：nexustrader-mcp logs [行数]"""
    log = _oc_log_file()
    if not log.is_file():
        click.echo(f"日志文件不存在：{log}")
        click.echo("服务器尚未启动，先运行：nexustrader-mcp start")
        return
    content = log.read_text(encoding="utf-8", errors="replace").splitlines()
    shown = content[-lines:]
    click.echo(f"─── {log} （最后 {len(shown)} 行）───")
    for line in shown:
        click.echo(line)


# Allow `nexustrader-mcp --config xxx` as shortcut for `nexustrader-mcp run --config xxx`
@main.result_callback()
@click.pass_context
def default_command(ctx, *args, **kwargs):
    pass


# Override group invoke to default to `run` when no subcommand given
_original_main = main


@click.command(cls=click.Group)
def main():
    """NexusTrader MCP Server — 让 AI 操控你的交易账户。"""
    pass


main = _original_main


def cli_entry():
    """Entry point that defaults to 'run' when called without subcommand."""
    if len(sys.argv) == 1 or (len(sys.argv) >= 2 and sys.argv[1].startswith("--")):
        sys.argv.insert(1, "run")
    main()
