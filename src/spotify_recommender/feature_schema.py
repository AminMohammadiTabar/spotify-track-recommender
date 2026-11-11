"""Feature architecture (V1): similarity dimensions, filters, and metadata.

Single source of truth for which feature belongs to which similarity
dimension and which columns act only as filters, ranking signals, or
display metadata. The categorization is a domain-driven design hypothesis;
it is revisited after the correlation analysis on the training split.

Rules enforced by ``validate_schema``:
- Every feature belongs to at most one similarity dimension (no double counting).
- Filter / ranking / metadata columns never contribute to a similarity score.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FeatureKind(str, Enum):
    """Statistical type of a feature; drives the choice of correlation method."""

    NUMERIC = "numeric"          # Pearson / Spearman
    CATEGORICAL = "categorical"  # Cramér's V, correlation ratio vs numeric
    MULTI_LABEL = "multi_label"  # set-valued (genres)


@dataclass(frozen=True)
class SimilarityDimension:
    """A musical aspect the user can choose to compare tracks on."""

    name: str
    features: tuple[str, ...]
    description: str


SIMILARITY_DIMENSIONS: tuple[SimilarityDimension, ...] = (
    SimilarityDimension(
        name="mood",
        features=("energy", "loudness", "valence"),
        description="Emotional feel and intensity of the track.",
    ),
    SimilarityDimension(
        name="acoustic",
        features=("acousticness", "instrumentalness", "liveness", "speechiness"),
        description="Timbre and sonic texture.",
    ),
    SimilarityDimension(
        name="rhythm",
        features=("tempo", "danceability", "time_signature"),
        description="Pulse, groove, and meter.",
    ),
    SimilarityDimension(
        name="harmonic",
        features=("key", "mode"),
        description="Tonal center and major/minor modality.",
    ),
    SimilarityDimension(
        name="genre",
        features=("genres",),
        description="Shared or closely related genres.",
    ),
)

FEATURE_KINDS: dict[str, FeatureKind] = {
    "energy": FeatureKind.NUMERIC,
    "loudness": FeatureKind.NUMERIC,
    "valence": FeatureKind.NUMERIC,
    "acousticness": FeatureKind.NUMERIC,
    "instrumentalness": FeatureKind.NUMERIC,
    "liveness": FeatureKind.NUMERIC,
    "speechiness": FeatureKind.NUMERIC,
    "tempo": FeatureKind.NUMERIC,
    "danceability": FeatureKind.NUMERIC,
    # Meter is a category (0 = unmetered), not a magnitude.
    "time_signature": FeatureKind.CATEGORICAL,
    # Pitch class is circular (11 is next to 0); never treat it as ordinal.
    "key": FeatureKind.CATEGORICAL,
    "mode": FeatureKind.CATEGORICAL,
    "genres": FeatureKind.MULTI_LABEL,
}

# Narrow candidate selection; never affect the similarity score.
FILTER_FEATURES: tuple[str, ...] = ("explicit", "is_remastered", "artists")

# Optional re-ranking / range control; not a musical similarity signal.
RANKING_FEATURES: tuple[str, ...] = ("popularity",)

# Carried through for display and identification only.
METADATA_FEATURES: tuple[str, ...] = (
    "track_id",
    "track_name",
    "artists",
    "album_name",
    "popularity",
    "duration_ms",
)


def dimension_names() -> tuple[str, ...]:
    return tuple(dimension.name for dimension in SIMILARITY_DIMENSIONS)


def get_dimension(name: str) -> SimilarityDimension:
    for dimension in SIMILARITY_DIMENSIONS:
        if dimension.name == name:
            return dimension
    raise KeyError(f"Unknown similarity dimension: {name!r}. Known: {dimension_names()}")


def similarity_features() -> tuple[str, ...]:
    """All features that feed any similarity dimension, in schema order."""
    return tuple(f for dimension in SIMILARITY_DIMENSIONS for f in dimension.features)


def dimension_of(feature: str) -> str:
    for dimension in SIMILARITY_DIMENSIONS:
        if feature in dimension.features:
            return dimension.name
    raise KeyError(f"Feature {feature!r} does not belong to any similarity dimension.")


def features_by_kind(kind: FeatureKind) -> tuple[str, ...]:
    return tuple(f for f in similarity_features() if FEATURE_KINDS[f] is kind)


def validate_schema() -> None:
    """Raise ValueError if the schema breaks the V1 design rules."""
    seen: dict[str, str] = {}
    for dimension in SIMILARITY_DIMENSIONS:
        if not dimension.features:
            raise ValueError(f"Dimension {dimension.name!r} has no features.")
        for feature in dimension.features:
            if feature in seen:
                raise ValueError(
                    f"Feature {feature!r} is in both {seen[feature]!r} and "
                    f"{dimension.name!r}; each feature may belong to one dimension."
                )
            seen[feature] = dimension.name

    names = dimension_names()
    if len(set(names)) != len(names):
        raise ValueError(f"Duplicate dimension names: {names}")

    missing_kinds = sorted(set(seen) - set(FEATURE_KINDS))
    if missing_kinds:
        raise ValueError(f"Features without a FeatureKind: {missing_kinds}")

    non_scoring = set(FILTER_FEATURES) | set(RANKING_FEATURES) | set(METADATA_FEATURES)
    leaked = sorted(non_scoring & set(seen))
    if leaked:
        raise ValueError(f"Filter/ranking/metadata columns used in a dimension: {leaked}")


validate_schema()
