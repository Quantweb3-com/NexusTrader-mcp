"""
NexusTrader MCP 接口完整测试脚本
================================

通过 fastmcp Client 连接 MCP server，自动测试所有已注册工具。
使用与 .cursor/mcp.json 相同的 MCPConfig 格式启动服务器。

运行方式:
    uv run python tests/test_mcp_tools.py
    uv run python tests/test_mcp_tools.py --config path/to/config.yaml

注意: NexusTrader 引擎首次启动需要 60-120 秒（连接交易所），请耐心等待。
"""

from __future__ import annotations

import argparse
import asyncio
import io
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from fastmcp import Client
from fastmcp.client.transports.stdio import StdioTransport

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ── result tracking ──────────────────────────────────────────────────────────


@dataclass
class TestResult:
    name: str
    status: str  # PASS / FAIL / SKIP / WARN
    elapsed_ms: float = 0.0
    response: Any = None
    error: str = ""
    note: str = ""


@dataclass
class TestReport:
    results: list[TestResult] = field(default_factory=list)

    def add(self, result: TestResult):
        self.results.append(result)

    def print_summary(self):
        print("\n" + "=" * 78)
        print("  NexusTrader MCP 接口测试报告 / MCP Interface Test Report")
        print("=" * 78)

        status_icon = {"PASS": "[OK]", "FAIL": "[FAIL]", "SKIP": "[SKIP]", "WARN": "[WARN]"}
        max_name = max(len(r.name) for r in self.results) if self.results else 20

        for r in self.results:
            icon = status_icon.get(r.status, "[??]")
            ms = f"{r.elapsed_ms:>8.0f}ms"
            line = f"  {icon:<6} {r.name:<{max_name}}  {ms}"
            if r.note:
                line += f"  | {r.note}"
            if r.error:
                line += f"  | ERROR: {r.error[:80]}"
            print(line)

        counts: dict[str, int] = {}
        for r in self.results:
            counts[r.status] = counts.get(r.status, 0) + 1
        print("-" * 78)
        parts = [f"{k}: {v}" for k, v in sorted(counts.items())]
        print(f"  Total: {len(self.results)}  |  {' | '.join(parts)}")
        print("=" * 78)


# ── helpers ──────────────────────────────────────────────────────────────────


def parse_response(raw: Any) -> Any:
    """Extract text content from MCP CallToolResult."""
    if hasattr(raw, "content"):
        texts = [c.text for c in raw.content if hasattr(c, "text")]
        combined = "\n".join(texts)
        try:
            return json.loads(combined)
        except (json.JSONDecodeError, TypeError):
            return combined
    return raw


async def call_tool(client: Client, name: str, args: dict | None = None) -> tuple[Any, float]:
    """Call a tool and return (parsed_response, elapsed_ms)."""
    t0 = time.perf_counter()
    raw = await client.call_tool(name, args or {})
    elapsed = (time.perf_counter() - t0) * 1000
    return parse_response(raw), elapsed


def is_error(resp: Any) -> bool:
    return isinstance(resp, dict) and "error" in resp


# ── test cases ───────────────────────────────────────────────────────────────


async def test_get_exchange_info(client: Client, report: TestReport, ctx: dict):
    name = "get_exchange_info"
    try:
        resp, ms = await call_tool(client, name)
        if isinstance(resp, list) and len(resp) > 0:
            ctx["exchange"] = resp[0].get("exchange", "okx")
            ctx["account_types"] = resp[0].get("account_types", [])
            report.add(TestResult(name, "PASS", ms, resp,
                                  note=f"exchanges={[r['exchange'] for r in resp]}"))
        else:
            report.add(TestResult(name, "WARN", ms, resp, note="empty result"))
    except Exception as e:
        report.add(TestResult(name, "FAIL", error=str(e)))


async def test_get_all_balances(client: Client, report: TestReport, ctx: dict):
    name = "get_all_balances"
    try:
        resp, ms = await call_tool(client, name)
        if isinstance(resp, list):
            report.add(TestResult(name, "PASS", ms, resp,
                                  note=f"accounts={len(resp)}"))
        else:
            report.add(TestResult(name, "WARN", ms, resp, note="unexpected type"))
    except Exception as e:
        report.add(TestResult(name, "FAIL", error=str(e)))


