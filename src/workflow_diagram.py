"""Unrolled Keim et al. (2008) workflow diagram: iteration 1 row, feedback loop, iteration 2 row.

Why unrolled: the brief asks for the feedback loop to be drawn by repeating the diamond
(Data -> Visualization <-> Models -> Knowledge) for the second iteration, joined by one edge
labelled exactly "Feedback loop", instead of an arrow bending back onto the first diamond.
There are no self-loops; the only two-way edge is Visualization <-> Models, which is the
diamond's own interaction step.

Nodes are data (id, stage, iteration, title, modules), so the drawing code never hard-codes
a position or a colour per node.
"""

from dataclasses import dataclass

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

STAGES = ["Data", "Visualization", "Models", "Knowledge"]
# Okabe-Ito colours, one per diamond stage (light fill, strong edge)
STAGE_COLORS = {
    "Data": ("#D6EAF8", "#0072B2"),
    "Visualization": ("#FDEBD0", "#E69F00"),
    "Models": ("#D5F5E3", "#009E73"),
    "Knowledge": ("#F5D5E6", "#CC79A7"),
}
FEEDBACK_LABEL = "Feedback loop"


@dataclass(frozen=True)
class Node:
    node_id: str
    stage: str
    iteration: int
    title: str
    modules: tuple[str, ...]


NODES = [
    Node(
        "d1",
        "Data",
        1,
        "D1: raw 2018 snapshot",
        (
            "OWID World Energy CSV (only source)",
            "drop aggregates, 2000-2021",
            "within-country interpolation",
            "coverage rule, balanced panel",
        ),
    ),
    Node(
        "v1",
        "Visualization",
        1,
        "V1: explore",
        (
            "missingness heatmap",
            "global mix area, distributions",
            "GDP vs energy scatter, choropleth",
            "Pearson vs Spearman heatmaps",
            "change 2000-02 -> 2016-18",
        ),
    ),
    Node(
        "m1",
        "Models",
        1,
        "M1: baseline models",
        (
            "statistics: Mann-Kendall, OLS + BP",
            "unsupervised: K-means + PCA",
            "supervised: Random Forest (CV)",
        ),
    ),
    Node(
        "k1",
        "Knowledge",
        1,
        "K1: inferences I1-1..I1-4",
        (
            "I1-1 skew, heteroscedasticity",
            "I1-2 shares are compositional",
            "I1-3 snapshot hides paths",
            "I1-4 RF lacks context",
        ),
    ),
    Node(
        "d2",
        "Data",
        2,
        "D2: transformed data",
        (
            "log1p of skewed variables",
            "CLR of the 8 mix shares",
            "one row per country (trajectories)",
            "income tiers, history; pre-2019 table",
        ),
    ),
    Node(
        "v2",
        "Visualization",
        2,
        "V2: explore again",
        (
            "decoupling quadrant, tier box plots",
            "log-log elasticity, slope chart",
            "archetype heatmap, map, time panels",
            "producers box plot",
        ),
    ),
    Node(
        "m2",
        "Models",
        2,
        "M2: re-modelling",
        (
            "statistics: log OLS (HC3), KW + Holm",
            "unsupervised: archetype clustering",
            "supervised: RF v2 (same folds)",
            "Mann-Kendall per archetype",
        ),
    ),
    Node(
        "k2",
        "Knowledge",
        2,
        "K2: inferences I2-1..I2-5",
        (
            "decoupling by income tier",
            "income elasticity of energy",
            "transition archetypes",
            "producers; what RF v2 learned",
        ),
    ),
]

# Directed edges within each iteration. ("v", "m") is drawn two-headed: the diamond's
# Visualization <-> Models interaction. No node points to itself.
ITERATION_EDGES = [("d", "v", False), ("v", "m", True), ("m", "k", False)]

BOX_W, BOX_H = 3.8, 2.45
X_GAP = 0.9
ROW_Y = {1: 4.2, 2: 0.0}


def _position(node: Node) -> tuple[float, float]:
    col = STAGES.index(node.stage)
    return col * (BOX_W + X_GAP), ROW_Y[node.iteration]


