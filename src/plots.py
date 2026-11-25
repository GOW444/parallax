"""Shared figure style and the single exit point for saving figures.

Why: every figure in the report must have a title, labelled axes, the data-source note,
a 200-dpi PNG in images/ and a row in results/figures.csv. Doing this in one function
makes those rules impossible to forget.
"""

from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.figure import Figure
from PIL import Image

if TYPE_CHECKING:
    import plotly.graph_objects as go

from src import config

FIGURE_REGISTRY_COLUMNS = ["filename", "phase", "what_it_shows", "why_this_chart", "inference_id"]
_SOURCE_NOTE_GID = "source-note"


def apply_style() -> None:
    """Apply one consistent matplotlib look (readable fonts, light grid, no top/right spines)."""
    mpl.rcParams.update(
        {
            "figure.dpi": 100,
            "savefig.dpi": config.FIG_DPI,
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.titleweight": "bold",
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 9,
            "legend.frameon": False,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.color": "#DDDDDD",
            "grid.linewidth": 0.6,
            "axes.axisbelow": True,
            "axes.prop_cycle": mpl.cycler(color=config.OKABE_ITO),
        }
    )


def add_source_note(fig: Figure, text: str = config.SOURCE_NOTE) -> None:
    """Write the data-source note in the bottom-right corner (only once per figure)."""
    already_there = any(t.get_gid() == _SOURCE_NOTE_GID for t in fig.texts)
    if not already_there:
        fig.text(
            0.995,
            0.005,
            text,
            ha="right",
            va="bottom",
            fontsize=8,
            color="#555555",
            gid=_SOURCE_NOTE_GID,
        )


def spread_positions(
    positions: list[float], min_gap: float, low: float, high: float
) -> list[float]:
    """Push sorted 1-D positions apart so neighbours are at least `min_gap` apart."""
    out = list(positions)
    for i in range(1, len(out)):  # push up
        out[i] = max(out[i], out[i - 1] + min_gap)
    if out and out[-1] > high:  # shift the block down if it ran off the top
        shift = out[-1] - high
        out = [p - shift for p in out]
    for i in range(len(out) - 2, -1, -1):  # push down again if needed
        out[i] = min(out[i], out[i + 1] - min_gap)
    return [max(p, low) for p in out]


def label_points(
    ax: mpl.axes.Axes,
    x: list[float],
    y: list[float],
    labels: list[str],
    min_gap: float = 0.045,
    offset: float = 0.06,
    fontsize: float = 8,
) -> None:
    """Label points without overlapping text, using leader lines.

    Call this AFTER the axis limits and scales are final: label positions are computed in
    axes-fraction units from the current view. Points in the right 35% of the axes are
    labelled to their left, the others to their right. Within each side, labels are
    spread vertically so no two are closer than `min_gap`.
    """
    to_axes = ax.transAxes.inverted()
    data_points = list(zip(x, y, strict=True))
    fractions = [to_axes.transform(ax.transData.transform(p)) for p in data_points]
    outside = [
        lab
        for f, lab in zip(fractions, labels, strict=True)
        if not (0 <= f[0] <= 1 and 0 <= f[1] <= 1)
    ]
    if outside:
        raise ValueError(f"points outside the axes (set limits before labelling): {outside}")
    for side in ("left", "right"):
        chosen = [
            (data_point, fraction, lab)
            for data_point, fraction, lab in zip(data_points, fractions, labels, strict=True)
            if (fraction[0] > 0.65) == (side == "left")
        ]
        chosen.sort(key=lambda item: item[1][1])
        targets = spread_positions([f[1] for _, f, _ in chosen], min_gap, 0.02, 0.98)
        for (data_point, fraction, label), ty in zip(chosen, targets, strict=True):
            tx = fraction[0] - offset if side == "left" else fraction[0] + offset
            ax.annotate(
                label,
                xy=data_point,
                xycoords="data",
                xytext=(tx, ty),
                textcoords="axes fraction",
                ha="right" if side == "left" else "left",
                va="center",
                fontsize=fontsize,
                # a light backing keeps the name readable where it crosses other points
                bbox={"boxstyle": "round,pad=0.15", "fc": "white", "ec": "none", "alpha": 0.85},
                zorder=5,
                arrowprops={"arrowstyle": "-", "color": "#777777", "linewidth": 0.6},
            )


