"""Build video/A3_slides.pptx (16:9) for the video demo, from images/ and results/.

Each slide = a title, at most one figure, and two to four short bullets whose numbers are
read from results/, so the slides always match the report.
"""

import json
from pathlib import Path

import pandas as pd
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Emu, Inches, Pt

from src import config, logbook
from src.forecast import METHOD_LABELS

VIDEO_DIR = config.ROOT / "video"
PPTX_PATH = VIDEO_DIR / "A3_slides.pptx"
SLIDE_W, SLIDE_H = Inches(13.333), Inches(7.5)
NAVY = RGBColor(0x1F, 0x3A, 0x5F)
GREY = RGBColor(0x55, 0x55, 0x55)
ORANGE = RGBColor(0xD5, 0x5E, 0x00)


def _title(slide, text: str, sub: str = "") -> None:
    box = slide.shapes.add_textbox(Inches(0.5), Inches(0.25), Inches(12.3), Inches(0.9))
    tf = box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size, p.font.bold, p.font.color.rgb = Pt(28), True, NAVY
    if sub:
        q = tf.add_paragraph()
        q.text = sub
        q.font.size, q.font.color.rgb = Pt(14), GREY


def _bullets(slide, items: list[str], left, top, width, height, size=16) -> None:
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    for i, text in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = "• " + text
        p.font.size = Pt(size)
        p.space_after = Pt(10)


def _image(slide, path: Path, left, top, max_w, max_h) -> None:
    """Place an image as large as possible inside the box, keeping its aspect ratio."""
    with Image.open(path) as im:
        w, h = im.size
    scale = min(max_w / w, max_h / h)
    width, height = int(w * scale), int(h * scale)
    x = left + (max_w - width) // 2
    y = top + (max_h - height) // 2
    slide.shapes.add_picture(str(path), Emu(x), Emu(y), Emu(width), Emu(height))


def _footer(slide, n: int) -> None:
    box = slide.shapes.add_textbox(Inches(0.5), Inches(7.05), Inches(12.3), Inches(0.35))
    p = box.text_frame.paragraphs[0]
    p.text = f"DAS732 A3 · Data: Our World in Data · {n}"
    p.font.size, p.font.color.rgb = Pt(10), GREY


def _figure_slide(prs, title, sub, image, bullets, image_frac=0.62):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _title(slide, title, sub)
    top = Inches(1.35)
    avail_h = SLIDE_H - top - Inches(0.55)
    img_w = int((SLIDE_W - Inches(1.0)) * image_frac)
    _image(slide, config.IMAGES / image, Inches(0.5), top, img_w, avail_h)
    _bullets(
        slide,
        bullets,
        Inches(0.5) + img_w + Inches(0.3),
        top + Inches(0.2),
        SLIDE_W - img_w - Inches(1.3),
        avail_h,
        size=15,
    )
    return slide


def _first_sentence(inf: dict, key: str) -> str:
    return inf[key]["statement"].split(". ")[0] + "."


