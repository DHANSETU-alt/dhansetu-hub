"""Read-only SHAKTHI_CLOUD readiness adapter for the executive dashboard."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

CLOUD_REPO = Path.home() / "Projects" / "SHAKTHI_CLOUD"
EXPECTED_UUID = "8c5c8a84-47a5-4cb2-9c90-a251d15b6466"

def _run(args: list[str]) -> str | None:
    if not shutil.which(args[0]): return None
    try: return subprocess.run(args, capture_output=True, text=True, timeout=2, check=True).stdout.strip()
    except (OSError, subprocess.SubprocessError): return None

def cloud_status() -> dict[str, Any]:
    disk = _run(["lsblk", "-J", "-o", "PATH,FSTYPE,LABEL,UUID,MOUNTPOINTS"])
    storage = {"state": "UNAVAILABLE", "device": "/dev/sda1", "label": None, "uuid": None, "mounted": False}
    if disk:
        for device in json.loads(disk).get("blockdevices", []):
            for child in device.get("children") or []:
                if child.get("path") == "/dev/sda1":
                    storage = {"state": "LOCAL", "device": child["path"], "label": child.get("label"), "uuid": child.get("uuid"), "mounted": bool(child.get("mountpoints") and any(child["mountpoints"]))}
    docker_access = _run(["docker", "info", "--format", "{{.ServerVersion}}"])
    milestones = [
        {"id":"repository","label":"Cloud repository","state":"VERIFIED" if (CLOUD_REPO/".git").exists() else "NOT CONNECTED"},
        {"id":"storage","label":"SSD formatted","state":"VERIFIED" if storage.get("uuid") == EXPECTED_UUID and storage.get("label") == "SHAKTHI_CLOUD" else "NOT CONNECTED"},
        {"id":"mount","label":"Stable SSD mount","state":"VERIFIED" if storage.get("mounted") else "PLANNED"},
        {"id":"docker","label":"Docker runtime access","state":"VERIFIED" if docker_access else "NOT CONNECTED"},
        {"id":"nextcloud","label":"Nextcloud service","state":"NOT CONNECTED"},
        {"id":"tunnel","label":"Secure tunnel","state":"NOT CONNECTED"},
        {"id":"domain","label":"blackboxops.co.in","state":"EXTERNAL VERIFICATION REQUIRED"},
        {"id":"backups","label":"Off-device backups","state":"NOT CONNECTED"},
    ]
    verified = sum(item["state"] == "VERIFIED" for item in milestones)
    return {"source":"LOCAL READ-ONLY PREFLIGHT","repository":str(CLOUD_REPO),"storage":storage,"dockerVersion":docker_access,"milestones":milestones,"progressPercent":round(verified/len(milestones)*100),"health":"NOT CONNECTED"}
