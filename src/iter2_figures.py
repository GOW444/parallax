"""Figures for iteration 2: archetypes, fossil producers, RF v2 and the forecast."""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.figure import Figure

from src import config

KM_COLOR, GMM_COLOR = "#0072B2", "#D55E00"


def k_selection(km: pd.DataFrame, gmm: pd.DataFrame, chosen_k: int, method: str) -> Figure:
    """Four panels: K-means inertia and silhouette, GMM BIC and silhouette, per k."""
    fig, axes = plt.subplots(2, 2, figsize=(11, 7.5), sharex=True)
    panels = [
        (axes[0, 0], km, "inertia", KM_COLOR, "K-means: inertia (elbow)", "Within-cluster SS"),
        (axes[0, 1], km, "silhouette", KM_COLOR, "K-means: mean silhouette", "Silhouette"),
        (axes[1, 0], gmm, "bic", GMM_COLOR, "Diagonal GMM: BIC (lower is better)", "BIC"),
        (axes[1, 1], gmm, "silhouette", GMM_COLOR, "Diagonal GMM: mean silhouette", "Silhouette"),
    ]
    for ax, data, col, colour, title, ylabel in panels:
        ax.plot(data["k"], data[col], marker="o", color=colour)
        ax.set_title(title)
        ax.set_ylabel(ylabel)
        ax.set_xticks(list(data["k"]))
        small = data[data["min_cluster_size"] < config.MIN_CLUSTER_SIZE]
        ax.scatter(
            small["k"],
            small[col],
            s=120,
            facecolor="none",
            edgecolor="black",
            label=f"a cluster has < {config.MIN_CLUSTER_SIZE} countries",
        )
        if (method == "kmeans") == (colour == KM_COLOR):
            ax.axvline(chosen_k, color="#555555", linestyle="--", linewidth=1)
    for ax in axes.ravel():
        ax.set_xlabel("Number of clusters k")
        ax.tick_params(labelbottom=True)
    axes[0, 1].legend(loc="lower right")
    fig.suptitle(
        f"Choosing the archetype model: {method} with k = {chosen_k} (dashed line)",
        fontweight="bold",
    )
    fig.tight_layout()
    return fig


def silhouette_comparison(rows: list[tuple[str, float]]) -> Figure:
    """Horizontal bars of mean silhouette for the same countries in different feature spaces."""
    fig, ax = plt.subplots(figsize=(8.5, 3.6))
    labels = [r[0] for r in rows]
    values = [r[1] for r in rows]
    bars = ax.barh(labels, values, color=["#999999", "#0072B2"][: len(rows)])
    for bar, v in zip(bars, values, strict=True):
        ax.text(v + 0.005, bar.get_y() + bar.get_height() / 2, f"{v:.2f}", va="center")
    for edge, _ in config.SILHOUETTE_BANDS[:2]:
        ax.axvline(edge, color="#BBBBBB", linestyle=":", linewidth=1)
    ax.set_xlim(0, 0.6)
    ax.set_xlabel("Mean silhouette (0.25 = no substantial structure, 0.50 = reasonable)")
    ax.set_ylabel("Clustering input")
    ax.set_title("Same countries, two feature spaces: how well-separated are the clusters?")
    ax.invert_yaxis()
    fig.tight_layout()
    return fig


def archetype_profiles(centroids: pd.DataFrame, names: list[str], sizes: list[int]) -> Figure:
    """Heatmap of standardised centroids (rows = archetype, columns = feature, grouped)."""
    cols = list(centroids.columns)
    fig, ax = plt.subplots(figsize=(13, 4.6))
    limit = float(np.abs(centroids.to_numpy()).max())
    image = ax.imshow(
        centroids.to_numpy(), cmap=config.DIVERGING_CMAP, vmin=-limit, vmax=limit, aspect="auto"
    )
    ax.grid(False)
    ax.set_xticks(
        range(len(cols)), labels=[config.ARCHETYPE_LABELS[c] for c in cols], rotation=40, ha="right"
    )
    ax.set_yticks(range(len(names)), labels=[f"A{i + 1} (n = {s})" for i, s in enumerate(sizes)])
    for i in range(centroids.shape[0]):
        for j in range(centroids.shape[1]):
            ax.text(j, i, f"{centroids.iat[i, j]:.1f}", ha="center", va="center", fontsize=8)
    split = len(config.ARCHETYPE_TRAJECTORY_COLS) - 0.5
    ax.axvline(split, color="black", linewidth=2)
    ax.set_xlabel("Features: left of the black line = trajectory, right = CLR of 2018 mix")
    ax.set_ylabel("Archetype")
    ax.set_title("Archetype profiles: centroid in standard deviations from the all-country mean")
    fig.colorbar(image, ax=ax, label="Standardised centroid (z)", fraction=0.025, pad=0.01)
    fig.tight_layout()
    return fig


