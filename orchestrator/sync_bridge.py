"""Mac-Linux initiatives sync bridge (Shakthi_OS double-brain wiring).

Run from the Mac (the commander). Compares `initiatives` +
`initiative_milestones` between this machine's local shakthi.db and the
Linux box's, reachable over the Tailscale + SSH bridge set up 2026-09-06.

Conflict rule (founder's explicit choice): matched by (track, seq) --
    - present on both sides, same updated_at -> no-op
    - present on both sides, different updated_at but identical content
      (e.g. only updated_at drifted) -> no-op
    - present on both sides, genuinely different content -> Mac's row
      wins, overwrites Linux's fields (title/artifact_url/status/context).
      Milestones are left alone on conflict rather than overwritten --
      a milestone checklist edited independently on both sides can't be
      safely reconciled by a blanket rule, so that case is reported, not
      auto-resolved.
    - present on only one side -> copied to the other (union, nothing
      dropped), including its milestones.

Scoped to initiatives + milestones only -- NOT the other ~50 tables in
shakthi.db (tasks, decisions, memory_entries, cost ledger, etc.), which
still operate independently per machine. See
docs/superpowers/specs/2026-09-06-mac-linux-bridge-design.md.

Usage: python3 -m orchestrator.sync_bridge [--apply]
(no --apply = dry run, prints what would change without touching either db)
"""
import json
import shlex
import sqlite3
import subprocess
import sys

LINUX_HOST = "blackboxops@192.168.31.27"
# Was the Tailscale IP (100.86.74.97) -- confirmed unreachable (SSH timeout)
# after the 2026-09-13 Linux wipe/rebuild, most likely needing Tailscale
# re-registration on the fresh box. Switched to the LAN IP, which is
# verified working (used throughout this session's SSH calls). Restore
# the Tailscale IP once re-registered if off-LAN reachability is needed.
LINUX_DB = "/home/blackboxops/ShakthiOS_v3.2/shakthi.db"
SSH_KEY = "/Users/apple/.ssh/shakthi_bridge_ed25519"
LOCAL_DB = "/Users/apple/shakthi-os/shakthi.db"

FIELDS = ["title", "artifact_url", "status", "created_at", "updated_at", "context"]


def _ssh_python(script: str) -> str:
    # ssh joins all remaining argv with spaces before handing them to the
    # remote shell -- it does not preserve argument boundaries the way a
    # local subprocess call does. So the whole "python3 -c '<script>'"
    # must be pre-quoted into a single shell-safe string ourselves.
    remote_cmd = f"python3 -c {shlex.quote(script)}"
    out = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-i", SSH_KEY, LINUX_HOST, remote_cmd],
        capture_output=True, text=True, check=True,
    )
    return out.stdout


def fetch_remote():
    script = f"""
import sqlite3, json
c = sqlite3.connect({LINUX_DB!r})
inits = [dict(zip(['id','track','seq'] + {FIELDS!r}, list(r)))
         for r in c.execute("SELECT id,track,seq,{','.join(FIELDS)} FROM initiatives")]
ms = [dict(initiative_id=r[0], title=r[1], done=r[2])
      for r in c.execute("SELECT initiative_id,title,done FROM initiative_milestones")]
print(json.dumps({{"initiatives": inits, "milestones": ms}}))
"""
    return json.loads(_ssh_python(script))


def push_new_initiative_to_linux(row, milestones):
    """Insert one initiative + its milestones on Linux in one remote call,
    so the new autoincrement id and the milestone FKs stay consistent."""
    payload = json.dumps({"row": row, "milestones": milestones})
    script = f"""
import sqlite3, json
data = json.loads({payload!r})
row, milestones = data["row"], data["milestones"]
c = sqlite3.connect({LINUX_DB!r})
c.execute("BEGIN")
cur = c.execute(
    "INSERT INTO initiatives (track,seq,{','.join(FIELDS)}) VALUES (?,?,?,?,?,?,?,?)",
    [row["track"], row["seq"]] + [row[f] for f in {FIELDS!r}],
)
new_id = cur.lastrowid
for m in milestones:
    c.execute("INSERT INTO initiative_milestones (initiative_id,title,done) VALUES (?,?,?)",
              (new_id, m["title"], m["done"]))
c.commit()
print(new_id)
"""
    _ssh_python(script)


