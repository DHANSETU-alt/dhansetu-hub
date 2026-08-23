"""
Thin Telegram Bot API wrapper. stdlib urllib only, same pattern as
model_gateway's Ollama calls -- no new dependency for a handful of HTTP
calls to a JSON API.

Token and chat_id are ALWAYS passed in explicitly by the caller, never read
from a stored config file -- the founder said these change frequently and
wants manual entry each time, not a cached value that goes stale silently.
An env var fallback exists purely as a convenience (see telegram_service.py
resolve_credentials()), never as the only path.
"""
import json
import urllib.error
import urllib.parse
import urllib.request

API_BASE = "https://api.telegram.org/bot{token}/{method}"


class TelegramError(RuntimeError):
    pass


def _call(token: str, method: str, params: dict, timeout: int = 15) -> dict:
    if not token:
        raise TelegramError("no bot token provided")
    url = API_BASE.format(token=token, method=method)
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read())
    except urllib.error.URLError as e:
        raise TelegramError(f"could not reach Telegram API: {e}") from e

    if not body.get("ok"):
        raise TelegramError(f"Telegram API error: {body.get('description', body)}")
    return body["result"]


def send_message(token: str, chat_id: str, text: str, parse_mode: str = "Markdown") -> dict:
    # Telegram caps messages at 4096 chars -- truncate rather than fail.
    if len(text) > 4000:
        text = text[:3990] + "\n...[truncated]"
    params = {"chat_id": chat_id, "text": text}
    if parse_mode:
        # Omit entirely when falsy -- passing parse_mode=None urlencodes as
        # the literal string "None", which isn't a valid Telegram parse
        # mode and would get rejected. Found live sending a plain-text
        # report that intentionally passed parse_mode=None to avoid
        # Markdown special-character parse errors on unescaped text.
        params["parse_mode"] = parse_mode
    return _call(token, "sendMessage", params)


def get_updates(token: str, offset: int = None, timeout: int = 25) -> list:
    params = {"timeout": timeout}
    if offset is not None:
        params["offset"] = offset
    return _call(token, "getUpdates", params, timeout=timeout + 10)


def get_me(token: str) -> dict:
    return _call(token, "getMe", {})
