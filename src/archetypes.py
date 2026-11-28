"""Iteration 2 archetype clustering: K-means vs diagonal GMM on trajectory + CLR features.

Why: iteration 1 clustered one year of raw shares. Here each country is described by its
path (growth, decoupling, change in the mix) plus the log-ratio mix, so a cluster is a
*kind of transition*, not a dominant source.
"""

import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.mixture import GaussianMixture

from src import config, models


def gmm_scan(z: np.ndarray, k_values: range) -> pd.DataFrame:
    """BIC, silhouette and smallest cluster size of a diagonal-covariance GMM per k."""
    rows = []
    for k in k_values:
        gmm = GaussianMixture(
            n_components=k,
            covariance_type="diag",
            n_init=config.GMM_N_INIT,
            random_state=config.SEED,
        ).fit(z)
        labels = gmm.predict(z)
        rows.append(
            {
                "k": k,
                "bic": float(gmm.bic(z)),
                "silhouette": (
                    float(silhouette_score(z, labels)) if len(set(labels)) > 1 else np.nan
                ),
                "min_cluster_size": int(np.bincount(labels, minlength=k).min()),
            }
        )
    return pd.DataFrame(rows)


def choose_method_and_k(km_scan: pd.DataFrame, gmm: pd.DataFrame) -> tuple[str, int]:
    """Apply config.ARCHETYPE_METHOD_RULE and return ("kmeans" | "gmm", k)."""
    km_k = models.choose_k(km_scan)
    km_sil = float(km_scan.loc[km_scan["k"] == km_k, "silhouette"].iloc[0])
    best_bic_k = int(gmm.loc[gmm["bic"].idxmin(), "k"])
    row = gmm[gmm["k"] == best_bic_k].iloc[0]
    if row["min_cluster_size"] >= config.MIN_CLUSTER_SIZE and row["silhouette"] > km_sil:
        return "gmm", best_bic_k
    return "kmeans", km_k


def assign_nearest(z_new: np.ndarray, centres_z: np.ndarray) -> np.ndarray:
    """Label 1..k of the nearest centroid (Euclidean), for small states left out of the fit."""
    dist = np.linalg.norm(z_new[:, None, :] - centres_z[None, :, :], axis=2)
    return dist.argmin(axis=1) + 1


def stability(z: np.ndarray, k: int, reference: np.ndarray, n_seeds: int) -> dict:
    """Adjusted Rand index of K-means refits (different seeds) against the reference labels."""
    from sklearn.cluster import KMeans

    scores = []
    for seed in range(n_seeds):
        fit = KMeans(n_clusters=k, n_init=config.KMEANS_N_INIT, random_state=seed).fit(z)
        scores.append(adjusted_rand_score(reference, fit.labels_))
    return {
        "k": k,
        "n_seeds": n_seeds,
        "ari_mean": float(np.mean(scores)),
        "ari_min": float(np.min(scores)),
        "ari_max": float(np.max(scores)),
    }


def name_archetypes(centres_z: np.ndarray, cols: list[str]) -> list[str]:
    """Name = the two standardised features with the largest |centre|, signed (documented rule)."""
    names = []
    for centre in centres_z:
        top = np.argsort(-np.abs(centre))[:2]
        parts = [
            f"{'high' if centre[i] > 0 else 'low'} {config.ARCHETYPE_LABELS.get(cols[i], cols[i])}"
            for i in top
        ]
        names.append(" + ".join(parts))
    return names


def short_name(centre_z: np.ndarray, cols: list[str], trend: str) -> str:
    """Readable archetype name: '<largest CLR source> grids, <trend>'.

    Rule (documented, not hand-picked): the CLR feature with the largest positive centroid
    gives the source; the Hamed-Rao Mann-Kendall trend of the archetype's median low-carbon
    share gives the direction (rising / falling / flat).
    """
    clr_idx = [i for i, c in enumerate(cols) if c.startswith("clr_")]
    best = max(clr_idx, key=lambda i: centre_z[i])
    source = cols[best].removeprefix("clr_").replace("_", " ")
    direction = {"increasing": "rising", "decreasing": "falling"}.get(trend, "flat")
    return f"{source.capitalize()} grids, low-carbon share {direction}"
