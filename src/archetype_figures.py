"""Figures for the iteration 2 archetype clustering (k selection, profiles, time series)."""

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
        ax.scatter(small["k"], small[col], s=120, facecolor="none", edgecolor="black",
                   label=f"a cluster has < {config.MIN_CLUSTER_SIZE} countries")
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
    image = ax.imshow(centroids.to_numpy(), cmap=config.DIVERGING_CMAP, vmin=-limit, vmax=limit,
                      aspect="auto")
    ax.grid(False)
    ax.set_xticks(range(len(cols)), labels=[config.ARCHETYPE_LABELS[c] for c in cols],
                  rotation=40, ha="right")
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


def archetype_small_multiples(series: pd.DataFrame, names: dict[int, str], colours: list[str]
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
    fig.suptitle("Low-carbon share by archetype: median line, interquartile band",
                 fontweight="bold")
    fig.tight_layout()
    return fig
