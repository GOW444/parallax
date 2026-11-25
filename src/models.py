"""Models used in the workflow: OLS regression, K-means, PCA and Random Forest.

Every model function returns plain numbers in a dict, so the results can be saved to
results/ and quoted in the report without re-fitting.
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.metrics import (
    adjusted_rand_score,
    mean_absolute_error,
    r2_score,
    root_mean_squared_error,
    silhouette_samples,
    silhouette_score,
)
from sklearn.model_selection import KFold
from sklearn.preprocessing import StandardScaler
from statsmodels.stats.diagnostic import het_breuschpagan

from src import config, features


# ---------------------------------------------------------------------------- step 47
def _ols_fit(data: pd.DataFrame, y_col: str, x_col: str, cov_type: str):
    """statsmodels OLS of y ~ x on complete rows: returns (fit, rows used, design matrix)."""
    rows = data[[y_col, x_col] + (["country"] if "country" in data else [])].dropna()
    design = sm.add_constant(rows[x_col])
    return sm.OLS(rows[y_col], design).fit(cov_type=cov_type), rows, design


def fit_ols(
    data: pd.DataFrame, y_col: str, x_col: str, cov_type: str = "nonrobust"
) -> tuple[dict, pd.DataFrame]:
    """Simple OLS y ~ x with a Breusch-Pagan test for heteroscedasticity.

    Breusch-Pagan asks whether the spread of the residuals grows with x. If it does
    (small p), the usual standard errors and confidence intervals are unreliable, which is
    a sign the scale of the data is wrong for a linear model. cov_type="HC3" gives
    heteroscedasticity-robust standard errors (MacKinnon & White 1985).

    Returns (summary dict, per-row frame with fitted values and residuals).
    """
    fit, rows, design = _ols_fit(data, y_col, x_col, cov_type)
    lm_stat, lm_p, _, _ = het_breuschpagan(fit.resid, design)
    low, high = fit.conf_int().loc[x_col]
    summary = {
        "n": int(fit.nobs),
        "y": y_col,
        "x": x_col,
        "cov_type": cov_type,
        "intercept": float(fit.params["const"]),
        "slope": float(fit.params[x_col]),
        "slope_ci95_low": float(low),
        "slope_ci95_high": float(high),
        "slope_p": float(fit.pvalues[x_col]),
        "r_squared": float(fit.rsquared),
        "breusch_pagan_lm": float(lm_stat),
        "breusch_pagan_p": float(lm_p),
    }
    per_row = rows.assign(fitted=fit.fittedvalues, residual=fit.resid)
    per_row["abs_residual"] = np.abs(per_row["residual"])
    return summary, per_row


def ols_band(
    data: pd.DataFrame, y_col: str, x_col: str, cov_type: str = "HC3", n_grid: int = 100
) -> pd.DataFrame:
    """Fitted line and 95% confidence band of the mean over the observed x range.

    Uses the same covariance type as the reported slope, so the band in the figure matches
    the confidence interval in the results file.
    """
    fit, rows, _ = _ols_fit(data, y_col, x_col, cov_type)
    grid = np.linspace(rows[x_col].min(), rows[x_col].max(), n_grid)
    frame = fit.get_prediction(sm.add_constant(pd.Series(grid, name=x_col))).summary_frame(
        alpha=config.ALPHA
    )
    return pd.DataFrame(
        {
            "x": grid,
            "fit": frame["mean"],
            "low": frame["mean_ci_lower"],
            "high": frame["mean_ci_upper"],
        }
    )


# ---------------------------------------------------------------------------- steps 51-56
def standardise(frame: pd.DataFrame, cols: list[str]) -> tuple[np.ndarray, StandardScaler]:
    """z-scores of `cols` (mean 0, sd 1), plus the fitted scaler for back-transforms.

    Why: K-means uses Euclidean distance, so without scaling, energy per person (thousands
    of kWh) would outweigh every share (0-100). The scaler is fitted on exactly the rows
    being clustered and nothing else.
    """
    scaler = StandardScaler().fit(frame[cols])
    return scaler.transform(frame[cols]), scaler


def kmeans_scan(z: np.ndarray, k_values: range) -> pd.DataFrame:
    """Inertia, mean silhouette and smallest cluster size of K-means for each k."""
    rows = []
    for k in k_values:
        fit = KMeans(n_clusters=k, n_init=config.KMEANS_N_INIT, random_state=config.SEED).fit(z)
        sizes = np.bincount(fit.labels_)
        rows.append(
            {
                "k": k,
                "inertia": float(fit.inertia_),
                "silhouette": float(silhouette_score(z, fit.labels_)),
                "min_cluster_size": int(sizes.min()),
            }
        )
    return pd.DataFrame(rows)


def choose_k(scan: pd.DataFrame, min_size: int = config.MIN_CLUSTER_SIZE) -> int:
    """Apply config.K_RULE: highest silhouette among k whose clusters all have >= min_size.

    The rule is fixed in config before fitting, so k is not picked by eye from the plot.
    The scan is sorted by k and idxmax returns the first maximum, so ties go to smaller k.
    """
    eligible = scan[scan["min_cluster_size"] >= min_size].sort_values("k")
    if eligible.empty:
        raise ValueError(f"no k gives clusters of at least {min_size} countries")
    return int(eligible.loc[eligible["silhouette"].idxmax(), "k"])


def fit_kmeans(z: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
    """K-means with clusters renumbered by size: 1 = largest (ties: lower original label).

    Returns (labels 1..k, centres in z-units ordered like the labels). Numbering by size
    makes the cluster names reproducible across runs and readable in the report.
    """
    fit = KMeans(n_clusters=k, n_init=config.KMEANS_N_INIT, random_state=config.SEED).fit(z)
    sizes = np.bincount(fit.labels_, minlength=k)
    order = sorted(range(k), key=lambda old: (-sizes[old], old))
    new_label = {old: new + 1 for new, old in enumerate(order)}
    labels = np.array([new_label[old] for old in fit.labels_])
    return labels, fit.cluster_centers_[order]


def silhouette_band(score: float) -> str:
    """Kaufman & Rousseeuw (1990) wording for a mean silhouette (config.SILHOUETTE_BANDS)."""
    for upper, words in config.SILHOUETTE_BANDS:
        if score <= upper:
            return words
    return config.SILHOUETTE_BANDS[-1][1]


def describe_centres(centres_z: np.ndarray, cols: list[str]) -> list[str]:
    """Name each cluster after its most extreme standardised centre value, e.g. 'high Oil share'.

    The name is computed from the centroid, never typed by hand, so it always matches the
    data. 'high'/'low' says on which side of the all-country average the centre lies.
    """
    names = []
    for centre in centres_z:
        j = int(np.argmax(np.abs(centre)))
        side = "high" if centre[j] > 0 else "low"
        names.append(f"{side} {config.FEATURE_SHORT[cols[j]]}")
    return names


def pca_2d(z: np.ndarray, cols: list[str]) -> tuple[np.ndarray, dict]:
    """2-component PCA of standardised data: scores and a JSON-ready summary.

    'loading' = Pearson correlation of each feature with the component scores, so arrows
    can be read on a unit circle (computed directly, because the weight x sqrt(eigenvalue)
    shortcut mixes sklearn's n-1 variance with StandardScaler's n and overshoots 1).
    'weight' is the raw component vector, which is used to rank the drivers of each PC.
    """
    pca = PCA(n_components=2, random_state=config.SEED).fit(z)
    scores = pca.transform(z)
    loadings = np.array(
        [[np.corrcoef(z[:, i], scores[:, k])[0, 1] for k in (0, 1)] for i in range(len(cols))]
    )
    summary = {
        "n": int(z.shape[0]),
        "explained_variance_ratio": [float(v) for v in pca.explained_variance_ratio_],
        "cumulative_explained": float(pca.explained_variance_ratio_.sum()),
        "weights": {
            col: {"PC1": float(pca.components_[0, i]), "PC2": float(pca.components_[1, i])}
            for i, col in enumerate(cols)
        },
        "loadings": {
            col: {"PC1": float(loadings[i, 0]), "PC2": float(loadings[i, 1])}
            for i, col in enumerate(cols)
        },
    }
    for pc in ("PC1", "PC2"):
        ranked = sorted(cols, key=lambda c: -abs(summary["weights"][c][pc]))
        summary[f"{pc}_top3"] = ranked[:3]
    return scores, summary


def mean_silhouette(z: np.ndarray, labels: np.ndarray) -> float:
    """Mean silhouette of a given labelling (used to score the same labels on a subset)."""
    return float(silhouette_score(z, labels))


def silhouette_per_row(z: np.ndarray, labels: np.ndarray) -> np.ndarray:
    """Silhouette of each row: near 1 = well inside its cluster, < 0 = closer to another."""
    return silhouette_samples(z, labels)


def agreement(labels_a, labels_b) -> float:
    """Adjusted Rand index: 1 = identical groupings, ~0 = no more agreement than chance."""
    return float(adjusted_rand_score(labels_a, labels_b))


# ---------------------------------------------------------------------------- step 84
def clr_eps_sensitivity(
    shares: pd.DataFrame,
    eps_grid: tuple[float, ...] = config.CLR_EPS_GRID,
    k_values: range = config.K_RANGE_ITER1,
) -> pd.DataFrame:
    """How much the K-means result on CLR shares depends on the zero-replacement eps.

    For each eps: CLR (no z-scoring: Euclidean distance on CLR is the Aitchison distance,
    and rescaling columns would break it), k chosen by config.K_RULE, its silhouette and
    smallest cluster. Then, at the k chosen for the default eps, the silhouette and the
    agreement (ARI) with the default labels, so the effect of eps is not confused with a
    change of k.
    """
    spaces = {eps: features.clr(shares, eps).to_numpy() for eps in eps_grid}
    rows = []
    for eps, z in spaces.items():
        scan = kmeans_scan(z, k_values)
        k = choose_k(scan)
        chosen = scan.set_index("k").loc[k]
        rows.append(
            {
                "eps": eps,
                "k_chosen": k,
                "silhouette_at_k_chosen": float(chosen["silhouette"]),
                "min_cluster_size": int(chosen["min_cluster_size"]),
            }
        )
    table = pd.DataFrame(rows)
    k_ref = int(table.loc[table["eps"] == config.CLR_EPS, "k_chosen"].iloc[0])
    ref_labels, _ = fit_kmeans(spaces[config.CLR_EPS], k_ref)
    at_ref = {eps: fit_kmeans(z, k_ref)[0] for eps, z in spaces.items()}
    table["k_ref"] = k_ref
    table["silhouette_at_k_ref"] = [mean_silhouette(spaces[e], at_ref[e]) for e in table["eps"]]
    table["ari_vs_default_eps"] = [agreement(ref_labels, at_ref[e]) for e in table["eps"]]
    return table


# ---------------------------------------------------------------------------- step 62
def assert_no_leakage(cols: list[str], banned: list[str] = config.LEAKAGE_BANNED) -> None:
    """Raise if any feature name contains a banned fragment (see config.LEAKAGE_BANNED).

    Why: carbon intensity is calculated from the electricity mix and the power-sector
    emissions. A model fed any of these would "predict" the target from its own
    ingredients and look far better than it is. Checking names before every fit makes the
    rule impossible to break by accident.
    """
    leaks = [col for col in cols if any(fragment in col for fragment in banned)]
    if leaks:
        raise ValueError(f"leakage: these features are derived from the target: {leaks}")


# ---------------------------------------------------------------------------- step 63
def make_folds(countries: list[str], n_folds: int = config.N_FOLDS) -> pd.DataFrame:
    """Shuffled K-fold assignment (seed 42), one row per country: country, fold (1..k).

    Saved to disk so the iteration 2 model is scored on exactly the same splits, which
    makes the before/after comparison fair. A random split is right here because the rows
    are countries in one year, not a time series.
    """
    countries = sorted(countries)
    folds = np.zeros(len(countries), dtype=int)
    splitter = KFold(n_splits=n_folds, shuffle=True, random_state=config.SEED)
    for fold, (_, test_idx) in enumerate(splitter.split(countries), start=1):
        folds[test_idx] = fold
    return pd.DataFrame({"country": countries, "fold": folds})


# ---------------------------------------------------------------------------- step 64
def _scores(y_true, y_pred) -> dict:
    return {
        "r2": float(r2_score(y_true, y_pred)),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(root_mean_squared_error(y_true, y_pred)),
    }


def _fold_fits(data: pd.DataFrame, feature_cols: list[str], target: str, folds: pd.DataFrame):
    """Yield (fold, fitted forest, train rows, test rows) for each saved fold."""
    assert_no_leakage(feature_cols)
    data = data.merge(folds, on="country", how="inner", validate="one_to_one")
    for fold in sorted(data["fold"].unique()):
        train, test = data[data["fold"] != fold], data[data["fold"] == fold]
        forest = RandomForestRegressor(
            n_estimators=config.RF_N_ESTIMATORS, random_state=config.SEED, n_jobs=-1
        ).fit(train[feature_cols], train[target])
        yield fold, forest, train, test


def cross_validate_rf(
    data: pd.DataFrame, feature_cols: list[str], target: str, folds: pd.DataFrame
) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    """Cross-validated Random Forest with a mean-predictor baseline and permutation importance.

    Returns
    - metrics: R2, MAE and RMSE per fold, their mean and sd, the pooled out-of-fold scores,
      and the same for the baseline (predict the training-fold mean). A model is only
      useful if it beats that baseline.
    - oof: one row per country with its out-of-fold prediction and residual (actual - pred).
    - importance: permutation importance on each HELD-OUT fold (rise in MAE, gCO2/kWh, when
      one feature is shuffled; config.PERMUTATION_REPEATS shuffles per fold). Held-out data
      shows what the model needs in order to generalise, not what it memorised.
    """
    fold_rows, oof_parts, importance_rows = [], [], []
    for fold, forest, train, test in _fold_fits(data, feature_cols, target, folds):
        pred = forest.predict(test[feature_cols])
        baseline = np.full(len(test), train[target].mean())
        row = {"fold": int(fold), "n_test": len(test), **_scores(test[target], pred)}
        row.update({f"baseline_{k}": v for k, v in _scores(test[target], baseline).items()})
        fold_rows.append(row)
        oof_parts.append(
            test[["country", target]].assign(fold=fold, predicted=pred, baseline=baseline)
        )
        result = permutation_importance(
            forest,
            test[feature_cols],
            test[target],
            scoring="neg_mean_absolute_error",
            n_repeats=config.PERMUTATION_REPEATS,
            random_state=config.SEED,
        )
        for i, col in enumerate(feature_cols):
            for value in result.importances[i]:
                importance_rows.append({"fold": int(fold), "feature": col, "mae_increase": value})

    per_fold = pd.DataFrame(fold_rows)
    oof = pd.concat(oof_parts).sort_values("country").reset_index(drop=True)
    oof["residual"] = oof[target] - oof["predicted"]
    oof["abs_residual"] = oof["residual"].abs()
    metrics = {
        "n": len(oof),
        "n_folds": len(per_fold),
        "target": target,
        "features": feature_cols,
        "per_fold": per_fold.to_dict(orient="records"),
    }
    for name in ("r2", "mae", "rmse", "baseline_r2", "baseline_mae", "baseline_rmse"):
        metrics[f"{name}_mean"] = float(per_fold[name].mean())
        metrics[f"{name}_sd"] = float(per_fold[name].std(ddof=1))
    metrics["pooled_oof"] = _scores(oof[target], oof["predicted"])
    metrics["pooled_oof_baseline"] = _scores(oof[target], oof["baseline"])

    importance = (
        pd.DataFrame(importance_rows)
        .groupby("feature")["mae_increase"]
        .agg(mean="mean", sd="std", min="min", max="max")
        .reset_index()
        .sort_values("mean", ascending=False, ignore_index=True)
    )
    return metrics, oof, importance
