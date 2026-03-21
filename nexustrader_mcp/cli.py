"""CLI 入口：setup / run。"""

from __future__ import annotations

import json
import os
import shutil
import sys
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

_DEFAULT_HOST = "127.0.0.1"
_DEFAULT_PORT = 18765


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
    """Stdio transport config (kept for reference / backward compat)."""
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


def _generate_sse_entry(host: str = _DEFAULT_HOST, port: int = _DEFAULT_PORT) -> dict:
    """SSE transport config entry for Claude Code / Cursor."""
    return {"type": "sse", "url": f"http://{host}:{port}/sse"}



def _detect_python_cmd() -> str:
    """Return 'python3' if available, else 'python'."""
    import subprocess as _sp
    try:
        _sp.run(["python3", "--version"], capture_output=True, check=True)
        return "python3"
    except (FileNotFoundError, _sp.CalledProcessError):
        return "python"


def _install_openclaw_skill(project_dir: str, skill_dir: Path, config_path: str) -> None:
    """将 OpenClaw Skill 文件安装到 ~/.openclaw/skills/nexustrader/。"""
    import datetime

    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "logs").mkdir(exist_ok=True)

    python_cmd = _detect_python_cmd()
    openclaw_src = Path(project_dir) / "openclaw"

    for fname in ["SKILL.md", "BOOT.md", "bridge.py", "nexustrader_daemon.sh"]:
        src = openclaw_src / fname
        if not src.is_file():
            continue
        if fname in ("SKILL.md", "BOOT.md") and python_cmd != "python3":
            # Replace python3 with the actually available command
            text = src.read_text(encoding="utf-8").replace("python3", python_cmd)
            (skill_dir / fname).write_text(text, encoding="utf-8")
        else:
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

    # Copy BOOT.md to ~/.openclaw/workspace/BOOT.md
    boot_src = openclaw_src / "BOOT.md"
    if boot_src.is_file():
        workspace_dir = skill_dir.parent.parent / "workspace"
        if workspace_dir.is_dir():
            shutil.copy2(boot_src, workspace_dir / "BOOT.md")


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


# ── Daemon management ─────────────────────────────────────────────────────────

def _daemon_home() -> Path:
    return Path.home() / ".nexustrader-mcp"


def _daemon_pid_file() -> Path:
    return _daemon_home() / "server.pid"


def _daemon_log_file() -> Path:
    return _daemon_home() / "server.log"


def _pid_exists(pid: int) -> bool:
    """Return True if a process with *pid* is alive.

    On Windows, os.kill(pid, 0) sends CTRL_C_EVENT (signal value 0) instead of
    doing a no-op existence check like POSIX does, so we use OpenProcess instead.
    On POSIX, PermissionError means the process exists (we just can't signal it).
    """
    if sys.platform == "win32":
        import ctypes
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if handle:
            # Also verify the process hasn't exited yet
            import ctypes.wintypes
            exit_code = ctypes.wintypes.DWORD()
            still_active = ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
            ctypes.windll.kernel32.CloseHandle(handle)
            # STILL_ACTIVE == 259
            return bool(still_active and exit_code.value == 259)
        return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except PermissionError:
            return True   # process exists, we just can't signal it
        except OSError:
            return False


def _daemon_is_running() -> bool:
    """Check if the daemon is running via PID file first, then port probe as fallback."""
    import socket as _socket
    pf = _daemon_pid_file()
    if pf.is_file():
        try:
            pid = int(pf.read_text().strip())
            if _pid_exists(pid):
                return True
        except ValueError:
            pass
        # Stale PID file — clean it up
        try:
            pf.unlink()
        except OSError:
            pass
    # Fallback: probe the port — catches cases where PID tracking was lost
    # (e.g. previous start via `uv run` where uv exited after exec'ing Python)
    try:
        with _socket.create_connection(("127.0.0.1", _DEFAULT_PORT), timeout=1):
            return True
    except OSError:
        return False


def _venv_python(project_dir: str) -> Optional[Path]:
    """Return the path to the venv Python if it exists, else None."""
    if sys.platform == "win32":
        p = Path(project_dir) / ".venv" / "Scripts" / "python.exe"
    else:
        p = Path(project_dir) / ".venv" / "bin" / "python"
    return p if p.is_file() else None


