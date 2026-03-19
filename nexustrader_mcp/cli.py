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
            "run", "nexustrader-mcp",
            "--config", config_path,
        ],
    }


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

            cfg = {"account_type": at}
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

    # ── Global user configs (optional) ──
    cursor_path = Path.home() / ".cursor" / "mcp.json"
    if click.confirm(f"\n同时写入全局 Cursor 配置 ({cursor_path})？", default=False):
        _write_mcp_config(cursor_path, server_entry)
        click.echo(f"✅ 已写入全局 Cursor MCP 配置")

    claude_path = Path.home() / ".claude" / "settings.json"
    if click.confirm(f"同时写入全局 Claude Code 配置 ({claude_path})？", default=False):
        _write_mcp_config(claude_path, server_entry)
        click.echo(f"✅ 已写入全局 Claude Code MCP 配置")

    click.echo("\n🎉 全部完成！重启 Cursor / Claude Code 即可使用 NexusTrader MCP。")


@main.command(name="run")
@click.option("--config", "config_path", default=None, help="配置文件路径")
def run_server(config_path: Optional[str]):
    """启动 MCP 服务器（通常由 AI 客户端自动调用）。"""
    from nexustrader_mcp.engine_manager import EngineManager
    from nexustrader_mcp.server import create_mcp_server

    engine = EngineManager()

    try:
        engine.start(config_path=config_path)
    except SystemExit:
        raise
    except Exception as e:
        click.echo(f"引擎启动失败: {e}", err=True)
        sys.exit(1)

    mcp = create_mcp_server(engine)

    try:
        mcp.run(transport="stdio")
    except KeyboardInterrupt:
        pass
    finally:
        engine.stop()


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
