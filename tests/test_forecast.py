"""Forecast guards: time-based split only (train <= 2018, test exactly 2019-2021)."""

import numpy as np
import pandas as pd
import pytest

from src import forecast


def _series(last_year=2021):
    years = range(2000, last_year + 1)
    return pd.Series(np.linspace(10, 30, len(years)), index=years)


def test_split_is_time_based():
    train, test = forecast.split_train_test(_series())
    assert train.index.max() == 2018
    assert list(test.index) == [2019, 2020, 2021]


def test_split_rejects_short_training_data():
    with pytest.raises(ValueError):
        forecast.split_train_test(_series()[lambda s: s.index != 2018])


def test_split_rejects_missing_test_year():
    with pytest.raises(ValueError):
        forecast.split_train_test(_series(last_year=2020))


def test_naive_repeats_last_training_value():
    pred, half = forecast.forecast_one(_series().loc[:2018], "naive", 3)
    assert half is None
    assert np.allclose(pred, _series().loc[2018])


def test_holt_follows_a_straight_line():
    s = _series()
    pred, _ = forecast.forecast_one(s.loc[:2018], "holt", 3)
    assert np.allclose(pred, s.loc[2019:].to_numpy(), atol=0.05)
