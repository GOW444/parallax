"""Workflow diagram in the style asked for in class: the rolled diamond, then the unrolled chain.

(a) Rolled: Keim et al.'s (2008) generic diamond (Data, Visualization, Model, Knowledge),
    two-way edges and the feedback loop drawn as an arrow back to Data. It has no
    self-loops (the brief asks for minimal ones). This is the reference model, not our
    application.
(b) Unrolled: the actual sequence of modules in our application, one oval per module,
    coloured by the diamond stage it belongs to. Each iteration runs
    Data -> Visualization -> three model lanes ([Statistics], [Unsupervised], [Supervised]),
    each lane Model -> Visualization of its output -> Knowledge. Iteration 1's knowledge
    feeds forward into new Data through a single edge labelled exactly "Feedback loop".
    The unrolled chain has no self-loops and no back-edges: every arrow points forward.

Nodes and edges are data (see NODES / EDGES), so tests can check the rules the brief sets.
"""

from dataclasses import dataclass

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.patches import Ellipse, FancyArrowPatch

from src import config

STAGES = ["Data", "Visualization", "Models", "Knowledge"]
STAGE_COLORS = config.STAGE_COLORS  # Okabe-Ito edge + light fill per diamond stage
FEEDBACK_LABEL = config.FEEDBACK_LABEL
NODE_W, NODE_H = 2.25, 1.0  # ellipse width / height in data units


@dataclass(frozen=True)
class Node:
    node_id: str
    stage: str
    iteration: int
    title: str
    detail: str
    x: float
    y: float


# x = column (left to right in time), y = lane. Iteration 1 lanes at y = 9.6 / 8.2 / 6.8,
# iteration 2 lanes at y = 3.4 / 2.0 / 0.6.
NODES = [
    # ---- iteration 1
    Node("d1a", "Data", 1, "Data", "raw OWID CSV\n22,012 rows", 0.0, 8.2),
    Node("d1b", "Data", 1, "Data", "clean panel,\n2018 snapshot", 2.7, 8.2),
    Node("v1a", "Visualization", 1, "Visualization", "missingness, mix,\nscatter, map", 5.4, 8.2),
    Node("m1s", "Models", 1, "[Statistics]", "Mann-Kendall,\nOLS + BP", 8.1, 9.6),
    Node("m1u", "Models", 1, "[Unsupervised]", "K-means + PCA", 8.1, 8.2),
    Node("m1r", "Models", 1, "[Supervised]", "Random Forest\n(5-fold CV)", 8.1, 6.8),
    Node("v1s", "Visualization", 1, "Vis", "residuals,\nchange plot", 10.8, 9.6),
    Node("v1u", "Visualization", 1, "Vis", "biplot,\ncluster map", 10.8, 8.2),
    Node("v1r", "Visualization", 1, "Vis", "pred vs actual,\nerror map", 10.8, 6.8),
    Node("k1s", "Knowledge", 1, "Knowledge", "I1-1 skew\nI1-3 hidden paths", 13.5, 9.6),
    Node("k1u", "Knowledge", 1, "Knowledge", "I1-2 shares are\ncompositional", 13.5, 8.2),
    Node("k1r", "Knowledge", 1, "Knowledge", "I1-4 RF lacks\ncontext", 13.5, 6.8),
    Node("k1", "Knowledge", 1, "Inferences", "I1-1 .. I1-4", 16.2, 8.2),
    # ---- iteration 2
    Node("d2", "Data", 2, "Data", "log1p, CLR,\ntrajectories, tiers", 2.7, 2.0),
    Node("v2a", "Visualization", 2, "Visualization", "decoupling quadrant,\nslope chart", 5.4, 2.0),
    Node("m2s", "Models", 2, "[Statistics]", "log-log OLS,\nKW + Holm, MK", 8.1, 3.4),
    Node("m2u", "Models", 2, "[Unsupervised]", "archetypes\nK-means vs GMM", 8.1, 2.0),
    Node("m2r", "Models", 2, "[Supervised]", "RF v2 + SHAP,\nHolt / ARIMA", 8.1, 0.6),
    Node("v2s", "Visualization", 2, "Vis", "log-log fit,\nbox plots", 10.8, 3.4),
    Node("v2u", "Visualization", 2, "Vis", "heatmap, map,\nsmall multiples", 10.8, 2.0),
    Node("v2r", "Visualization", 2, "Vis", "RF bars, SHAP,\nforecast", 10.8, 0.6),
    Node("k2s", "Knowledge", 2, "Knowledge", "I2-1 decoupling\nI2-2, I2-4", 13.5, 3.4),
    Node("k2u", "Knowledge", 2, "Knowledge", "I2-3 transition\narchetypes", 13.5, 2.0),
    Node("k2r", "Knowledge", 2, "Knowledge", "I2-5 RF v2\nI2-6 forecast", 13.5, 0.6),
    Node("k2", "Knowledge", 2, "Answer", "research\nquestion", 16.2, 2.0),
]