def archetype_small_multiples(
    series: pd.DataFrame, names: dict[int, str], colours: list[str]
) -> Figure:
    """Median and IQR of the low-carbon share per archetype per year, shared y axis."""
    ids = sorted(series["archetype"].unique())
    fig, axes = plt.subplots(1, len(ids), figsize=(3.1 * len(ids), 4.2), sharey=True)
    for ax, a, colour in zip(np.atleast_1d(axes), ids, colours, strict=False):
        d = series[series["archetype"] == a]
        ax.fill_between(d["year"], d["q25"], d["q75"], color=colour, alpha=0.25)
        ax.plot(d["year"], d["median"], color=colour, linewidth=2)
        ax.set_title(f"A{a} (n = {int(d['n'].iloc[0])})", fontsize=10)
        ax.set_xlabel("Year")
        ax.set_xticks([2000, 2010, 2020])
        ax.set_ylabel("Low-carbon share (%)")
    fig.suptitle(
        "Low-carbon share by archetype: median line, interquartile band", fontweight="bold"
    )
    fig.tight_layout()
    return fig


def producers_carbon(data: pd.DataFrame, test: dict) -> Figure:
    """Box + strip of 2018 grid carbon intensity, fossil producers vs the rest."""
    fig, ax = plt.subplots(figsize=(7.5, 5.2))
    groups = [("Other countries", False, "#56B4E9"), ("Fossil producers", True, "#D55E00")]
    rng = np.random.default_rng(config.SEED)
    for pos, (_, flag, colour) in enumerate(groups):
        vals = data.loc[data["producer"] == flag, "carbon_intensity_elec"].to_numpy()
        ax.boxplot(
            vals,
            positions=[pos],
            widths=0.5,
            showfliers=False,
            medianprops={"color": "black", "linewidth": 2},
        )
        ax.scatter(
            pos + rng.uniform(-0.18, 0.18, len(vals)),
            vals,
            s=16,
            color=colour,
            edgecolor="#333333",
            linewidth=0.3,
            alpha=0.8,
            zorder=3,
        )
    ax.set_xticks(
        [0, 1],
        labels=[f"{g[0]}\n(n = {(data['producer'] == g[1]).sum()})" for g in groups],
    )
    ax.set_xlabel("Group (producer = mean fossil production >= own energy use, 2000-16)")
    ax.set_ylabel("Carbon intensity of electricity, 2018 (gCO2/kWh)")
    ax.set_title(
        f"Fossil producers vs the rest: medians {test['median_in']:.0f} vs "
        f"{test['median_out']:.0f} gCO2/kWh\nMann-Whitney p = {test['p']:.2g}, "
        f"rank-biserial r = {test['rank_biserial']:.2f}",
        fontsize=11,
    )
    fig.tight_layout()
    return fig


def rf_improvement(per_fold: pd.DataFrame, summary: dict) -> Figure:
    """R² and MAE per model (mean +- fold sd), with the paired fold-by-fold lines."""
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
    models_ = ["baseline", "v1", "v2"]
    labels = ["Mean predictor", "RF v1 (2018 levels)", "RF v2 (+ history, context)"]
    colours = ["#BBBBBB", "#56B4E9", "#0072B2"]
    for ax, metric, ylabel in (
        (axes[0], "r2", "Cross-validated R² (higher is better)"),
        (axes[1], "mae", "Cross-validated MAE, gCO2/kWh (lower is better)"),
    ):
        means = [per_fold[f"{m}_{metric}"].mean() for m in models_]
        sds = [per_fold[f"{m}_{metric}"].std(ddof=1) for m in models_]
        ax.bar(range(3), means, yerr=sds, capsize=5, color=colours, edgecolor="#333333")
        for fold in per_fold.itertuples():
            ax.plot(
                [1, 2],
                [getattr(fold, f"v1_{metric}"), getattr(fold, f"v2_{metric}")],
                color="#555555",
                linewidth=0.8,
                marker="o",
                markersize=3,
                alpha=0.7,
            )
        ax.set_xticks(range(3), labels=labels, fontsize=8.5)
        ax.set_xlabel("Model (grey lines join the same fold)")
        ax.set_ylabel(ylabel)
        ax.axhline(0, color="#999999", linewidth=0.6)
    axes[0].set_title(
        f"R²: v1 {summary['v1_r2_mean']:.2f} -> v2 {summary['v2_r2_mean']:.2f}", fontsize=11
    )
    axes[1].set_title(
        f"MAE: v1 {summary['v1_mae_mean']:.0f} -> v2 {summary['v2_mae_mean']:.0f} gCO2/kWh",
        fontsize=11,
    )
    fig.suptitle(
        f"Random Forest before and after the feedback loop (same {summary['n']} countries, "
        f"same {summary['n_folds']} folds)",
        fontweight="bold",
    )
    fig.tight_layout()
    return fig


