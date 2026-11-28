"""Submission package (STEPS 197): assemble submission/ and a zip, and say what is missing.

Why: the brief assesses a report, an images folder and a video demo. Building the package
by script means it can be rebuilt after the report and video are finished, and the script
refuses to call it complete while a required item is absent, stale or still a placeholder.
"""

import json
import shutil
import zipfile
from pathlib import Path

from src import config

# (source relative to the repo root, folder inside submission/)
INCLUDE = [
    ("report/A3_report.docx", "report"),
    ("report/A3_report.pdf", "report"),
    ("report/A3_report.md", "report"),
    ("report/workflow.png", "report"),
    ("images", "images"),
    ("notebooks/A3_workflow.ipynb", "notebooks"),
    ("src", "src"),
    ("tests", "tests"),
    ("results", "results"),
    ("data/raw", "data/raw"),
    ("video/A3_slides.pptx", "video"),
    ("video/script.md", "video"),
    ("requirements.txt", "."),
    ("pyproject.toml", "."),
    ("README.md", "."),
]
VIDEO_SUFFIXES = {".mp4", ".mov", ".mkv", ".webm", ".avi"}
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".ipynb_checkpoints")


def find_problems(root: Path) -> list[str]:
    """Items that stop the package from being final (empty list = ready to submit)."""
    problems = []
    if not any(p.suffix.lower() in VIDEO_SUFFIXES for p in (root / "video").glob("*")):
        problems.append("video: no recording found in video/ (mp4, mov, mkv, webm or avi)")
    if not (root / "report" / "A3_report.pdf").exists():
        problems.append("report: report/A3_report.pdf (with the A1 report appended) is missing")
    for name in ("README.md", "video/A3_slides.pptx"):
        path = root / name
        if path.exists() and b"TODO(team)" in _text_bytes(path):
            problems.append(f"{name}: still contains TODO(team) (member names / contributions)")
    problems += _stale(root)
    return problems


def _text_bytes(path: Path) -> bytes:
    """README text, or the concatenated slide XML of a pptx (a zip)."""
    if path.suffix != ".pptx":
        return path.read_bytes()
    try:
        with zipfile.ZipFile(path) as z:
            return b"".join(z.read(n) for n in z.namelist() if n.startswith("ppt/slides/slide"))
    except zipfile.BadZipFile:  # not a real deck: search the raw bytes instead
        return path.read_bytes()


def _stale(root: Path) -> list[str]:
    """Generated deliverables older than the results they are built from."""
    results = [p.stat().st_mtime for p in (root / "results").glob("*.json")]
    if not results:
        return []
    newest = max(results)
    out = []
    for name, command in (
        ("report/A3_report.docx", "python -m src.report && python -m src.export_docx"),
        ("video/A3_slides.pptx", "python -m src.slides"),
    ):
        path = root / name
        if path.exists() and path.stat().st_mtime < newest:
            out.append(f"{name}: older than results/ (regenerate with: {command})")
    return out


def build(root: Path = config.ROOT) -> dict:
    """Copy the deliverables into submission/, zip them, and return what is still missing."""
    out_dir = root / "submission"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    copied, absent = [], []
    for source, folder in INCLUDE:
        src = root / source
        if not src.exists():
            absent.append(source)
            continue
        if src.is_dir():  # the folder entry names the destination folder itself
            shutil.copytree(src, out_dir / folder, ignore=IGNORE)
        else:
            (out_dir / folder).mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, out_dir / folder / src.name)
        copied.append(source)
    for video in (root / "video").glob("*"):
        if video.suffix.lower() in VIDEO_SUFFIXES:
            (out_dir / "video").mkdir(parents=True, exist_ok=True)
            shutil.copy2(video, out_dir / "video" / video.name)
            copied.append(f"video/{video.name}")
    zip_path = root / "submission.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(out_dir.rglob("*")):
            if path.is_file():
                z.write(path, path.relative_to(out_dir))
    problems = find_problems(root)
    manifest = {
        "copied": copied,
        "not_in_repo": absent,
        "zip": zip_path.name,
        "zip_mb": round(zip_path.stat().st_size / 1e6, 1),
        "problems": problems,
        "ready_to_submit": not problems,
    }
    (out_dir / "MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    result = build()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["ready_to_submit"] else 1)
