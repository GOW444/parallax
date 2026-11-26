"""Forecast vs reality: fit on 2000-2018, forecast 2019-2021, compare with what happened.

Why a time-based split: a random split would let the model see 2020 while predicting 2019,
which is impossible in real forecasting. `split_train_test` enforces the split and raises if
the training data reaches past 2018 (leakage guard).

Models (per group median series, one value per year):
- naive: repeat the last training value (the baseline every model must beat);
- Holt's linear trend, plain and damped (exponential smoothing with a trend);
- ARIMA(1,1,0): one autoregressive term on the year-to-year changes.
"""

import warnings

import numpy as np
import pandas as pd
from statsmodels.tools.sm_exceptions import ConvergenceWarning
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.holtwinters import Holt

from src import config

METHODS = ["naive", "holt", "holt_damped", "arima_110"]
METHOD_LABELS = {
    "naive": "Naive (last value)",
    "holt": "Holt linear trend",
    "holt_damped": "Holt damped trend",
    "arima_110": "ARIMA(1,1,0)",
}


def split_train_test(series: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Split a year-indexed series into train (<= 2018) and test (2019-2021), with guards."""
    train = series[series.index <= config.PRE2019_MAX_YEAR]
    test = series[series.index.isin(config.FORECAST_TEST_YEARS)]
    if train.index.max() != config.PRE2019_MAX_YEAR:
        raise ValueError(f"training data must end at {config.PRE2019_MAX_YEAR}")
    if list(test.index) != list(config.FORECAST_TEST_YEARS):
        raise ValueError(f"test years must be exactly {list(config.FORECAST_TEST_YEARS)}")
    return train, test


def forecast_one(
    train: pd.Series, method: str, horizon: int
) -> tuple[np.ndarray, np.ndarray | None]:
    """Point forecast and (for ARIMA) a 95% interval half-width, for `horizon` years ahead."""
    y = train.to_numpy(dtype=float)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConvergenceWarning)
        warnings.simplefilter("ignore", UserWarning)
        if method == "naive":
            return np.repeat(y[-1], horizon), None
        if method in ("holt", "holt_damped"):
            fit = Holt(
                y, damped_trend=(method == "holt_damped"), initialization_method="estimated"
            ).fit()
            return fit.forecast(horizon), None
        if method == "arima_110":
            fit = ARIMA(y, order=(1, 1, 0)).fit()
            fc = fit.get_forecast(horizon)
            low, high = fc.conf_int(alpha=0.05).T
            return fc.predicted_mean, (high - low) / 2
    raise ValueError(f"unknown method {method!r}")


def evaluate(series_by_group: dict[str, pd.Series]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Forecast every group with every method; return (forecasts long table, metrics table)."""
    rows, metrics = [], []
    for group, series in series_by_group.items():
        train, test = split_train_test(series)
        for method in METHODS:
            pred, half = forecast_one(train, method, len(test))
            for i, year in enumerate(test.index):
                rows.append(
                    {
                        "group": group,
                        "method": method,
                        "year": int(year),
                        "actual": float(test.iloc[i]),
                        "forecast": float(pred[i]),
                        "pi_half_width": float(half[i]) if half is not None else np.nan,
                    }
                )
            err = test.to_numpy() - pred
            nonzero = test.to_numpy() != 0
            metrics.append(
                {
                    "group": group,
                    "method": method,
                    "mae": float(np.mean(np.abs(err))),
                    "mape": float(np.mean(np.abs(err[nonzero] / test.to_numpy()[nonzero])) * 100)
                    if nonzero.any()
                    else np.nan,
                    "error_2020": float(err[list(test.index).index(2020)]),
                }
            )
    return pd.DataFrame(rows), pd.DataFrame(metrics)
