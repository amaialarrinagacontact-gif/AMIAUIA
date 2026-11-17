"""AMIAUIA Photos module: statistical culling, bursts, exposure and EXIF technical audit."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

import numpy as np
from PIL import Image

from . import stats
from .findings import Finding
from .scanner import FileInfo

ANALYSIS_SIDE = 1024        # resolution is normalized so sharpness is comparable across cameras
MIN_SHARPNESS = 40.0        # absolute floor for the Laplacian variance
BLUR_Z = -2.0               # robust z below which a photo is considered out of focus
BURST_DISTANCE = 10         # max Hamming distance between dHashes of the same scene
BURST_SECONDS = 2.0         # max seconds between shots in a burst

EXIF_IFD = 0x8769
TAGS = {"FNumber": 33437, "ExposureTime": 33434, "ISO": 34855, "FocalLength": 37386,
        "DateTimeOriginal": 36867, "LensModel": 42036}


@dataclass
class PhotoInfo:
    path: str
    sharpness: float
    luminance: float
    clipped_highlights: float   # % of pixels >= 250
    crushed_shadows: float      # % of pixels <= 5
    dhash: int
    timestamp: float
    exif: dict = field(default_factory=dict)
    exif_time: bool = False     # True if the time comes from the camera (reliable for bursts)
    sharpness_z: float = 0.0
    blurry: bool = False
    score: float = 0.0


# ---------- Image features ----------

def load_gray(path: str) -> tuple[np.ndarray, Image.Image]:
    img = Image.open(path)
    try:
        img.draft("L", (ANALYSIS_SIDE, ANALYSIS_SIDE))  # fast JPEG decoding
    except Exception:
        pass
    gray = img.convert("L")
    gray.thumbnail((ANALYSIS_SIDE, ANALYSIS_SIDE))
    return np.asarray(gray, dtype=np.float32), img


def laplacian_variance(g: np.ndarray) -> float:
    """Classic sharpness measure: variance of the image's second derivative."""
    if g.shape[0] < 3 or g.shape[1] < 3:
        return 0.0
    lap = (-4 * g[1:-1, 1:-1] + g[:-2, 1:-1] + g[2:, 1:-1] + g[1:-1, :-2] + g[1:-1, 2:])
    return float(lap.var())


def dhash(g: np.ndarray, size: int = 8) -> int:
    """Difference hash: similar images → similar hashes."""
    img = Image.fromarray(g.astype(np.uint8)).resize((size + 1, size), Image.Resampling.LANCZOS)
    a = np.asarray(img, dtype=np.int16)
    bits = (a[:, 1:] > a[:, :-1]).flatten()
    return int("".join("1" if b else "0" for b in bits), 2)


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def _rational(v) -> float | None:
    try:
        if isinstance(v, tuple):
            return v[0] / v[1] if v[1] else None
        return float(v)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def read_exif(img: Image.Image) -> dict:
    try:
        base = img.getexif()
    except Exception:
        return {}
    data: dict = {}
    if base.get(272):
        data["Camera"] = str(base.get(272)).strip()
    try:
        sub = base.get_ifd(EXIF_IFD)
    except Exception:
        sub = {}
    for name, tag in TAGS.items():
        v = sub.get(tag, base.get(tag))
        if v is None:
            continue
        if name in ("DateTimeOriginal", "LensModel"):
            data[name] = str(v).strip("\x00 ")
        else:
            num = _rational(v[0] if isinstance(v, (list, tuple)) and name == "ISO" else v)
            if num is not None:
                data[name] = num
    return data


def analyze_photo(path: str, mtime: float = 0.0) -> PhotoInfo:
    g, img = load_gray(path)
    exif = read_exif(img)
    timestamp, exif_time = mtime, False
    if "DateTimeOriginal" in exif:
        try:
            timestamp = datetime.strptime(exif["DateTimeOriginal"][:19], "%Y:%m:%d %H:%M:%S").timestamp()
            exif_time = True
        except ValueError:
            pass
    n = g.size or 1
    return PhotoInfo(
        path=path,
        sharpness=laplacian_variance(g),
        luminance=float(g.mean()),
        clipped_highlights=100 * float((g >= 250).sum()) / n,
        crushed_shadows=100 * float((g <= 5).sum()) / n,
        dhash=dhash(g),
        timestamp=timestamp,
        exif=exif,
        exif_time=exif_time,
    )


# ---------- Scoring and selection ----------

def score_photos(photos: list[PhotoInfo]) -> None:
    """Sharpness relative to the session itself + exposure penalties."""
    if not photos:
        return
    logs = [math.log1p(p.sharpness) for p in photos]
    zs = stats.robust_zscores(logs) if len(photos) >= 5 else [0.0] * len(photos)
    for p, z in zip(photos, zs):
        p.sharpness_z = z
        p.blurry = p.sharpness < MIN_SHARPNESS or z < BLUR_Z
        penalty = 0.15 * max(0.0, p.clipped_highlights - 1) + 0.05 * max(0.0, p.crushed_shadows - 5)
        penalty += abs(p.luminance - 118) / 118  # drifting away from mid-gray is penalized
        p.score = round(z - penalty - (3 if p.blurry else 0), 3)


def group_bursts(photos: list[PhotoInfo]) -> list[list[PhotoInfo]]:
    """Groups near-identical consecutive shots (by camera time or by dHash)."""
    ordered = sorted(photos, key=lambda p: (p.timestamp, p.path))
    groups: list[list[PhotoInfo]] = []
    for p in ordered:
        if groups:
            prev = groups[-1][-1]
            # Time only counts if it comes from EXIF: file dates change when files are copied.
            same_moment = p.exif_time and prev.exif_time and abs(p.timestamp - prev.timestamp) <= BURST_SECONDS
            if same_moment or hamming(p.dhash, prev.dhash) <= BURST_DISTANCE:
                groups[-1].append(p)
                continue
        groups.append([p])
    return groups


