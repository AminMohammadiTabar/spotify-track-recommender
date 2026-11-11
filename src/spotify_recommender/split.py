"""Group-aware multi-label stratified Train / Validation / Test split.

Why both constraints:
- Group-aware: different releases of the same song (same normalized title +
  artists, different track_id) often have identical audio. They must land in
  the same split, otherwise test tracks are effectively seen during training.
- Multi-label stratified: a track can carry several genres. Every genre should
  keep roughly the same share across splits, including rare ones.

Algorithm: iterative stratification (Sechidis et al., 2011) applied to groups.
Each group carries the summed genre counts of its tracks. Labels are processed
from rarest to most common; every unassigned group holding the current label
goes to the split that still "wants" that label the most (ties: the split with
the most remaining capacity, then a seeded random draw).

The core works on plain Python sequences; pandas is only needed for the
DataFrame wrapper, the reports, and the CLI entry point.
"""

from __future__ import annotations

import random
from collections import Counter, defaultdict
from typing import TYPE_CHECKING, Hashable, Mapping, Sequence

if TYPE_CHECKING:
    import pandas as pd

SPLIT_NAMES: tuple[str, ...] = ("train", "validation", "test")
DEFAULT_RATIOS: dict[str, float] = {"train": 0.70, "validation": 0.15, "test": 0.15}
DEFAULT_SEED = 42
GROUP_SEPARATOR = " || "


def _validate_ratios(ratios: Mapping[str, float]) -> None:
    if not ratios:
        raise ValueError("At least one split ratio is required.")
    if any(r <= 0 for r in ratios.values()):
        raise ValueError(f"Split ratios must be positive: {dict(ratios)}")
    if abs(sum(ratios.values()) - 1.0) > 1e-9:
        raise ValueError(f"Split ratios must sum to 1.0, got {sum(ratios.values())}")


def group_stratified_split(
    groups: Sequence[Hashable],
    labels: Sequence[Sequence[str]],
    ratios: Mapping[str, float] = DEFAULT_RATIOS,
    seed: int = DEFAULT_SEED,
) -> dict[Hashable, str]:
    """Assign every group to a split, stratifying on multi-label targets.

    Parameters
    ----------
    groups : one group id per sample (track).
    labels : one collection of labels (genres) per sample.
    ratios : split name -> fraction of samples; must sum to 1.
    seed : controls tie-breaking and processing order; same seed, same split.

    Returns
    -------
    dict mapping each group id to a split name.
    """
    _validate_ratios(ratios)
    if len(groups) != len(labels):
        raise ValueError(
            f"groups and labels must have equal length ({len(groups)} != {len(labels)})."
        )

    split_names = list(ratios)
    rng = random.Random(seed)

    group_size: Counter = Counter()
    group_labels: dict[Hashable, Counter] = defaultdict(Counter)
    for group, sample_labels in zip(groups, labels):
        group_size[group] += 1
        group_labels[group].update(set(sample_labels))  # also registers label-less groups

    order = list(group_size)
    rng.shuffle(order)

    total_per_label: Counter = Counter()
    for counts in group_labels.values():
        total_per_label.update(counts)

    n_samples = len(groups)
    wanted_size = {s: ratios[s] * n_samples for s in split_names}
    wanted_label = {
        s: {label: ratios[s] * count for label, count in total_per_label.items()}
        for s in split_names
    }
    remaining = dict(total_per_label)

    groups_by_label: dict[str, list[Hashable]] = defaultdict(list)
    for group in order:
        for label in group_labels[group]:
            groups_by_label[label].append(group)

    assignment: dict[Hashable, str] = {}

    def assign(group: Hashable, split: str) -> None:
        assignment[group] = split
        wanted_size[split] -= group_size[group]
        for label, count in group_labels[group].items():
            wanted_label[split][label] -= count
            remaining[label] -= count

    while True:
        active = [label for label, count in remaining.items() if count > 0]
        if not active:
            break
        # Rarest label first: its few groups get placed while every split
        # still has room for it.
        label = min(active, key=lambda lbl: (remaining[lbl], lbl))
        for group in groups_by_label[label]:
            if group in assignment:
                continue
            split = max(
                split_names,
                key=lambda s: (wanted_label[s][label], wanted_size[s], rng.random()),
            )
            assign(group, split)

    for group in order:  # groups without any label
        if group not in assignment:
            split = max(split_names, key=lambda s: (wanted_size[s], rng.random()))
            assign(group, split)

    return assignment


def find_leaked_groups(
    groups: Sequence[Hashable], sample_splits: Sequence[str]
) -> dict[Hashable, set[str]]:
    """Return groups whose samples appear in more than one split (should be empty)."""
    seen: dict[Hashable, set[str]] = defaultdict(set)
    for group, split in zip(groups, sample_splits):
        seen[group].add(split)
    return {group: splits for group, splits in seen.items() if len(splits) > 1}


# ---------------------------------------------------------------------------
# DataFrame layer (requires pandas)
# ---------------------------------------------------------------------------

