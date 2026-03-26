"""CLI 入口：setup / run / serve。"""

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
        "# 由 nexustrader-mcp setup 自动生成\n\n"
        f"NEXUSTRADER_PROJECT_DIR={project_dir}\n"
        f"NEXUSTRADER_MCP_CONFIG={config_path}\n"
        "NEXUSTRADER_MCP_PORT=18765\n"
        "NEXUSTRADER_MCP_HOST=127.0.0.1\n"
        "NEXUSTRADER_MCP_URL=http://127.0.0.1:18765/sse\n"
        f"NEXUSTRADER_LOG_DIR={skill_dir / 'logs'}\n"
        "\n"
        "# 自动启动控制（默认禁用）\n"
        "# 设为 0 可允许 bridge.py 在服务离线时自动启动后台 daemon\n"
        "# 启用前请确认已阅读安全说明并已配置好 API 密钥\n"
        "NEXUSTRADER_NO_AUTOSTART=1\n"
    )
    (skill_dir / ".env").write_text(env_content, encoding="utf-8")

    # Register in ~/.openclaw/skills/index.json (include full metadata for registry auditors)
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
        "credentials": [
            {
                "name": "NEXUSTRADER_API_KEYS",
                "description": "Exchange API keys in .keys/.secrets.toml (local file, not transmitted)",
                "scope": "local_file",
                "required": True,
            }
        ],
        "env": [
            {"name": "NEXUSTRADER_MCP_URL", "description": "MCP server URL (default: http://127.0.0.1:18765/sse)", "required": False},
            {"name": "NEXUSTRADER_PROJECT_DIR", "description": "Path to NexusTrader-mcp project (default: ~/NexusTrader-mcp)", "required": False},
            {"name": "NEXUSTRADER_NO_AUTOSTART", "description": "Set to 1 to disable automatic daemon start", "required": False},
        ],
        "metadata": {
            "openclaw": {
                "requires": {
                    "bins": [python_cmd, "uv"],
                    "python_packages": ["fastmcp"],
                },
                "credentials": [
                    {
                        "name": "NEXUSTRADER_API_KEYS",
                        "description": "Exchange API keys stored in NexusTrader-mcp project at .keys/.secrets.toml",
                        "scope": "local_file",
                    }
                ],
                "network": [
                    "127.0.0.1:18765 (local MCP server via SSE)",
                ],
                "side_effects": [
                    "May auto-start nexustrader-mcp background daemon (set NEXUSTRADER_NO_AUTOSTART=1 to disable)",
                    "Reads .env and .keys/.secrets.toml from NexusTrader-mcp project directory",
                    "Can execute real trades via create_order/cancel_order/modify_order (requires explicit user confirmation)",
                ],
            }
        },
    }
    existing_idx = next((i for i, s in enumerate(skills) if s.get("id") == "nexustrader"), None)
    if existing_idx is not None:
        skills[existing_idx] = entry
    else:
        skills.append(entry)
    index_path.write_text(json.dumps(index_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Append BOOT.md fragment to ~/.openclaw/workspace/BOOT.md (idempotent)
    boot_src = openclaw_src / "BOOT.md"
    if boot_src.is_file():
        workspace_dir = skill_dir.parent.parent / "workspace"
        workspace_dir.mkdir(parents=True, exist_ok=True)
        boot_dst = workspace_dir / "BOOT.md"
        marker = "# NexusTrader Boot Check"
        fragment = boot_src.read_text(encoding="utf-8")
        if boot_dst.is_file():
            existing = boot_dst.read_text(encoding="utf-8")
            if marker not in existing:
                boot_dst.write_text(existing.rstrip() + "\n\n" + fragment, encoding="utf-8")
        else:
            boot_dst.write_text(fragment, encoding="utf-8")


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


def _write_codex_config(filepath: Path, source_path: Path, sse_url: str):
    """Merge nexustrader into Codex TOML config while preserving other sections."""
    source_lines = source_path.read_text(encoding="utf-8").splitlines()
    rendered_lines = []
    for line in source_lines:
        if line.strip().startswith("url = "):
            rendered_lines.append(f'url = "{sse_url}"')
        else:
            rendered_lines.append(line)

    block_lines = rendered_lines
    header = "[mcp_servers.nexustrader]"
    filepath.parent.mkdir(parents=True, exist_ok=True)

    if not filepath.is_file():
        filepath.write_text("\n".join(block_lines).rstrip() + "\n", encoding="utf-8")
        return

    existing_lines = filepath.read_text(encoding="utf-8").splitlines()
    start_idx = next((i for i, line in enumerate(existing_lines) if line.strip() == header), None)

    if start_idx is None:
        merged_lines = existing_lines[:]
        if merged_lines and merged_lines[-1].strip():
            merged_lines.append("")
        merged_lines.extend(block_lines)
    else:
        end_idx = len(existing_lines)
        for i in range(start_idx + 1, len(existing_lines)):
            stripped = existing_lines[i].strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                end_idx = i
                break
        merged_lines = existing_lines[:start_idx] + block_lines + existing_lines[end_idx:]

    filepath.write_text("\n".join(merged_lines).rstrip() + "\n", encoding="utf-8")


def _create_dual_http_app(mcp):
    """Expose legacy SSE and streamable HTTP together for client compatibility."""
    from contextlib import asynccontextmanager

    from fastmcp.server.context import reset_transport, set_transport
    from fastmcp.server.http import StreamableHTTPASGIApp, set_http_request
    from mcp.server.sse import SseServerTransport
    from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
    from starlette.applications import Starlette
    from starlette.middleware import Middleware
    from starlette.requests import Request
    from starlette.responses import Response
    from starlette.routing import Mount, Route

    sse_path = "/sse"
    message_path = "/messages/"
    streamable_http_path = "/mcp"

    class _PathAwareRequestContextMiddleware:
        def __init__(self, app):
            self.app = app

        async def __call__(self, scope, receive, send):
            if scope["type"] != "http":
                await self.app(scope, receive, send)
                return

            path = scope.get("path", "")
            if path.startswith(streamable_http_path):
                transport_type = "streamable-http"
            else:
                transport_type = "sse"

            token = set_transport(transport_type)
            try:
                with set_http_request(Request(scope)):
                    await self.app(scope, receive, send)
            finally:
                reset_transport(token)

    sse = SseServerTransport(message_path)

    async def handle_sse(scope, receive, send):
        async with sse.connect_sse(scope, receive, send) as streams:
            await mcp._mcp_server.run(
                streams[0],
                streams[1],
                mcp._mcp_server.create_initialization_options(),
            )
        return Response()

    async def sse_endpoint(request: Request) -> Response:
        return await handle_sse(request.scope, request.receive, request._send)

    session_manager = StreamableHTTPSessionManager(
        app=mcp._mcp_server,
        event_store=None,
        retry_interval=None,
        json_response=False,
        # Codex uses Streamable HTTP and may not retain MCP session IDs between
        # requests, so expose `/mcp` in stateless mode for compatibility.
        stateless=True,
    )
    streamable_http_app = StreamableHTTPASGIApp(session_manager)

    @asynccontextmanager
    async def lifespan(app):
        async with mcp._lifespan_manager(), session_manager.run():
            yield

    routes = [
        Route(sse_path, endpoint=sse_endpoint, methods=["GET"]),
        Mount(message_path, app=sse.handle_post_message),
        Route(streamable_http_path, endpoint=streamable_http_app),
    ]

    app = Starlette(
        routes=routes,
        middleware=[Middleware(_PathAwareRequestContextMiddleware)],
        lifespan=lifespan,
    )
    app.state.fastmcp_server = mcp
    return app


def _venv_python(project_dir: str) -> Optional[Path]:
    """Return the path to the venv Python if it exists, else None."""
    if sys.platform == "win32":
        p = Path(project_dir) / ".venv" / "Scripts" / "python.exe"
    else:
        p = Path(project_dir) / ".venv" / "bin" / "python"
    return p if p.is_file() else None


# ──────────────────────────────────────────────────────
# Background-server process helpers (start / stop / status / logs)
# ──────────────────────────────────────────────────────

def _get_log_dir() -> Path:
    """Return the log/PID directory (env override → ~/.nexustrader-mcp/logs)."""
    env_dir = os.environ.get("NEXUSTRADER_LOG_DIR")
    if env_dir:
        return Path(env_dir)
    return Path.home() / ".nexustrader-mcp" / "logs"


def _pid_file() -> Path:
    return _get_log_dir() / "server.pid"


def _log_file() -> Path:
    return _get_log_dir() / "server.log"


def _read_pid() -> Optional[int]:
    p = _pid_file()
    if p.is_file():
        try:
            return int(p.read_text().strip())
        except (ValueError, OSError):
            pass
    return None


def _is_process_alive(pid: int) -> bool:
    """Return True if pid is an active process."""
    if sys.platform == "win32":
        import subprocess as _sp
        r = _sp.run(
            f'tasklist /FI "PID eq {pid}" /NH',
            shell=True, capture_output=True, text=True,
        )
        return str(pid) in r.stdout
    else:
        try:
            os.kill(pid, 0)
            return True
        except (ProcessLookupError, PermissionError, OSError):
            return False


def _build_serve_cmd(project_dir: str, host: str, port: int, config_path: Optional[str]) -> list:
    """Return the command list that runs `nexustrader-mcp serve` as a subprocess."""
    python = _venv_python(project_dir)
    base = (
        [str(python), "-m", "nexustrader_mcp", "serve"]
        if python
        else ["uv", "--directory", project_dir, "run", "nexustrader-mcp", "serve"]
    )
    cmd = base + ["--host", host, "--port", str(port)]
    if config_path:
        cmd += ["--config", config_path]
    return cmd


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
    codex_url = f"http://{host}:{port}/mcp"

    click.echo("\n─── 安装到 AI 客户端（SSE 模式）───")
    click.echo(f"    服务器 URL: {sse_url}")

    is_windows = sys.platform == "win32"
    is_linux = sys.platform.startswith("linux")

    # ── Claude Code config and skills (all platforms) ──
    project_claude_path = Path(project_dir) / ".claude" / "mcp.json"
    skills_dest = Path(project_dir) / ".claude" / "commands"
    try:
        if click.confirm(f"\n安装 Claude Code 配置 ({project_claude_path}) 和技能？", default=True):
            _write_mcp_config(project_claude_path, sse_entry)
            click.echo(f"✅ 已更新 Claude Code 配置：{project_claude_path}")

            installed = _install_skills(project_dir, skills_dest)
            if installed:
                click.echo(f"✅ 已安装 {len(installed)} 个 Claude Code 技能：" + ", ".join(f"/{s}" for s in installed))
    except click.Abort:
        pass

    # ── Codex config (all platforms) ──
    codex_template = Path(project_dir) / ".codex" / "config.toml"
    if codex_template.is_file():
        try:
            codex_path = Path.home() / ".codex" / "config.toml"
            if click.confirm(f"\n写入全局 Codex 配置 ({codex_path})？", default=True):
                _write_codex_config(codex_path, codex_template, codex_url)
                click.echo("✅ 已写入全局 Codex 配置")
        except click.Abort:
            pass

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

    secrets_path_display = str(Path(project_dir) / ".keys" / ".secrets.toml")
    start_cmd = "uv run nexustrader-mcp start"
    start_note = (
        f"\n   服务器在后台运行，关闭终端后仍继续。"
        f"\n   停止：uv run nexustrader-mcp stop"
        f"\n   状态：uv run nexustrader-mcp status"
        f"\n   日志：uv run nexustrader-mcp logs"
    )

    click.echo(
        f"\n🎉 配置完成！下一步："
        f"\n"
        f"\n   【第一步】填写 API 凭证："
        f"\n       {secrets_path_display}"
        f"\n       将各交易所的 API_KEY / SECRET 替换为真实凭证"
        f"\n"
        f"\n   【第二步】启动服务器："
        f"\n       {start_cmd}"
        f"{start_note}"
        f"\n"
        f"\n   SSE URL: {sse_url}"
        f"\n   Codex URL: {codex_url}"
        f"\n   重启 Cursor / Claude Code / Codex 后即可使用 NexusTrader MCP。"
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


@main.command(name="start")
@click.option("--host", default=_DEFAULT_HOST, show_default=True, help="绑定地址")
@click.option("--port", type=int, default=_DEFAULT_PORT, show_default=True, help="监听端口")
@click.option("--config", "config_path", default=None, help="配置文件路径（默认自动查找 config.yaml）")
@click.option("--no-wait", is_flag=True, help="启动后不等待服务器上线")
def start_server(host: str, port: int, config_path: Optional[str], no_wait: bool):
    """后台启动 MCP 服务器（写入 PID 文件，可用 stop 停止）。"""
    import subprocess as _sp
    import time as _time

    # Check if already running
    pid = _read_pid()
    if pid and _is_process_alive(pid):
        click.echo(f"[NexusTrader MCP] ✅ 服务器已在运行（PID {pid}），无需重复启动。")
        click.echo(f"   状态：uv run nexustrader-mcp status")
        return

    project_dir = str(Path(__file__).resolve().parent.parent)
    if config_path is None:
        env_cfg = os.environ.get("NEXUSTRADER_MCP_CONFIG")
        config_path = env_cfg if env_cfg else os.path.join(project_dir, "config.yaml")

    log_dir = _get_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    lf = _log_file()
    pf = _pid_file()

    cmd = _build_serve_cmd(project_dir, host, port, config_path)

    with open(lf, "a", encoding="utf-8") as log_fh:
        if sys.platform == "win32":
            DETACHED = 0x00000008
            NEW_GROUP = 0x00000200
            proc = _sp.Popen(
                cmd, stdout=log_fh, stderr=log_fh,
                creationflags=DETACHED | NEW_GROUP,
            )
        else:
            proc = _sp.Popen(
                cmd, stdout=log_fh, stderr=log_fh,
                start_new_session=True,
            )

    pf.write_text(str(proc.pid), encoding="utf-8")
    click.echo(f"[NexusTrader MCP] 服务器已启动（PID {proc.pid}）")
    click.echo(f"   日志：{lf}")

    if no_wait:
        return

    import socket as _sock
    click.echo("[NexusTrader MCP] 等待服务器上线（最长 90 秒）…")
    deadline = _time.monotonic() + 90
    online = False
    while _time.monotonic() < deadline:
        # Abort early if process died
        if not _is_process_alive(proc.pid):
            click.echo("[NexusTrader MCP] ❌ 服务器进程已意外退出。查看日志：")
            click.echo(f"   tail -20 {lf}")
            sys.exit(1)
        try:
            with _sock.create_connection((host, port), timeout=2):
                online = True
                break
        except OSError:
            _time.sleep(2)

    if online:
        click.echo(f"[NexusTrader MCP] ✅ 已上线  http://{host}:{port}/sse")
    else:
        click.echo("[NexusTrader MCP] ⚠️  超时，服务器可能仍在初始化（交易引擎需要 30–90 秒）。")
        click.echo(f"   持续查看日志：tail -f {lf}")
        click.echo(f"   手动检查：uv run nexustrader-mcp status")


@main.command(name="stop")
def stop_server():
    """停止后台服务器。"""
    import signal as _signal
    import subprocess as _sp
    import time as _time

    pid = _read_pid()
    if not pid:
        click.echo("[NexusTrader MCP] 未找到 PID 文件，服务器可能未在运行。")
        return

    if not _is_process_alive(pid):
        click.echo(f"[NexusTrader MCP] 进程 {pid} 已不存在，清理 PID 文件。")
        _pid_file().unlink(missing_ok=True)
        return

    try:
        if sys.platform == "win32":
            _sp.run(["taskkill", "/PID", str(pid), "/F"], check=True, capture_output=True)
        else:
            os.kill(pid, _signal.SIGTERM)
            # Give process up to 10 s to exit gracefully before SIGKILL
            deadline = _time.monotonic() + 10
            while _time.monotonic() < deadline:
                if not _is_process_alive(pid):
                    break
                _time.sleep(0.5)
            else:
                os.kill(pid, _signal.SIGKILL)
    except Exception as e:
        click.echo(f"[NexusTrader MCP] ❌ 停止失败：{e}", err=True)
        sys.exit(1)

    _pid_file().unlink(missing_ok=True)
    click.echo(f"[NexusTrader MCP] ✅ 服务器已停止（PID {pid}）")


@main.command(name="status")
@click.option("--host", default=_DEFAULT_HOST, show_default=True)
@click.option("--port", type=int, default=_DEFAULT_PORT, show_default=True)
def server_status(host: str, port: int):
    """查看后台服务器运行状态。"""
    import socket as _sock

    pid = _read_pid()
    alive = pid and _is_process_alive(pid)

    if not alive:
        if pid:
            _pid_file().unlink(missing_ok=True)
        click.echo("[NexusTrader MCP] ❌ OFFLINE  （未检测到运行中的服务器）")
        click.echo("   启动：uv run nexustrader-mcp start")
        sys.exit(1)

    try:
        with _sock.create_connection((host, port), timeout=3):
            click.echo(f"[NexusTrader MCP] ✅ ONLINE   PID={pid}  http://{host}:{port}/sse")
    except OSError:
        click.echo(f"[NexusTrader MCP] ⏳ STARTING  PID={pid}（端口 {port} 未就绪，引擎可能仍在初始化）")
        click.echo(f"   查看日志：uv run nexustrader-mcp logs")
        sys.exit(2)


@main.command(name="logs")
@click.argument("lines", default=50, type=int)
def server_logs(lines: int):
    """查看服务器日志（最后 N 行，默认 50）。"""
    lf = _log_file()
    if not lf.is_file():
        click.echo(f"日志文件不存在：{lf}")
        click.echo("请先运行：uv run nexustrader-mcp start")
        sys.exit(1)
    all_lines = lf.read_text(encoding="utf-8", errors="replace").splitlines()
    tail = all_lines[-lines:]
    click.echo(f"# {lf}  （最后 {min(lines, len(all_lines))} / {len(all_lines)} 行）")
    for line in tail:
        click.echo(line)


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
    """启动 HTTP MCP 服务器，同时提供 `/sse` 和 `/mcp`。"""
    if sys.platform == "win32":
        import asyncio as _asyncio

        # Avoid noisy Proactor transport reset tracebacks when local MCP clients
        # probe endpoints and close the connection immediately on Windows.
        _asyncio.set_event_loop_policy(_asyncio.WindowsSelectorEventLoopPolicy())

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
                f"  请先停止已有的服务器：uv run nexustrader-mcp stop\n"
                f"  或查看占用端口的进程（Linux/macOS）：lsof -i :{port}\n"
                f"  Windows：netstat -ano | findstr :{port}",
                err=True,
            )
            sys.exit(1)

    from nexustrader_mcp.engine_manager import EngineManager
    from nexustrader_mcp.server import create_mcp_server

    engine = EngineManager()
    mcp = create_mcp_server(engine, config_path=config_path)

    click.echo(
        f"[NexusTrader MCP] HTTP server listening on http://{host}:{port} "
        f"(SSE: /sse, Codex: /mcp)",
        err=True,
    )
    try:
        try:
            from uvicorn import Config, Server

            app = _create_dual_http_app(mcp)
            config = Config(
                app,
                host=host,
                port=port,
                log_level="info",
                timeout_graceful_shutdown=0,
                lifespan="on",
                ws="websockets-sansio",
            )
            server = Server(config)
            server.run()
        except TypeError:
            # Fallback for older FastMCP versions
            os.environ.setdefault("HOST", host)
            os.environ.setdefault("PORT", str(port))
            mcp.run(transport="sse")
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