def _daemon_start_bg(project_dir: str, config_path: Optional[str], host: str, port: int) -> int:
    """Start SSE server as a detached background process. Returns PID.

    Uses .venv Python directly when available so that proc.pid is the actual
    server process — not a uv launcher that may exit after exec'ing Python,
    which would make PID-based status checks unreliable.
    """
    import subprocess as _sp
    _daemon_home().mkdir(parents=True, exist_ok=True)
    log_f = _daemon_log_file()

    python = _venv_python(project_dir)
    env = dict(os.environ)
    for k in ("PYTHONPATH", "PYTHONHOME", "CONDA_PREFIX", "CONDA_DEFAULT_ENV"):
        env.pop(k, None)
    env["CONDA_SHLVL"] = "0"

    if python is not None:
        # Direct invocation — proc.pid == actual server PID
        cmd = [str(python), "-m", "nexustrader_mcp.cli", "serve",
               "--host", host, "--port", str(port)]
    else:
        # venv not ready yet, fall back to uv run
        cmd = [
            "uv", "--directory", project_dir,
            "run", "--python", "3.11",
            "nexustrader-mcp", "serve",
            "--host", host, "--port", str(port),
        ]
        env["UV_PYTHON_PREFERENCE"] = "only-managed"
        env["UV_PYTHON"] = "cpython-3.11"

    if config_path and Path(config_path).is_file():
        cmd += ["--config", config_path]

    with open(log_f, "a") as lf:
        if sys.platform == "win32":
            proc = _sp.Popen(
                cmd, stdout=lf, stderr=lf, env=env,
                creationflags=_sp.DETACHED_PROCESS | _sp.CREATE_NEW_PROCESS_GROUP,
                cwd=project_dir,
            )
        else:
            proc = _sp.Popen(cmd, stdout=lf, stderr=lf, env=env,
                             start_new_session=True, cwd=project_dir)
    _daemon_pid_file().write_text(str(proc.pid))
    return proc.pid


def _daemon_stop() -> bool:
    """Send SIGTERM to daemon. Returns True if a process was found."""
    import signal
    pf = _daemon_pid_file()
    if not _daemon_is_running():
        return False
    try:
        pid = int(pf.read_text().strip())
        os.kill(pid, signal.SIGTERM)
        try:
            pf.unlink()
        except OSError:
            pass
        return True
    except (ValueError, OSError):
        return False


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
@click.option("--host", default=_DEFAULT_HOST, show_default=True, help="SSE 服务器绑定地址")
@click.option("--port", type=int, default=_DEFAULT_PORT, show_default=True, help="SSE 服务器端口")
def setup(config_only: bool, install_only: bool, host: str, port: int):
    """交互式配置 + 一键安装到 AI 客户端（SSE 模式）。"""
    import subprocess as _sp
    project_dir = str(Path(__file__).resolve().parent.parent)
    config_path = os.path.join(project_dir, "config.yaml")

    # ── Ensure venv is ready (run uv sync if .venv Python is missing) ──
    if _venv_python(project_dir) is None:
        click.echo("⚙️  未检测到虚拟环境，正在运行 uv sync …")
        result = _sp.run(["uv", "sync"], cwd=project_dir)
        if result.returncode != 0:
            click.echo("❌ uv sync 失败，请手动运行后重试：\n   uv sync")
            return
        click.echo("✅ 虚拟环境初始化完成\n")

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

    # ── Install to AI clients (SSE mode) ──
    if not Path(config_path).is_file():
        click.echo(f"找不到 {config_path}，请先运行 setup 生成配置。")
        return

    # SSE entry: clients connect to the running server via URL
    sse_entry = _generate_sse_entry(host, port)
    sse_url = f"http://{host}:{port}/sse"

    click.echo("\n─── 安装到 AI 客户端（SSE 模式）───")
    click.echo(f"    服务器 URL: {sse_url}")

    is_windows = sys.platform == "win32"
    is_linux = sys.platform.startswith("linux")

    # ── Project-local Claude Code config (all platforms) ──
    project_claude_path = Path(project_dir) / ".claude" / "mcp.json"
    _write_mcp_config(project_claude_path, sse_entry)
    click.echo(f"✅ 已更新项目本地 Claude Code 配置：{project_claude_path}")

    # ── Install Claude Code skills (all platforms) ──
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

    # ── Windows: Cursor (global) ──
    if is_windows:
        try:
            cursor_path = Path.home() / ".cursor" / "mcp.json"
            if click.confirm(f"\n写入全局 Cursor 配置 ({cursor_path})？", default=True):
                _write_mcp_config(cursor_path, sse_entry)
                click.echo("✅ 已写入全局 Cursor MCP 配置")
        except click.Abort:
            pass

    # ── Linux: OpenClaw Skill ──
    if is_linux:
        openclaw_src = Path(project_dir) / "openclaw"
        if openclaw_src.is_dir():
            openclaw_skill_dir = Path.home() / ".openclaw" / "skills" / "nexustrader"
            try:
                if click.confirm(
                    f"\n安装 OpenClaw Skill ({openclaw_skill_dir})？",
                    default=True,
                ):
                    _install_openclaw_skill(project_dir, openclaw_skill_dir, config_path)
                    click.echo(f"✅ OpenClaw Skill 已安装：{openclaw_skill_dir}")
            except click.Abort:
                pass

    # ── Global Claude Code config (optional, all platforms) ──
    try:
        claude_path = Path.home() / ".claude.json"
        if click.confirm(f"\n同时写入全局 Claude Code 配置 ({claude_path})？", default=False):
            _write_mcp_config(claude_path, sse_entry)
            click.echo("✅ 已写入全局 Claude Code MCP 配置")
    except click.Abort:
        pass

    click.echo(
        f"\n🎉 配置完成！"
        f"\n"
        f"\n   ▶ 启动服务器："
        f"\n       uv run nexustrader-mcp serve"
        f"\n"
        f"\n   服务器 URL: {sse_url}"
        f"\n   重启 Cursor / Claude Code 后即可使用 NexusTrader MCP。"
    )


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
    import socket as _socket

    # Fail fast if the port is already occupied — gives a clear error instead of
    # a cryptic OS error buried deep in the FastMCP startup sequence.
    # NOTE: do NOT set SO_REUSEADDR here — on Windows it allows binding to an
    # already-occupied port, making the check a false pass.
    with _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM) as _s:
        try:
            _s.bind((host, port))
        except OSError:
            click.echo(
                f"[NexusTrader MCP] ❌ 端口 {port} 已被占用，无法启动。\n"
                f"  请先停止已有实例：nexustrader-mcp daemon stop\n"
                f"  或查看占用端口的进程（Linux）：lsof -i :{port}\n"
                f"  Windows：netstat -ano | findstr :{port}",
                err=True,
            )
            sys.exit(1)

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


