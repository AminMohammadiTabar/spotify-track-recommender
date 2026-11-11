import sys
from pathlib import Path

# Support running directly via 'Run Python File'
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SRC_DIR = _PROJECT_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from spotify_recommender import feature_schema as fs


def test_v1_dimensions_and_features():
    assert fs.dimension_names() == ("mood", "acoustic", "rhythm", "harmonic", "genre")
    assert fs.get_dimension("mood").features == ("energy", "loudness", "valence")
    assert fs.get_dimension("acoustic").features == (
        "acousticness", "instrumentalness", "liveness", "speechiness",
    )
    assert fs.get_dimension("rhythm").features == ("tempo", "danceability", "time_signature")
    assert fs.get_dimension("harmonic").features == ("key", "mode")
    assert fs.get_dimension("genre").features == ("genres",)


def test_each_feature_belongs_to_exactly_one_dimension():
    features = fs.similarity_features()
    assert len(features) == len(set(features))
    assert fs.dimension_of("energy") == "mood"
    assert fs.dimension_of("acousticness") == "acoustic"


def test_filters_and_metadata_never_score():
    scoring = set(fs.similarity_features())
    for column in ("explicit", "is_remastered", "artists", "popularity", "duration_ms"):
        assert column not in scoring
    assert set(fs.FILTER_FEATURES) == {"explicit", "is_remastered", "artists"}
    assert fs.RANKING_FEATURES == ("popularity",)


def test_feature_kinds_route_correlation_methods():
    assert set(fs.features_by_kind(fs.FeatureKind.CATEGORICAL)) == {"time_signature", "key", "mode"}
    assert fs.features_by_kind(fs.FeatureKind.MULTI_LABEL) == ("genres",)
    assert "key" not in fs.features_by_kind(fs.FeatureKind.NUMERIC)


def test_validate_schema_rejects_double_counting(monkeypatch):
    broken = fs.SIMILARITY_DIMENSIONS + (
        fs.SimilarityDimension("extra", ("energy",), "duplicates mood.energy"),
    )
    monkeypatch.setattr(fs, "SIMILARITY_DIMENSIONS", broken)
    try:
        fs.validate_schema()
    except ValueError as exc:
        assert "energy" in str(exc)
    else:
        raise AssertionError("validate_schema accepted a feature in two dimensions")


def test_unknown_dimension_raises():
    try:
        fs.get_dimension("popularity")
    except KeyError:
        pass
    else:
        raise AssertionError("expected KeyError")


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