def rf_importance_v2(importance: pd.DataFrame, history_cols: list[str]) -> Figure:
    """Held-out permutation importance of RF v2; history/context features highlighted."""
    data = importance.sort_values("mean")
    fig, ax = plt.subplots(figsize=(8.5, 5.6))
    colours = ["#0072B2" if f in history_cols else "#BBBBBB" for f in data["feature"]]
    ax.barh(
        [config.FEATURE_SHORT.get(f, f) for f in data["feature"]],
        data["mean"],
        xerr=data["sd"],
        color=colours,
        edgecolor="#333333",
        capsize=3,
    )
    ax.axvline(0, color="#555555", linewidth=0.8)
    ax.set_xlabel("Rise in held-out MAE when the feature is shuffled (gCO2/kWh, mean +- sd)")
    ax.set_ylabel("Feature (blue = added by the feedback loop)")
    ax.set_title("What RF v2 relies on: permutation importance on held-out folds")
    fig.tight_layout()
    return fig


def forecast_vs_actual(
    series_by_group: dict, forecasts: pd.DataFrame, best: dict, colours: list[str]
) -> Figure:
    """Small multiples per group: 2000-18 training line, 2019-21 forecasts, actual values."""
    from src import forecast as fc

    groups = list(series_by_group)
    fig, axes = plt.subplots(1, len(groups), figsize=(3.3 * len(groups), 4.6), sharey=True)
    styles = {"naive": ":", "holt": "--", "holt_damped": "-.", "arima_110": "-"}
    for ax, group, colour in zip(np.atleast_1d(axes), groups, colours, strict=False):
        series = series_by_group[group]
        train = series[series.index <= config.PRE2019_MAX_YEAR]
        ax.plot(train.index, train.to_numpy(), color=colour, linewidth=2, label="Train 2000-18")
        test = series[series.index > config.PRE2019_MAX_YEAR]
        ax.scatter(
            test.index, test.to_numpy(), color="black", zorder=5, s=22, label="Actual 2019-21"
        )
        for method in fc.METHODS:
            d = forecasts[(forecasts["group"] == group) & (forecasts["method"] == method)]
            ax.plot(
                d["year"],
                d["forecast"],
                color="#555555",
                linestyle=styles[method],
                linewidth=1.3,
                label=fc.METHOD_LABELS[method],
            )
            if method == "arima_110":
                ax.fill_between(
                    d["year"],
                    d["forecast"] - d["pi_half_width"],
                    d["forecast"] + d["pi_half_width"],
                    color="#999999",
                    alpha=0.2,
                )
        ax.axvline(2020, color="#D55E00", linewidth=0.8, linestyle=":")
        ax.axvspan(config.PRE2019_MAX_YEAR + 0.5, 2021.5, color="#F2F2F2", zorder=0)
        ax.set_title(f"{group}\nbest: {fc.METHOD_LABELS[best[group]]}", fontsize=9.5)
        ax.set_xlabel("Year")
        ax.set_ylabel("Median low-carbon share (%)")
        ax.set_xticks([2000, 2010, 2020])
    np.atleast_1d(axes)[0].legend(loc="upper left", fontsize=7.5)
    fig.suptitle(
        "Forecast vs reality: trained on 2000-2018, tested on 2019-2021 (grey band = ARIMA 95% "
        "interval, orange line = 2020)",
        fontweight="bold",
    )
    fig.tight_layout()
    return fig
