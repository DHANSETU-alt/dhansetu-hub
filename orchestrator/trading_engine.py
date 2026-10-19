"""
Trading OS -- Phase 1 (Task 6), per CEO decision #12: crypto spot only,
paper trading only. Two real, standard, well-known strategies -- not an
open-ended rules DSL, which CEO explicitly said to defer until the core
simulation/journaling engine is proven.

Every function here computes real math from real market data
(market_data.py, Binance's public API) -- no invented prices, no
simulated-to-look-good numbers. Positions are simulated (never a real
broker order); every entry and exit is written to trading_journal,
append-only, per the founder's explicit "auto save in trading journal"
requirement.
"""
from . import db, market_data

RULE_TYPES = ("sma_crossover", "rsi_threshold")


class TradingEngineError(RuntimeError):
    pass


def _sma(closes: list, period: int) -> float:
    if len(closes) < period:
        raise TradingEngineError(f"need at least {period} candles, got {len(closes)}")
    return sum(closes[-period:]) / period


def _rsi(closes: list, period: int) -> float:
    """Standard RSI, simple (not Wilder-smoothed) average -- a real,
    honest simplification of the textbook formula, not a different
    indicator wearing the same name. Documented here, not hidden."""
    if len(closes) < period + 1:
        raise TradingEngineError(f"need at least {period + 1} candles, got {len(closes)}")
    deltas = [closes[i] - closes[i - 1] for i in range(-period, 0)]
    gains = [d for d in deltas if d > 0]
    losses = [-d for d in deltas if d < 0]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def create_strategy(name: str, symbol: str, rule_type: str, params: dict) -> dict:
    if rule_type not in RULE_TYPES:
        raise TradingEngineError(f"rule_type must be one of {RULE_TYPES}")
    if rule_type == "sma_crossover":
        for key in ("fast_period", "slow_period", "trade_quantity"):
            if key not in params:
                raise TradingEngineError(f"sma_crossover requires '{key}' in params")
    elif rule_type == "rsi_threshold":
        for key in ("period", "oversold", "overbought", "trade_quantity"):
            if key not in params:
                raise TradingEngineError(f"rsi_threshold requires '{key}' in params")

    with db.get_conn() as conn:
        strategy_id = db.insert_strategy(conn, name, symbol, rule_type, params)
        return _get_strategy(conn, strategy_id)


def _get_strategy(conn, strategy_id: int) -> dict:
    for s in db.list_strategies(conn):
        if s["id"] == strategy_id:
            return s
    raise TradingEngineError(f"no strategy with id {strategy_id}")


def list_strategies(status: str = None) -> list:
    with db.get_conn() as conn:
        return db.list_strategies(conn, status=status)


def set_strategy_status(strategy_id: int, status: str) -> None:
    if status not in ("active", "paused"):
        raise TradingEngineError("status must be 'active' or 'paused'")
    with db.get_conn() as conn:
        db.set_strategy_status(conn, strategy_id, status)


def _signal(strategy: dict, closes: list) -> tuple:
    """Returns (direction, reason) -- direction is 'bullish' | 'bearish'."""
    p = strategy["params"]
    if strategy["rule_type"] == "sma_crossover":
        fast = _sma(closes, p["fast_period"])
        slow = _sma(closes, p["slow_period"])
        if fast > slow:
            return "bullish", f"SMA{p['fast_period']} ({fast:.2f}) above SMA{p['slow_period']} ({slow:.2f})"
        return "bearish", f"SMA{p['fast_period']} ({fast:.2f}) below SMA{p['slow_period']} ({slow:.2f})"
    else:  # rsi_threshold
        rsi = _rsi(closes, p["period"])
        if rsi < p["oversold"]:
            return "bullish", f"RSI({p['period']}) = {rsi:.1f}, below oversold threshold {p['oversold']}"
        if rsi > p["overbought"]:
            return "bearish", f"RSI({p['period']}) = {rsi:.1f}, above overbought threshold {p['overbought']}"
        return "neutral", f"RSI({p['period']}) = {rsi:.1f}, no threshold crossed"


def run_signal_check() -> list:
    """Real, idempotent: fetches real market data, evaluates each active
    strategy's rule, opens/closes simulated positions on real signals,
    journals every fill. Safe to call repeatedly (e.g. from a loop or
    cron) -- a strategy with no open position and no bullish signal does
    nothing; one already in position does nothing until its exit
    condition is real."""
    results = []
    with db.get_conn() as conn:
        strategies = db.list_strategies(conn, status="active")

    for strat in strategies:
        try:
            closes = market_data.closing_prices(strat["symbol"], interval="1h", limit=100)
            price = market_data.current_price(strat["symbol"])
            direction, reason = _signal(strat, closes)
        except market_data.MarketDataError as e:
            results.append({"strategy_id": strat["id"], "action": "error", "detail": str(e)})
            continue

        with db.get_conn() as conn:
            open_pos = db.get_open_position(conn, strat["id"])

            if direction == "bullish" and not open_pos:
                qty = strat["params"]["trade_quantity"]
                position_id = db.open_position(conn, strat["id"], strat["symbol"], qty, price)
                db.insert_journal_entry(conn, position_id, strat["id"], strat["symbol"],
                                         "entry", qty, price, reason)
                results.append({"strategy_id": strat["id"], "action": "entry", "price": price, "reason": reason})

            elif direction == "bearish" and open_pos:
                pnl = (price - open_pos["entry_price"]) * open_pos["quantity"]
                db.close_position(conn, open_pos["id"], price)
                db.insert_journal_entry(conn, open_pos["id"], strat["id"], strat["symbol"],
                                         "exit", open_pos["quantity"], price, reason, pnl=pnl)
                results.append({"strategy_id": strat["id"], "action": "exit", "price": price,
                                 "pnl": pnl, "reason": reason})

            else:
                results.append({"strategy_id": strat["id"], "action": "hold", "reason": reason})

    return results


def list_positions(status: str = None) -> list:
    with db.get_conn() as conn:
        return db.list_positions(conn, status=status)


def list_journal(limit: int = 100) -> list:
    with db.get_conn() as conn:
        return db.list_journal(conn, limit=limit)
