import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = os.environ.get("SHAKTHI_DB_PATH", str(ROOT / "shakthi.db"))
AGENTS_DIR = ROOT / "agents"
SCHEMA_PATH = ROOT / "db" / "schema.sql"
WORKSPACES_DIR = ROOT / "workspaces"
TEMPLATES_DIR = ROOT / "templates"

# Local-tier provider for call_local() -- "ollama" (default, genuinely free/
# local) or "codex" (OpenAI Codex CLI, real paid API usage under whatever
# account `codex login` authenticated on this machine -- NOT free just
# because it's called through the "local" call site). Founder directive
# 2026-09-16, scoped to the Linux box specifically (it already has a real
# authenticated `codex` CLI; the Mac does not) -- set via env, not hardcoded,
# so this stays per-machine.
LOCAL_PROVIDER = os.environ.get("SHAKTHI_LOCAL_PROVIDER", "ollama")
CODEX_TIMEOUT_SECONDS = int(os.environ.get("SHAKTHI_CODEX_TIMEOUT", "180"))

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
# 180s was too tight -- gemma4 (9.6GB, CPU-bound on this machine) has taken
# 2:24-3:26 across real calls this session and hit the old timeout at least
# once. 420s gives real headroom without hanging forever on a truly dead
# Ollama process.
OLLAMA_TIMEOUT_SECONDS = int(os.environ.get("SHAKTHI_OLLAMA_TIMEOUT", "420"))

# Cloud escalation is opt-in: unset ANTHROPIC_API_KEY means the system stays
# fully local and any escalation attempt fails loudly instead of silently
# spending money.
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
CLOUD_MODEL = os.environ.get("SHAKTHI_CLOUD_MODEL", "claude-sonnet-5")

# --- Phase 0.2: tool system gates -------------------------------------
# Both are deliberate, out-of-band founder decisions -- not something a
# yaml file (or a manipulated agent) controls alone.
ALLOW_EXEC = os.environ.get("SHAKTHI_ALLOW_EXEC") == "1"
TOOLS_DRY_RUN = os.environ.get("SHAKTHI_TOOLS_DRY_RUN") == "1"

COMMAND_TIMEOUT_SECONDS = int(os.environ.get("SHAKTHI_COMMAND_TIMEOUT", "15"))
MAX_OUTPUT_BYTES = 20_000
MAX_FILE_WRITE_BYTES = 2_000_000
MAX_FILE_READ_BYTES = 2_000_000
MAX_LIST_ENTRIES = 500

DENIED_FILENAME_PATTERNS = (
    ".env", ".git", ".ssh", ".pem", "id_rsa", "id_ed25519", "credentials",
)

# --- WEB-001: external website audit -----------------------------------
WEBSITE_AUDIT_TIMEOUT_SECONDS = int(os.environ.get("SHAKTHI_WEB_AUDIT_TIMEOUT", "15"))
WEBSITE_AUDIT_MAX_LINKS_CHECKED = 25
WEBSITE_AUDIT_USER_AGENT = "ShakthiOS-Sentinel/1.0 (+website-audit)"

# --- Worker Pool ----------------------------------------------------------
# Queue depth above which load_manager scales worker concurrency up.
WORKER_QUEUE_SCALE_THRESHOLD = int(os.environ.get("SHAKTHI_WORKER_SCALE_THRESHOLD", "3"))
# Hard ceiling -- above this, check_queue_overflow alerts; a real backstop,
# not just a scaling knob.
WORKER_QUEUE_MAX_SIZE = int(os.environ.get("SHAKTHI_WORKER_QUEUE_MAX", "50"))
WORKER_CONCURRENCY_LIMITS = {"rapid": 8, "engineering": 3, "infra": 4}
WORKER_BASE_CONCURRENCY = 1  # per worker type, when queue depth is at/under the scale threshold

# --- Dhansetu PDF Studio ---------------------------------------------------
PDF_STUDIO_DIR = ROOT / "pdf_studio_files"  # gitignored; uploads + processed output
PDF_STUDIO_MAX_FILE_BYTES = 50_000_000  # 50MB per uploaded file

# --- Emergency Response Team (ERT) -----------------------------------------
POSTMORTEMS_DIR = ROOT / "postmortems"  # one file per incident, never overwritten

# --- AI usage panel ---------------------------------------------------------
# Optional founder-set daily cloud spend budget for the dashboard's usage
# panel. 0/unset means "no budget configured" -- the panel shows real spend
# with no remaining-budget claim rather than dividing by a number nobody set.
CLOUD_DAILY_BUDGET_USD = float(os.environ.get("SHAKTHI_CLOUD_DAILY_BUDGET_USD", "0") or 0)
# Assumed active hours/day for the local-capacity estimate shown alongside
# real Ollama usage -- a rough, labeled estimate, not a hard limit (local
# has none). Override if this machine actually runs SHAKTHI_OS fewer/more
# hours a day.
LOCAL_OPERATING_HOURS_PER_DAY = float(os.environ.get("SHAKTHI_LOCAL_OPERATING_HOURS", "16"))