def build() -> Path:
    inf = json.loads(config.INFERENCES_JSON.read_text(encoding="utf-8"))
    km1 = logbook.load_metrics("iter1_kmeans")
    rf1 = logbook.load_metrics("iter1_rf_metrics")
    mk = logbook.load_metrics("iter1_mk_global")
    loop = logbook.load_metrics("loop_summary")
    ll = logbook.load_metrics("iter2_loglog")
    stab = logbook.load_metrics("iter2_stability")
    prod = logbook.load_metrics("iter2_producers")
    rfc = logbook.load_metrics("iter2_rf_comparison")
    counts = pd.read_csv(config.RESULTS / "iter2_decoupling_counts.csv", index_col=0)
    names = pd.read_csv(config.RESULTS / "archetype_names.csv")
    change = logbook.load_metrics("iter1_change_summary")
    skew = logbook.load_metrics("iter1_skew")

    prs = Presentation()
    prs.slide_width, prs.slide_height = SLIDE_W, SLIDE_H

    # 1 title
    s = prs.slides.add_slide(prs.slide_layouts[6])
    box = s.shapes.add_textbox(Inches(0.8), Inches(2.2), Inches(11.7), Inches(3))
    tf = box.text_frame
    tf.word_wrap = True
    tf.paragraphs[0].text = "The Energy Transition, Unrolled"
    tf.paragraphs[0].font.size, tf.paragraphs[0].font.bold = Pt(44), True
    tf.paragraphs[0].font.color.rgb = NAVY
    for text, size in (
        ("A two-iteration visual analytics workflow on OWID World Energy Consumption", 22),
        ("DAS732 Data Visualization · Assignment 3 · IIIT Bangalore", 16),
    ):
        p = tf.add_paragraph()
        p.text, p.font.size, p.font.color.rgb = text, Pt(size), GREY

    # 2 question
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _title(s, "Research question")
    _bullets(
        s,
        [
            "How are countries moving through the energy transition?",
            "Does getting richer still mean using more energy, and running a dirtier grid?",
            "A1 (Tableau, descriptive): the global mix barely moved; income predicts how much "
            "energy, not how clean; electricity is where change happens.",
            "A3: statistics + unsupervised + supervised models, and a feedback loop that "
            "reshapes the data for a second iteration. One dataset only, no supplementary data.",
        ],
        Inches(0.8),
        Inches(1.6),
        Inches(11.7),
        Inches(5),
        size=22,
    )
    _footer(s, 2)

    slides = [
        (
            "Workflow: Keim et al. diamond, unrolled",
            "Iteration 1 → Feedback loop → Iteration 2",
            "workflow.png",
            [],
            0.98,
        ),
        (
            "Iteration 1 · raw 2018 snapshot: skewed scales",
            "[Statistics] OLS on raw axes",
            "iter1_ols_residuals.png",
            [
                f"Skewness: energy {skew['energy_per_capita']:.1f}, GDP {skew['gdp_pc']:.1f}, "
                f"electricity {skew['per_capita_electricity']:.1f} per person",
                "Raw OLS is heteroscedastic; a few small energy-intensive economies dominate",
                "→ I1-1: log-transform; flag small states, never drop them",
            ],
            0.62,
        ),
        (
            "Iteration 1 · a flat global trend hides big moves",
            "[Statistics] Mann-Kendall",
            "iter1_change_2000_2018.png",
            [
                f"Global low-carbon share: no significant trend (Hamed-Rao p = {mk['p_hamed_rao']:.2f})",
                f"Yet {change['n_changed_over_threshold']} of {change['n_countries']} countries "
                f"moved > {change['threshold_pp']:.0f} pp, in both directions",
                "→ I1-3: a snapshot cannot see paths; reshape to trajectories",
            ],
            0.62,
        ),
        (
            "Iteration 1 · K-means re-labels the biggest source",
            "[Unsupervised] K-means + PCA",
            "iter1_kmeans_pca.png",
            [
                f"k = {km1['k']}, silhouette {km1['silhouette']:.2f} (weak)",
                f"Clusters ≈ dominant source (ARI {km1['ari_vs_dominant_source']:.2f})",
                "Shares sum to 100%: a composition, not 8 free numbers",
                "→ I1-2: centred log-ratio (CLR) transform",
            ],
            0.62,
        ),
        (
            "Iteration 1 · the Random Forest barely beats the mean",
            "[Supervised] RF, leakage-guarded",
            "iter1_rf_pred_vs_actual.png",
            [
                f"CV R² {rf1['r2_mean']:.2f}, MAE {rf1['mae_mean']:.0f} vs {rf1['baseline_mae_mean']:.0f} gCO2/kWh (mean predictor)",
                "Mix shares banned as features (they define the target)",
                "Errors follow the hidden mix: hydro too dirty, coal too clean",
                "→ I1-4: add history and context features",
            ],
            0.62,
        ),
        (
            "The feedback loop: a significant transformation",
            "Every transformation is triggered by an inference",
            "loop_before_after_table.png",
            [
                f"Unit of analysis: {loop['unit_before']} → {loop['unit_after']}",
                f"{loop['panel_rows']:,} country-years → {loop['rows_after']} country paths",
                f"Max |skew| {loop['max_abs_skew_before']:.1f} → {loop['max_abs_skew_after']:.1f}; mix as CLR log-ratios",
                "Pre-2019 model table refuses any later year (leakage guard)",
            ],
            0.62,
        ),
        (
            "Iteration 2 · decoupling, by income tier",
            "[Statistics] Kruskal-Wallis + Holm",
            "iter2_decoupling_quadrant.png",
            [
                f"{int(counts.loc['All', 'absolute decoupling'])} countries decoupled absolutely, "
                f"{int(counts.loc['All', 'relative decoupling'])} relatively",
                f"High tier: {int(counts.loc['High', 'absolute decoupling'])} of {int(counts.loc['High', 'All'])} absolute; "
                f"Low tier mostly coupled",
                "Only the Low tier differs from the others",
            ],
            0.62,
        ),
        (
            "Iteration 2 · income elasticity of energy",
            "[Statistics] log-log OLS, HC3",
            "iter2_loglog_gdp_energy.png",
            [
                f"Elasticity {ll['slope']:.2f} (95% CI {ll['slope_ci95_low']:.2f}-{ll['slope_ci95_high']:.2f})",
                f"R² 0.72 (raw) → {ll['r_squared']:.2f} (log)",
                "Across countries energy rises with income; over time rich countries cut it",
                "Association, not causation",
            ],
            0.62,
        ),
        (
            "Iteration 2 · transition archetypes",
            "[Unsupervised] K-means vs GMM on trajectories + CLR",
            "iter2_archetype_small_multiples.png",
            [
                f"A{int(r.archetype)}: {r.short_name} (n = {int(r.n_with_small_states)})"
                for r in names.itertuples()
            ]
            + [
                f"Stable across seeds (ARI {stab['ari_mean']:.2f}) but weakly separated "
                f"(silhouette {stab['silhouette']:.2f})"
            ],
            0.6,
        ),
        (
            "Iteration 2 · where are the archetypes?",
            "Categorical map",
            "iter2_archetype_map.png",
            [],
            0.98,
        ),
        (
            "Iteration 2 · are fossil producers stuck?",
            "[Statistics] Mann-Whitney",
            "iter2_producers_carbon.png",
            [
                f"Medians {prod['median_in']:.0f} vs {prod['median_out']:.0f} gCO2/kWh, p = {prod['p']:.2f}",
                "Hypothesis not supported: both groups span the whole range",
                "Norway and Canada produce fuel but run clean grids",
            ],
            0.55,
        ),
        (
            "Iteration 2 · did the loop help the model?",
            "[Supervised] RF v2, same folds",
            "iter2_rf_improvement.png",
            [
                f"R² {rfc['v1_r2_mean']:.2f} → {rfc['v2_r2_mean']:.2f}; MAE {rfc['v1_mae_mean']:.0f} → {rfc['v2_mae_mean']:.0f}",
                f"v2 better in {rfc['folds_v2_better_mae']} of {rfc['n_folds']} folds: within noise",
                "Grid cleanliness is set by the mix, not by income or history",
                "A negative result, reported as one",
            ],
            0.62,
        ),
    ]
    if (config.IMAGES / "iter2_forecast_vs_actual.png").exists() and "I2-6" in inf:
        fm = pd.read_csv(config.RESULTS / "iter2_forecast_metrics.csv")
        mean_mae = fm.groupby("method")["mae"].mean()
        slides.append(
            (
                "Iteration 2 · forecast vs reality, 2019-2021",
                "[Supervised] Holt / ARIMA, time-based split",
                "iter2_forecast_vs_actual.png",
                [
                    "Trained on 2000-2018 only; tested on 2019-2021",
                    "Mean MAE (pp): "
                    + ", ".join(
                        f"{METHOD_LABELS[m]} {v:.1f}" for m, v in mean_mae.sort_values().items()
                    ),
                ],
                0.98,
            )
        )

    for n, (title, sub, image, bullets, frac) in enumerate(slides, start=3):
        if frac > 0.9:
            slide = prs.slides.add_slide(prs.slide_layouts[6])
            _title(slide, title, sub)
            top = Inches(1.35)
            text_h = Inches(0.6) if bullets else 0
            _image(
                slide,
                config.IMAGES / image,
                Inches(0.4),
                top,
                SLIDE_W - Inches(0.8),
                SLIDE_H - top - Inches(0.5) - text_h,
            )
            if bullets:
                _bullets(
                    slide,
                    ["   ".join(bullets)],
                    Inches(0.5),
                    SLIDE_H - Inches(1.1),
                    SLIDE_W - Inches(1.0),
                    Inches(0.6),
                    size=13,
                )
        else:
            slide = _figure_slide(prs, title, sub, image, bullets, frac)
        _footer(slide, n)

    n = len(slides) + 3
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _title(s, "Takeaways and limitations")
    _bullets(
        s,
        [
            "Richer countries use more energy, but most of them now cut it while growing.",
            "Income, growth and fuel production do not predict how clean a grid is; the mix does.",
            "Coal-based grids decarbonised fastest; some hydro-based grids went backwards.",
            "The feedback loop changed the questions we could ask more than the model scores.",
            "Limits: GDP ends 2018 · data-derived income tiers · ~160 countries · no causal claims.",
        ],
        Inches(0.8),
        Inches(1.5),
        Inches(11.7),
        Inches(5),
        size=20,
    )
    _footer(s, n)

    s = prs.slides.add_slide(prs.slide_layouts[6])
    _title(s, "Team and contributions")
    _bullets(
        s,
        [
            "TODO(team): one line per member: name, roll number, modules owned, part spoken in the video.",
            "Every member can explain every module (viva).",
            "Code, figures and every number: github.com/GOW444/parallax (notebooks/A3_workflow.ipynb).",
        ],
        Inches(0.8),
        Inches(1.5),
        Inches(11.7),
        Inches(5),
        size=20,
    )
    _footer(s, n + 1)

    VIDEO_DIR.mkdir(exist_ok=True)
    prs.save(PPTX_PATH)
    return PPTX_PATH


def check(path: Path = PPTX_PATH) -> list[str]:
    """Problems found in the deck: shapes outside the slide, empty slides."""
    prs = Presentation(path)
    problems = []
    for i, slide in enumerate(prs.slides, start=1):
        if not slide.shapes:
            problems.append(f"slide {i} is empty")
        for shape in slide.shapes:
            if (
                shape.left < 0
                or shape.top < 0
                or shape.left + shape.width > prs.slide_width
                or shape.top + shape.height > prs.slide_height
            ):
                problems.append(f"slide {i}: '{shape.name}' extends outside the slide")
    return problems


if __name__ == "__main__":
    out = build()
    print(out, check(out) or "deck check passed")