_CHAIN = [("d1a", "d1b"), ("d1b", "v1a")]
for _it in (1, 2):
    _start = "v1a" if _it == 1 else "v2a"
    for _lane in ("s", "u", "r"):
        _CHAIN += [
            (_start, f"m{_it}{_lane}"),
            (f"m{_it}{_lane}", f"v{_it}{_lane}"),
            (f"v{_it}{_lane}", f"k{_it}{_lane}"),
            (f"k{_it}{_lane}", f"k{_it}"),
        ]
_CHAIN.append(("d2", "v2a"))

# (from, to, label). The only labelled edge is the feedback loop, and it is the only edge
# between the iterations.
EDGES = [(a, b, "") for a, b in _CHAIN] + [("k1", "d2", FEEDBACK_LABEL)]


def edges() -> list[tuple[str, str, str]]:
    """Every edge of the unrolled chain as (from, to, label); used by the tests."""
    return list(EDGES)


# Panel (a), the generic Keim et al. diamond: stage positions and its two-way edges. Kept as
# data so a test can assert that the rolled panel has no self-loops either.
ROLLED_POS = {
    "Data": (0, 0),
    "Visualization": (2.2, 1.1),
    "Models": (2.2, -1.1),
    "Knowledge": (4.4, 0),
}
ROLLED_EDGES = [
    ("Data", "Visualization"),
    ("Data", "Models"),
    ("Visualization", "Knowledge"),
    ("Models", "Knowledge"),
]


# ---------------------------------------------------------------------------- drawing
def _arrow(ax, start, end, color="#333333", lw=1.5, rad=0.0, style="-|>", **kw):
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle=style,
            mutation_scale=13,
            linewidth=lw,
            color=color,
            connectionstyle=f"arc3,rad={rad}",
            shrinkA=0,
            shrinkB=0,
            **kw,
        )
    )


def _edge_points(a: Node, b: Node) -> tuple[tuple[float, float], tuple[float, float]]:
    """Start/end on the ellipse borders along the line between the two centres."""
    dx, dy = b.x - a.x, b.y - a.y
    length = (dx**2 + dy**2) ** 0.5
    ux, uy = dx / length, dy / length
    # distance from centre to the ellipse border in direction (ux, uy)
    rx, ry = NODE_W / 2, NODE_H / 2
    r = 1 / ((ux / rx) ** 2 + (uy / ry) ** 2) ** 0.5
    return (a.x + ux * (r + 0.03), a.y + uy * (r + 0.03)), (
        b.x - ux * (r + 0.06),
        b.y - uy * (r + 0.06),
    )


def _draw_node(ax, node: Node) -> None:
    fill, edge = STAGE_COLORS[node.stage]
    ax.add_patch(
        Ellipse((node.x, node.y), NODE_W, NODE_H, facecolor=fill, edgecolor=edge, linewidth=1.8)
    )
    ax.text(
        node.x, node.y + 0.2, node.title, ha="center", va="center", fontsize=8.6, fontweight="bold"
    )
    ax.text(
        node.x, node.y - 0.13, node.detail, ha="center", va="center", fontsize=6.9, linespacing=1.15
    )


def _draw_rolled(ax) -> None:
    """Panel (a): the generic diamond and one feedback loop back to Data, with no self-loops.

    The brief asks for minimal self-loops, so the generic model is drawn only with its
    two-way stage-to-stage edges (ROLLED_EDGES) and the single feedback edge.
    """
    pos = ROLLED_POS
    for stage, (x, y) in pos.items():
        fill, edge = STAGE_COLORS[stage]
        ax.add_patch(Ellipse((x, y), 1.7, 0.75, facecolor=fill, edgecolor=edge, linewidth=1.8))
        ax.text(x, y, stage, ha="center", va="center", fontsize=9, fontweight="bold")
    for a, b in ROLLED_EDGES:
        (xa, ya), (xb, yb) = pos[a], pos[b]
        dx, dy = xb - xa, yb - ya
        n = (dx**2 + dy**2) ** 0.5
        sa = (xa + dx / n * 0.75, ya + dy / n * 0.45)
        sb = (xb - dx / n * 0.75, yb - dy / n * 0.45)
        _arrow(ax, sa, sb, style="<|-|>", lw=1.2)
    # feedback loop: Knowledge back to Data, routed underneath the diamond
    floor = -1.95
    ax.plot([4.4, 4.4, 0], [-0.4, floor, floor], color="#D55E00", linewidth=1.8)
    _arrow(ax, (0, floor), (0, -0.4), color="#D55E00", lw=1.8)
    ax.text(
        2.2,
        floor - 0.08,
        FEEDBACK_LABEL,
        ha="center",
        va="top",
        fontsize=9.5,
        color="#D55E00",
        fontweight="bold",
    )
    ax.set_xlim(-1.2, 5.6)
    ax.set_ylim(-2.5, 1.95)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("(a) Rolled: Keim et al. (2008) diamond", fontsize=11, fontweight="bold")


