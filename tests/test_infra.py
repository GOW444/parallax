"""Tests for the shared infrastructure: config, figure saving and the results logbook."""

import json

import matplotlib

matplotlib.use("Agg")  # headless backend for tests

import matplotlib.pyplot as plt
import pandas as pd
import pytest

from src import config, logbook, plots


def _labelled_figure():
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    ax.set_title("Test title")
    ax.set_xlabel("x (unit)")
    ax.set_ylabel("y (unit)")
    return fig


# ---------------------------------------------------------------- config
def test_mix_lists_are_aligned():
    assert len(config.MIX_SHARE_COLS) == 8
    assert len(config.MIX_TWH_COLS) == len(config.SOURCE_NAMES) == 8
    assert set(config.SOURCE_COLORS) == set(config.SOURCE_NAMES)


def test_year_windows_are_consistent():
    assert config.YEAR_START <= config.BASE_YEARS[0] < config.END_YEARS_GDP[1]
    assert config.END_YEARS_GDP[1] == config.GDP_LAST_YEAR == config.FORECAST_TRAIN_END
    # CAGR exponent = distance between endpoint-window centres
    base_mid = sum(config.BASE_YEARS) / 2
    end_mid = sum(config.END_YEARS_GDP) / 2
    assert end_mid - base_mid == config.CAGR_YEARS


# ---------------------------------------------------------------- save_figure
def test_save_figure_writes_png_and_one_registry_row(tmp_path):
    registry = tmp_path / "figures.csv"
    for _ in range(2):  # saving twice must not duplicate the row
        plots.save_figure(
            _labelled_figure(),
            "t.png",
            "test",
            "shows x",
            "why x",
            images_dir=tmp_path,
            registry=registry,
        )
    assert (tmp_path / "t.png").exists()
    table = pd.read_csv(registry)
    assert list(table.columns) == plots.FIGURE_REGISTRY_COLUMNS
    assert len(table) == 1


def test_save_figure_rejects_unlabelled_figure(tmp_path):
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])  # no title, no labels
    with pytest.raises(ValueError, match="no title"):
        plots.save_figure(
            fig, "bad.png", "test", "s", "w", images_dir=tmp_path, registry=tmp_path / "f.csv"
        )
    plt.close(fig)
    assert not (tmp_path / "bad.png").exists()


def test_save_figure_rejects_bad_filename(tmp_path):
    with pytest.raises(ValueError, match="bare .png"):
        plots.save_figure(
            _labelled_figure(),
            "sub/x.png",
            "t",
            "s",
            "w",
            images_dir=tmp_path,
            registry=tmp_path / "f.csv",
        )


def test_source_note_added_once():
    fig = _labelled_figure()
    plots.add_source_note(fig)
    plots.add_source_note(fig)
    notes = [t for t in fig.texts if t.get_text() == config.SOURCE_NOTE]
    assert len(notes) == 1
    plt.close(fig)


# ---------------------------------------------------------------- logbook
def test_save_and_load_metrics_handles_numpy(tmp_path):
    import numpy as np

    logbook.save_metrics(
        "m", {"a": np.float64(1.5), "b": np.int64(3), "c": np.nan}, results_dir=tmp_path
    )
    assert logbook.load_metrics("m", results_dir=tmp_path) == {"a": 1.5, "b": 3, "c": None}


def test_log_inference_upserts_and_sorts(tmp_path):
    j, m = tmp_path / "inf.json", tmp_path / "inf.md"
    logbook.log_inference("I1-10", "s10", "fig.png", False, json_path=j, md_path=m)
    logbook.log_inference("I1-2", "old", "fig.png", False, json_path=j, md_path=m)
    logbook.log_inference("I1-2", "new", "fig.png", True, "log1p", json_path=j, md_path=m)
    entries = json.loads(j.read_text())
    assert list(entries) == ["I1-2", "I1-10"]
    assert entries["I1-2"]["statement"] == "new"
    assert "**Transformation:** log1p" in m.read_text()


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"inference_id": "X1"}, "look like"),
        ({"evidence": "trust me"}, "cite a figure"),
        ({"triggers_loop": True, "transformation": ""}, "needs a transformation"),
    ],
)
def test_log_inference_validates(tmp_path, kwargs, message):
    args = {
        "inference_id": "I1-1",
        "statement": "s",
        "evidence": "f.png",
        "triggers_loop": False,
        "json_path": tmp_path / "a.json",
        "md_path": tmp_path / "a.md",
    }
    args.update(kwargs)
    with pytest.raises(ValueError, match=message):
        logbook.log_inference(**args)


# ---------------------------------------------------------------- plotly maps
def _map_frame():
    return pd.DataFrame({"iso_code": ["IND", "BRA"], "country": ["India", "Brazil"], "v": [1, 2]})


def test_choropleth_has_title_unit_and_source_note():
    fig = plots.choropleth(_map_frame(), "v", "Test map", "Value (unit)", range_color=(0, 2))
    assert "Test map" in fig.layout.title.text
    assert fig.layout.coloraxis.colorbar.title.text == "Value (unit)"
    assert config.SOURCE_NOTE in [a.text for a in fig.layout.annotations]
    assert fig.layout.geo.projection.type == "natural earth"


def test_save_plotly_rejects_missing_source_note(tmp_path):
    fig = plots.choropleth(_map_frame(), "v", "Test map", "Value (unit)")
    fig.layout.annotations = []  # remove the source note
    with pytest.raises(ValueError, match="source note"):
        plots.save_plotly_figure(
            fig, "m.png", "t", "s", "w", images_dir=tmp_path, registry=tmp_path / "f.csv"
        )


def test_save_plotly_writes_200_dpi_png(tmp_path):
    from PIL import Image

    fig = plots.choropleth(_map_frame(), "v", "Test map", "Value (unit)")
    path = plots.save_plotly_figure(
        fig,
        "m.png",
        "t",
        "s",
        "w",
        width=300,
        height=200,
        images_dir=tmp_path,
        registry=tmp_path / "f.csv",
    )
    with Image.open(path) as image:
        assert round(image.info["dpi"][0]) == config.FIG_DPI
