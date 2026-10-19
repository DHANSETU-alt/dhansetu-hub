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
import time
import urllib.error
import urllib.parse
import urllib.request

API_BASE = "https://api.telegram.org/bot{token}/{method}"

# Telegram's MarkdownV2 spec: these characters MUST be escaped with a
# backslash anywhere they appear outside real formatting entities, or the
# whole message is rejected with "can't parse entities". This codebase's
# real report content is full of underscores (agent_id, template_landing_v1,
# file paths) -- legacy "Markdown" mode treats a lone underscore as an
# unclosed italic marker and breaks constantly; MarkdownV2 with real
# escaping is the actually-safe way to get bold headers.
_MDV2_SPECIAL = set(r"_*[]()~`>#+-=|{}.!\\")


class TelegramError(RuntimeError):
    pass


def format_report_md(title: str, body: str) -> str:
    """Bold title (must be a static string this codebase writes, never
    dynamic data) + fully-escaped body -- the safe default for every
    multi-line report this system sends, so a report's own content can
    never break Telegram's MarkdownV2 parser regardless of what real data
    ends up in it."""
    return f"*{escape_markdown_v2(title)}*\n\n{escape_markdown_v2(body)}"


def escape_markdown_v2(text: str) -> str:
    """Escape all MarkdownV2 special characters in DYNAMIC content before
    interpolating it into a report string. Never call this on the bold
    markers/section headers you write yourself -- only on values that come
    from data (agent ids, file paths, goal text, urls, etc)."""
    return "".join(f"\\{c}" if c in _MDV2_SPECIAL else c for c in str(text))


def _call(token: str, method: str, params: dict, timeout: int = 15) -> dict:
    if not token:
        raise TelegramError("no bot token provided")
    url = API_BASE.format(token=token, method=method)
    data = urllib.parse.urlencode(params).encode()

    # Real incident, 2026-09-16/17: an unattended overnight cron run hit
    # "Connection reset by peer" on an otherwise-healthy Telegram API and
    # the alert was simply lost -- no other layer retries. This is a
    # transient network-level failure (confirmed: an immediate manual
    # retry succeeded with identical params), not a bad request, so one
    # short retry is the honest fix -- not a longer backoff loop that
    # would delay a real outage alert.
    last_error = None
    for attempt in range(2):
        req = urllib.request.Request(url, data=data, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = json.loads(resp.read())
            break
        except urllib.error.URLError as e:
            last_error = e
            if attempt == 0:
                time.sleep(2)
    else:
        raise TelegramError(f"could not reach Telegram API after retry: {last_error}") from last_error

    if not body.get("ok"):
        raise TelegramError(f"Telegram API error: {body.get('description', body)}")
    return body["result"]


def send_message(token: str, chat_id: str, text: str, parse_mode: str = "MarkdownV2") -> dict:
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