def select(photos: list[PhotoInfo]) -> tuple[list[PhotoInfo], list[PhotoInfo]]:
    """Returns (keepers, rejects): the best of each burst, unless it is blurry."""
    keepers, rejects = [], []
    for g in group_bursts(photos):
        best = max(g, key=lambda p: p.score)
        for p in g:
            (keepers if p is best and not p.blurry else rejects).append(p)
    return keepers, rejects


# ---------- Statistical audit of shooting habits (EXIF) ----------

def audit(photos: list[PhotoInfo], condition: Callable[[PhotoInfo], bool | None], description: str,
          advice: str, min_n: int = 10) -> Finding | None:
    """Compares the blur rate when a condition holds versus when it does not."""
    group, rest = [], []
    for p in photos:
        c = condition(p)
        if c is None:
            continue
        (group if c else rest).append(p)
    if len(group) < min_n or len(rest) < min_n:
        return None
    k1, n1 = sum(p.blurry for p in group), len(group)
    k2, n2 = sum(p.blurry for p in rest), len(rest)
    t = stats.two_proportion_test(k1, n1, k2, n2)
    if t["p"] >= 0.05 or k1 / n1 <= k2 / n2:
        return None
    r1, r2 = 100 * k1 / n1, 100 * k2 / n2
    return Finding(
        module="photos",
        title=f"{description}: {r1:.0f} % out-of-focus shots vs {r2:.0f} % otherwise",
        evidence={
            "photos_condition": n1, "blurry_condition": k1,
            "photos_rest": n2, "blurry_rest": k2,
            "ci95_condition": [round(100 * x, 1) for x in stats.wilson_interval(k1, n1)],
            "p_value": round(t["p"], 4),
        },
        confidence=stats.confidence_from_p(t["p"]),
        action=advice,
        priority=2,
    )


def _wide_aperture(p: PhotoInfo) -> bool | None:
    v = p.exif.get("FNumber")
    return None if v is None else v <= 2.0


def _below_reciprocal_rule(p: PhotoInfo) -> bool | None:
    t, focal = p.exif.get("ExposureTime"), p.exif.get("FocalLength")
    if not t or not focal:
        return None
    return t > 1.0 / focal


def _high_iso(p: PhotoInfo) -> bool | None:
    v = p.exif.get("ISO")
    return None if v is None else v >= 3200


def audits(photos: list[PhotoInfo]) -> list[Finding]:
    rules = [
        (_wide_aperture, "Shooting at f/2 or wider",
         "Stop down to f/2.8 when you don't need the shallow depth of field, or use eye-tracking AF."),
        (_below_reciprocal_rule, "Shutter speed slower than 1/focal length",
         "Use a faster shutter speed (at least 1/focal length) or turn on stabilization."),
        (_high_iso, "At ISO 3200 or higher",
         "In low light, prioritize shutter speed and aperture; apply noise reduction afterwards."),
    ]
    results = [audit(photos, c, d, a) for c, d, a in rules]
    # Lens with the most misses
    by_lens: dict[str, list[PhotoInfo]] = {}
    for p in photos:
        if p.exif.get("LensModel"):
            by_lens.setdefault(p.exif["LensModel"], []).append(p)
    for lens in by_lens:
        results.append(audit(
            photos,
            lambda p, l=lens: None if not p.exif.get("LensModel") else p.exif["LensModel"] == l,
            f"With the {lens} lens",
            "Calibrate this lens's AF micro-adjustment or have it checked.",
        ))
    return [r for r in results if r]


# ---------- Orchestration ----------

def analyze(files: list[FileInfo], progress: Callable[[int, int], None] | None = None
            ) -> tuple[list[Finding], list[PhotoInfo], list[PhotoInfo]]:
    images = [f for f in files if f.is_image]
    photos: list[PhotoInfo] = []
    errors = 0
    for i, f in enumerate(images, 1):
        try:
            photos.append(analyze_photo(f.path, f.mtime))
        except Exception:
            errors += 1
        if progress:
            progress(i, len(images))
    score_photos(photos)
    keepers, rejects = select(photos)
    findings: list[Finding] = []
    if photos:
        blurry = [p for p in photos if p.blurry]
        bursts = [g for g in group_bursts(photos) if len(g) > 1]
        findings.append(Finding(
            module="photos",
            title=f"Suggested selection: {len(keepers)} of {len(photos)} photos",
            evidence={
                "photos_analyzed": len(photos),
                "keepers": len(keepers),
                "rejects": len(rejects),
                "out_of_focus": len(blurry),
                "bursts_detected": len(bursts),
                "median_sharpness": round(stats.median([p.sharpness for p in photos]), 1),
                "unreadable": errors,
            },
            confidence=0.75,
            action="Review the selection; export the list with --selection to import it into your editor.",
            priority=1 if len(rejects) > len(keepers) else 2,
            details=[p.path for p in keepers[:200]],
        ))
        clipped = [p for p in photos if p.clipped_highlights > 2]
        if len(clipped) >= max(3, 0.1 * len(photos)):
            findings.append(Finding(
                module="photos",
                title=f"{len(clipped)} photos with blown highlights (>2 % of pixels)",
                evidence={"affected": len(clipped), "percent": round(100 * len(clipped) / len(photos), 1)},
                confidence=0.9,
                action="Lower exposure by 1/3 to 2/3 of a stop or turn on the highlight warning (zebras).",
                priority=2,
                details=[p.path for p in clipped[:50]],
            ))
        findings.extend(audits(photos))
    return findings, keepers, rejects