async def test_get_balance(client: Client, report: TestReport, ctx: dict):
    name = "get_balance"
    exchange = ctx.get("exchange", "okx")
    account_type = ctx["account_types"][0] if ctx.get("account_types") else "live"
    try:
        resp, ms = await call_tool(client, name, {
            "exchange": exchange, "account_type": account_type
        })
        if is_error(resp):
            report.add(TestResult(name, "WARN", ms, resp, note=resp["error"][:60]))
        else:
            report.add(TestResult(name, "PASS", ms, resp,
                                  note=f"exchange={exchange}, type={account_type}"))
    except Exception as e:
        report.add(TestResult(name, "FAIL", error=str(e)))


async def test_get_all_positions(client: Client, report: TestReport, ctx: dict):
    name = "get_all_positions"
    try:
        resp, ms = await call_tool(client, name)
        if isinstance(resp, list):
            report.add(TestResult(name, "PASS", ms, None,
                                  note=f"positions={len(resp)}"))
        else:
            report.add(TestResult(name, "WARN", ms, resp, note="unexpected type"))
    except Exception as e:
        report.add(TestResult(name, "FAIL", error=str(e)))


async def test_get_position(client: Client, report: TestReport, ctx: dict):
    name = "get_position"
    symbol = ctx.get("perp_symbol", "BTCUSDT-PERP.OKX")
    try:
        resp, ms = await call_tool(client, name, {"symbol": symbol})
        if is_error(resp):
            report.add(TestResult(name, "FAIL", ms, resp, error=resp["error"]))
        else:
            report.add(TestResult(name, "PASS", ms, resp,
                                  note=f"side={resp.get('side', '?')}"))
    except Exception as e:
        report.add(TestResult(name, "FAIL", error=str(e)))


async def test_get_symbols(client: Client, report: TestReport, ctx: dict):
    exchange = ctx.get("exchange", "okx")
    for itype in ("linear", "spot"):
        name = f"get_symbols[{itype}]"
        try:
            resp, ms = await call_tool(client, "get_symbols", {
                "exchange": exchange, "instrument_type": itype
            })
            if isinstance(resp, list):
                if itype == "linear" and resp:
                    ctx["perp_symbol"] = resp[0]
                report.add(TestResult(name, "PASS", ms, None,
                                      note=f"count={len(resp)}"))
            elif is_error(resp):
                report.add(TestResult(name, "FAIL", ms, resp, error=resp["error"]))
            else:
                report.add(TestResult(name, "WARN", ms, resp))
        except Exception as e:
            report.add(TestResult(name, "FAIL", error=str(e)))


async def test_get_market_info(client: Client, report: TestReport, ctx: dict):
    name = "get_market_info"
    symbol = ctx.get("perp_symbol", "BTCUSDT-PERP.OKX")
    try:
        resp, ms = await call_tool(client, name, {"symbol": symbol})
        if is_error(resp):
            report.add(TestResult(name, "FAIL", ms, resp, error=resp["error"]))
        else:
            report.add(TestResult(name, "PASS", ms, resp,
                                  note=f"id={resp.get('id', '?')}, type={resp.get('type', '?')}"))
    except Exception as e:
        report.add(TestResult(name, "FAIL", error=str(e)))


async def test_get_ticker(client: Client, report: TestReport, ctx: dict):
    name = "get_ticker"
    symbol = ctx.get("perp_symbol", "BTCUSDT-PERP.OKX")
    try:
        resp, ms = await call_tool(client, name, {"symbol": symbol})
        if is_error(resp):
            report.add(TestResult(name, "FAIL", ms, resp, error=resp["error"]))
        else:
            report.add(TestResult(name, "PASS", ms, resp,
                                  note=f"last={resp.get('last_price', '?')}"))
    except Exception as e:
        report.add(TestResult(name, "FAIL", error=str(e)))


async def test_get_klines(client: Client, report: TestReport, ctx: dict):
    name = "get_klines"
    symbol = ctx.get("perp_symbol", "BTCUSDT-PERP.OKX")
    try:
        resp, ms = await call_tool(client, name, {
            "symbol": symbol, "interval": "1h", "limit": 3
        })
        if isinstance(resp, list):
            report.add(TestResult(name, "PASS", ms, None,
                                  note=f"bars={len(resp)}"))
        elif is_error(resp):
            report.add(TestResult(name, "FAIL", ms, resp, error=resp["error"]))
        else:
            report.add(TestResult(name, "WARN", ms, resp))
    except Exception as e:
        report.add(TestResult(name, "FAIL", error=str(e)))


