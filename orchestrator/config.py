import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = os.environ.get("SHAKTHI_DB_PATH", str(ROOT / "shakthi.db"))
AGENTS_DIR = ROOT / "agents"
SCHEMA_PATH = ROOT / "db" / "schema.sql"
WORKSPACES_DIR = ROOT / "workspaces"
TEMPLATES_DIR = ROOT / "templates"

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