def _is_colorbar(ax: mpl.axes.Axes) -> bool:
    return ax.get_label() == "<colorbar>"


def check_figure_labels(fig: Figure) -> list[str]:
    """Return a list of labelling problems (empty list means the figure is fine).

    Rules: the figure needs a title (suptitle or an axes title), and every visible,
    non-colorbar axes that shows its axis needs both an x and a y label.
    """
    problems = []
    has_suptitle = fig.get_suptitle().strip() != ""
    data_axes = [ax for ax in fig.axes if ax.get_visible() and not _is_colorbar(ax)]
    has_axes_title = any(ax.get_title().strip() for ax in data_axes)
    if not (has_suptitle or has_axes_title):
        problems.append("figure has no title")
    for i, ax in enumerate(data_axes):
        if not ax.axison:  # e.g. a rendered table: no axes to label
            continue
        if not ax.get_xlabel().strip():
            problems.append(f"axes {i} has no x label")
        if not ax.get_ylabel().strip():
            problems.append(f"axes {i} has no y label")
    return problems


def register_figure(
    filename: str,
    phase: str,
    what_it_shows: str,
    why_this_chart: str,
    inference_id: str = "",
    registry: Path = config.FIGURES_CSV,
) -> None:
    """Insert or replace the figure's row in figures.csv (re-runs never create duplicates)."""
    new_row = pd.DataFrame(
        [[filename, phase, what_it_shows, why_this_chart, inference_id]],
        columns=FIGURE_REGISTRY_COLUMNS,
    )
    if registry.exists():
        table = pd.read_csv(registry, dtype=str, keep_default_na=False)
        table = table[table["filename"] != filename]
        table = pd.concat([table, new_row], ignore_index=True)
    else:
        table = new_row
    registry.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(registry, index=False)


