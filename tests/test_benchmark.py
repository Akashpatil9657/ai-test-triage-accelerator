from scripts.benchmark import pairwise_scores


def test_pairwise_scores_are_perfect_for_matching_groups():
    groups = {"a": "one", "b": "one", "c": "two"}
    assert pairwise_scores(groups, groups) == (1.0, 1.0, 1.0)


def test_pairwise_scores_penalize_false_merge_and_missed_merge():
    expected = {"a": "one", "b": "one", "c": "two"}
    predicted = {"a": "left", "b": "right", "c": "right"}
    assert pairwise_scores(expected, predicted) == (0.0, 0.0, 0.0)