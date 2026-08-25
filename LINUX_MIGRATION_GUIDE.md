# SHAKTHI OS — Linux Migration Guide (Ubuntu 24.04 LTS)

Run these in order. Each step is real, tested-pattern commands for Ubuntu 24.04 — not placeholders. Where a step differs meaningfully from the macOS setup, that's called out explicitly.

## 0. Prerequisites

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl git build-essential
```

## 1. Restore the project

```bash
mkdir -p ~/shakthi-os
tar -xzf shakthi_os_backup_<DATE>.tar.gz -C ~/shakthi-os
cd ~/shakthi-os
chmod +x start_dashboard.sh stop_dashboard.sh   # tar preserves the exec bit; re-set it if restoring
                                                  # from a filesystem that doesn't (e.g. a FAT/exFAT drive)
```

## 2. Ollama Installation

```bash
curl -fsSL https://ollama.com/install.sh | sh
```
Installs Ollama as a systemd service (`ollama.service`), already enabled and started — this replaces macOS's launchd auto-start, no extra step needed here (unlike the API/dashboard below, which do need one).

Pull the two models this project uses (11.6 GB total, real sizes from the source machine):
```bash
ollama pull llama3.2      # 2.0 GB — used by most agents
ollama pull gemma4        # 9.6 GB — slower, used where individual agents/*.yaml specify it
```

Verify:
```bash
ollama list
curl http://localhost:11434/api/tags   # should return 200 with both models listed
```

## 3. Python Environment Setup

Ubuntu 24.04 ships Python 3.12 by default — this project was built and tested against 3.14 on macOS but has no 3.14-specific code; 3.12 is fine and actually simplifies one thing (see faster-whisper note below).

```bash
sudo apt install -y python3 python3-venv python3-pip
cd ~/shakthi-os
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Notes carried over from `requirements.txt` (real blockers hit on macOS, worth knowing before you hit the Linux equivalents):
- `faster-whisper` pulls in `av` (PyAV) as a transitive dependency of some install paths; on Ubuntu this builds cleanly with `build-essential` + `ffmpeg` dev headers already present via apt (`sudo apt install -y ffmpeg`) — the macOS blocker (no Homebrew, no pkg-config) doesn't apply here.
- Voice Commander needs a working audio input device (`sounddevice` → PortAudio): `sudo apt install -y libportaudio2`.
- Cloud escalation (optional): `pip install anthropic` and set `ANTHROPIC_API_KEY` — only if you want Claude escalation; the system runs fully local without it, same as on macOS.

## 4. Database

SQLite needs no installation on a fresh Ubuntu box beyond what Python already provides (`sqlite3` is stdlib). Restore `shakthi.db` from the backup and it works as-is — SQLite database files are portable across OSes byte-for-byte, no conversion needed.

```bash
sqlite3 shakthi.db ".tables"    # sanity check after restore — should list 21+ tables
```

### PostgreSQL Setup (optional — only if you also want the SQLite→Postgres engine migration)

The schema was deliberately designed for this (`tenant_id`/`business_id` on every row already), but **this is a separate, larger project from the OS migration** — don't block getting SHAKTHI OS running again on this. If/when you do it:

```bash
sudo apt install -y postgresql postgresql-contrib
sudo -u postgres createuser --superuser shakthi
sudo -u postgres createdb shakthi_os -O shakthi
```
Then: adapt `db/schema.sql`'s few SQLite-isms (`AUTOINCREMENT` → `SERIAL`/`GENERATED ALWAYS AS IDENTITY`, `TEXT DEFAULT CURRENT_TIMESTAMP` works as-is in Postgres too), write a one-time migration script (`orchestrator/db.py`'s `get_conn()` is the single choke point to swap `sqlite3.connect()` for `psycopg2.connect()` — every other function already goes through it). Not done as part of this guide; flagging it as the concrete next step if you choose to pursue it.

### Docker Setup (optional)

SHAKTHI OS itself has no Docker dependency today — nothing in this codebase requires a container. Install it only if you want to run Postgres in a container instead of natively (above), or plan to containerize the API/dashboard later:

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER   # log out/in after this for the group change to take effect
docker --version
```

## 5. Dashboard Setup

```bash
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt install -y nodejs
node --version    # v20.x or later expected for Next.js 16
cd ~/shakthi-os/dashboard
npm install       # rebuilds node_modules from package-lock.json — not part of the backup
```

## 6. SHAKTHI OS Startup Procedure

Same two scripts as macOS — they're plain bash, no macOS-specific commands inside (`start_dashboard.sh`/`stop_dashboard.sh` use `lsof`, `curl`, `nohup`, all available on Ubuntu via `apt install lsof` if not already present):

```bash
cd ~/shakthi-os
python3 -m orchestrator.cli --init      # creates shakthi.db tables if not restored, registers all 15 agents
./start_dashboard.sh                     # http://localhost:3000, http://127.0.0.1:8787
```

### Optional: make it survive a reboot (systemd, closer to how Ollama already behaves)

macOS's launchd auto-started Ollama; the API and dashboard were manual (`start_dashboard.sh`). To make all three behave the same way on Ubuntu:

```bash
sudo tee /etc/systemd/system/shakthi-api.service > /dev/null <<'EOF'
[Unit]
Description=Shakthi OS API
After=network.target

[Service]
WorkingDirectory=/home/YOUR_USER/shakthi-os
ExecStart=/home/YOUR_USER/shakthi-os/.venv/bin/python3 -m orchestrator.api
Restart=on-failure
User=YOUR_USER

[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/systemd/system/shakthi-dashboard.service > /dev/null <<'EOF'
[Unit]
Description=Shakthi OS Dashboard
After=network.target shakthi-api.service

[Service]
WorkingDirectory=/home/YOUR_USER/shakthi-os/dashboard
ExecStart=/usr/bin/npm run dev
Restart=on-failure
User=YOUR_USER

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now shakthi-api shakthi-dashboard
```
Replace `YOUR_USER` with your actual Ubuntu username in both files first. This is optional infrastructure the guide adds for you — it did not exist on the macOS setup (which relied on manual `start_dashboard.sh`).

## 7. Post-migration verification checklist

```bash
cd ~/shakthi-os
source .venv/bin/activate
python3 -m unittest discover -s tests    # expect 144/144 passing, same as on macOS
curl http://127.0.0.1:8787/api/health    # {"db_ok": true, ...}
curl -o /dev/null -s -w "%{http_code}\n" http://localhost:3000/   # 200
```
If tests fail on a fresh restore, it's almost always one of: `ollama list` missing a model, `.venv` not activated, or `shakthi.db` not restored to the project root (see BACKUP_CHECKLIST.md for the exact restore order).