def save_figure(
    fig: Figure,
    filename: str,
    phase: str,
    what_it_shows: str,
    why_this_chart: str,
    inference_id: str = "",
    images_dir: Path = config.IMAGES,
    registry: Path = config.FIGURES_CSV,
) -> Path:
    """Validate, annotate, save (200 dpi PNG) and register a matplotlib figure.

    Raises ValueError instead of saving a figure that breaks the figure rules, so a
    badly labelled chart can never reach the report.
    """
    if not filename.endswith(".png") or "/" in filename or "\\" in filename:
        raise ValueError(f"filename must be a bare .png name, got {filename!r}")
    if not what_it_shows.strip() or not why_this_chart.strip():
        raise ValueError("what_it_shows and why_this_chart must both be filled in")
    problems = check_figure_labels(fig)
    if problems:
        raise ValueError(f"{filename}: " + "; ".join(problems))

    add_source_note(fig)
    images_dir.mkdir(parents=True, exist_ok=True)
    path = images_dir / filename
    fig.savefig(path, dpi=config.FIG_DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    register_figure(filename, phase, what_it_shows, why_this_chart, inference_id, registry)
    return path


# ---------------------------------------------------------------------------- step 56
def cluster_colors(names: list[str]) -> list[str]:
    """One colour per cluster name: the source's own colour for 'high <Source> share'.

    Why: clusters are named after sources, and painting the hydro cluster in wind's colour
    would mislead anyone reading across figures. Names that are not a source (or a source
    already taken) get the next CLUSTER_FALLBACK_COLORS entry.
    """
    fallback = iter(config.CLUSTER_FALLBACK_COLORS)
    used, colours = set(), []
    for name in names:
        source = name.removeprefix("high ").removesuffix(" share")
        colour = config.SOURCE_COLORS.get(source) if name.startswith("high ") else None
        if colour is None or colour in used:
            colour = next(fallback)
        used.add(colour)
        colours.append(colour)
    return colours


# ---------------------------------------------------------------------------- maps (step 38)
NO_DATA_COLOR = "#D9D9D9"


def choropleth(
    data: pd.DataFrame,
    value_col: str,
    title: str,
    colorbar_title: str,
    range_color: tuple[float, float] | None = None,
    color_scale: str = config.SEQUENTIAL_CMAP,
    categorical_colors: dict[str, str] | None = None,
) -> "go.Figure":
    """World map coloured by `value_col`, keyed on ISO3 codes in `iso_code`.

    Natural Earth projection centred on 0 degrees longitude (plotly's default centres on
    the Pacific). Countries absent from `data` are drawn in light grey and a "no data"
    note says so, so missing never looks like a low value.
    Pass `categorical_colors` (category -> colour) for a categorical map.
    """
    import plotly.express as px

    if categorical_colors is not None:
        fig = px.choropleth(
            data,
            locations="iso_code",
            color=value_col,
            hover_name="country",
            color_discrete_map=categorical_colors,
            category_orders={value_col: list(categorical_colors)},
        )
        fig.update_layout(legend_title_text=colorbar_title)
    else:
        fig = px.choropleth(
            data,
            locations="iso_code",
            color=value_col,
            hover_name="country",
            color_continuous_scale=color_scale,
            range_color=range_color,
        )
        # title runs along the bar ("right"), so it never collides with the top tick label
        fig.update_layout(
            coloraxis_colorbar={"title": {"text": colorbar_title, "side": "right"}, "len": 0.85}
        )
    fig.update_geos(
        projection_type="natural earth",
        projection_rotation_lon=0,
        showframe=False,
        showcoastlines=False,
        showland=True,
        landcolor=NO_DATA_COLOR,
        showcountries=True,
        countrycolor="white",
        lataxis_range=[-58, 85],
    )
    fig.update_traces(marker_line_color="white", marker_line_width=0.4)
    fig.update_layout(
        # black text, like the matplotlib figures (plotly's default is a blue-grey #2a3f5f)
        title={
            "text": f"<b>{title}</b>",
            "x": 0.5,
            "xanchor": "center",
            "font": {"size": 18, "color": "black"},
        },
        margin={"l": 10, "r": 10, "t": 60, "b": 40},
        font={"family": "Arial", "size": 13, "color": "black"},
        paper_bgcolor="white",
    )
    fig.add_annotation(
        text=config.SOURCE_NOTE,
        x=1,
        y=-0.04,
        xref="paper",
        yref="paper",
        xanchor="right",
        showarrow=False,
        font={"size": 11, "color": "#555555"},
    )
    fig.add_annotation(
        text="Grey: no data / excluded",
        x=0,
        y=-0.04,
        xref="paper",
        yref="paper",
        xanchor="left",
        showarrow=False,
        font={"size": 11, "color": "#555555"},
    )
    return fig


def save_plotly_figure(
    fig: "go.Figure",
    filename: str,
    phase: str,
    what_it_shows: str,
    why_this_chart: str,
    inference_id: str = "",
    width: int = 1400,
    height: int = 720,
    images_dir: Path = config.IMAGES,
    registry: Path = config.FIGURES_CSV,
) -> Path:
    """Validate, export (PNG at scale 2, about 200 dpi) and register a plotly figure."""
    if not filename.endswith(".png") or "/" in filename or "\\" in filename:
        raise ValueError(f"filename must be a bare .png name, got {filename!r}")
    if not what_it_shows.strip() or not why_this_chart.strip():
        raise ValueError("what_it_shows and why_this_chart must both be filled in")
    title = fig.layout.title.text or ""
    if not title.strip():
        raise ValueError(f"{filename}: figure has no title")
    colorbar_title = fig.layout.coloraxis.colorbar.title.text
    legend_title = fig.layout.legend.title.text
    if not (colorbar_title or legend_title):
        raise ValueError(f"{filename}: colour scale has no title (unit)")
    notes = [a.text for a in fig.layout.annotations]
    if config.SOURCE_NOTE not in notes:
        raise ValueError(f"{filename}: missing source note")
    images_dir.mkdir(parents=True, exist_ok=True)
    path = images_dir / filename
    fig.write_image(path, width=width, height=height, scale=2)
    # plotly writes no dpi metadata; stamp it so Word/PDF size the image like the others
    with Image.open(path) as image:
        image.load()
    image.save(path, dpi=(config.FIG_DPI, config.FIG_DPI))
    register_figure(filename, phase, what_it_shows, why_this_chart, inference_id, registry)
    return path
