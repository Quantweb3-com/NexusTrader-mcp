"""Convert NexusTrader msgspec Struct objects to JSON-serializable dicts."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Optional

from nexustrader.schema import (
    AccountBalance,
    Balance,
    BaseMarket,
    BookL1,
    FundingRate,
    IndexPrice,
    Kline,
    MarkPrice,
    Order,
    Position,
    Ticker,
)


def _dec(v: Optional[Decimal]) -> Optional[str]:
    return str(v) if v is not None else None


def _enum(v) -> Optional[str]:
    return v.value if v is not None else None


def serialize_balance(b: Balance) -> Dict[str, Any]:
    return {"asset": b.asset, "free": _dec(b.free), "locked": _dec(b.locked), "total": _dec(b.total)}


def serialize_account_balance(ab: AccountBalance) -> Dict[str, Any]:
    return {
        "balances": {
            asset: serialize_balance(bal) for asset, bal in ab.balances.items()
        },
    }


def serialize_position(pos: Position) -> Dict[str, Any]:
    return {
        "symbol": pos.symbol,
        "exchange": _enum(pos.exchange),
        "side": _enum(pos.side),
        "signed_amount": _dec(pos.signed_amount),
        "entry_price": str(pos.entry_price) if pos.entry_price is not None else None,
        "unrealized_pnl": str(pos.unrealized_pnl) if pos.unrealized_pnl is not None else None,
        "realized_pnl": str(pos.realized_pnl) if pos.realized_pnl is not None else None,
    }


def serialize_order(o: Order) -> Dict[str, Any]:
    return {
        "oid": o.oid,
        "eid": o.eid,
        "exchange": _enum(o.exchange),
        "symbol": o.symbol,
        "side": _enum(o.side),
        "type": _enum(o.type),
        "status": _enum(o.status),
        "amount": _dec(o.amount),
        "filled": _dec(o.filled),
        "remaining": _dec(o.remaining),
        "price": o.price,
        "average": o.average,
        "fee": _dec(o.fee),
        "fee_currency": o.fee_currency,
        "reduce_only": o.reduce_only,
        "timestamp": o.timestamp,
    }


def serialize_bookl1(b: BookL1) -> Dict[str, Any]:
    return {
        "symbol": b.symbol,
        "exchange": _enum(b.exchange),
        "bid": b.bid,
        "ask": b.ask,
        "bid_size": b.bid_size,
        "ask_size": b.ask_size,
        "mid": b.mid,
        "spread": b.spread,
        "timestamp": b.timestamp,
    }


def serialize_kline(k: Kline) -> Dict[str, Any]:
    return {
        "symbol": k.symbol,
        "exchange": _enum(k.exchange),
        "interval": _enum(k.interval),
        "open": k.open,
        "high": k.high,
        "low": k.low,
        "close": k.close,
        "volume": k.volume,
        "start": k.start,
        "timestamp": k.timestamp,
        "confirm": k.confirm,
    }


def serialize_ticker(t: Ticker) -> Dict[str, Any]:
    return {
        "symbol": t.symbol,
        "exchange": _enum(t.exchange),
        "last_price": t.last_price,
        "volume": t.volume,
        "volume_currency": t.volumeCcy,
        "timestamp": t.timestamp,
    }


def serialize_funding_rate(fr: FundingRate) -> Dict[str, Any]:
    return {
        "symbol": fr.symbol,
        "exchange": _enum(fr.exchange),
        "rate": fr.rate,
        "timestamp": fr.timestamp,
        "next_funding_time": fr.next_funding_time,
    }


def serialize_mark_price(mp: MarkPrice) -> Dict[str, Any]:
    return {
        "symbol": mp.symbol,
        "exchange": _enum(mp.exchange),
        "price": mp.price,
        "timestamp": mp.timestamp,
    }


def serialize_index_price(ip: IndexPrice) -> Dict[str, Any]:
    return {
        "symbol": ip.symbol,
        "exchange": _enum(ip.exchange),
        "price": ip.price,
        "timestamp": ip.timestamp,
    }


def serialize_market(m: BaseMarket) -> Dict[str, Any]:
    return {
        "id": m.id,
        "symbol": m.symbol,
        "base": m.base,
        "quote": m.quote,
        "type": _enum(m.type),
        "spot": m.spot,
        "swap": m.swap,
        "future": m.future,
        "linear": m.linear,
        "inverse": m.inverse,
        "active": m.active,
        "contract_size": m.contractSize,
        "taker_fee": m.taker,
        "maker_fee": m.maker,
        "precision": {
            "amount": m.precision.amount,
            "price": m.precision.price,
        },
        "limits": {
            "amount": {
                "min": m.limits.amount.min if m.limits.amount else None,
                "max": m.limits.amount.max if m.limits.amount else None,
            },
            "price": {
                "min": m.limits.price.min if m.limits.price else None,
                "max": m.limits.price.max if m.limits.price else None,
            },
        },
    }
