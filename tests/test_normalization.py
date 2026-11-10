import sys
from pathlib import Path
import unicodedata
import pandas as pd

# Support running directly via 'Run Python File'
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SRC_DIR = _PROJECT_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from spotify_recommender.normalization import (
    extract_primary_version_tag,
    extract_version_tags,
    normalize_dataset,
    normalize_genre_list,
    normalize_text,
)


def test_case_insensitive_normalization():
    """Verify case-insensitive normalization using casefold()."""
    assert normalize_text("Acoustic") == "acoustic"
    assert normalize_text("ACOUSTIC") == "acoustic"
    assert normalize_text("aCoUsTiC") == "acoustic"
    assert normalize_text("ROCK") == "rock"
    assert normalize_text("DeEp-HoUsE") == "deep-house"


def test_whitespace_normalization():
    """Verify removal of leading/trailing whitespace and collapsing of internal consecutive whitespace."""
    assert normalize_text("   Rock   ") == "rock"
    assert normalize_text("  Indie   Rock  ") == "indie rock"
    assert normalize_text("\t\nElectronic   Dance \t Music \n") == "electronic dance music"
    assert normalize_text("   ") == ""
    assert normalize_text(None) == ""


def test_unicode_normalization_nfkc():
    """Verify NFKC normalization transforms fullwidth, decomposed characters, and ligatures."""
    # Fullwidth latin characters to ASCII
    fullwidth_str = "Ｒｏｃｋ"
    assert normalize_text(fullwidth_str) == "rock"

    # Decomposed accents: 'e' + combining acute accent -> composed 'é'
    decomposed = "cafe\u0301"
    composed = "café"
    assert normalize_text(decomposed) == normalize_text(composed)
    assert normalize_text(decomposed) == "café"

    # Ligatures: 'ﬁ' decomposes to 'fi' in NFKC
    ligature = "ﬁlter"
    assert normalize_text(ligature) == "filter"


def test_duplicate_genre_removal():
    """Verify duplicate genre removal after normalization, preserving distinct genres and sorting."""
    raw_genres = ["Acoustic", "ACOUSTIC", " acoustic ", " Rock ", "ROCK", "rock"]
    normalized = normalize_genre_list(raw_genres)
    assert normalized == ["acoustic", "rock"]

    # String representation of list
    raw_str = "['Pop', 'POP', 'pop', 'Dance', 'dance ']"
    assert normalize_genre_list(raw_str) == ["dance", "pop"]


def test_preservation_of_semantically_different_labels():
    """Verify that semantically different labels are never merged."""
    genres = ["rock", "alt-rock", "punk-rock", "hard-rock", "pop", "indie-pop"]
    normalized = normalize_genre_list(genres)
    assert len(normalized) == len(genres)
    for g in genres:
        assert g in normalized


def test_idempotency_of_normalization():
    """Verify that normalizations are strictly idempotent: f(f(x)) == f(x)."""
    samples = [
        "   Acoustic   Rock  \n",
        "Ｒｏｃｋ ＆ Ｒｏｌｌ",
        "cafe\u0301  CONCERT",
        "‘Classic’",
        "",
        "Already Normalized",
    ]
    for s in samples:
        first_pass = normalize_text(s)
        second_pass = normalize_text(first_pass)
        assert first_pass == second_pass

    genre_inputs = [
        ["Rock", "ROCK", "pop"],
        "['Alt-Rock', 'alt-rock', 'Jazz']",
        ["acoustic", "folk", "indie"],
    ]
    for g in genre_inputs:
        first_pass = normalize_genre_list(g)
        second_pass = normalize_genre_list(first_pass)
        assert first_pass == second_pass


def test_preservation_of_original_metadata():
    """Verify original metadata (names, titles, raw genres) is preserved without modification."""
    sample_df = pd.DataFrame([
        {
            "track_id": "track_001",
            "track_name": "Comfortably Numb - Live at Pompeii",
            "artists": "Pink Floyd",
            "album_name": "Live at Pompeii (Deluxe)",
            "genres": "['Prog-Rock', 'Classic Rock']",
            "duration_ms": 480000,
        },
        {
            "track_id": "track_002",
            "track_name": "Hotel California - 2013 Remaster",
            "artists": "Eagles",
            "album_name": "Hotel California (40th Anniversary)",
            "genres": "['Rock']",
            "duration_ms": 391000,
        },
    ])

    normalized_df = normalize_dataset(sample_df)

    # 1. Original DataFrame must not be mutated
    assert "genres_raw" not in sample_df.columns
    assert "version_tag" not in sample_df.columns

    # 2. Track names, artist names, and album names must be completely intact (no stripping)
    assert normalized_df["track_name"].iloc[0] == "Comfortably Numb - Live at Pompeii"
    assert normalized_df["album_name"].iloc[0] == "Live at Pompeii (Deluxe)"
    assert normalized_df["artists"].iloc[0] == "Pink Floyd"

    assert normalized_df["track_name"].iloc[1] == "Hotel California - 2013 Remaster"
    assert normalized_df["album_name"].iloc[1] == "Hotel California (40th Anniversary)"
    assert normalized_df["artists"].iloc[1] == "Eagles"

    # 3. Original genres preserved in genres_raw
    assert normalized_df["genres_raw"].iloc[0] == "['Prog-Rock', 'Classic Rock']"
    assert normalized_df["genres_raw"].iloc[1] == "['Rock']"

    # 4. Normalized genres stored in genres and genres_str
    assert normalized_df["genres"].iloc[0] == ["classic rock", "prog-rock"]
    assert normalized_df["genres_str"].iloc[0] == "classic rock; prog-rock"
    assert normalized_df["genres"].iloc[1] == ["rock"]
    assert normalized_df["genres_str"].iloc[1] == "rock"

    # 5. Version tags extracted into derived fields
    assert normalized_df["version_tag"].iloc[0] == "live"
    assert "live" in normalized_df["version_tags"].iloc[0]
    assert "deluxe" in normalized_df["version_tags"].iloc[0]

    assert normalized_df["version_tag"].iloc[1] == "remaster"
    assert "remaster" in normalized_df["version_tags"].iloc[1]
    assert "deluxe" in normalized_df["version_tags"].iloc[1]


def test_version_tag_extraction_defaults_to_original():
    """Verify that tracks without explicit version keywords are tagged as 'original'."""
    tags = extract_version_tags("Bohemian Rhapsody", "A Night at the Opera")
    assert tags == ["original"]
    primary = extract_primary_version_tag("Bohemian Rhapsody", "A Night at the Opera")
    assert primary == "original"


if __name__ == "__main__":
    # pyrefly: ignore[missing-import]
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
