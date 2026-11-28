"""Code standards from STEPS.md, enforced: constants live in config.py, not in the modules."""

import ast
import re
from pathlib import Path

from src import config

SRC = Path(__file__).resolve().parents[1] / "src"
MODULES = [p for p in sorted(SRC.glob("*.py")) if p.name != "config.py"]

# Pale panel/box fills that are decoration, not a category colour. Anything new has to be
# added here deliberately or moved to config.py.
ALLOWED_FILLS = {
    "#2A3F5F",  # plotly axis text
    "#B9D6EB", "#CFE3F1", "#E3EEF7", "#E8F1F8", "#F3F8FC",  # light-blue note boxes
}  # fmt: skip


def _hexes(text: str) -> set[str]:
    return {h.upper() for h in re.findall(r"#[0-9A-Fa-f]{6}", text)}


def _is_grey(h: str) -> bool:
    return h[1:3] == h[3:5] == h[5:7]


def test_no_random_seed_or_restart_count_literals_outside_config():
    """Keyword arguments like random_state=42 or n_init=5 must name a config constant."""
    names = {"random_state", "n_init", "seed"}
    offenders = []
    for p in MODULES:
        for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call):
                for kw in node.keywords:
                    if kw.arg in names and isinstance(kw.value, ast.Constant):
                        offenders.append(f"{p.name}:{kw.value.lineno} {kw.arg}={kw.value.value}")
    assert offenders == []


def test_category_colours_are_not_redefined_outside_config():
    """A hex outside config.py must be in the config palette, a neutral grey or a known fill."""
    palette = _hexes((SRC / "config.py").read_text(encoding="utf-8"))
    offenders = []
    for p in MODULES:
        for h in _hexes(p.read_text(encoding="utf-8")):
            if h not in palette and not _is_grey(h) and h not in ALLOWED_FILLS:
                offenders.append(f"{p.name}: {h}")
    assert offenders == []


def test_stage_colours_and_feedback_label_come_from_config():
    from src import workflow_diagram as wd

    assert wd.STAGE_COLORS is config.STAGE_COLORS
    assert wd.FEEDBACK_LABEL == "Feedback loop"
