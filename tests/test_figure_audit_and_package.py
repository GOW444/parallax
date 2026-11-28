"""Tests for the figure audit (STEPS 153), contact sheets and the submission packager (197)."""

import json
import os
import time
import zipfile

import pandas as pd
from PIL import Image

from src import figure_audit as fa
from src import package


def _png(path, dpi=(200, 200), size=(40, 30)):
    Image.new("RGB", size, "white").save(path, dpi=dpi)


def _registry(rows):
    return pd.DataFrame(
        rows, columns=["filename", "phase", "what_it_shows", "why_this_chart", "inference_id"]
    )


def test_audit_passes_a_complete_figure(tmp_path):
    _png(tmp_path / "iter2_a.png")
    reg = _registry([["iter2_a.png", "P4", "shows", "why", "I2-1"]])
    out = fa.audit_figures(reg, tmp_path, {"I2-1"}, ["iter2_a.png"])
    assert out["ok"] and out["n_checked"] == 1


def test_audit_reports_each_kind_of_problem(tmp_path):
    _png(tmp_path / "iter2_low.png", dpi=(72, 72))
    _png(tmp_path / "iter2_orphan.png")
    reg = _registry(
        [
            ["iter2_low.png", "P4", "shows", "", "I9-9"],
            ["iter2_gone.png", "P4", "shows", "why", "I2-1"],
        ]
    )
    out = fa.audit_figures(reg, tmp_path, {"I2-1"}, ["iter2_plan.png"])
    problems = out["figures_with_problems"]
    assert "dpi" in " ".join(problems["iter2_low.png"])
    assert "empty why_this_chart" in problems["iter2_low.png"]
    assert "unknown inference I9-9" in problems["iter2_low.png"]
    assert problems["iter2_gone.png"] == ["file missing"]
    assert out["png_not_registered"] == ["iter2_orphan.png"]
    assert out["plan_names_without_file"] == ["iter2_plan.png"]
    assert not out["ok"]


def test_plan_figure_names_reads_backticked_names():
    text = "see `iter2_a.png` and `loop_b.png`, not `other.png`"
    assert fa.plan_figure_names(text) == ["iter2_a.png", "loop_b.png", "workflow.png"]


def test_contact_sheets_tile_four_per_sheet(tmp_path):
    for i in range(5):
        _png(tmp_path / f"f{i}.png")
    sheets = fa.contact_sheets([f"f{i}.png" for i in range(5)], tmp_path, tmp_path / "out")
    assert [s.name for s in sheets] == ["sheet_1.png", "sheet_2.png"]
    assert Image.open(sheets[0]).width == 2000


def _project(tmp_path, with_video=False, todo=False):
    for folder in ("report", "images", "notebooks", "src", "tests", "results", "data/raw", "video"):
        (tmp_path / folder).mkdir(parents=True, exist_ok=True)
    (tmp_path / "report/A3_report.docx").write_bytes(b"docx")
    (tmp_path / "report/A3_report.pdf").write_bytes(b"pdf")
    (tmp_path / "images/x.png").write_bytes(b"png")
    (tmp_path / "results/m.json").write_text("{}")
    earlier = time.time() - 60  # results are older than the deliverables built from them
    os.utime(tmp_path / "results/m.json", (earlier, earlier))
    (tmp_path / "README.md").write_text("TODO(team)" if todo else "ok")
    (tmp_path / "video/A3_slides.pptx").write_bytes(b"not a zip")
    if with_video:
        (tmp_path / "video/demo.mp4").write_bytes(b"video")
    return tmp_path


def test_package_lists_what_is_missing(tmp_path):
    manifest = package.build(_project(tmp_path, todo=True))
    assert not manifest["ready_to_submit"]
    joined = " ".join(manifest["problems"])
    assert "no recording" in joined and "TODO(team)" in joined
    assert (tmp_path / "submission/images/x.png").exists()
    with zipfile.ZipFile(tmp_path / "submission.zip") as z:
        assert "report/A3_report.docx" in z.namelist()


def test_package_is_ready_when_nothing_is_missing(tmp_path):
    manifest = package.build(_project(tmp_path, with_video=True))
    assert manifest["problems"] == [] and manifest["ready_to_submit"]
    saved = json.loads((tmp_path / "submission/MANIFEST.json").read_text())
    assert saved["zip"] == "submission.zip"
    assert (tmp_path / "submission/video/demo.mp4").exists()


def test_package_flags_a_report_older_than_the_results(tmp_path):
    root = _project(tmp_path, with_video=True)
    old = time.time() - 3600
    os.utime(root / "report/A3_report.docx", (old, old))
    manifest = package.build(root)
    assert any("older than results" in p for p in manifest["problems"])
