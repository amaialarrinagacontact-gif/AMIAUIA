"""Ingestion: walks folders and extracts metadata without moving or modifying files."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from .stats import shannon_entropy

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".bmp", ".heic"}
RAW_EXT = {".cr2", ".cr3", ".nef", ".arw", ".raf", ".orf", ".rw2", ".dng"}


@dataclass
class FileInfo:
    path: str
    size: int
    mtime: float
    ext: str

    @property
    def is_image(self) -> bool:
        return self.ext in IMAGE_EXT

    @property
    def is_raw(self) -> bool:
        return self.ext in RAW_EXT


def scan(root: str | Path, include_hidden: bool = False) -> list[FileInfo]:
    return list(iter_files(root, include_hidden))


def iter_files(root: str | Path, include_hidden: bool = False) -> Iterator[FileInfo]:
    root = Path(root)
    if root.is_file():
        st = root.stat()
        yield FileInfo(str(root), st.st_size, st.st_mtime, root.suffix.lower())
        return
    for dirpath, dirnames, filenames in os.walk(root):
        if not include_hidden:
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for name in filenames:
            if not include_hidden and name.startswith("."):
                continue
            path = os.path.join(dirpath, name)
            try:
                st = os.stat(path, follow_symlinks=False)
            except OSError:
                continue
            if not os.path.isfile(path) or os.path.islink(path):
                continue
            yield FileInfo(path, st.st_size, st.st_mtime, Path(name).suffix.lower())


def file_hash(path: str, block: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(block):
            h.update(chunk)
    return h.hexdigest()


def partial_hash(path: str, n: int = 65536) -> str:
    """Fast hash of the first n bytes, used to discard candidates before the full hash."""
    with open(path, "rb") as f:
        return hashlib.sha256(f.read(n)).hexdigest()


def file_entropy(path: str, n: int = 65536) -> float:
    with open(path, "rb") as f:
        return shannon_entropy(f.read(n))