async def test_get_orderbook(client: Client, report: TestReport, ctx: dict):
    """需要 bookl1 订阅。分别测试 PERP 和 SPOT 格式。"""
    for label, symbol in [
        ("PERP", ctx.get("perp_symbol", "BTCUSDT-PERP.OKX")),
        ("SPOT", "BTCUSDT.OKX"),
    ]:
        name = f"get_orderbook[{label}]"
        try:
            resp, ms = await call_tool(client, "get_orderbook", {"symbol": symbol})
            if is_error(resp):
                report.add(TestResult(name, "WARN", ms, resp,
                                      note=f"未订阅 bookl1: {symbol}"))
            else:
                report.add(TestResult(name, "PASS", ms, resp,
                                      note=f"bid={resp.get('bid')}, ask={resp.get('ask')}"))
        except Exception as e:
            report.add(TestResult(name, "FAIL", error=str(e)))


async def test_get_funding_rate(client: Client, report: TestReport, ctx: dict):
    name = "get_funding_rate"
    symbol = ctx.get("perp_symbol", "BTCUSDT-PERP.OKX")
    try:
        resp, ms = await call_tool(client, name, {"symbol": symbol})
        if is_error(resp):
            report.add(TestResult(name, "WARN", ms, resp,
                                  note="需在 config.yaml subscribe 中添加 funding_rate"))
        else:
            report.add(TestResult(name, "PASS", ms, resp))
    except Exception as e:
        report.add(TestResult(name, "FAIL", error=str(e)))


async def test_get_mark_price(client: Client, report: TestReport, ctx: dict):
    name = "get_mark_price"
    symbol = ctx.get("perp_symbol", "BTCUSDT-PERP.OKX")
    try:
        resp, ms = await call_tool(client, name, {"symbol": symbol})
        if is_error(resp):
            report.add(TestResult(name, "WARN", ms, resp,
                                  note="需在 config.yaml subscribe 中添加 mark_price"))
        else:
            report.add(TestResult(name, "PASS", ms, resp))
    except Exception as e:
        report.add(TestResult(name, "FAIL", error=str(e)))


async def test_get_index_price(client: Client, report: TestReport, ctx: dict):
    name = "get_index_price"
    symbol = ctx.get("perp_symbol", "BTCUSDT-PERP.OKX")
    try:
        resp, ms = await call_tool(client, name, {"symbol": symbol})
        if is_error(resp):
            report.add(TestResult(name, "WARN", ms, resp,
                                  note="需在 config.yaml subscribe 中添加 index_price"))
        else:
            report.add(TestResult(name, "PASS", ms, resp))
    except Exception as e:
        report.add(TestResult(name, "FAIL", error=str(e)))


async def test_get_open_orders(client: Client, report: TestReport, ctx: dict):
    name = "get_open_orders"
    exchange = ctx.get("exchange", "okx")
    try:
        resp, ms = await call_tool(client, name, {"exchange": exchange})
        if isinstance(resp, list):
            report.add(TestResult(name, "PASS", ms, None,
                                  note=f"open_orders={len(resp)}"))
        elif is_error(resp):
            report.add(TestResult(name, "FAIL", ms, resp, error=resp["error"]))
        else:
            report.add(TestResult(name, "WARN", ms, resp))
    except Exception as e:
        report.add(TestResult(name, "FAIL", error=str(e)))


async def test_get_order(client: Client, report: TestReport, ctx: dict):
    name = "get_order"
    try:
        resp, ms = await call_tool(client, name, {"oid": "nonexistent-test-id"})
        if is_error(resp) and "未找到" in resp["error"]:
            report.add(TestResult(name, "PASS", ms, resp,
                                  note="正确返回 not-found"))
        elif is_error(resp):
            report.add(TestResult(name, "FAIL", ms, resp, error=resp["error"]))
        else:
            report.add(TestResult(name, "PASS", ms, resp))
    except Exception as e:
        report.add(TestResult(name, "FAIL", error=str(e)))


async def test_cancel_all_orders(client: Client, report: TestReport, ctx: dict):
    name = "cancel_all_orders"
    symbol = ctx.get("perp_symbol", "BTCUSDT-PERP.OKX")
    try:
        resp, ms = await call_tool(client, name, {"symbol": symbol})
        if is_error(resp):
            report.add(TestResult(name, "FAIL", ms, resp, error=resp["error"]))
        else:
            report.add(TestResult(name, "PASS", ms, resp,
                                  note=f"status={resp.get('status', '?')}"))
    except Exception as e:
        report.add(TestResult(name, "FAIL", error=str(e)))


