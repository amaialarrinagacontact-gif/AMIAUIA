import os
import time

from amiauia import capacity, files_analysis
from amiauia.scanner import scan


def test_duplicates(tmp_path):
    (tmp_path / "a.txt").write_bytes(b"hello" * 1000)
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.txt").write_bytes(b"hello" * 1000)
    (tmp_path / "c.txt").write_bytes(b"world" * 1000)  # same size, different content
    files = scan(tmp_path)
    groups = files_analysis.find_duplicates(files)
    assert len(groups) == 1 and len(groups[0]) == 2
    f = files_analysis.duplicates_finding(files)
    assert f.evidence["recoverable_bytes"] == 5000


def test_ransomware_detects_encrypted_text(tmp_path):
    for i in range(5):
        (tmp_path / f"doc{i}.txt").write_bytes(os.urandom(4096))
    (tmp_path / "note.txt").write_text("normal text " * 100)
    (tmp_path / "photo.jpg.locked").write_bytes(os.urandom(1000))
    f = files_analysis.ransomware_finding(scan(tmp_path))
    assert f is not None
    assert f.evidence["text_files_with_high_entropy"] == 5
    assert f.evidence["suspicious_extensions"] == 1
    assert f.priority == 1


def test_no_ransomware(tmp_path):
    (tmp_path / "note.txt").write_text("normal text " * 100)
    assert files_analysis.ransomware_finding(scan(tmp_path)) is None


def test_stale_files(tmp_path):
    old = time.time() - 2 * 365 * 86400
    for i in range(20):
        p = tmp_path / f"f{i}.bin"
        p.write_bytes(b"x" * (100 if i < 18 else 100_000))
        if i >= 18:
            os.utime(p, (old, old))
    f = files_analysis.stale_files_finding(scan(tmp_path))
    assert f is not None and f.evidence["files"] == 2


def test_capacity_forecast():
    day = 86400
    gb = 1024 ** 3
    m = [{"t": i * day, "used": (500 + 10 * i) * gb, "total": 1000 * gb} for i in range(10)]
    f = capacity.forecast(m, "/data")
    # Free = 1000 - 590 = 410 GB at 10 GB/day → 41 days
    assert "41" in f.title
    assert f.confidence > 0.9


def test_record_capacity(tmp_path):
    path = tmp_path / "history.json"
    data = capacity.record(str(tmp_path), path)
    assert len(next(iter(data.values()))) == 1
