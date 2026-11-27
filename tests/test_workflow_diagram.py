"""Rules for the workflow diagram, taken from the brief (unrolled, labelled, few self-loops)."""

import matplotlib

matplotlib.use("Agg")

from src import workflow_diagram as wd  # noqa: E402


def _iteration(node_id: str) -> int:
    return {n.node_id: n.iteration for n in wd.NODES}[node_id]


def test_no_self_loops_in_the_unrolled_chain():
    assert all(a != b for a, b, _ in wd.edges())


def test_every_edge_points_forward():
    """Unrolled means no back-edges: within an iteration, x never decreases along an edge."""
    pos = {n.node_id: n.x for n in wd.NODES}
    for a, b, label in wd.edges():
        if label != "Feedback loop":
            assert pos[b] > pos[a], (a, b)


def test_exactly_one_feedback_edge_joins_the_iterations():
    feedback = [e for e in wd.edges() if e[2] == "Feedback loop"]
    assert feedback == [("k1", "d2", "Feedback loop")]
    cross = [(a, b) for a, b, _ in wd.edges() if _iteration(a) != _iteration(b)]
    assert cross == [("k1", "d2")]


def test_every_stage_appears_in_both_iterations():
    for it in (1, 2):
        stages = {n.stage for n in wd.NODES if n.iteration == it}
        assert stages == set(wd.STAGES)


def test_each_model_lane_is_followed_by_a_visualization():
    """The brief needs visualization AND analysis: every model node feeds a Vis node."""
    stage = {n.node_id: n.stage for n in wd.NODES}
    for node in wd.NODES:
        if node.stage == "Models":
            targets = [b for a, b, _ in wd.edges() if a == node.node_id]
            assert targets and all(stage[t] == "Visualization" for t in targets)


def test_draw_has_the_feedback_label():
    fig = wd.draw()
    texts = [t.get_text() for ax in fig.axes for t in ax.texts]
    assert texts.count("Feedback loop") == 2  # rolled panel + unrolled panel
