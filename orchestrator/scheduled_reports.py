"""
Meant to be invoked BY actual cron, not run as a long-lived Python
scheduler daemon. See README for real crontab lines.

Phase 0.3 behavior change: Google Sheets is now the system of record for
reporting. This script's job is (1) sync Sheets, (2) run the Telegram alert
sweep. It does NOT send full report text to Telegram anymore -- that's the
explicit "Telegram must NOT send full reports" requirement. A founder can
still pull one full report on demand via `cli --telegram-send <report>`;
that's a person asking, not the automated path pushing.

Sheets credentials and Telegram token/chat-id are always passed explicitly
(argv), per the founder's "changing frequently, manual entry" requirement.
"""
import argparse
import sys

from . import alerts, sheets
from . import telegram_service as ts


def run(period: str, sheets_credentials: str, sheets_id: str, telegram_token: str, telegram_chat_id: str,
        tax_rate: float, skip_sheets: bool = False, skip_alerts: bool = False):
    if not skip_sheets:
        if not sheets_credentials or not sheets_id:
            print("Skipping Sheets sync: --sheets-credentials and --sheets-id are required", file=sys.stderr)
        else:
            print(f"Syncing Google Sheets ({period})...")
            result = sheets.sync_all(sheets_credentials, sheets_id, period=period, tax_rate=tax_rate)
            for name, r in result.items():
                print(f"  {name}: {r}")

    if not skip_alerts:
        token, chat_id = ts.resolve_credentials(telegram_token, telegram_chat_id)
        print("Running Telegram alert sweep...")
        sent = alerts.run_sweep(token, chat_id)
        for category, count in sent.items():
            print(f"  {category}: {count} alert(s) sent")


def main():
    parser = argparse.ArgumentParser(description="Sync Google Sheets and run the Telegram alert sweep")
    parser.add_argument("--period", choices=["daily", "weekly", "monthly", "quarterly", "yearly"], default="daily")
    parser.add_argument("--sheets-credentials", help="Path to a Google service account JSON key")
    parser.add_argument("--sheets-id", help="Target spreadsheet ID")
    parser.add_argument("--tax-rate", type=float, default=None, help="Fraction, e.g. 0.18 for 18%% -- overrides SHAKTHI_DEFAULT_TAX_RATE")
    parser.add_argument("--telegram-token")
    parser.add_argument("--telegram-chat-id")
    parser.add_argument("--skip-sheets", action="store_true")
    parser.add_argument("--skip-alerts", action="store_true")
    args = parser.parse_args()

    from . import sheets as sheets_mod
    tax_rate = args.tax_rate if args.tax_rate is not None else sheets_mod.DEFAULT_TAX_RATE

    try:
        run(args.period, args.sheets_credentials, args.sheets_id, args.telegram_token, args.telegram_chat_id,
            tax_rate, skip_sheets=args.skip_sheets, skip_alerts=args.skip_alerts)
    except Exception as e:
        print(f"scheduled_reports failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