@main.command(name="daemon")
@click.argument("action", type=click.Choice(["start", "stop", "restart", "status", "logs"]))
@click.option("--host", default=_DEFAULT_HOST, show_default=True, help="SSE 服务器绑定地址")
@click.option("--port", type=int, default=_DEFAULT_PORT, show_default=True, help="SSE 服务器端口")
@click.option("--config", "config_path", default=None, help="配置文件路径")
def daemon_cmd(action: str, host: str, port: int, config_path: Optional[str]):
    """管理 NexusTrader MCP 后台守护进程（SSE 服务器）。

    \b
    动作:
      start    后台启动 SSE 服务器
      stop     停止服务器
      restart  重启服务器
      status   查看运行状态
      logs     实时跟踪日志（Ctrl+C 退出）
    """
    project_dir = str(Path(__file__).resolve().parent.parent)
    if config_path is None:
        default_cfg = os.path.join(project_dir, "config.yaml")
        if Path(default_cfg).is_file():
            config_path = default_cfg

    if action == "start":
        if _daemon_is_running():
            pf = _daemon_pid_file()
            pid_text = pf.read_text().strip() if pf.is_file() else "未知"
            click.echo(f"⚠️  服务器已在运行（PID {pid_text}）")
            click.echo(f"   SSE URL: http://{host}:{port}/sse")
            return
        pid = _daemon_start_bg(project_dir, config_path, host, port)
        click.echo(f"✅ NexusTrader MCP 服务器已启动（PID {pid}）")
        click.echo(f"   SSE URL: http://{host}:{port}/sse")
        click.echo(f"   日志: {_daemon_log_file()}")
        click.echo(f"   停止: nexustrader-mcp daemon stop")

    elif action == "stop":
        if _daemon_stop():
            click.echo("✅ 服务器已停止")
        else:
            click.echo("⚠️  服务器未在运行")

    elif action == "restart":
        _daemon_stop()
        import time as _time
        _time.sleep(1)
        pid = _daemon_start_bg(project_dir, config_path, host, port)
        click.echo(f"✅ 服务器已重启（PID {pid}）")
        click.echo(f"   SSE URL: http://{host}:{port}/sse")

    elif action == "status":
        if _daemon_is_running():
            pf = _daemon_pid_file()
            pid_text = pf.read_text().strip() if pf.is_file() else "未知"
            click.echo(f"● NexusTrader MCP 服务器运行中（PID {pid_text}）")
            click.echo(f"  SSE URL: http://{host}:{port}/sse")
            click.echo(f"  日志: {_daemon_log_file()}")
        else:
            click.echo("○ NexusTrader MCP 服务器未运行")
            click.echo("  启动: uv run nexustrader-mcp daemon start")

    elif action == "logs":
        import subprocess as _sp
        log_f = _daemon_log_file()
        if not log_f.is_file():
            click.echo(f"日志文件不存在：{log_f}")
            return
        try:
            if sys.platform == "win32":
                _sp.run(["powershell", "-Command", f"Get-Content -Wait '{log_f}'"])
            else:
                _sp.run(["tail", "-f", str(log_f)])
        except KeyboardInterrupt:
            pass


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