def _draw_unrolled(ax) -> None:
    by_id = {n.node_id: n for n in NODES}
    for node in NODES:
        _draw_node(ax, node)
    for a, b, label in EDGES:
        na, nb = by_id[a], by_id[b]
        if label == FEEDBACK_LABEL:
            continue
        start, end = _edge_points(na, nb)
        _arrow(ax, start, end)

    # the feedback loop: from iteration 1's inferences down and back to iteration 2's data,
    # routed between the two bands so it never crosses a node
    k1, d2 = by_id["k1"], by_id["d2"]
    corridor_y = 5.15
    path = [(k1.x, k1.y - NODE_H / 2 - 0.05), (k1.x, corridor_y), (d2.x, corridor_y)]
    for (x0, y0), (x1, y1) in zip(path[:-1], path[1:], strict=True):
        ax.plot([x0, x1], [y0, y1], color="#D55E00", linewidth=2.4, solid_capstyle="round")
    _arrow(ax, (d2.x, corridor_y), (d2.x, d2.y + NODE_H / 2 + 0.05), color="#D55E00", lw=2.4)
    ax.text(
        (k1.x + d2.x) / 2,
        corridor_y + 0.28,
        FEEDBACK_LABEL,
        ha="center",
        va="bottom",
        fontsize=12,
        fontweight="bold",
        color="#D55E00",
        bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "edgecolor": "#D55E00"},
    )
    ax.text(
        (k1.x + d2.x) / 2,
        corridor_y - 0.12,
        "I1-1 → log1p     I1-2 → CLR     I1-3 → country trajectories     "
        "I1-4 → income tiers + history",
        ha="center",
        va="top",
        fontsize=8.2,
        color="#333333",
    )

    for label, y in (("Iteration 1", 8.2), ("Iteration 2", 2.0)):
        ax.text(
            -1.55, y, label, rotation=90, ha="center", va="center", fontsize=11.5, fontweight="bold"
        )
    for y0, y1 in ((6.15, 10.25), (-0.05, 4.05)):
        ax.add_patch(
            plt.Rectangle(
                (-1.25, y0), 18.75, y1 - y0, facecolor="#F7F7F7", edgecolor="#DDDDDD", zorder=0
            )
        )
    ax.set_xlim(-1.9, 17.6)
    ax.set_ylim(-0.2, 10.4)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(
        "(b) Unrolled: the modules of our application, in order", fontsize=11, fontweight="bold"
    )


def draw() -> Figure:
    """Return the two-panel workflow figure (rolled diamond above, unrolled chain below)."""
    fig = plt.figure(figsize=(16, 12.5))
    grid = fig.add_gridspec(2, 2, height_ratios=[1, 2.25], width_ratios=[1, 1.35])
    _draw_rolled(fig.add_subplot(grid[0, 0]))
    legend_ax = fig.add_subplot(grid[0, 1])
    legend_ax.axis("off")
    for i, stage in enumerate(STAGES):
        fill, edge = STAGE_COLORS[stage]
        legend_ax.add_patch(
            Ellipse(
                (0.12, 0.8 - i * 0.17),
                0.13,
                0.11,
                facecolor=fill,
                edgecolor=edge,
                linewidth=1.8,
                transform=legend_ax.transAxes,
            )
        )
        legend_ax.text(
            0.22, 0.8 - i * 0.17, stage, va="center", fontsize=11, transform=legend_ax.transAxes
        )
    legend_ax.text(
        0.02,
        0.03,
        "No node has a self-loop. In the unrolled chain every arrow points forward;\n"
        "the only edge between iterations is the Feedback loop, carrying four\n"
        "inferences to four transformations of the data.",
        fontsize=9.5,
        color="#333333",
        transform=legend_ax.transAxes,
    )
    legend_ax.set_title("Stage colours", fontsize=11, fontweight="bold")
    _draw_unrolled(fig.add_subplot(grid[1, :]))
    fig.suptitle(
        "Visual analytics workflow of this project (Keim et al. 2008)",
        fontsize=15,
        fontweight="bold",
        y=0.995,
    )
    fig.tight_layout()
    return fig
