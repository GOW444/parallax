"""Rules for the workflow diagram, taken from the brief (unrolled, labelled, few self-loops)."""

import matplotlib

matplotlib.use("Agg")

from src import workflow_diagram as wd  # noqa: E402


def test_no_self_loops():
    assert all(a != b for a, b, _ in wd.edges())


def test_exactly_one_feedback_edge_joins_the_iterations():
    feedback = [e for e in wd.edges() if e[2] == "Feedback loop"]
    assert feedback == [("k1", "d2", "Feedback loop")]
    cross = [(a, b) for a, b, _ in wd.edges() if a[-1] != b[-1]]
    assert cross == [("k1", "d2")]


def test_every_stage_appears_in_both_iterations():
    for it in (1, 2):
        stages = {n.stage for n in wd.NODES if n.iteration == it}
        assert stages == set(wd.STAGES)


def test_draw_has_the_feedback_label():
    fig = wd.draw()
    texts = [t.get_text() for t in fig.axes[0].texts]
    assert "Feedback loop" in texts
