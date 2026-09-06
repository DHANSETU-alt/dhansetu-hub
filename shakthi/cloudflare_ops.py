"""Read-only Cloudflare/domain incident helpers."""
from __future__ import annotations
import socket
import subprocess
from datetime import datetime, timezone
from typing import Any

from .auto_mode import AutoModePolicy
from .browser_operator import BrowserOperator
from .executive_loop import ExecutiveLoop, MissionState


MISSION = "CF-DNS-DHANSETU-001"


def ensure_incident(loop: ExecutiveLoop | None = None) -> dict[str, Any]:
    """Create the Cloudflare incident and its governed task plan idempotently."""
    loop = loop or ExecutiveLoop()
    t = datetime.now(timezone.utc).isoformat()
    with loop.db() as c:
        c.execute("INSERT OR IGNORE INTO missions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            MISSION, "Resolve dhansetuhub.in Invalid Nameservers", "PROJECT\nSHAKTHI_OS 3.1\n\nOBJECTIVE\nDiagnose and safely resolve the Cloudflare nameserver mismatch.",
            MissionState.PLANNING, "MEDIUM", 0, '["real Cloudflare evidence", "DNS verification", "Guardian review"]', 60, None, None, t, t, t))
        tasks = [
            ("T1", "Cloudflare authenticated recon", "Cloudflare Ops Agent", "Inspect zone, assigned nameservers, DNSSEC, records and alerts."),
            ("T2", "Registrar and authoritative nameserver recon", "Domain Ops Agent", "Determine registrar and compare current vs required nameservers."),
            ("T3", "Risk classification", "Security Guardian", "Classify correction and record rollback path."),
            ("T4", "Zone verification", "Cloudflare Ops Agent", "Recheck Cloudflare status after any authorized change."),
            ("T5", "DNS and HTTP verification", "QA Agent", "Verify NS, A/AAAA/CNAME, DNSSEC and HTTPS reachability."),
            ("T6", "Post-change monitoring", "Sentinel", "Monitor until ACTIVE_VERIFIED or WAITING_EXTERNAL."),
        ]
        for suffix, title, owner, acceptance in tasks:
            tid = f"{MISSION}-{suffix}"
            c.execute("INSERT OR IGNORE INTO tasks VALUES(?,?,?,?,?,?,?,?,?,?,?)", (tid, MISSION, title, owner, "[]", "MEDIUM" if suffix in {"T1", "T2", "T5", "T6"} else "LOW", f'["{acceptance}"]', "READY", "PLANNING", t, t))
    loop.event(MISSION, "MISSION_CREATED", "Cloudflare nameserver incident plan created", "Angella Executive Loop")
    loop.event(MISSION, "PLAN_CREATED", "T1-T6 governed dependency plan", "Mission Planner")
    return loop.mission(MISSION)


def inspect_domain(domain: str = "dhansetuhub.in", *, browser: BrowserOperator | None = None) -> dict[str, Any]:
    browser_result = (browser or BrowserOperator()).inspect("https://dash.cloudflare.com/")
    try:
        ns = socket.getaddrinfo(domain, 443, type=socket.SOCK_STREAM)
        addresses = sorted({row[4][0] for row in ns})
    except OSError as exc:
        addresses = []
        browser_result["dns_error"] = str(exc)
    try:
        raw = subprocess.run(["dig", "+short", "NS", domain], capture_output=True, text=True, timeout=5, check=False).stdout
        nameservers = [x.strip().rstrip(".") for x in raw.splitlines() if x.strip()]
    except (OSError, subprocess.SubprocessError):
        nameservers = []
    return {"mission": MISSION, "domain": domain, "browser": browser_result, "nameservers": nameservers, "addresses": addresses, "state": "DIAGNOSED" if nameservers else "WAITING_EXTERNAL"}


def record_inspection(policy: AutoModePolicy, evidence: dict[str, Any]) -> dict[str, Any]:
    return policy.audit(mission=MISSION, task="T1/T2", agent="Cloudflare Ops / Domain Ops", target=evidence["domain"], action="inspect_domain", risk="LOW", before_state={"nameservers": evidence["nameservers"]}, after_state=evidence, verification="read-only DNS lookup", rollback="none required", result=evidence["state"])
