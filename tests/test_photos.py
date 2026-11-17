import os

import numpy as np
from PIL import Image, ImageFilter

from amiauia import photo_analysis as pa
from amiauia.scanner import scan


def _scene(seed: int, size: int = 512) -> Image.Image:
    rng = np.random.default_rng(seed)
    base = rng.integers(60, 190, size=(size // 16, size // 16), dtype=np.uint8)
    img = Image.fromarray(base).resize((size, size), Image.Resampling.NEAREST)  # sharp edges
    return img.convert("RGB")


def test_sharpness_detects_blur(tmp_path):
    sharp = _scene(1)
    blurred = sharp.filter(ImageFilter.GaussianBlur(6))
    sharp.save(tmp_path / "s.jpg", quality=95)
    blurred.save(tmp_path / "b.jpg", quality=95)
    ps = pa.analyze_photo(str(tmp_path / "s.jpg"))
    pb = pa.analyze_photo(str(tmp_path / "b.jpg"))
    assert ps.sharpness > 5 * pb.sharpness


def test_dhash_similar_and_different():
    a = np.asarray(_scene(1).convert("L"), dtype=np.float32)
    b = np.asarray(_scene(1).filter(ImageFilter.GaussianBlur(1)).convert("L"), dtype=np.float32)
    c = np.asarray(_scene(99).convert("L"), dtype=np.float32)
    assert pa.hamming(pa.dhash(a), pa.dhash(b)) <= pa.BURST_DISTANCE
    assert pa.hamming(pa.dhash(a), pa.dhash(c)) > pa.BURST_DISTANCE


def test_selection_keeps_sharp_shot_of_each_burst(tmp_path):
    for scene in range(4):
        img = _scene(scene + 10)
        img.save(tmp_path / f"s{scene}_sharp.jpg", quality=95)
        img.filter(ImageFilter.GaussianBlur(5)).save(tmp_path / f"s{scene}_blurred.jpg", quality=95)
    findings, keepers, rejects = pa.analyze(scan(tmp_path))
    names = sorted(os.path.basename(p.path) for p in keepers)
    assert names == [f"s{i}_sharp.jpg" for i in range(4)]
    assert len(rejects) == 4
    assert findings[0].evidence["photos_analyzed"] == 8


def test_audit_detects_pattern():
    photos = []
    for i in range(40):
        wide = i < 20
        p = pa.PhotoInfo(path=f"{i}.jpg", sharpness=100, luminance=118, clipped_highlights=0,
                         crushed_shadows=0, dhash=i, timestamp=i * 10,
                         exif={"FNumber": 1.4 if wide else 5.6})
        p.blurry = (wide and i % 2 == 0) or (not wide and i == 39)
        photos.append(p)
    f = pa.audit(photos, pa._wide_aperture, "Shooting at f/2", "Stop down")
    assert f is not None
    assert f.evidence["blurry_condition"] == 10
    assert f.confidence > 0.95
