"""
Real market data -- Binance's public REST API. No API key needed for
public price/candle data (confirmed live: reachable, no auth required).
stdlib urllib only, same pattern as telegram.py -- no new dependency for
a handful of HTTP calls to a JSON API.

Crypto only, per CEO decision #12: Nifty options data is a real, separate,
harder problem (no free reliable public NSE option-chain API) -- explicitly
deferred to a later phase, not faked here with placeholder numbers.
"""
import json
import urllib.error
import urllib.request

BASE_URL = "https://api.binance.com/api/v3"


class MarketDataError(RuntimeError):
    pass


def _get(path: str, timeout: int = 10) -> dict:
    try:
        with urllib.request.urlopen(f"{BASE_URL}{path}", timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.URLError as e:
        raise MarketDataError(f"could not reach Binance API: {e}") from e


def current_price(symbol: str) -> float:
    data = _get(f"/ticker/price?symbol={symbol}")
    if "price" not in data:
        raise MarketDataError(f"unexpected response for {symbol}: {data}")
    return float(data["price"])


def closing_prices(symbol: str, interval: str = "1h", limit: int = 100) -> list:
    """Real historical candles. Each Binance kline is
    [open_time, open, high, low, close, volume, ...] -- index 4 is close."""
    data = _get(f"/klines?symbol={symbol}&interval={interval}&limit={limit}")
    if not isinstance(data, list):
        raise MarketDataError(f"unexpected klines response for {symbol}: {data}")
    return [float(k[4]) for k in data]
