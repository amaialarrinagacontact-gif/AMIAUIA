"""AMIAUIA Files module: duplicates, space breakdown, stale files and ransomware alert."""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Iterable

from . import stats
from .findings import Finding
from .scanner import FileInfo, file_entropy, file_hash, partial_hash

# Formats that are normally plain text (low entropy). If they suddenly look random,
# that is a classic sign of ransomware encryption.
LOW_ENTROPY_EXT = {".txt", ".csv", ".json", ".xml", ".html", ".htm", ".md", ".log",
                   ".svg", ".sql", ".ini", ".cfg", ".yaml", ".yml", ".py", ".js", ".bmp"}
SUSPICIOUS_EXT = {".locked", ".encrypted", ".enc", ".crypt", ".crypted", ".lock",
                  ".locky", ".wncry", ".cerber", ".ryk"}
ENTROPY_THRESHOLD = 7.5   # bits/byte
ONE_YEAR = 365 * 24 * 3600


def human_size(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def find_duplicates(files: Iterable[FileInfo], min_size: int = 1) -> list[list[FileInfo]]:
    """Groups exact duplicates in 3 passes: size → partial hash → full hash."""
    by_size: dict[int, list[FileInfo]] = defaultdict(list)
    for f in files:
        if f.size >= min_size:
            by_size[f.size].append(f)

    groups: list[list[FileInfo]] = []
    for candidates in by_size.values():
        if len(candidates) < 2:
            continue
        by_partial: dict[str, list[FileInfo]] = defaultdict(list)
        for f in candidates:
            try:
                by_partial[partial_hash(f.path)].append(f)
            except OSError:
                continue
        for sub in by_partial.values():
            if len(sub) < 2:
                continue
            by_hash: dict[str, list[FileInfo]] = defaultdict(list)
            for f in sub:
                try:
                    by_hash[file_hash(f.path)].append(f)
                except OSError:
                    continue
            groups.extend(g for g in by_hash.values() if len(g) > 1)
    groups.sort(key=lambda g: g[0].size * (len(g) - 1), reverse=True)
    return groups


def duplicates_finding(files: list[FileInfo]) -> Finding | None:
    groups = find_duplicates(files)
    if not groups:
        return None
    wasted = sum(g[0].size * (len(g) - 1) for g in groups)
    total = sum(f.size for f in files) or 1
    copies = sum(len(g) - 1 for g in groups)
    return Finding(
        module="files",
        title=f"{copies} duplicate cop{'y' if copies == 1 else 'ies'} taking up {human_size(wasted)}",
        evidence={
            "duplicate_groups": len(groups),
            "redundant_copies": copies,
            "recoverable_bytes": wasted,
            "percent_of_total": round(100 * wasted / total, 2),
        },
        confidence=0.99,  # a full SHA-256 match guarantees identical content
        action="Review each group and keep one copy (AMIAUIA never deletes without confirmation).",
        priority=1 if wasted / total > 0.1 else 2,
        details=[[f.path for f in g] for g in groups[:50]],
    )


def breakdown_finding(files: list[FileInfo]) -> Finding | None:
    if not files:
        return None
    by_ext: dict[str, int] = defaultdict(int)
    for f in files:
        by_ext[f.ext or "(no extension)"] += f.size
    total = sum(by_ext.values()) or 1
    top = sorted(by_ext.items(), key=lambda kv: kv[1], reverse=True)[:8]
    main_ext, weight = top[0]
    return Finding(
        module="files",
        title=f"'{main_ext}' files account for {100 * weight / total:.0f} % of the space",
        evidence={
            "files": len(files),
            "total_space": human_size(total),
            "breakdown": {ext: f"{human_size(b)} ({100 * b / total:.1f} %)" for ext, b in top},
            "median_size": human_size(stats.median([f.size for f in files])),
        },
        confidence=1.0,
        action="Use this breakdown to decide what to archive or compress first.",
        priority=3,
    )


def stale_files_finding(files: list[FileInfo], now: float | None = None) -> Finding | None:
    """Large files (90th percentile) not modified for more than a year."""
    if len(files) < 10:
        return None
    now = now or time.time()
    p90 = stats.percentile([f.size for f in files], 90)
    stale = [f for f in files if f.size >= p90 and now - f.mtime > ONE_YEAR]
    if not stale:
        return None
    size = sum(f.size for f in stale)
    stale.sort(key=lambda f: f.size, reverse=True)
    return Finding(
        module="files",
        title=f"{len(stale)} large files untouched for over a year ({human_size(size)})",
        evidence={"size_threshold_p90": human_size(p90), "files": len(stale), "space": human_size(size)},
        confidence=0.8,
        action="Move them to an archive drive or cold storage to free up your working disk.",
        priority=2,
        details=[f.path for f in stale[:50]],
    )


def ransomware_finding(files: list[FileInfo], hours: float = 24, now: float | None = None) -> Finding | None:
    """Detects signs of mass encryption among recently modified files."""
    now = now or time.time()
    recent = [f for f in files if now - f.mtime <= hours * 3600]
    suspicious = [f for f in recent if f.ext in SUSPICIOUS_EXT]
    recent_text = [f for f in recent if f.ext in LOW_ENTROPY_EXT and f.size >= 256]
    encrypted = []
    for f in recent_text:
        try:
            if file_entropy(f.path) >= ENTROPY_THRESHOLD:
                encrypted.append(f)
        except OSError:
            continue

    signals = len(encrypted) + len(suspicious)
    if signals == 0:
        return None
    n = max(len(recent_text), 1)
    rate = len(encrypted) / n
    lo, _ = stats.wilson_interval(len(encrypted), n)
    # Confidence grows with the number of signals and the share of "randomized" text files
    confidence = min(0.99, 0.3 + 0.1 * signals + 0.5 * lo)
    return Finding(
        module="security",
        title=f"Possible file encryption: {signals} signals in the last {hours:.0f} h",
        evidence={
            "text_files_with_high_entropy": len(encrypted),
            "recent_text_files": len(recent_text),
            "rate": round(rate, 3),
            "suspicious_extensions": len(suspicious),
            "entropy_threshold_bits_per_byte": ENTROPY_THRESHOLD,
        },
        confidence=confidence,
        action="Disconnect the folder or drive from the network, do not pay any ransom, and restore from a verified backup.",
        priority=1,
        details=[f.path for f in (encrypted + suspicious)[:50]],
    )


def analyze(files: list[FileInfo]) -> list[Finding]:
    results = [
        ransomware_finding(files),
        duplicates_finding(files),
        stale_files_finding(files),
        breakdown_finding(files),
    ]
    return [r for r in results if r is not None]
