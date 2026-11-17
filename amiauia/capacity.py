"""Capacity forecasting: stores disk measurements and estimates when the disk will be full."""

from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path

from . import stats
from .files_analysis import human_size
from .findings import Finding

DAY = 86400


def history_path() -> Path:
    base = Path(os.environ.get("AMIAUIA_HOME", Path.home() / ".amiauia"))
    base.mkdir(parents=True, exist_ok=True)
    return base / "capacity_history.json"


def load(path: Path | None = None) -> dict:
    path = path or history_path()
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def record(volume: str, path: Path | None = None, now: float | None = None) -> dict:
    """Appends a measurement (time, used, total) for the given volume."""
    path = path or history_path()
    data = load(path)
    usage = shutil.disk_usage(volume)
    key = str(Path(volume).resolve())
    data.setdefault(key, []).append({"t": now or time.time(), "used": usage.used, "total": usage.total})
    path.write_text(json.dumps(data, indent=1), encoding="utf-8")
    return data


def forecast(measurements: list[dict], volume: str = "") -> Finding | None:
    """Linear regression of used space over time."""
    if len(measurements) < 3:
        return None
    t0 = measurements[0]["t"]
    xs = [(m["t"] - t0) / DAY for m in measurements]
    ys = [m["used"] for m in measurements]
    total = measurements[-1]["total"]
    try:
        r = stats.linear_regression(xs, ys)
    except ValueError:
        return None
    rate = r["slope"]  # bytes/day
    free = total - ys[-1]
    name = volume or "the disk"
    if rate <= 0:
        return Finding(
            module="capacity",
            title=f"Usage of {name} is stable or decreasing",
            evidence={"daily_rate": human_size(rate), "free": human_size(free), "measurements": len(ys)},
            confidence=max(0.3, r["r2"]),
            action="No need to add storage for now.",
            priority=3,
        )
    days = free / rate
    # Approximate interval using the regression's standard error
    margin = 2 * r["error"]
    days_min = max(0.0, (free - margin) / rate)
    days_max = (free + margin) / rate
    priority = 1 if days < 30 else 2 if days < 90 else 3
    return Finding(
        module="capacity",
        title=f"{name} will be full in about {days:.0f} days",
        evidence={
            "daily_rate": human_size(rate),
            "free_space": human_size(free),
            "interval_days": [round(days_min), round(days_max)],
            "r2": round(r["r2"], 3),
            "measurements": len(ys),
        },
        confidence=max(0.2, min(0.95, r["r2"])),
        action="Archive old projects or remove duplicates before then; if that is not enough, add capacity.",
        priority=priority,
    )