def _draw_node(ax, node: Node) -> None:
    x, y = _position(node)
    fill, edge = STAGE_COLORS[node.stage]
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            BOX_W,
            BOX_H,
            boxstyle="round,pad=0.04,rounding_size=0.12",
            facecolor=fill,
            edgecolor=edge,
            linewidth=2,
        )
    )
    ax.text(
        x + BOX_W / 2,
        y + BOX_H - 0.25,
        node.title,
        ha="center",
        va="top",
        fontsize=10.5,
        fontweight="bold",
    )
    body = "\n".join(f"- {m}" for m in node.modules)
    ax.text(x + 0.15, y + BOX_H - 0.68, body, ha="left", va="top", fontsize=8.1, linespacing=1.45)


def _arrow(ax, start, end, two_way=False, **kwargs) -> None:
    style = "<|-|>" if two_way else "-|>"
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle=style,
            mutation_scale=16,
            linewidth=1.8,
            color="#333333",
            **kwargs,
        )
    )


def draw() -> Figure:
    """Return the unrolled workflow figure (two rows of four stages + the feedback edge)."""
    fig, ax = plt.subplots(figsize=(16, 9))
    by_id = {n.node_id: n for n in NODES}
    for node in NODES:
        _draw_node(ax, node)
    for it in (1, 2):
        for a, b, two_way in ITERATION_EDGES:
            xa, ya = _position(by_id[f"{a}{it}"])
            xb, _ = _position(by_id[f"{b}{it}"])
            _arrow(ax, (xa + BOX_W + 0.05, ya + BOX_H / 2), (xb - 0.05, ya + BOX_H / 2), two_way)

    # The single edge joining the iterations: K1 -> D2, labelled exactly "Feedback loop"
    xk, yk = _position(by_id["k1"])
    xd, yd = _position(by_id["d2"])
    start = (xk + BOX_W / 2, yk - 0.05)
    end = (xd + BOX_W / 2, yd + BOX_H + 0.05)
    _arrow(ax, start, end, connectionstyle="arc3,rad=0.0", linestyle="-")
    mid_x, mid_y = (start[0] + end[0]) / 2, (start[1] + end[1]) / 2
    ax.text(
        mid_x,
        mid_y + 0.12,
        FEEDBACK_LABEL,
        ha="center",
        va="center",
        fontsize=13,
        fontweight="bold",
        color="#D55E00",
        bbox={"boxstyle": "round,pad=0.3", "facecolor": "white", "edgecolor": "#D55E00"},
    )
    ax.text(
        mid_x,
        mid_y - 0.55,
        "I1-1 -> log1p   I1-2 -> CLR   I1-3 -> trajectories   I1-4 -> context features",
        ha="center",
        va="center",
        fontsize=8.8,
        color="#333333",
    )

    width = 4 * BOX_W + 3 * X_GAP
    for it, label in ((1, "Iteration 1"), (2, "Iteration 2")):
        ax.text(
            -0.35,
            ROW_Y[it] + BOX_H / 2,
            label,
            rotation=90,
            ha="center",
            va="center",
            fontsize=12,
            fontweight="bold",
        )
    for i, stage in enumerate(STAGES):
        _, edge = STAGE_COLORS[stage]
        ax.text(
            i * (BOX_W + X_GAP) + BOX_W / 2,
            ROW_Y[1] + BOX_H + 0.35,
            stage.upper(),
            ha="center",
            fontsize=11,
            fontweight="bold",
            color=edge,
        )
    ax.set_xlim(-0.7, width + 0.2)
    ax.set_ylim(-0.3, ROW_Y[1] + BOX_H + 0.8)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        "Visual analytics workflow (Keim et al. 2008 diamond), unrolled over two iterations",
        fontsize=14,
        fontweight="bold",
    )
    return fig


def edges() -> list[tuple[str, str, str]]:
    """Every edge as (from, to, label): used by the tests to check the diagram's rules."""
    out = []
    for it in (1, 2):
        for a, b, two_way in ITERATION_EDGES:
            out.append((f"{a}{it}", f"{b}{it}", ""))
            if two_way:
                out.append((f"{b}{it}", f"{a}{it}", ""))
    out.append(("k1", "d2", FEEDBACK_LABEL))
    return out
