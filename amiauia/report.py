"""Output: console, JSON and Markdown."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from . import __version__
from .findings import Finding

ICONS = {1: "🔴", 2: "🟠", 3: "🟢"}


def sort_findings(findings: list[Finding]) -> list[Finding]:
    return sorted(findings, key=lambda f: (f.priority, -f.confidence))


def console(findings: list[Finding], details: int = 5) -> str:
    lines = [f"\nAMIAUIA {__version__} — {len(findings)} findings\n" + "=" * 60]
    if not findings:
        lines.append("No relevant findings. Everything looks good.")
    for f in sort_findings(findings):
        lines.append(f"\n{ICONS.get(f.priority, '•')} [{f.priority_label}] [{f.module}] {f.title}")
        lines.append(f"   Confidence: {f.confidence:.0%}")
        for k, v in f.evidence.items():
            lines.append(f"   · {k}: {v}")
        lines.append(f"   → Action: {f.action}")
        for d in f.details[:details]:
            lines.append(f"     - {d}")
        if len(f.details) > details:
            lines.append(f"     … and {len(f.details) - details} more (see --json)")
    return "\n".join(lines)


def to_json(findings: list[Finding], dest: str | Path) -> None:
    data = {
        "amiauia": __version__,
        "generated": datetime.now().isoformat(timespec="seconds"),
        "findings": [f.to_dict() for f in sort_findings(findings)],
    }
    Path(dest).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def to_markdown(findings: list[Finding], dest: str | Path) -> None:
    lines = ["# AMIAUIA report", f"_Generated on {datetime.now():%Y-%m-%d %H:%M}_", ""]
    for f in sort_findings(findings):
        lines += [f"## {ICONS.get(f.priority, '')} {f.title}",
                  f"**Module:** {f.module} · **Priority:** {f.priority_label} · "
                  f"**Confidence:** {f.confidence:.0%}", "", "| Evidence | Value |", "|---|---|"]
        lines += [f"| {k} | {v} |" for k, v in f.evidence.items()]
        lines += ["", f"**Action:** {f.action}", ""]
    Path(dest).write_text("\n".join(lines), encoding="utf-8")
