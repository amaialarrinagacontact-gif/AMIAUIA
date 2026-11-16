# AMIAUIA

**Advanced Multivariate Intelligence for Unified Image & Archive analysis**

AMIAUIA is a statistical, explainable AI that analyzes your files and photos and gives you **logical solutions**. Every answer follows the same structure:

| | |
|---|---|
| **Finding** | What it detected |
| **Evidence** | The numbers that prove it |
| **Confidence** | How sure it is (0–100 %) |
| **Action** | What to do next |

All analysis runs **on your own computer**: no file is uploaded, and AMIAUIA **never deletes or moves anything** on its own.

---

## What it does

### 🗂️ Files module (IT)
- **Exact duplicates** in three passes (size → partial hash → full SHA-256) and the space you can recover.
- **Space breakdown** by file type.
- **Stale files**: the largest files (90th percentile) not modified for over a year.
- **Early ransomware warning**: text files modified in the last 24 h whose Shannon entropy exceeds 7.5 bits/byte (they look encrypted), plus typical ransom extensions (`.locked`, `.encrypted`…).
- **Capacity forecast**: linear regression over daily disk measurements to estimate when the disk will be full, with an interval.

### 📷 Photos module
- **Automatic culling**: scores each photo by sharpness (Laplacian variance), exposure and blown highlights, relative to the rest of the session (robust z-score).
- **Bursts**: groups near-identical shots using a perceptual hash (dHash) and camera time, and keeps the best one of each group.
- **Technical audit of your shooting habits** from EXIF data, using a two-proportion statistical test (p < 0.05):
  - Do you miss focus more at f/2 or wider?
  - Below the 1/focal-length shutter speed?
  - At ISO 3200 or higher?
  - With a specific lens?

Example output:

```
🟠 [MEDIUM] [photos] With the 85mm F1.4 lens: 31 % out-of-focus shots vs 9 % otherwise
   Confidence: 99%
   · photos_condition: 412
   · ci95_condition: [26.8, 35.6]
   · p_value: 0.0001
   → Action: Calibrate this lens's AF micro-adjustment or have it checked.
```

---

## Installation

Requires Python 3.10 or later.

```bash
git clone https://github.com/YOUR_USERNAME/amiauia.git
cd amiauia
pip install -e .
```

## Usage

```bash
# Files: duplicates, space, stale files and ransomware
amiauia files /path/to/your/drive

# Photos: culling, bursts, exposure and EXIF audit
amiauia photos /path/to/session --selection keepers.txt

# Capacity: run it daily (e.g. with cron or Task Scheduler)
amiauia capacity /

# Everything at once, with reports
amiauia all /path --json report.json --md report.md
```

Common options: `--json FILE`, `--md FILE`, `--hidden` (include hidden files).

> In this version the photos module analyzes JPEG, PNG, TIFF, WebP and BMP. RAW files are counted as files but not analyzed yet (see roadmap).

---

## Architecture

```
amiauia/
├── scanner.py         # Ingestion: folder walking, hashes, entropy
├── stats.py           # Home-grown statistical engine (robust z, regression, Wilson, proportion test, entropy)
├── files_analysis.py  # Files module
├── capacity.py        # Capacity forecasting
├── photo_analysis.py  # Photos module
├── findings.py        # Finding / Evidence / Confidence / Action structure
├── report.py          # Console, JSON and Markdown output
└── cli.py             # Command line
```

The statistical engine is written from scratch using the Python standard library; only `numpy` and `Pillow` are used to read and process images.

## Tests

```bash
pip install -e ".[dev]"
pytest
```

GitHub Actions runs the tests on Linux, Windows and macOS on every push.

---

## Roadmap

- [ ] RAW (embedded preview) and HEIC support
- [ ] Closed-eye and face detection
- [ ] Visual (not just exact) duplicates across drives
- [ ] Source vs. backup comparison
- [ ] Real-time ransomware monitoring
- [ ] Natural-language explanations with a local model
- [ ] Desktop app and Lightroom plugin
- [ ] API for integrators

## License

MIT. See [LICENSE](LICENSE).
