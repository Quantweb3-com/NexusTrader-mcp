from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, field_validator

from nexustrader.config import (
    BasicConfig,
    Config,
    LogConfig,
    PrivateConnectorConfig,
    PublicConnectorConfig,
)
from nexustrader.constants import ExchangeType

from nexustrader.exchange import (
    BinanceAccountType,
    BybitAccountType,
    OkxAccountType,
    HyperLiquidAccountType,
    BitgetAccountType,
)

ACCOUNT_TYPE_MAP: Dict[str, Dict[str, Any]] = {
    "binance": {e.value: e for e in BinanceAccountType},
    "bybit": {e.value: e for e in BybitAccountType},
    "okx": {e.value: e for e in OkxAccountType},
    "hyperliquid": {e.value: e for e in HyperLiquidAccountType},
    "bitget": {e.value: e for e in BitgetAccountType},
}

TESTNET_KEYWORDS = {"TESTNET", "DEMO", "demo"}


# ---------------------------------------------------------------------------
# Pydantic config models
# ---------------------------------------------------------------------------

class ExchangeConfig(BaseModel):
    account_type: str
    api_key: Optional[str] = None
    secret: Optional[str] = None
    passphrase: Optional[str] = None
    env_prefix: Optional[str] = None
    settings_key: Optional[str] = None
    symbols: List[str] = []
    subscribe: List[str] = []

    @field_validator("account_type")
    @classmethod
    def upper_account_type(cls, v: str) -> str:
        return v.strip()


class MCPConfig(BaseModel):
    strategy_id: str = "nexus_mcp"
    user_id: str = "mcp_user"
    exchanges: Dict[str, ExchangeConfig]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_testnet(account_type_str: str) -> bool:
    return any(kw in account_type_str for kw in TESTNET_KEYWORDS)


def _infer_settings_key(exchange_name: str, account_type_str: str) -> str:
    label = "DEMO" if _is_testnet(account_type_str) else "LIVE"
    return f"{exchange_name.upper()}.{label}"


def _resolve_account_type(exchange_name: str, account_type_str: str):
    exchange_key = exchange_name.lower()
    mapping = ACCOUNT_TYPE_MAP.get(exchange_key)
    if mapping is None:
        raise ValueError(f"不支持的交易所: {exchange_name}")

    at = mapping.get(account_type_str)
    if at is None:
        valid = ", ".join(sorted(mapping.keys()))
        raise ValueError(
            f"交易所 {exchange_name} 不支持 account_type '{account_type_str}'。"
            f"可选值: {valid}"
        )
    return at


def _build_basic_config(exchange_name: str, exc_cfg: ExchangeConfig) -> BasicConfig:
    is_test = _is_testnet(exc_cfg.account_type)

    if exc_cfg.api_key and exc_cfg.secret:
        return BasicConfig(
            api_key=exc_cfg.api_key,
            secret=exc_cfg.secret,
            passphrase=exc_cfg.passphrase,
            testnet=is_test,
        )

    if exc_cfg.env_prefix:
        return BasicConfig.from_env(exc_cfg.env_prefix, testnet=is_test)

    settings_key = exc_cfg.settings_key or _infer_settings_key(
        exchange_name, exc_cfg.account_type
    )
    return BasicConfig(settings_key=settings_key, testnet=is_test)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def find_config_path(cli_path: Optional[str] = None) -> Path:
    """按优先级查找 config.yaml。"""
    candidates = []

    if cli_path:
        candidates.append(Path(cli_path))

    candidates.append(Path.cwd() / "config.yaml")
    candidates.append(Path.home() / ".nexustrader-mcp" / "config.yaml")

    for p in candidates:
        if p.is_file():
            return p

    print(
        "找不到配置文件 config.yaml。\n"
        "请运行 `nexustrader-mcp setup` 生成配置，或通过 --config 指定路径。",
        file=sys.stderr,
    )
    sys.exit(1)


def load_mcp_config(path: Path) -> MCPConfig:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return MCPConfig(**raw)


class SubscriptionInfo:
    """记录需要预订阅的行情信息。"""

    def __init__(self):
        self.items: List[Dict[str, Any]] = []

    def add(self, sub_type: str, symbols: List[str], **kwargs):
        self.items.append({"type": sub_type, "symbols": symbols, **kwargs})


def build_nexus_config(
    mcp_cfg: MCPConfig,
    strategy,
) -> tuple[Config, SubscriptionInfo]:
    """将 MCPConfig 转换为 NexusTrader 原生 Config + 订阅信息。"""
    basic_configs: Dict[ExchangeType, BasicConfig] = {}
    public_conn_configs: Dict[ExchangeType, List[PublicConnectorConfig]] = {}
    private_conn_configs: Dict[ExchangeType, List[PrivateConnectorConfig]] = {}
    subscriptions = SubscriptionInfo()

    for exchange_name, exc_cfg in mcp_cfg.exchanges.items():
        exchange_type = ExchangeType(exchange_name.lower())
        account_type = _resolve_account_type(exchange_name, exc_cfg.account_type)

        basic_configs[exchange_type] = _build_basic_config(exchange_name, exc_cfg)

        public_conn_configs[exchange_type] = [
            PublicConnectorConfig(account_type=account_type, enable_rate_limit=True)
        ]

        private_conn_configs[exchange_type] = [
            PrivateConnectorConfig(account_type=account_type, enable_rate_limit=True)
        ]

        if exc_cfg.symbols and exc_cfg.subscribe:
            for sub_type in exc_cfg.subscribe:
                subscriptions.add(sub_type, exc_cfg.symbols)

    config = Config(
        strategy_id=mcp_cfg.strategy_id,
        user_id=mcp_cfg.user_id,
        strategy=strategy,
        basic_config=basic_configs,
        public_conn_config=public_conn_configs,
        private_conn_config=private_conn_configs,
        log_config=LogConfig(level_stdout="WARNING"),
    )
    return config, subscriptions
