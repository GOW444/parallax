"""Builders for the individual report figures.

Each function takes prepared data and returns a matplotlib Figure. Saving, the source note
and figures.csv registration are done by plots.save_figure() in the notebook, so the
figure rules are enforced in one place.
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from matplotlib.ticker import FuncFormatter, MaxNLocator, MultipleLocator

from src import config, logbook, plots

THOUSANDS = FuncFormatter(lambda value, _: f"{value:,.0f}")

# Row groups for the missingness heatmap: (group label, columns), top to bottom
MISSINGNESS_GROUPS = [
    ("GDP", ["gdp", "energy_per_gdp"]),
    ("Energy use", ["energy_per_capita", "per_capita_electricity", config.GENERATION_COL]),
    (
        "Electricity grid",
        [config.TARGET_COL, "greenhouse_gas_emissions", config.LOW_CARBON_SHARE_COL]
        + config.MIX_SHARE_COLS,
    ),
    ("Fossil production", config.RAW_PRODUCER_COLS),
]


def missingness_heatmap(pct_missing: pd.DataFrame) -> Figure:
    """Heatmap of % of countries missing each column per year, with structural breaks marked.

    pct_missing: rows = column names, columns = years (output of prep.missingness_by_year).
    """
    rows = [col for _, cols in MISSINGNESS_GROUPS for col in cols]
    data = pct_missing.loc[rows]
    years = list(data.columns)

    fig, ax = plt.subplots(figsize=(11, 7.5))
    image = ax.imshow(
        data.to_numpy(),
        aspect="auto",
        cmap=config.SEQUENTIAL_CMAP,
        vmin=0,
        vmax=100,
        interpolation="nearest",
    )
    ax.grid(False)
    ax.set_xticks(range(len(years)), labels=years, rotation=90)
    ax.set_yticks(range(len(rows)), labels=rows)

    # Separate the variable groups and name them on the right-hand side
    start = 0
    for label, cols in MISSINGNESS_GROUPS:
        end = start + len(cols)
        if start > 0:
            ax.axhline(start - 0.5, color="white", linewidth=2)
        ax.text(
            len(years) - 0.3,
            (start + end - 1) / 2,
            f" {label}",
            va="center",
            ha="left",
            fontsize=9,
            fontweight="bold",
        )
        start = end

    # Mark the two structural breaks the analysis is designed around. The lines are only
    # two columns apart, so the labels sit on opposite sides of their lines.
    breaks = [
        (config.PRODUCER_LAST_FULL_YEAR, "Producer data: main producers only from 2017 ", "right"),
        (config.GDP_LAST_YEAR, " GDP ends after 2018", "left"),
    ]
    for year, text, align in breaks:
        x = years.index(year) + 0.5
        ax.axvline(x, color="#D55E00", linewidth=2, linestyle="--")
        ax.text(
            x, -0.7, text, color="#D55E00", ha=align, va="bottom", fontsize=8.5, fontweight="bold"
        )

    colorbar = fig.colorbar(image, ax=ax, pad=0.16, fraction=0.03)
    colorbar.set_label("% of countries missing")
    ax.set_xlabel("Year")
    ax.set_ylabel("Column (raw OWID name)")
    ax.set_title(
        f"Missing data by column and year, {len(pct_missing.columns)} years "
        f"x {config.N_COUNTRIES_WITH_ISO} countries and territories",
        pad=34,
    )
    return fig


# ---------------------------------------------------------------------------- step 33
def global_mix_area(twh: pd.DataFrame, low_carbon_pct: pd.Series, n_countries: int) -> Figure:
    """Stacked area of world generation by source, with the fossil/low-carbon boundary."""
    fig, ax = plt.subplots(figsize=(10.5, 5.5))
    years = twh.index.to_numpy()
    layers = [twh[source].to_numpy() for source in config.SOURCE_NAMES]
    colors = [config.SOURCE_COLORS[source] for source in config.SOURCE_NAMES]
    ax.stackplot(
        years, *layers, labels=config.SOURCE_NAMES, colors=colors, edgecolor="white", linewidth=0.3
    )

    fossil_total = twh[["Coal", "Gas", "Oil"]].sum(axis=1)
    ax.plot(
        years,
        fossil_total,
        color="black",
        linewidth=1.2,
        linestyle="--",
        label="Fossil (below) / low-carbon (above)",
    )

    lowest_year = int(low_carbon_pct.idxmin())
    summary = (
        f"Low-carbon share of generation:\n"
        f"{low_carbon_pct.iloc[0]:.1f}% in {years[0]}, lowest {low_carbon_pct.min():.1f}% "
        f"in {lowest_year}, {low_carbon_pct.iloc[-1]:.1f}% in {years[-1]}"
    )
    ax.text(
        0.02,
        0.97,
        summary,
        transform=ax.transAxes,
        va="top",
        fontsize=9,
        bbox={"facecolor": "white", "edgecolor": "#BBBBBB", "boxstyle": "round,pad=0.4"},
    )

    # Reverse so the legend reads in the same order as the stack (top to bottom); the
    # boundary line (plotted last, so first after reversing) is moved to the end.
    handles, labels = ax.get_legend_handles_labels()
    handles, labels = handles[::-1], labels[::-1]
    handles, labels = handles[1:] + handles[:1], labels[1:] + labels[:1]
    ax.legend(
        handles,
        labels,
        loc="upper left",
        bbox_to_anchor=(1.01, 1.0),
        title="Source (top to bottom)",
    )
    ax.xaxis.set_major_locator(MultipleLocator(3))
    ax.set_xlim(years[0], years[-1])
    ax.set_ylim(0, twh["Total"].max() * 1.08)
    ax.yaxis.set_major_formatter(THOUSANDS)
    ax.set_xlabel("Year")
    ax.set_ylabel("Electricity generation (TWh)")
    ax.set_title(
        f"World electricity generation by source, {years[0]}-{years[-1]} "
        f"({n_countries} countries, fixed panel)"
    )
    return fig


# ---------------------------------------------------------------------------- step 34
def distributions(snapshot: pd.DataFrame, columns: list[str], skewness: dict) -> Figure:
    """2x2 histograms on raw scales, each annotated with n, median and skewness."""
    fig, axes = plt.subplots(2, 2, figsize=(11, 7.5))
    for ax, col in zip(axes.flat, columns, strict=True):
        values = snapshot[col].dropna()
        counts, _, _ = ax.hist(
            values, bins=30, color=config.OKABE_ITO[3], edgecolor="white", linewidth=0.4
        )
        ax.set_ylim(0, counts.max() * 1.45)  # headroom so the stats box never covers a bar
        median = values.median()
        ax.axvline(median, color=config.OKABE_ITO[4], linestyle="--", linewidth=1.3)
        ax.text(
            0.97,
            0.95,
            f"n = {len(values)}\nmedian (dashed) = {median:,.0f}\nskewness = {skewness[col]:.2f}",
            transform=ax.transAxes,
            ha="right",
            va="top",
            fontsize=9,
            bbox={"facecolor": "white", "edgecolor": "#BBBBBB", "boxstyle": "round,pad=0.3"},
        )
        ax.xaxis.set_major_formatter(THOUSANDS)
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))  # counts are whole countries
        ax.set_xlabel(config.VAR_LABELS[col][1])
        ax.set_ylabel("Number of countries")
        ax.set_title(config.VAR_LABELS[col][0])
    fig.suptitle(
        f"Distributions across countries in {config.SNAPSHOT_YEAR} (raw scales)",
        fontweight="bold",
        fontsize=13,
    )
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------- step 35
def _population_label(pop: float) -> str:
    return f"{pop / 1e9:g} billion" if pop >= 1e9 else f"{pop / 1e6:g} million"


def gdp_vs_energy_linear(snapshot: pd.DataFrame, n_label: int = 10, n_populous: int = 3) -> Figure:
    """Bubble scatter of GDP vs energy per person on linear axes.

    The top energy users and the most populous countries are labelled, so the reader can
    see both the outliers that dominate the axes and where most people actually live.
    """
    data = snapshot.dropna(subset=["gdp_pc", "energy_per_capita", "population"])
    max_pop = data["population"].max()

    def bubble_size(pop):
        return 15 + 1500 * np.asarray(pop) / max_pop

    fig, ax = plt.subplots(figsize=(10.5, 7))
    ax.scatter(
        data["gdp_pc"],
        data["energy_per_capita"],
        s=bubble_size(data["population"]),
        color=config.OKABE_ITO[3],
        alpha=0.55,
        edgecolor="white",
        linewidth=0.6,
    )

    for pop in (10e6, 100e6, 1e9):
        ax.scatter(
            [],
            [],
            s=bubble_size(pop),
            color=config.OKABE_ITO[3],
            alpha=0.55,
            edgecolor="white",
            label=_population_label(pop),
        )
    ax.legend(title="Population", loc="lower right", labelspacing=1.6, borderpad=1.1)

    ax.xaxis.set_major_formatter(THOUSANDS)
    ax.yaxis.set_major_formatter(THOUSANDS)
    ax.set_xlim(0, data["gdp_pc"].max() * 1.05)
    ax.set_ylim(0, data["energy_per_capita"].max() * 1.08)

    # labels last: their positions depend on the final axis limits
    top = data.nlargest(n_label, "energy_per_capita")
    populous = data.nlargest(n_populous, "population")
    labelled = pd.concat([top, populous]).drop_duplicates("country")
    plots.label_points(
        ax,
        labelled["gdp_pc"].tolist(),
        labelled["energy_per_capita"].tolist(),
        labelled["country"].tolist(),
    )
    ax.set_xlabel(config.VAR_LABELS["gdp_pc"][1])
    ax.set_ylabel(config.VAR_LABELS["energy_per_capita"][1])
    ax.set_title(
        f"GDP vs energy use per person, {config.SNAPSHOT_YEAR} (linear axes, n = {len(data)})\n"
        f"labelled: top {n_label} energy users and the {n_populous} most populous countries"
    )
    return fig


# ---------------------------------------------------------------------------- step 37
def correlation_pair(
    pearson: pd.DataFrame, spearman: pd.DataFrame, n: int, flag_gap: float = 0.2
) -> Figure:
    """Pearson and Spearman heatmaps side by side; cells where they differ by >= flag_gap
    are outlined, because a large gap signals non-linearity or outliers."""
    names = [config.VAR_LABELS[c][0] for c in pearson.columns]
    # wide spacing: each panel keeps its own row labels, which need room between panels
    fig, axes = plt.subplots(1, 2, figsize=(16.5, 6.8), gridspec_kw={"wspace": 0.75})
    gap = (spearman - pearson).abs()
    for ax, matrix, title in zip(
        axes, (pearson, spearman), ("Pearson r (linear)", "Spearman rho (rank)"), strict=True
    ):
        image = ax.imshow(matrix.to_numpy(), cmap=config.DIVERGING_CMAP, vmin=-1, vmax=1)
        ax.grid(False)
        ax.set_xticks(range(len(names)), labels=names, rotation=40, ha="right")
        ax.set_yticks(range(len(names)), labels=names)
        for i in range(len(names)):
            for j in range(len(names)):
                value = matrix.iat[i, j]
                ax.text(
                    j,
                    i,
                    f"{value:.2f}",
                    ha="center",
                    va="center",
                    fontsize=8,
                    color="white" if abs(value) > 0.6 else "black",
                )
                if i != j and gap.iat[i, j] >= flag_gap:
                    ax.add_patch(
                        Rectangle(
                            (j - 0.5, i - 0.5), 1, 1, fill=False, edgecolor="black", linewidth=2
                        )
                    )
        ax.set_title(title)
        ax.set_xlabel("Variable")
        ax.set_ylabel("Variable")
    colorbar = fig.colorbar(image, ax=axes, fraction=0.025, pad=0.02)
    colorbar.set_label("Correlation coefficient")
    fig.suptitle(
        f"Correlations between key variables, {config.SNAPSHOT_YEAR} (n = {n} countries); "
        f"outlined cells: |rho - r| >= {flag_gap}",
        fontweight="bold",
        fontsize=13,
    )
    return fig


# ---------------------------------------------------------------------------- step 42
def change_2000_2018(
    table: pd.DataFrame, summary: dict, rank_rho: float, n_movers: int = config.N_CHANGE_MOVERS
) -> Figure:
    """(a) distribution of each country's change in low-carbon share; (b) rank vs rank.

    Evidence for I1-3: if countries kept their positions, every point in (b) would lie on
    the diagonal. `summary` comes from features.change_summary(), so the counts printed on
    the figure are the saved ones.
    """
    base_label = f"{config.BASE_YEARS[0]}-{config.BASE_YEARS[1] % 100:02d}"
    end_label = f"{config.END_YEARS_GDP[0]}-{config.END_YEARS_GDP[1] % 100:02d}"
    fig, (ax_hist, ax_rank) = plt.subplots(1, 2, figsize=(14, 6.2))

    change = table["change"]
    q1, median, q3 = change.quantile([0.25, 0.5, 0.75])
    counts, _, _ = ax_hist.hist(
        change, bins=30, color=config.OKABE_ITO[3], edgecolor="white", linewidth=0.4
    )
    ax_hist.axvspan(q1, q3, color=config.OKABE_ITO[1], alpha=0.25, label="Middle 50% of countries")
    ax_hist.axvline(0, color="black", linewidth=1, label="No change")
    ax_hist.axvline(
        median,
        color=config.OKABE_ITO[4],
        linestyle="--",
        linewidth=1.4,
        label=f"Median ({median:+.1f} pp)",
    )
    threshold = summary["threshold_pp"]
    for edge in (-threshold, threshold):
        ax_hist.axvline(edge, color="#777777", linestyle=":", linewidth=1)
    ax_hist.text(
        0.02,
        0.97,
        f"n = {summary['n_countries']} countries\n"
        f"{summary['n_changed_over_threshold']} "
        f"({summary['share_changed_over_threshold']:.0%}) moved by more than "
        f"{threshold:.0f} pp\n(beyond the dotted lines): "
        f"{summary['n_rose_over_threshold']} rose, {summary['n_fell_over_threshold']} fell",
        transform=ax_hist.transAxes,
        va="top",
        fontsize=9,
        bbox={"facecolor": "white", "edgecolor": "#BBBBBB", "boxstyle": "round,pad=0.3"},
    )
    ax_hist.set_ylim(0, counts.max() * 1.35)
    ax_hist.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax_hist.legend(loc="upper right")
    ax_hist.set_xlabel(
        f"Change in low-carbon share, {base_label} to {end_label} (percentage points)"
    )
    ax_hist.set_ylabel("Number of countries")
    ax_hist.set_title("(a) How much did each country's low-carbon share change?")

    n = len(table)
    ax_rank.scatter(
        table["base_rank"],
        table["end_rank"],
        s=22,
        color=config.OKABE_ITO[3],
        alpha=0.6,
        edgecolor="white",
        linewidth=0.4,
    )
    ax_rank.plot(
        [1, n], [1, n], color="black", linewidth=1, linestyle="--", label="Same rank at both ends"
    )
    ax_rank.set_xlim(0, n + 1)
    ax_rank.set_ylim(0, n + 1)
    ax_rank.text(
        0.97,
        0.05,
        "rose in the ranking",
        transform=ax_rank.transAxes,
        ha="right",
        fontsize=9,
        color="#444444",
        style="italic",
    )
    ax_rank.text(
        0.03,
        0.93,
        "fell in the ranking",
        transform=ax_rank.transAxes,
        ha="left",
        fontsize=9,
        color="#444444",
        style="italic",
    )
    movers = pd.concat(
        [table.nlargest(n_movers, "rank_change"), table.nsmallest(n_movers, "rank_change")]
    )
    plots.label_points(
        ax_rank,
        movers["base_rank"].tolist(),
        movers["end_rank"].tolist(),
        [f"{c} ({d:+.0f} pp)" for c, d in zip(movers["country"], movers["change"], strict=True)],
    )
    ax_rank.legend(loc="upper center")
    # Countries at 0% low-carbon at the base share one tied (average) rank, which creates a
    # vertical column of points; the axis label explains it so it is not read as an error.
    zero_base = table[table["base_mean"] == 0]
    tie_note = ""
    if len(zero_base) > 1:
        tie_note = (
            f"\n(vertical column at {zero_base['base_rank'].iloc[0]:.0f}: "
            f"{len(zero_base)} countries at 0% share one tied rank)"
        )
    ax_rank.set_xlabel(f"Rank by low-carbon share, {base_label} (1 = highest){tie_note}")
    ax_rank.set_ylabel(f"Rank by low-carbon share, {end_label} (1 = highest)")
    ax_rank.set_title(f"(b) Rank then vs rank now (Spearman rho = {rank_rho:.2f})")

    fig.suptitle(
        f"Low-carbon share of electricity, {base_label} vs {end_label}: median change "
        f"{summary['median_change_pp']:+.1f} pp, but "
        f"{summary['share_changed_over_threshold']:.0%} of countries moved by more than "
        f"{threshold:.0f} pp",
        fontweight="bold",
        fontsize=13,
    )
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------- step 48
def ols_residuals(per_row: pd.DataFrame, summary: dict, n_label: int = 5) -> Figure:
    """Residuals vs fitted values of the raw OLS, with a LOWESS trend of the residuals.

    A funnel (spread growing with the fitted value) means heteroscedasticity; a curved
    LOWESS line means the straight-line model misses a non-linear relationship.
    """
    from statsmodels.nonparametric.smoothers_lowess import lowess

    fig, ax = plt.subplots(figsize=(10.5, 6.5))
    ax.scatter(
        per_row["fitted"],
        per_row["residual"],
        s=24,
        color=config.OKABE_ITO[3],
        alpha=0.6,
        edgecolor="white",
        linewidth=0.4,
        label="Country",
    )
    smooth = lowess(per_row["residual"], per_row["fitted"], frac=0.5)
    ax.plot(
        smooth[:, 0],
        smooth[:, 1],
        color=config.OKABE_ITO[4],
        linewidth=2,
        label="LOWESS trend of residuals",
    )
    ax.axhline(0, color="black", linewidth=1)
    p_text = (
        "< 0.001" if summary["breusch_pagan_p"] < 0.001 else f"= {summary['breusch_pagan_p']:.3f}"
    )
    # top-right is empty in this plot (large residuals sit at mid fitted values and Ireland
    # sits bottom-right)
    ax.text(
        0.98,
        0.97,
        f"OLS: energy per person = {summary['intercept']:,.0f} + "
        f"{summary['slope']:.2f} x GDP per person\n"
        f"n = {summary['n']}, R² = {summary['r_squared']:.2f}\n"
        f"Breusch-Pagan p {p_text} (spread of residuals is not constant)",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=9,
        bbox={"facecolor": "white", "edgecolor": "#BBBBBB", "boxstyle": "round,pad=0.4"},
    )
    ax.xaxis.set_major_formatter(THOUSANDS)
    ax.yaxis.set_major_formatter(THOUSANDS)
    pad_x = (per_row["fitted"].max() - per_row["fitted"].min()) * 0.05
    pad_y = (per_row["residual"].max() - per_row["residual"].min()) * 0.12
    ax.set_xlim(per_row["fitted"].min() - pad_x, per_row["fitted"].max() + pad_x)
    ax.set_ylim(per_row["residual"].min() - pad_y, per_row["residual"].max() + pad_y)
    ax.legend(loc="lower left")
    worst = per_row.nlargest(n_label, "abs_residual")
    plots.label_points(
        ax, worst["fitted"].tolist(), worst["residual"].tolist(), worst["country"].tolist()
    )
    ax.set_xlabel("Fitted primary energy per person (kWh)")
    ax.set_ylabel("Residual: actual minus fitted (kWh)")
    ax.set_title(
        f"Raw-scale OLS of energy on GDP per person, {config.SNAPSHOT_YEAR}: residuals vs fitted"
    )
    return fig


# ---------------------------------------------------------------------------- step 53
def kmeans_k_selection(scan: pd.DataFrame, chosen_k: int) -> Figure:
    """(a) elbow: inertia vs k; (b) mean silhouette vs k, with the chosen k marked.

    Two panels because the two criteria answer different questions: inertia always falls
    as k grows (so only its bend is informative), while silhouette measures how well
    separated the clusters are and can be read against fixed strength bands.
    """
    fig, (ax_in, ax_si) = plt.subplots(1, 2, figsize=(13, 5.4))
    chosen = scan.set_index("k").loc[chosen_k]
    for ax, col in ((ax_in, "inertia"), (ax_si, "silhouette")):
        ax.plot(scan["k"], scan[col], marker="o", color=config.OKABE_ITO[3], linewidth=2)
        ax.plot(
            chosen_k,
            chosen[col],
            marker="o",
            markersize=13,
            markerfacecolor="none",
            markeredgecolor=config.OKABE_ITO[4],
            markeredgewidth=2.2,
            linestyle="none",
            label=f"Chosen k = {chosen_k}",
        )
        ax.xaxis.set_major_locator(MultipleLocator(1))
        ax.set_xlabel("Number of clusters k")

    ax_in.yaxis.set_major_formatter(THOUSANDS)
    ax_in.set_ylabel("Inertia (within-cluster sum of squared z-distances)")
    ax_in.set_title("(a) Elbow: inertia falls with every extra cluster")
    ax_in.legend(loc="upper right")

    # shade the Kaufman & Rousseeuw strength bands that the scores fall into
    top = max(scan["silhouette"].max() * 1.25, config.SILHOUETTE_BANDS[1][0] + 0.05)
    lower = 0.0
    band_colors = ["#F2F2F2", "#E3EEF7", "#CFE3F1", "#B9D6EB"]
    for (upper, words), shade in zip(config.SILHOUETTE_BANDS, band_colors, strict=True):
        if lower >= top:
            break
        ax_si.axhspan(lower, min(upper, top), color=shade, zorder=0)
        ax_si.text(
            scan["k"].min() - 0.35,
            (lower + min(upper, top)) / 2,
            f"{words} structure",
            fontsize=8.5,
            color="#555555",
            va="center",
        )
        lower = upper
    ax_si.set_ylim(0, top)
    ax_si.set_xlim(scan["k"].min() - 0.45, scan["k"].max() + 0.45)
    ax_si.set_ylabel("Mean silhouette (-1 to 1, higher = better separated)")
    ax_si.set_title("(b) Silhouette, shaded by Kaufman & Rousseeuw bands")
    if chosen_k == scan["k"].max():
        ax_si.text(
            chosen_k,
            chosen["silhouette"] - 0.035,
            "maximum at the edge\nof the pre-set range",
            ha="center",
            va="top",
            fontsize=8.5,
            color=config.OKABE_ITO[4],
        )
    ax_si.legend(loc="lower right")
    fig.suptitle(
        f"Iteration 1 K-means on raw shares + intensities ({config.SNAPSHOT_YEAR}): choosing k\n"
        f"rule fixed before fitting: {config.K_RULE}",
        fontweight="bold",
        fontsize=13,
    )
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------- step 56
def kmeans_pca(
    scores: np.ndarray,
    labels: np.ndarray,
    names: list[str],
    pca_summary: dict,
    countries: list[str],
    n_label: int = config.N_PCA_LABELS,
) -> Figure:
    """(a) countries on PC1/PC2 coloured by cluster; (b) correlation circle of the features.

    The biplot is split into two panels so the 11 loading arrows do not hide the points:
    both panels share the same PC axes, so a direction in (b) is the same direction in (a).
    """
    var1, var2 = (v * 100 for v in pca_summary["explained_variance_ratio"])
    fig, (ax_sc, ax_ld) = plt.subplots(
        1, 2, figsize=(15, 7.4), gridspec_kw={"width_ratios": [1.3, 1]}
    )
    sizes = np.bincount(labels)[1:]
    colours = plots.cluster_colors(names)
    for c in range(1, len(names) + 1):
        mask = labels == c
        ax_sc.scatter(
            scores[mask, 0],
            scores[mask, 1],
            s=30,
            color=colours[c - 1],
            edgecolor="#333333",
            linewidth=0.4,
            alpha=0.85,
            label=f"C{c}: {names[c - 1]} (n = {sizes[c - 1]})",
        )
    pad = 0.08
    for axis, col in ((ax_sc.set_xlim, 0), (ax_sc.set_ylim, 1)):
        low, high = scores[:, col].min(), scores[:, col].max()
        span = high - low
        axis(low - pad * span, high + pad * span)
    ax_sc.axhline(0, color="#999999", linewidth=0.6, zorder=0)
    ax_sc.axvline(0, color="#999999", linewidth=0.6, zorder=0)
    far = np.argsort(-np.hypot(scores[:, 0], scores[:, 1]))[:n_label]
    plots.label_points(
        ax_sc,
        scores[far, 0].tolist(),
        scores[far, 1].tolist(),
        [countries[i] for i in far],
    )
    ax_sc.set_xlabel(f"PC1 ({var1:.1f}% of variance)")
    ax_sc.set_ylabel(f"PC2 ({var2:.1f}% of variance)")
    ax_sc.set_title(f"(a) Countries, coloured by K-means cluster ({n_label} farthest named)")

    circle = plt.Circle((0, 0), 1, fill=False, color="#999999", linewidth=0.8)
    ax_ld.add_patch(circle)
    # labels sit in two columns outside the unit circle (left/right of the arrow tip),
    # spread vertically so none overlap, and joined to their tip by a dotted leader
    column_x, min_gap, y_limit = 1.22, 0.14, 1.3
    for load in pca_summary["loadings"].values():
        ax_ld.annotate(
            "",
            xy=(load["PC1"], load["PC2"]),
            xytext=(0, 0),
            arrowprops={"arrowstyle": "-|>", "color": config.OKABE_ITO[3], "linewidth": 1.4},
        )
    for side in (-1, 1):
        tips = sorted(
            (
                (load["PC2"], load["PC1"], col)
                for col, load in pca_summary["loadings"].items()
                if (load["PC1"] < 0) == (side < 0)
            ),
        )
        targets = plots.spread_positions([y for y, _, _ in tips], min_gap, -y_limit, y_limit)
        for (y, x, col), ty in zip(tips, targets, strict=True):
            ax_ld.plot(
                [x, side * (column_x - 0.03)],
                [y, ty],
                linestyle=":",
                color="#999999",
                linewidth=0.8,
            )
            ax_ld.text(
                side * column_x,
                ty,
                config.FEATURE_SHORT[col],
                fontsize=8.5,
                ha="left" if side > 0 else "right",
                va="center",
            )
    ax_ld.axhline(0, color="#999999", linewidth=0.6, zorder=0)
    ax_ld.axvline(0, color="#999999", linewidth=0.6, zorder=0)
    ax_ld.set_xlim(-2.25, 2.25)
    ax_ld.set_ylim(-y_limit - 0.1, y_limit + 0.1)
    ax_ld.set_aspect("equal")
    ax_ld.set_xlabel("Correlation with PC1")
    ax_ld.set_ylabel("Correlation with PC2")
    ax_ld.set_title("(b) Feature loadings (arrow = correlation with each PC)")

    handles, legend_labels = ax_sc.get_legend_handles_labels()
    fig.legend(
        handles,
        legend_labels,
        loc="lower center",
        ncol=4,
        frameon=False,
        bbox_to_anchor=(0.5, -0.01),
        title="Iteration 1 cluster (named after its most extreme standardised centre value)",
    )
    fig.suptitle(
        f"PCA of the iteration 1 clustering features ({config.SNAPSHOT_YEAR}, standardised): "
        f"the first two components keep {var1 + var2:.0f}% of the variance",
        fontweight="bold",
        fontsize=13,
    )
    fig.tight_layout(rect=(0, 0.12, 1, 1))
    return fig


# ---------------------------------------------------------------------------- step 65
def rf_pred_vs_actual(
    oof: pd.DataFrame,
    metrics: dict,
    dominant: pd.Series,
    target: str = config.RF_TARGET,
    n_label: int = config.N_RF_LABELS,
) -> Figure:
    """Out-of-fold predictions against actual values, coloured by dominant source.

    Points on the 1:1 line are perfect predictions. The colour (largest source in the mix)
    is for interpretation only and is NOT a model feature: it shows whether the errors line
    up with something the model was not allowed to see.
    """
    fig, ax = plt.subplots(figsize=(12.5, 8.6))
    data = oof.assign(dominant=dominant.to_numpy())
    for source in config.SOURCE_NAMES:
        rows = data[data["dominant"] == source]
        if rows.empty:
            continue
        ax.scatter(
            rows[target],
            rows["predicted"],
            s=36,
            color=config.SOURCE_COLORS[source],
            edgecolor="#333333",
            linewidth=0.4,
            alpha=0.9,
            label=f"{source} (n = {len(rows)})",
        )
    top = max(data[target].max(), data["predicted"].max()) * 1.05
    ax.plot([0, top], [0, top], color="black", linewidth=1, linestyle="--", label="Perfect (1:1)")
    # the baseline predicts each fold's training mean; the line shows their average
    ax.axhline(
        data["baseline"].mean(),
        color="#999999",
        linewidth=1.2,
        linestyle=":",
        label="Mean-predictor baseline (avg. over folds)",
    )
    ax.set_xlim(0, top)
    ax.set_ylim(0, top)
    ax.set_aspect("equal")
    ax.text(
        0.02,
        0.98,
        f"{metrics['n_folds']}-fold cross-validation, out-of-fold, n = {metrics['n']}\n"
        f"Random Forest: R² = {metrics['r2_mean']:.2f} ± {metrics['r2_sd']:.2f}, "
        f"MAE = {metrics['mae_mean']:.0f} ± {metrics['mae_sd']:.0f}\n"
        f"Baseline (mean): R² = {metrics['baseline_r2_mean']:.2f} ± "
        f"{metrics['baseline_r2_sd']:.2f}, MAE = {metrics['baseline_mae_mean']:.0f} ± "
        f"{metrics['baseline_mae_sd']:.0f}\n(mean ± sd over folds; MAE in gCO2/kWh)",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9,
        bbox={"facecolor": "white", "edgecolor": "#BBBBBB", "boxstyle": "round,pad=0.4"},
    )
    # outside the axes: every corner of this plot holds points or named errors
    ax.legend(
        loc="upper left",
        bbox_to_anchor=(1.02, 1),
        title="Dominant source\n(display only, not a feature)",
        fontsize=9,
        title_fontsize=9,
    )
    worst = data.nlargest(n_label, "abs_residual")
    plots.label_points(
        ax, worst[target].tolist(), worst["predicted"].tolist(), worst["country"].tolist()
    )
    label = config.VAR_LABELS[target][1]
    ax.set_xlabel(f"Actual {label[0].lower()}{label[1:]}")
    ax.set_ylabel(f"Predicted {label[0].lower()}{label[1:]}")
    ax.set_title(
        f"Iteration 1 Random Forest: predicted vs actual grid carbon intensity "
        f"({config.SNAPSHOT_YEAR})\n{n_label} largest errors named"
    )
    return fig


# ---------------------------------------------------------------------------- step 66
def rf_importance(importance: pd.DataFrame) -> Figure:
    """Permutation importance on held-out folds: mean rise in MAE, with ±1 sd error bars."""
    data = importance.sort_values("mean")
    labels = [config.FEATURE_SHORT[f] for f in data["feature"]]
    fig, ax = plt.subplots(figsize=(10, 5.2))
    ax.barh(
        labels,
        data["mean"],
        xerr=data["sd"],
        color=config.OKABE_ITO[3],
        edgecolor="white",
        error_kw={"ecolor": "#333333", "capsize": 3, "linewidth": 1},
    )
    ax.axvline(0, color="black", linewidth=1)
    ax.set_xlabel(
        "Increase in mean absolute error when the feature is shuffled (gCO2/kWh)\n"
        f"bars: mean over {config.N_FOLDS} held-out folds x {config.PERMUTATION_REPEATS} "
        "shuffles; whiskers: ±1 sd"
    )
    ax.set_ylabel("Feature")
    ax.set_title(
        "Iteration 1 Random Forest: permutation importance on held-out folds\n"
        "(values near 0 or below: the model does not rely on that feature)"
    )
    return fig


# ============================================================================ Phase 3: loop
# ---------------------------------------------------------------------------- step 91
def loop_before_after_table(summary: dict) -> Figure:
    """The feedback loop as a before/after table: what changed in the data, and why.

    Every number comes from features.loop_summary(); the last column names the iteration 1
    inference that triggered each change, so the table doubles as the loop's audit trail.
    """
    s = summary
    rows = [
        ("Unit of analysis", s["unit_before"], s["unit_after"], "I1-3"),
        (
            "Rows",
            f"{s['rows_before']} countries (from {s['panel_rows']:,} country-years)",
            f"{s['rows_after']} countries (common set for iteration 2)",
            "I1-3",
        ),
        (
            "Years used",
            s["years_before"],
            f"{s['years_after_models']} (models); {s['years_after_descriptive']} (visuals)",
            "I1-3",
        ),
        (
            "Feature columns",
            f"{s['feature_cols_before']} (raw levels)",
            f"{s['feature_cols_after']}: {len(s['multi_year_cols'])} built from several years, "
            f"{len(s['transformed_2018_cols'])} transformed 2018 values, "
            f"{len(s['copied_2018_cols'])} unchanged",
            "I1-3, I1-4",
        ),
        (
            "Skewed variables",
            f"raw scale (max |skew| {s['max_abs_skew_before']:.2f})",
            f"log1p (max |skew| {s['max_abs_skew_after']:.2f})",
            "I1-1",
        ),
        ("Electricity mix", s["mix_before"], s["mix_after"], "I1-2"),
        ("Income context", s["income_before"], s["income_after"], "I1-4"),
        ("Change over time", s["time_before"], s["time_after"], "I1-3"),
    ]
    fig, ax = plt.subplots(figsize=(15, 4.6))
    ax.axis("off")
    table = ax.table(
        cellText=[list(r) for r in rows],
        colLabels=["Aspect", "Iteration 1 (before the loop)", "Iteration 2 (after)", "From"],
        colWidths=[0.15, 0.33, 0.42, 0.10],
        cellLoc="left",
        loc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2.0)
    for (r, c), cell in table.get_celld().items():
        cell.set_edgecolor("#BBBBBB")
        if r == 0:
            cell.set_text_props(fontweight="bold", color="white")
            cell.set_facecolor("#3A3A3A")  # neutral: no source colour
        elif c == 0:
            cell.set_text_props(fontweight="bold")
            cell.set_facecolor("#F2F2F2")
        elif c == 2:
            cell.set_facecolor("#E8F1F8")
    ax.set_title(
        "The feedback loop changes the unit of analysis, the scale and the geometry of the data",
        fontweight="bold",
        fontsize=13,
    )
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------- step 92
def loop_skew_before_after(
    snapshot: pd.DataFrame, cols: list[str], skew_table: pd.DataFrame
) -> Figure:
    """Raw (top) vs log1p (bottom) histograms of the skewed variables, skewness annotated.

    The skew values are read from skew_table (results/loop_skew.csv), not recomputed, so
    the figure and the saved numbers cannot disagree.
    """
    skew = skew_table.set_index("column")
    fig, axes = plt.subplots(2, len(cols), figsize=(5 * len(cols), 7.6))
    for j, col in enumerate(cols):
        values = snapshot[col].dropna()
        short, long_label = config.VAR_LABELS[col]
        for i, (data, label, colour, key) in enumerate(
            [
                # neutral colours: the source colours (e.g. pink = nuclear) mean something else
                (values, long_label, config.OKABE_ITO[3], "skew_raw"),
                (np.log1p(values), f"log1p of {long_label}", "#999933", "skew_log1p"),
            ]
        ):
            ax = axes[i, j]
            ax.hist(data, bins=30, color=colour, edgecolor="white", linewidth=0.4)
            ax.text(
                0.97,
                0.95,
                f"n = {len(values)}\nskewness = {skew.loc[col, key]:.2f}",
                transform=ax.transAxes,
                ha="right",
                va="top",
                fontsize=9,
                bbox={"facecolor": "white", "edgecolor": "#BBBBBB", "boxstyle": "round,pad=0.3"},
            )
            ax.set_xlabel(label)
            ax.set_ylabel("Number of countries")
            ax.yaxis.set_major_locator(MaxNLocator(integer=True))
            ax.set_title(f"{short}: {'raw' if i == 0 else 'after log1p'}")
    fig.suptitle(
        f"Loop transformation from I1-1: log1p removes the long right tail "
        f"({config.SNAPSHOT_YEAR}, top = raw, bottom = log1p)\n"
        f"largest |skewness| over all {len(skew)} logged variables: "
        f"{skew['skew_raw'].abs().max():.2f} raw -> {skew['skew_log1p'].abs().max():.2f}",
        fontweight="bold",
        fontsize=13,
    )
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------- step 93
def _ordinal(fraction: float) -> str:
    """0.224 -> '22nd', 0.965 -> '96th' (percentile wording)."""
    n = int(round(fraction * 100))
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _pca_panel(ax, scores: np.ndarray, summary: dict, dominant: pd.Series, title: str) -> None:
    """One PCA scatter coloured by dominant source (colour only, not a model input)."""
    for source, colour in config.SOURCE_COLORS.items():
        mask = (dominant == source).to_numpy()
        if mask.any():
            ax.scatter(
                scores[mask, 0],
                scores[mask, 1],
                s=28,
                color=colour,
                edgecolor="#333333",
                linewidth=0.4,
                alpha=0.85,
                label=f"{source} (n = {int(mask.sum())})",
            )
    var1, var2 = (v * 100 for v in summary["explained_variance_ratio"])
    ax.axhline(0, color="#999999", linewidth=0.6, zorder=0)
    ax.axvline(0, color="#999999", linewidth=0.6, zorder=0)
    ax.set_xlabel(f"PC1 ({var1:.1f}% of variance)")
    ax.set_ylabel(f"PC2 ({var2:.1f}% of variance)")
    ax.set_title(title)


def loop_clr_before_after(
    raw_scores: np.ndarray,
    raw_summary: dict,
    clr_scores: np.ndarray,
    clr_summary: dict,
    dominant: pd.Series,
    shift: dict,
) -> Figure:
    """PCA of z-scored raw shares (before, as in iteration 1) vs CLR (after), same countries.

    The neighbour-shift numbers (features.neighbour_shift) are printed, not drawn: they
    compare full 8-dimensional distances, which a 2-D PCA projection does not preserve, so
    marking the pair on the projections would mislead.
    """
    fig, (ax_raw, ax_clr) = plt.subplots(1, 2, figsize=(15, 7.2))
    _pca_panel(ax_raw, raw_scores, raw_summary, dominant, "(a) Before: raw shares (%), z-scored")
    _pca_panel(
        ax_clr,
        clr_scores,
        clr_summary,
        dominant,
        f"(b) After: CLR log-ratios (eps = {config.CLR_EPS:g} pp)",
    )
    first, second = shift["pair"]
    fig.text(
        0.5,
        0.075,
        f"Distances between all {shift['n_pairs']:,} country pairs (8 dimensions), raw shares "
        f"in pp vs CLR: Spearman rho = {shift['spearman_rho_distances']:.2f}, so CLR changes "
        "which countries count as neighbours.\n"
        f"Largest change (by rule): {first} and {second}"
        f" are at the {_ordinal(shift['pair_raw_percentile'])} percentile of distance in raw "
        f"shares but the {_ordinal(shift['pair_clr_percentile'])} in CLR.",
        ha="center",
        fontsize=9,
        bbox={"facecolor": "white", "edgecolor": "#BBBBBB", "boxstyle": "round,pad=0.4"},
    )
    handles, labels = ax_raw.get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="lower center",
        ncol=len(labels),
        frameon=False,
        title="Dominant source in 2018 (colour only)",
        bbox_to_anchor=(0.5, -0.01),
    )
    fig.suptitle(
        f"Loop transformation from I1-2: the electricity mix as log-ratios "
        f"({config.SNAPSHOT_YEAR}, the same {shift['n_countries']} countries)",
        fontweight="bold",
        fontsize=13,
    )
    fig.tight_layout(rect=(0, 0.12, 1, 1))
    return fig


# ============================================================================ Phase 4: iter 2
def _tier_handles(small_state_note: bool = True) -> list:
    """Legend handles: one filled marker per income tier (+ the hollow small-state marker)."""
    handles = [
        Line2D([], [], marker="o", linestyle="", markersize=7, color=colour, label=tier)
        for tier, colour in config.TIER_COLORS.items()
    ]
    if small_state_note:
        handles.append(
            Line2D(
                [],
                [],
                marker="o",
                linestyle="",
                markersize=7,
                markerfacecolor="none",
                markeredgecolor="#333333",
                label="hollow = small state (< 1 M people)",
            )
        )
    return handles


# ---------------------------------------------------------------------------- step 102
def decoupling_quadrant(traj: pd.DataFrame, class_counts: pd.Series) -> Figure:
    """Growth of GDP vs energy per person (2001 -> 2017), coloured by income tier.

    Below the 45-degree line GDP grew faster than energy (decoupling); below zero energy use
    per person fell (absolute decoupling). Small states are hollow so they stay visible
    without dominating. Named: the most populous countries and the extremes of decoupling.
    """
    x, y = traj["cagr_gdp_pc"] * 100, traj["cagr_energy_pc"] * 100
    fig, ax = plt.subplots(figsize=(11, 8))
    lim_x = (min(x.min(), 0) - 0.6, x.max() + 0.6)
    lim_y = (y.min() - 0.6, y.max() + 0.6)
    ax.fill_between([0, lim_x[1]], lim_y[0], 0, color="#E8F1F8", zorder=0)
    ax.fill_between([0, lim_x[1]], [0, 0], [0, lim_x[1]], color="#F3F8FC", zorder=0)
    ax.plot(
        [min(lim_x[0], lim_y[0]), max(lim_x[1], lim_y[1])],
        [min(lim_x[0], lim_y[0]), max(lim_x[1], lim_y[1])],
        color="black",
        linestyle="--",
        linewidth=1,
        label="45-degree line (equal growth)",
    )
    ax.axhline(0, color="#777777", linewidth=0.8)
    ax.axvline(0, color="#777777", linewidth=0.8)
    for tier, colour in config.TIER_COLORS.items():
        for small in (False, True):
            m = (traj["income_tier"] == tier) & (traj["small_state"] == small)
            ax.scatter(
                x[m],
                y[m],
                s=40,
                linewidth=1.1,
                zorder=3,
                facecolor="none" if small else colour,
                edgecolor=colour if small else "white",
            )
    populous = traj.nlargest(config.N_QUADRANT_POPULOUS, "population_2018").index
    extremes = (
        traj["decoupling"]
        .nlargest(config.N_QUADRANT_EXTREMES)
        .index.union(traj["decoupling"].nsmallest(config.N_QUADRANT_EXTREMES).index)
    )
    named = populous.union(extremes)
    ax.set_xlim(lim_x)  # limits first: label_points places labels in the final view
    ax.set_ylim(lim_y)
    plots.label_points(
        ax, x[named].tolist(), y[named].tolist(), traj.loc[named, "country"].tolist(), offset=0.1
    )
    absolute, relative, coupled, gdp_fell = config.DECOUPLING_CLASSES
    # (x, y, ha, va, class, line break after the first word?) in axes fractions; the
    # relative-decoupling note sits inside the wedge, clear of the labelled countries
    notes = [
        (0.98, 0.03, "right", "bottom", absolute, False),
        (0.97, 0.62, "right", "center", relative, True),
        (0.45, 0.97, "center", "top", coupled, False),
        (0.02, 0.97, "left", "top", gdp_fell, False),
    ]
    for nx, ny, ha, va, name, wrap in notes:
        shown = name.replace(" ", "\n", 1) if wrap else name
        ax.text(
            nx,
            ny,
            f"{shown}: {int(class_counts.get(name, 0))} countries",
            transform=ax.transAxes,
            ha=ha,
            va=va,
            fontsize=9.5,
            style="italic",
            color="#333333",
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.8, "pad": 1.5},
        )
    ax.set_xlabel("Growth of GDP per person, 2000-02 to 2016-18 (% per year)")
    ax.set_ylabel("Growth of energy use per person, same period (% per year)")
    handles = _tier_handles() + ax.get_legend_handles_labels()[0]
    ax.legend(
        handles=handles,
        loc="upper left",
        bbox_to_anchor=(0.0, 0.92),
        fontsize=9,
        title="Income tier (2000-02 GDP quartile)",
    )
    ax.set_title(
        f"Iteration 2: is energy use decoupling from GDP? ({len(traj)} countries; shaded = "
        "GDP grew faster than energy)",
        fontweight="bold",
    )
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------- step 104
def loglog_gdp_energy(
    rows: pd.DataFrame, summary: dict, band: pd.DataFrame, n_label: int = config.N_OLS_NAMED
) -> Figure:
    """Energy vs GDP per person on log-log axes with the OLS line, HC3 95% band and slope.

    The slope of log(energy) on log(GDP) is the income elasticity of energy: +1% GDP per
    person goes with +slope% energy per person across countries (an association, not a
    causal effect). The largest residuals are named to show who still stands out.
    """
    fig, ax = plt.subplots(figsize=(10.5, 7))
    ax.scatter(
        rows["gdp_pc"],
        rows["energy_per_capita"],
        s=26,
        color=config.OKABE_ITO[3],
        alpha=0.6,
        edgecolor="white",
        linewidth=0.4,
        label="Country (2018)",
    )
    ax.plot(
        np.exp(band["x"]),
        np.exp(band["fit"]),
        color="black",
        linewidth=1.6,
        label="OLS fit on logs",
    )
    ax.fill_between(
        np.exp(band["x"]),
        np.exp(band["low"]),
        np.exp(band["high"]),
        color="black",
        alpha=0.15,
        label="95% confidence band (HC3)",
    )
    ax.set_xscale("log")
    ax.set_yscale("log")
    worst = rows.nlargest(n_label, "abs_residual")
    plots.label_points(
        ax, worst["gdp_pc"].tolist(), worst["energy_per_capita"].tolist(), worst["country"].tolist()
    )
    ax.text(
        0.03,
        0.97,
        f"n = {summary['n']}\nelasticity = {summary['slope']:.2f} "
        f"(95% CI {summary['slope_ci95_low']:.2f}-{summary['slope_ci95_high']:.2f}, HC3)\n"
        f"R² = {summary['r_squared']:.2f}\n"
        f"Breusch-Pagan p {logbook.format_p(summary['breusch_pagan_p'])}",
        transform=ax.transAxes,
        va="top",
        fontsize=9.5,
        bbox={"facecolor": "white", "edgecolor": "#BBBBBB", "boxstyle": "round,pad=0.3"},
    )
    ax.legend(loc="lower right")
    ax.set_xlabel("GDP per person (international-$, PPP; log scale)")
    ax.set_ylabel("Primary energy per person (kWh; log scale)")
    ax.set_title(
        f"Iteration 2: energy vs GDP per person on log scales ({config.SNAPSHOT_YEAR}); "
        f"{n_label} largest residuals named",
        fontweight="bold",
    )
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------- step 107
def decoupling_by_tier(traj: pd.DataFrame, kw: dict, pairwise: pd.DataFrame) -> Figure:
    """Box + strip plot of decoupling per income tier, with n, the Kruskal-Wallis p and the
    pairs that differ after Holm correction."""
    tiers = config.INCOME_TIER_LABELS
    fig, ax = plt.subplots(figsize=(10.5, 6.8))
    rng = np.random.default_rng(config.SEED)
    for i, tier in enumerate(tiers):
        rows = traj[traj["income_tier"] == tier]
        values = rows["decoupling"] * 100
        ax.boxplot(
            values,
            positions=[i],
            widths=0.55,
            showfliers=False,
            medianprops={"color": "black", "linewidth": 1.6},
            boxprops={"color": "#555555"},
            whiskerprops={"color": "#555555"},
            capprops={"color": "#555555"},
        )
        jitter = rng.uniform(-0.18, 0.18, len(values))
        small = rows["small_state"].to_numpy()
        colour = config.TIER_COLORS[tier]
        ax.scatter(
            i + jitter[~small],
            values[~small],
            s=22,
            color=colour,
            alpha=0.75,
            edgecolor="white",
            linewidth=0.4,
            zorder=3,
        )
        ax.scatter(
            i + jitter[small],
            values[small],
            s=22,
            facecolor="none",
            edgecolor=colour,
            linewidth=1.0,
            zorder=3,
        )
    ax.axhline(0, color="#777777", linewidth=0.8)
    ax.set_xticks(range(len(tiers)))
    counts = traj["income_tier"].value_counts()
    ax.set_xticklabels([f"{t}\n(n = {counts.get(t, 0)})" for t in tiers])
    sig = pairwise[pairwise["significant_holm"]]
    sig_text = (
        "; ".join(
            f"{r.group_a} vs {r.group_b} (Holm p {logbook.format_p(r.p_holm)})"
            for r in sig.itertuples()
        )
        or "none"
    )
    ax.set_xlabel("Income tier (quartile of 2000-02 GDP per person)")
    ax.set_ylabel("Decoupling: GDP growth minus energy growth (pp per year)")
    fig.suptitle(
        f"Decoupling by income tier (Kruskal-Wallis p {logbook.format_p(kw['kruskal_p'])}); "
        "> 0 = GDP grew faster than energy use; hollow = small state",
        fontweight="bold",
        fontsize=12,
    )
    ax.set_title(f"Pairs that differ (Mann-Whitney, Holm-corrected): {sig_text}", fontsize=9)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------- step 109
def slope_lowcarbon_by_income(tier_table: pd.DataFrame) -> Figure:
    """Slope chart of the median low-carbon share per income tier, start vs end window,
    with the interquartile range at each end and the median of the per-country changes."""
    base_label = f"{config.BASE_YEARS[0]}-{config.BASE_YEARS[1] % 100:02d}"
    end_label = f"{config.END_YEARS_DESCRIPTIVE[0]}-{config.END_YEARS_DESCRIPTIVE[1] % 100:02d}"
    fig, ax = plt.subplots(figsize=(10.5, 7))
    offsets = np.linspace(-0.06, 0.06, len(tier_table))
    for off, row in zip(offsets, tier_table.itertuples(), strict=True):
        colour = config.TIER_COLORS[row.tier]
        ax.plot(
            [0 + off, 1 + off],
            [row.median_start, row.median_end],
            color=colour,
            linewidth=2.4,
            marker="o",
            markersize=7,
        )
        for xpos, q1, q3 in (
            (0 + off, row.q1_start, row.q3_start),
            (1 + off, row.q1_end, row.q3_end),
        ):
            ax.plot([xpos, xpos], [q1, q3], color=colour, linewidth=1, alpha=0.5)
    order = tier_table.sort_values("median_end")  # spread_positions expects sorted input
    targets = plots.spread_positions(order["median_end"].tolist(), 4.0, 0, 100)
    for row, ty in zip(order.itertuples(), targets, strict=True):
        ax.annotate(
            f"{row.tier} (n = {row.n}): {row.median_start:.0f}% -> {row.median_end:.0f}%; "
            f"median change {row.median_change:+.1f} pp",
            xy=(1.07, row.median_end),
            xytext=(1.12, ty),
            va="center",
            fontsize=9.5,
            color=config.TIER_COLORS[row.tier],
            arrowprops={
                "arrowstyle": "-",
                "color": "#999999",
                "linewidth": 0.6,
                "relpos": (0, 0.5),  # leader meets the start of the text
            },
        )
    ax.text(
        0.52,
        0.04,
        "median change = median of each country's own change,\nso it need not equal the "
        "difference of the two tier medians",
        transform=ax.transAxes,
        fontsize=8.5,
        color="#444444",
    )
    ax.set_xlim(-0.3, 2.6)
    ax.set_ylim(0, 100)
    ax.set_xticks([0, 1])
    ax.set_xticklabels([base_label, end_label])
    ax.set_xlabel("3-year window (mean of the three years)")
    ax.set_ylabel("Low-carbon share of electricity, tier median (%)")
    ax.set_title(
        "Low-carbon share by income tier: tier medians at both ends (bars = middle 50% of "
        "countries)",
        fontweight="bold",
    )
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return fig