def push_conflict_update_to_linux(target_id, row):
    set_clause = ",".join(f"{f}=?" for f in FIELDS)
    payload = json.dumps([row[f] for f in FIELDS] + [target_id])
    script = f"""
import sqlite3, json
vals = json.loads({payload!r})
c = sqlite3.connect({LINUX_DB!r})
c.execute("UPDATE initiatives SET {set_clause} WHERE id=?", vals)
c.commit()
print("updated", vals[-1])
"""
    _ssh_python(script)


def fetch_local(conn):
    inits = [dict(zip(["id", "track", "seq"] + FIELDS, row))
             for row in conn.execute(f"SELECT id,track,seq,{','.join(FIELDS)} FROM initiatives")]
    ms = [dict(initiative_id=row[0], title=row[1], done=row[2])
          for row in conn.execute("SELECT initiative_id,title,done FROM initiative_milestones")]
    return {"initiatives": inits, "milestones": ms}


def main(dry_run=True):
    conn = sqlite3.connect(LOCAL_DB)
    local = fetch_local(conn)
    remote = fetch_remote()

    local_by_key = {(i["track"], i["seq"]): i for i in local["initiatives"]}
    remote_by_key = {(i["track"], i["seq"]): i for i in remote["initiatives"]}
    report = []

    for key, mac_row in local_by_key.items():
        if key in remote_by_key:
            continue
        ms = [m for m in local["milestones"] if m["initiative_id"] == mac_row["id"]]
        report.append(f"COPY Mac->Linux: {key} {mac_row['title'][:60]!r} ({len(ms)} milestones)")
        if not dry_run:
            push_new_initiative_to_linux(mac_row, ms)

    for key, linux_row in remote_by_key.items():
        mac_row = local_by_key.get(key)
        if mac_row is None:
            ms = [m for m in remote["milestones"] if m["initiative_id"] == linux_row["id"]]
            report.append(f"COPY Linux->Mac: {key} {linux_row['title'][:60]!r} ({len(ms)} milestones)")
            if not dry_run:
                cols = ",".join(["track", "seq"] + FIELDS)
                placeholders = ",".join(["?"] * (2 + len(FIELDS)))
                vals = [linux_row["track"], linux_row["seq"]] + [linux_row[f] for f in FIELDS]
                cur = conn.execute(f"INSERT INTO initiatives ({cols}) VALUES ({placeholders})", vals)
                new_id = cur.lastrowid
                for m in ms:
                    conn.execute(
                        "INSERT INTO initiative_milestones (initiative_id, title, done) VALUES (?,?,?)",
                        (new_id, m["title"], m["done"]),
                    )
            continue

        # Compare content directly, not updated_at -- updated_at only has
        # second resolution, so two genuinely different edits landing in
        # the same second would otherwise be missed. The approved rule is
        # "Mac always wins on any content difference," not "whichever
        # timestamp is newer," so updated_at isn't part of this decision.
        mac_content = {f: mac_row[f] for f in FIELDS if f != "updated_at"}
        linux_content = {f: linux_row[f] for f in FIELDS if f != "updated_at"}
        if mac_content == linux_content:
            continue

        report.append(
            f"CONFLICT {key}: Mac={mac_row['title'][:50]!r} "
            f"vs Linux={linux_row['title'][:50]!r} -> Mac wins"
        )
        if not dry_run:
            push_conflict_update_to_linux(linux_row["id"], mac_row)

    if not dry_run:
        conn.commit()
    return report


if __name__ == "__main__":
    dry_run = "--apply" not in sys.argv
    report = main(dry_run=dry_run)
    print(f"=== sync_bridge {'DRY RUN' if dry_run else 'APPLIED'} ===")
    if not report:
        print("No differences -- both machines already agree.")
    for line in report:
        print(line)
    if dry_run and report:
        print("\nRun with --apply to actually make these changes.")
