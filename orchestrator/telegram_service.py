"""
Telegram Command Center — the founder-facing layer on top of telegram.py
and report_generators.py.

Credentials: manual entry every time, by design (the founder said the bot
token/chat id change frequently). Every function here takes token/chat_id
as explicit arguments. resolve_credentials() will fall back to
TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID env vars ONLY if nothing is passed in --
that's a convenience for scripted/cron use, never the primary path, and the
CLI always accepts --telegram-token/--telegram-chat-id to override it.
"""
import json
import os

from . import db, report_generators
from . import telegram as tg


def resolve_credentials(token: str = None, chat_id: str = None) -> tuple:
    token = token or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise tg.TelegramError(
            "no Telegram credentials — pass --telegram-token/--telegram-chat-id, "
            "or set TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID for this invocation only"
        )
    return token, chat_id


def send_report(name: str, token: str, chat_id: str, business_id=None) -> dict:
    fn = report_generators.ALL_REPORTS.get(name)
    if not fn:
        raise ValueError(f"unknown report: {name!r}. choices: {list(report_generators.ALL_REPORTS)}")
    try:
        text = fn(business_id=business_id) if name in ("ceo", "finance", "security") else fn()
    except TypeError:
        text = fn()
    return tg.send_message(token, chat_id, text)


def send_daily_reports(token: str, chat_id: str, business_id=None) -> list:
    results = []
    for name in report_generators.ALL_REPORTS:
        try:
            results.append((name, send_report(name, token, chat_id, business_id=business_id)))
        except Exception as e:
            results.append((name, {"error": str(e)}))
    return results


def alert(token: str, chat_id: str, category: str, message: str) -> dict:
    text = f"*SHAKTHI ALERT — {category.upper()}*\n\n{message}"
    return tg.send_message(token, chat_id, text)


# --- Commands -------------------------------------------------------------

def _cmd_status(args):
    with db.get_conn() as conn:
        return (f"*Shakthi Status*\nActive tasks: {db.active_task_count(conn)}\n"
                f"Agents: {len(db.list_agents(conn))}\nBusinesses: {len(db.list_businesses(conn))}")


def _cmd_agents(args):
    with db.get_conn() as conn:
        rows = db.list_agents(conn)
    return "*Agents:*\n" + "\n".join(f"  {a['id']} ({a['layer']}, {a['default_model_tier']})" for a in rows)


def _cmd_websites(args):
    return report_generators.website_health_report_text()


def _cmd_projects(args):
    with db.get_conn() as conn:
        rows = db.list_businesses(conn)
    return "*Businesses:*\n" + "\n".join(f"  #{b['id']} {b['name']}" for b in rows)


def _cmd_memory(args):
    with db.get_conn() as conn:
        rows = db.recent_memory(conn, business_id=None, cross_tenant=True, limit=8)
    return "*Recent Memory:*\n" + "\n".join(f"  [{m['layer']}] {m['content'][:80]}" for m in rows)


def _cmd_health(args):
    return report_generators.agent_health_report_text()


def _cmd_voice(args):
    from . import voice_history
    return voice_history.format_report(limit=10)


COMMANDS = {
    "/status": _cmd_status,
    "/ceo": lambda args: report_generators.ceo_report(),
    "/finance": lambda args: report_generators.finance_report_text(),
    "/security": lambda args: report_generators.security_report_text(),
    "/costs": lambda args: report_generators.cost_ledger_report_text(),
    "/agents": _cmd_agents,
    "/websites": _cmd_websites,
    "/projects": _cmd_projects,
    "/memory": _cmd_memory,
    "/health": _cmd_health,
    "/voice": _cmd_voice,
}


def handle_command(text: str) -> str:
    parts = text.strip().split()
    if not parts:
        return "Send a command: " + ", ".join(sorted(COMMANDS))
    cmd, args = parts[0].lower(), parts[1:]
    fn = COMMANDS.get(cmd)
    if not fn:
        return f"Unknown command {cmd!r}. Available: " + ", ".join(sorted(COMMANDS))
    try:
        return fn(args)
    except Exception as e:
        return f"Error running {cmd}: {e}"


def poll_forever(token: str, chat_id: str = None):
    """Long-polls getUpdates and answers /commands. If chat_id is given,
    only messages from that chat are answered -- otherwise anyone who
    messages the bot can run commands, which is NOT what you want for a
    founder-only control bot. Pass --telegram-chat-id to lock it down."""
    print("Polling Telegram for commands (Ctrl+C to stop)...")
    offset = None
    while True:
        try:
            updates = tg.get_updates(token, offset=offset)
        except tg.TelegramError as e:
            print(f"[telegram] {e}")
            continue
        for update in updates:
            offset = update["update_id"] + 1
            message = update.get("message", {})
            text = message.get("text", "")
            from_chat = str(message.get("chat", {}).get("id", ""))
            if not text.startswith("/"):
                continue
            if chat_id and from_chat != str(chat_id):
                print(f"[telegram] ignoring command from unrecognized chat_id={from_chat}")
                continue
            reply = handle_command(text)
            tg.send_message(token, from_chat, reply)
