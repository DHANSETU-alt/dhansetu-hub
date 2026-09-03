"""Read-only host telemetry with macOS adapters and explicit availability."""

from __future__ import annotations

import platform
import shutil
import subprocess
import time
from dataclasses import dataclass
from typing import Any

import psutil


def metric(value: Any = None, *, state: str = "LIVE", reason: str | None = None) -> dict[str, Any]:
    return {"value": value, "state": state, "reason": reason}


def _command(args: list[str], timeout: float = 3) -> str | None:
    if not shutil.which(args[0]):
        return None
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=True).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def _mac_profile() -> dict[str, Any]:
    chip = _command(["sysctl", "-n", "machdep.cpu.brand_string"]) or _command(["sysctl", "-n", "hw.model"])
    return {
        "chip": metric(chip, state="LOCAL") if chip else metric(state="UNAVAILABLE", reason="sysctl did not expose chip model"),
        "gpu": metric(state="UNAVAILABLE", reason="GPU activity requires a privileged/native macOS sensor bridge"),
        "thermal": metric(state="UNAVAILABLE", reason="Thermal state requires ProcessInfo/IOKit bridge"),
        "fans": metric(state="UNAVAILABLE", reason="Fan sensors are not exposed on all Macs and may require permission"),
    }


@dataclass
class _NetworkSample:
    timestamp: float
    sent: int
    received: int


class TelemetryCollector:
    def __init__(self) -> None:
        counters = psutil.net_io_counters()
        self._network = _NetworkSample(time.monotonic(), counters.bytes_sent, counters.bytes_recv)
        self._static_at = 0.0
        self._static: dict[str, Any] = {}

    def _static_profile(self) -> dict[str, Any]:
        if time.monotonic() - self._static_at < 60 and self._static:
            return self._static
        uname = platform.uname()
        mac = _mac_profile() if uname.system == "Darwin" else {
            "chip": metric(uname.processor or uname.machine, state="LOCAL"),
            "gpu": metric(state="UNAVAILABLE", reason="Linux GPU collector is not configured"),
            "thermal": metric(state="UNAVAILABLE", reason="Linux thermal sensor access is not configured"),
            "fans": metric(state="UNAVAILABLE", reason="Linux fan sensor access is not configured"),
        }
        self._static = {"os": uname.system, "os_version": uname.release, "hostname": uname.node, **mac}
        self._static_at = time.monotonic()
        return self._static

    def collect(self) -> dict[str, Any]:
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        disk = psutil.disk_usage("/")
        battery = psutil.sensors_battery()
        counters = psutil.net_io_counters()
        now = time.monotonic()
        elapsed = max(0.1, now - self._network.timestamp)
        download = max(0, counters.bytes_recv - self._network.received) / elapsed
        upload = max(0, counters.bytes_sent - self._network.sent) / elapsed
        self._network = _NetworkSample(now, counters.bytes_sent, counters.bytes_recv)
        cpu = psutil.cpu_percent(interval=None)
        storage_pct = disk.percent
        thermal_state = self._static_profile()["thermal"].get("value")
        penalty = max(0, cpu - 70) * 0.3 + max(0, memory.percent - 75) * 0.5 + max(0, storage_pct - 80) * 0.7
        if thermal_state in {"serious", "critical"}:
            penalty += 20
        score = max(0, min(100, round(100 - penalty)))
        return {
            "source": "LOCAL", "collected_at": time.time(), "system": self._static_profile(),
            "cpu": {"usage_percent": metric(round(cpu, 1)), "logical_cores": metric(psutil.cpu_count(), state="LOCAL")},
            "memory": {"used": metric(memory.used), "total": metric(memory.total), "available": metric(memory.available),
                       "percent": metric(memory.percent), "cached": metric(getattr(memory, "cached", None), state="LOCAL"),
                       "swap_used": metric(swap.used)},
            "storage": [{"name": "/", "used": metric(disk.used), "free": metric(disk.free),
                         "total": metric(disk.total), "percent": metric(storage_pct),
                         "read_bps": metric(state="UNAVAILABLE", reason="Per-volume disk rate not connected"),
                         "write_bps": metric(state="UNAVAILABLE", reason="Per-volume disk rate not connected")}],
            "network": {"download_bps": metric(round(download)), "upload_bps": metric(round(upload)),
                        "interface": metric("ACTIVE INTERFACE", state="LOCAL")},
            "battery": ({"percent": metric(round(battery.percent, 1)), "charging": metric(bool(battery.power_plugged)),
                         "time_remaining_seconds": metric(battery.secsleft if battery.secsleft >= 0 else None,
                                                          state="LIVE" if battery.secsleft >= 0 else "UNAVAILABLE")}
                        if battery else {"percent": metric(state="NOT AVAILABLE", reason="No battery detected")}),
            "uptime_seconds": metric(round(time.time() - psutil.boot_time())),
            "health": {"score": score, "state": "HEALTHY" if score >= 85 else "ATTENTION" if score >= 60 else "CRITICAL",
                       "method": "deterministic-v1"},
        }
