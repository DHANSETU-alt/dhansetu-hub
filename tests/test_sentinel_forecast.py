"""Real tests for sentinel.forecast() -- SHAKTHI_OS 3.1 Phase 1
(see SHAKTHI_OS_3.1_ULTRA_OMNI_ROADMAP.md). Verifies the trend math
against known, hand-computed inputs -- not just "it runs."
"""
from unittest.mock import patch

from orchestrator import sentinel


def _rows(values, start="2026-08-01 00:00:00"):
    """Build fake system_health rows, one per day starting at `start`."""
    from datetime import datetime, timedelta
    t0 = datetime.strptime(start, "%Y-%m-%d %H:%M:%S")
    return [
        {"disk_percent": v, "created_at": (t0 + timedelta(days=i)).strftime("%Y-%m-%d %H:%M:%S")}
        for i, v in enumerate(values)
    ]


def test_forecast_projects_a_real_linear_trend():
    # Disk grows exactly 2%/day for 6 real days, starting at 50%.
    rows = _rows([50, 52, 54, 56, 58, 60])
    with patch("orchestrator.db.recent_health_snapshots", return_value=list(reversed(rows))):
        result = sentinel.forecast("disk_percent", threshold=90.0)
    assert result["current"] == 60
    assert abs(result["slope_per_day"] - 2.0) < 0.01
    # (90 - 60) / 2 = 15 real days out
    assert abs(result["days_to_threshold"] - 15.0) < 0.5


def test_forecast_reports_no_projection_for_flat_trend():
    rows = _rows([40, 40, 40, 40, 40])
    with patch("orchestrator.db.recent_health_snapshots", return_value=list(reversed(rows))):
        result = sentinel.forecast("disk_percent")
    assert result["days_to_threshold"] is None
    assert "flat" in result["reason"] or "decreasing" in result["reason"]


def test_forecast_honest_about_insufficient_history():
    rows = _rows([50, 55])  # only 2 points
    with patch("orchestrator.db.recent_health_snapshots", return_value=list(reversed(rows))):
        result = sentinel.forecast("disk_percent", min_points=5)
    assert result["days_to_threshold"] is None
    assert "only 2" in result["reason"]


def test_forecast_already_over_threshold_reports_zero_days():
    rows = _rows([91, 92, 93, 94, 95])
    with patch("orchestrator.db.recent_health_snapshots", return_value=list(reversed(rows))):
        result = sentinel.forecast("disk_percent", threshold=90.0)
    assert result["days_to_threshold"] == 0