async def test_create_order_skip(client: Client, report: TestReport, ctx: dict):
    report.add(TestResult("create_order", "SKIP", note="SKIP - 真实交易, 需手动测试"))


async def test_cancel_order_skip(client: Client, report: TestReport, ctx: dict):
    report.add(TestResult("cancel_order", "SKIP", note="SKIP - 需要有效订单 ID"))


async def test_modify_order_skip(client: Client, report: TestReport, ctx: dict):
    report.add(TestResult("modify_order", "SKIP", note="SKIP - 需要有效订单 ID"))


# ── main runner ──────────────────────────────────────────────────────────────

ALL_TESTS = [
    test_get_exchange_info,
    test_get_all_balances,
    test_get_balance,
    test_get_all_positions,
    test_get_position,
    test_get_symbols,
    test_get_market_info,
    test_get_ticker,
    test_get_klines,
    test_get_orderbook,
    test_get_funding_rate,
    test_get_mark_price,
    test_get_index_price,
    test_get_open_orders,
    test_get_order,
    test_cancel_all_orders,
    test_create_order_skip,
    test_cancel_order_skip,
    test_modify_order_skip,
]


def build_transport(config_path: str) -> StdioTransport:
    """Build StdioTransport matching the .cursor/mcp.json config."""
    config_abs = str(Path(config_path).resolve())
    project_dir = str(PROJECT_ROOT)

    env = os.environ.copy()
    env.update({
        "PYTHONPATH": "",
        "PYTHONHOME": "",
        "CONDA_PREFIX": "",
        "CONDA_DEFAULT_ENV": "",
        "CONDA_SHLVL": "0",
        "UV_PYTHON_PREFERENCE": "only-managed",
        "UV_PYTHON": "cpython-3.11",
    })

    return StdioTransport(
        command="uv",
        args=[
            "--directory", project_dir,
            "run", "--python", "3.11",
            "nexustrader-mcp",
            "--config", config_abs,
        ],
        env=env,
        log_file=PROJECT_ROOT / "tests" / "mcp_server.log",
    )


async def wait_for_engine(client: Client, timeout: int = 180) -> bool:
    """Wait for the NexusTrader engine to be ready by polling get_exchange_info."""
    print(f"  Waiting for engine startup (up to {timeout}s) ...", end="", flush=True)
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < timeout:
        try:
            resp, _ = await call_tool(client, "get_exchange_info")
            if isinstance(resp, list) and len(resp) > 0:
                elapsed = time.perf_counter() - t0
                print(f" ready ({elapsed:.0f}s)")
                return True
        except Exception:
            pass
        print(".", end="", flush=True)
        await asyncio.sleep(5)
    print(f" TIMEOUT after {timeout}s")
    return False


async def run_tests(config_path: str, engine_timeout: int = 180):
    transport = build_transport(config_path)

    report = TestReport()
    ctx: dict[str, Any] = {}

    print(f"Starting MCP server ...")
    print(f"  config: {Path(config_path).resolve()}")
    print()

    async with Client(transport) as client:
        print("[OK] MCP server connected\n")

        if not await wait_for_engine(client, timeout=engine_timeout):
            print("\n[FAIL] Engine startup timeout. Check network/config.\n")
            print("  Server log: tests/mcp_server.log")
            return 1

        print("\nRunning tests...")
        print("-" * 78)

        for test_fn in ALL_TESTS:
            fn_name = test_fn.__name__.replace("test_", "")
            print(f"  >> {fn_name} ...", end="", flush=True)
            await test_fn(client, report, ctx)
            last = report.results[-1]
            print(f" {last.status} ({last.elapsed_ms:.0f}ms)")

    report.print_summary()

    fail_count = sum(1 for r in report.results if r.status == "FAIL")
    return fail_count


def main():
    parser = argparse.ArgumentParser(description="Test all NexusTrader MCP tools")
    parser.add_argument(
        "--config", "-c",
        default=str(PROJECT_ROOT / "config.yaml"),
        help="Path to config.yaml (default: project root config.yaml)",
    )
    parser.add_argument(
        "--timeout", "-t",
        type=int,
        default=180,
        help="Engine startup timeout in seconds (default: 180)",
    )
    args = parser.parse_args()

    fail_count = asyncio.run(run_tests(args.config, args.timeout))
    sys.exit(1 if fail_count > 0 else 0)


if __name__ == "__main__":
    main()
