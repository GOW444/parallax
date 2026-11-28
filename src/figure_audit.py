"""Figure audit (STEPS 153): every figure file, its registry row and its inference agree.

Why: the rubric rewards a complete images folder with a rationale for every chart, and
CLAUDE.md requires each figure to be saved under the plan's name, registered in
results/figures.csv and tied to an inference. This checks that mechanically; what a figure
*looks like* (overlaps, readable labels) still needs eyes, see ``contact_sheets``.
"""

import json
import re
from pathlib import Path

import pandas as pd
from PIL import Image

from src import config

REQUIRED_FIELDS = ["filename", "phase", "what_it_shows", "why_this_chart"]
MIN_DPI = 150  # CLAUDE.md section 4: "150+ dpi"


def plan_figure_names(plan_text: str) -> list[str]:
    """Figure filenames the plan names in backticks (iter1_*, iter2_*, loop_*) plus workflow."""
    return sorted(
        set(re.findall(r"`((?:iter1|iter2|loop)_[a-z0-9_]+\.png)`", plan_text)) | {"workflow.png"}
    )


def audit_figures(
    registry: pd.DataFrame,
    images_dir: Path,
    inference_ids: set[str],
    plan_names: list[str],
    prefixes: tuple[str, ...] = ("iter1_", "iter2_", "loop_", "workflow"),
) -> dict:
    """Check the figures whose filename starts with one of ``prefixes`` (all four by default).

    Problems found per figure: missing file, unreadable PNG, dpi below MIN_DPI, empty
    registry fields, an inference ID that is not in the inference log. Global problems:
    PNGs that are not registered, registered names without a file, plan names without a file.
    """
    on_disk = {p.name for p in images_dir.glob("*.png")}
    rows = registry[registry["filename"].str.startswith(prefixes)]
    per_figure: dict[str, list[str]] = {}
    for row in rows.itertuples():
        problems = []
        path = images_dir / row.filename
        if not path.exists():
            problems.append("file missing")
        else:
            try:
                with Image.open(path) as image:
                    dpi = image.info.get("dpi")
                    if dpi is None or min(dpi) < MIN_DPI:
                        problems.append(f"dpi {dpi} below {MIN_DPI}")
            except OSError as error:
                problems.append(f"unreadable PNG ({error})")
        for field in REQUIRED_FIELDS:
            if not str(getattr(row, field, "")).strip() or pd.isna(getattr(row, field, None)):
                problems.append(f"empty {field}")
        inference = str(row.inference_id) if pd.notna(row.inference_id) else ""
        if inference and inference not in inference_ids:
            problems.append(f"unknown inference {inference}")
        per_figure[row.filename] = problems
    registered = set(registry["filename"])
    result = {
        "n_checked": len(per_figure),
        "figures_with_problems": {f: p for f, p in per_figure.items() if p},
        "png_not_registered": sorted(on_disk - registered),
        "registered_without_file": sorted(registered - on_disk),
        "plan_names_without_file": sorted(set(plan_names) - on_disk),
    }
    result["ok"] = not (
        result["figures_with_problems"]
        or result["png_not_registered"]
        or result["registered_without_file"]
        or result["plan_names_without_file"]
    )
    return result


def contact_sheets(
    filenames: list[str], images_dir: Path, out_dir: Path, per_sheet: int = 4, width: int = 1000
) -> list[Path]:
    """Tile figures 2 x 2 into review sheets so many can be inspected at once.

    Returns the sheet paths. Each tile is scaled to ``width`` px wide; the label above each
    tile is the file name, so a problem can be traced back.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    sheets = []
    for start in range(0, len(filenames), per_sheet):
        chunk = filenames[start : start + per_sheet]
        tiles = []
        for name in chunk:
            with Image.open(images_dir / name) as image:
                tiles.append(
                    image.convert("RGB").resize((width, int(image.height * width / image.width)))
                )
        cols = 2
        rows = -(-len(tiles) // cols)
        row_h = [max(t.height for t in tiles[r * cols : (r + 1) * cols]) for r in range(rows)]
        sheet = Image.new("RGB", (cols * width, sum(row_h)), "white")
        y = 0
        for r in range(rows):
            for c, tile in enumerate(tiles[r * cols : (r + 1) * cols]):
                sheet.paste(tile, (c * width, y))
            y += row_h[r]
        path = out_dir / f"sheet_{start // per_sheet + 1}.png"
        sheet.save(path)
        sheets.append(path)
    return sheets


def run(results_dir: Path = config.RESULTS, images_dir: Path = config.IMAGES) -> dict:
    """Audit every figure (iteration 1, loop, iteration 2, workflow); write figure_audit.json."""
    registry = pd.read_csv(results_dir / "figures.csv")
    ids = set(json.loads((results_dir / "inferences.json").read_text(encoding="utf-8")))
    plan = (config.ROOT / "A3_PLAN.md").read_text(encoding="utf-8")
    result = audit_figures(registry, images_dir, ids, plan_figure_names(plan))
    (results_dir / "figure_audit.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    outcome = run()
    print(json.dumps(outcome, indent=2))
    raise SystemExit(0 if outcome["ok"] else 1)