def build_group_ids(df: "pd.DataFrame") -> "pd.Series":
    """Group id = normalized track_name + normalized artists."""
    from .normalization import normalize_text

    titles = df["track_name"].map(normalize_text)
    artists = df["artists"].map(normalize_text)
    return titles + GROUP_SEPARATOR + artists


def split_tracks(
    df: "pd.DataFrame",
    ratios: Mapping[str, float] = DEFAULT_RATIOS,
    seed: int = DEFAULT_SEED,
) -> "pd.DataFrame":
    """Return one row per track: track_id, group_id, genres, split.

    Raises ValueError if any group ends up in more than one split.
    """
    import pandas as pd

    from .normalization import normalize_genre_list

    if df["track_id"].duplicated().any():
        raise ValueError("track_id must be unique; split the aggregated/normalized dataset.")

    group_ids = build_group_ids(df)
    genres = df["genres"].map(normalize_genre_list)

    group_to_split = group_stratified_split(
        group_ids.tolist(), genres.tolist(), ratios=ratios, seed=seed
    )

    result = pd.DataFrame({
        "track_id": df["track_id"].to_numpy(),
        "group_id": group_ids.to_numpy(),
        "genres": genres.to_numpy(),
        "split": group_ids.map(group_to_split).to_numpy(),
    })

    leaked = find_leaked_groups(result["group_id"].tolist(), result["split"].tolist())
    if leaked:
        raise ValueError(f"{len(leaked)} groups span multiple splits, e.g. {next(iter(leaked))!r}")
    return result


def split_size_report(assignments: "pd.DataFrame") -> "pd.DataFrame":
    """Tracks and groups per split, with their shares."""
    report = assignments.groupby("split").agg(
        n_tracks=("track_id", "size"),
        n_groups=("group_id", "nunique"),
    )
    report["track_share"] = report["n_tracks"] / report["n_tracks"].sum()
    report["group_share"] = report["n_groups"] / report["n_groups"].sum()
    order = [s for s in SPLIT_NAMES if s in report.index]
    return report.loc[order + [s for s in report.index if s not in order]]


def genre_distribution_report(
    assignments: "pd.DataFrame",
    ratios: Mapping[str, float] = DEFAULT_RATIOS,
) -> "pd.DataFrame":
    """Per-genre track counts and shares by split, plus deviation from the target ratio.

    Columns: <split>_count, <split>_share for each split, total, max_abs_dev.
    Sorted by max_abs_dev descending, so the worst-balanced genres come first.
    """
    import pandas as pd

    exploded = assignments[["split", "genres"]].explode("genres").dropna(subset=["genres"])
    counts = exploded.groupby(["genres", "split"]).size().unstack(fill_value=0)
    splits = list(ratios)
    for split in splits:
        if split not in counts.columns:
            counts[split] = 0
    counts = counts[splits]

    total = counts.sum(axis=1)
    report = counts.add_suffix("_count")
    for split in splits:
        report[f"{split}_share"] = counts[split] / total
    report["total"] = total
    deviations = [(report[f"{s}_share"] - ratios[s]).abs() for s in splits]
    report["max_abs_dev"] = pd.concat(deviations, axis=1).max(axis=1)
    report.index.name = "genre"
    return report.sort_values("max_abs_dev", ascending=False)


def main() -> None:
    import argparse
    from pathlib import Path

    import pandas as pd

    from .config import PROCESSED_DATA_DIR, PROCESSED_NORMALIZED_PATH

    parser = argparse.ArgumentParser(description="Group-aware multi-label stratified split")
    parser.add_argument("--input", default=str(PROCESSED_NORMALIZED_PATH))
    parser.add_argument("--output", default=str(PROCESSED_DATA_DIR / "split_assignments.csv"))
    parser.add_argument(
        "--genre-report", default=str(PROCESSED_DATA_DIR / "split_genre_distribution.csv")
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    assignments = split_tracks(df, seed=args.seed)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    assignments.drop(columns=["genres"]).to_csv(out, index=False)

    genre_report = genre_distribution_report(assignments)
    genre_report.to_csv(args.genre_report)

    print(f"Assignments saved to: {out}")
    print(f"Genre report saved to: {args.genre_report}\n")
    print("Group leakage check: PASS (no group spans more than one split)\n")
    print(split_size_report(assignments).to_string(float_format=lambda v: f"{v:.4f}"))

    missing = genre_report[(genre_report[[f"{s}_count" for s in DEFAULT_RATIOS]] == 0).any(axis=1)]
    print(f"\nGenres missing from at least one split: {len(missing)}")
    print(f"Max per-genre share deviation: {genre_report['max_abs_dev'].max():.4f}")
    print(f"Mean per-genre share deviation: {genre_report['max_abs_dev'].mean():.4f}")
    print("\nWorst-balanced genres:")
    print(genre_report.head(10).to_string(float_format=lambda v: f"{v:.3f}"))


if __name__ == "__main__":
    main()
