"""Common structure shared by every AMIAUIA answer."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

PRIORITIES = {1: "HIGH", 2: "MEDIUM", 3: "LOW"}


@dataclass
class Finding:
    """A logical solution: what was seen, why, how sure we are, and what to do."""

    module: str                 # "files", "photos", "capacity", "security"
    title: str                  # one-sentence finding
    evidence: dict[str, Any]    # the numbers behind it
    confidence: float           # 0..1
    action: str                 # concrete recommendation
    priority: int = 2           # 1 high, 2 medium, 3 low
    details: list[Any] = field(default_factory=list)  # affected items (paths, groups…)

    def __post_init__(self) -> None:
        self.confidence = max(0.0, min(1.0, float(self.confidence)))

    @property
    def priority_label(self) -> str:
        return PRIORITIES.get(self.priority, "MEDIUM")

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["priority"] = self.priority_label
        return d
