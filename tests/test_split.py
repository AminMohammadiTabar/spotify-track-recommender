import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pytest

# Support running directly via 'Run Python File'
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SRC_DIR = _PROJECT_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from spotify_recommender.split import (
    DEFAULT_RATIOS,
    find_leaked_groups,
    group_stratified_split,
)


def _synthetic(n_groups=1500, n_labels=20, seed=0):
    """Groups of 1-4 tracks; label frequencies decay so some labels are rare."""
    rng = random.Random(seed)
    labels_pool = [f"g{i:02d}" for i in range(n_labels)]
    weights = [1.0 / (i + 1) for i in range(n_labels)]
    groups, labels = [], []
    for g in range(n_groups):
        group_labels = set(rng.choices(labels_pool, weights=weights, k=rng.choice([1, 1, 2])))
        for _ in range(rng.choice([1, 1, 1, 2, 3, 4])):
            groups.append(f"group-{g}")
            labels.append(sorted(group_labels))
    return groups, labels


def _sample_splits(groups, assignment):
    return [assignment[g] for g in groups]


def test_no_group_spans_multiple_splits():
    groups, labels = _synthetic()
    assignment = group_stratified_split(groups, labels)
    assert find_leaked_groups(groups, _sample_splits(groups, assignment)) == {}
    assert set(assignment) == set(groups)


def test_split_sizes_follow_ratios():
    groups, labels = _synthetic()
    assignment = group_stratified_split(groups, labels)
    sizes = Counter(_sample_splits(groups, assignment))
    for split, ratio in DEFAULT_RATIOS.items():
        assert abs(sizes[split] / len(groups) - ratio) < 0.02


def test_every_label_is_balanced_across_splits():
    groups, labels = _synthetic()
    assignment = group_stratified_split(groups, labels)
    per_label = defaultdict(Counter)
    for group, sample_labels in zip(groups, labels):
        for label in sample_labels:
            per_label[label][assignment[group]] += 1

    for label, counts in per_label.items():
        total = sum(counts.values())
        for split, ratio in DEFAULT_RATIOS.items():
            assert counts[split] > 0, f"{label} missing from {split}"
            if total >= 200:
                assert abs(counts[split] / total - ratio) < 0.05, (label, dict(counts))


def test_same_seed_same_split_and_seed_matters():
    groups, labels = _synthetic()
    assert group_stratified_split(groups, labels, seed=7) == group_stratified_split(groups, labels, seed=7)
    assert group_stratified_split(groups, labels, seed=7) != group_stratified_split(groups, labels, seed=8)


def test_groups_without_labels_are_assigned():
    groups = ["a", "b", "c", "d"]
    labels = [["pop"], [], [], ["rock"]]
    assignment = group_stratified_split(groups, labels, ratios={"train": 0.5, "test": 0.5})
    assert set(assignment) == {"a", "b", "c", "d"}


def test_invalid_inputs_raise():
    with pytest.raises(ValueError):
        group_stratified_split(["a"], [["pop"]], ratios={"train": 0.7, "test": 0.2})
    with pytest.raises(ValueError):
        group_stratified_split(["a"], [["pop"]], ratios={"train": 1.2, "test": -0.2})
    with pytest.raises(ValueError):
        group_stratified_split(["a", "b"], [["pop"]])


def test_split_tracks_groups_versions_of_same_song():
    pd = pytest.importorskip("pandas")
    from spotify_recommender.split import genre_distribution_report, split_size_report, split_tracks

    rows = []
    for i in range(300):
        rows.append({
            "track_id": f"id-{i}",
            "track_name": f"Song {i % 120}" if (i // 120) % 2 else f"  SONG {i % 120} ",
            "artists": "Artist A" if i % 3 else "artist a",
            "genres": "['pop', 'rock']" if i % 5 == 0 else "['jazz']",
        })
    df = pd.DataFrame(rows)

    assignments = split_tracks(df)
    assert assignments.groupby("group_id")["split"].nunique().max() == 1

    # Title/artist variants that differ only in case or whitespace share one group.
    variants = assignments[assignments["track_id"].isin(["id-0", "id-120"])]
    assert variants["group_id"].nunique() == 1

    sizes = split_size_report(assignments)
    assert sizes["n_tracks"].sum() == len(df)

    genres = genre_distribution_report(assignments)
    assert set(genres.index) == {"jazz", "pop", "rock"}
    assert {"train_count", "validation_share", "max_abs_dev"} <= set(genres.columns)


def test_split_tracks_rejects_duplicate_track_ids():
    pd = pytest.importorskip("pandas")
    from spotify_recommender.split import split_tracks

    df = pd.DataFrame([
        {"track_id": "x", "track_name": "A", "artists": "B", "genres": "['pop']"},
        {"track_id": "x", "track_name": "A", "artists": "B", "genres": "['rock']"},
    ])
    with pytest.raises(ValueError):
        split_tracks(df)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
