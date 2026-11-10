"""Text normalization and categorical metadata processing utilities.

Provides Unicode (NFKC) normalization, case-folding, whitespace collapsing,
genre list deduplication, and version tag extraction while preserving
original track and album metadata.
"""

from __future__ import annotations

import ast
import re
import unicodedata
from pathlib import Path
from typing import Sequence

import pandas as pd

try:
    from .config import (
        PROCESSED_DATA_PATH,
        PROCESSED_NORMALIZED_PATH,
    )
except (ImportError, ValueError):
    # pyrefly: ignore[missing-import]
    from config import (
        PROCESSED_DATA_PATH,
        PROCESSED_NORMALIZED_PATH,
    )

# Compiled regular expressions for version pattern detection
VERSION_PATTERNS: dict[str, re.Pattern[str]] = {
    "remaster": re.compile(
        r"(?i)\b(?:remaster(?:ed)?(?:\s+\d{4})?|\d{4}\s+remaster(?:ed)?|remasterizado|remastering)\b"
    ),
    "live": re.compile(
        r"(?i)\b(?:live(?:\s+at|\s+from|\s+in|\s+version|\s+session|\s+concert)?|en\s+vivo|ao\s+vivo)\b"
    ),
    "acoustic": re.compile(
        r"(?i)\b(?:acoustic(?:\s+version)?|unplugged|stripped|ac[uú]stico)\b"
    ),
    "remix": re.compile(
        r"(?i)\b(?:remix(?:ed)?|club\s+mix|extended\s+mix|vip\s+mix|dub\s+mix|re-mix)\b"
    ),
    "radio_edit": re.compile(
        r"(?i)\b(?:radio\s+edit|radio\s+mix|single\s+version|single\s+edit)\b"
    ),
    "instrumental": re.compile(
        r"(?i)\b(?:instrumental(?:\s+version)?|karaoke)\b"
    ),
    "deluxe": re.compile(
        r"(?i)\b(?:deluxe(?:\s+edition)?|expanded(?:\s+edition)?|special\s+edition|anniversary(?:\s+edition)?)\b"
    ),
    "demo": re.compile(
        r"(?i)\b(?:demo(?:\s+version)?)\b"
    ),
}


def normalize_text(text: str | None) -> str:
    """
    Normalize text using Unicode NFKC, casefolding, and whitespace collapsing.

    Rules applied:
    1. Unicode Normalization: Form NFKC (canonical decomposition + canonical composition,
       mapping compatibility characters to their standard equivalents).
    2. Whitespace Normalization: Strip leading and trailing whitespace, collapse
       multiple consecutive whitespace characters into a single space.
    3. Case-Insensitive Normalization: Convert to lowercase using casefold()
       for robust caseless matching across languages and scripts.

    The function is strictly idempotent:
        normalize_text(normalize_text(x)) == normalize_text(x)

    Parameters
    ----------
    text : str or None
        Input string to normalize.

    Returns
    -------
    str
        Normalized string. Returns empty string if input is None or whitespace.
    """
    if text is None:
        return ""

    # Convert to string in case non-string objects are passed
    raw = str(text)

    # 1. Unicode NFKC normalization
    normalized = unicodedata.normalize("NFKC", raw)

    # 2. Whitespace collapsing and stripping
    normalized = re.sub(r"\s+", " ", normalized).strip()

    # 3. Case-insensitive casefolding
    return normalized.casefold()


def parse_genre_field(genres_value: object) -> list[str]:
    """
    Safely parse a genre field from various potential representations.

    Supports Python list, tuple, set, string representation of a Python list
    (e.g., "['rock', 'pop']"), and delimited strings (semicolon or comma).

    Parameters
    ----------
    genres_value : object
        Raw genre value from DataFrame or user input.

    Returns
    -------
    list[str]
        List of raw genre strings.
    """
    if genres_value is None or (isinstance(genres_value, float) and pd.isna(genres_value)):
        return []

    if isinstance(genres_value, (list, tuple, set)):
        return [str(g) for g in genres_value if g is not None]

    if isinstance(genres_value, str):
        s = genres_value.strip()
        if not s:
            return []
        if s.startswith("[") and s.endswith("]"):
            try:
                parsed = ast.literal_eval(s)
                if isinstance(parsed, (list, tuple, set)):
                    return [str(g) for g in parsed if g is not None]
            except (ValueError, SyntaxError):
                pass
        # Fallback for semicolon or comma delimited string
        if ";" in s:
            return [part.strip() for part in s.split(";") if part.strip()]
        if "," in s:
            return [part.strip() for part in s.split(",") if part.strip()]
        return [s]

    return [str(genres_value)]


def normalize_genre_list(genres_value: object) -> list[str]:
    """
    Normalize each genre label, remove duplicate labels, and sort consistently.

    Semantically distinct genres (e.g. 'alt-rock' vs 'rock') are preserved.
    Only exact matches after normalization (NFKC, casefold, whitespace)
    are deduplicated.

    Parameters
    ----------
    genres_value : object
        Raw genre sequence or serialized string.

    Returns
    -------
    list[str]
        Deduplicated, consistently sorted list of normalized genre labels.
    """
    raw_genres = parse_genre_field(genres_value)
    normalized_set: set[str] = set()

    for item in raw_genres:
        norm = normalize_text(item)
        if norm:
            normalized_set.add(norm)

    return sorted(normalized_set)


def extract_version_tags(
    track_name: str | None,
    album_name: str | None = None,
) -> list[str]:
    """
    Extract identifiable version tags from track and album titles.

    Identifiable versions include:
    - remaster
    - live
    - acoustic
    - remix
    - radio_edit
    - instrumental
    - deluxe
    - demo

    Matches are extracted and normalized using normalize_text().
    Original titles are never modified.

    Parameters
    ----------
    track_name : str or None
        Song title.
    album_name : str or None, optional
        Album title.

    Returns
    -------
    list[str]
        Sorted list of matched version tags, or ['original'] if none detected.
    """
    combined = f"{track_name or ''} {album_name or ''}"
    if not combined.strip():
        return ["original"]

    detected: set[str] = set()
    for tag_name, pattern in VERSION_PATTERNS.items():
        if pattern.search(combined):
            detected.add(normalize_text(tag_name))

    if not detected:
        return ["original"]

    return sorted(detected)


def extract_primary_version_tag(
    track_name: str | None,
    album_name: str | None = None,
) -> str:
    """
    Extract single primary version tag based on hierarchical precedence.

    Hierarchy:
    remix > live > acoustic > radio_edit > instrumental > remaster > deluxe > demo > original

    Parameters
    ----------
    track_name : str or None
        Song title.
    album_name : str or None, optional
        Album title.

    Returns
    -------
    str
        Primary version label (e.g., 'live', 'remix', 'original').
    """
    tags = extract_version_tags(track_name, album_name)
    if "original" in tags:
        return "original"

    precedence = [
        "remix",
        "live",
        "acoustic",
        "radio_edit",
        "instrumental",
        "remaster",
        "deluxe",
        "demo",
    ]
    for p in precedence:
        if p in tags:
            return p

    return tags[0]


def normalize_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply categorical text normalization and version tag extraction to DataFrame.

    Guarantees:
    - Preserves original metadata (track_name, artists, album_name untouched).
    - Preserves original genre values in separate field 'genres_raw'.
    - Stores normalized genre lists in 'genres' and formatted string in 'genres_str'.
    - Extracts derived fields 'version_tag' (primary) and 'version_tags' (list/str).
    - Does not modify or drop any records.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame (e.g. tracks_aggregated.csv).

    Returns
    -------
    pd.DataFrame
        New normalized DataFrame.
    """
    result = df.copy()

    # 1. Preserve original genre metadata in genres_raw
    if "genres_raw" not in result.columns:
        if "genres" in result.columns:
            result["genres_raw"] = result["genres"]
        elif "track_genre" in result.columns:
            result["genres_raw"] = result["track_genre"]
        else:
            result["genres_raw"] = ""

    # 2. Normalize genre lists
    normalized_genres = result["genres_raw"].apply(normalize_genre_list)
    result["genres"] = normalized_genres
    result["genres_str"] = normalized_genres.apply(lambda g: "; ".join(g))

    # 3. Extract version tags into separate derived fields
    t_names = result["track_name"].fillna("").astype(str)
    a_names = result["album_name"].fillna("").astype(str) if "album_name" in result.columns else pd.Series([""] * len(result))

    version_tags_series = [
        extract_version_tags(t, a)
        for t, a in zip(t_names, a_names)
    ]
    primary_tags_series = [
        extract_primary_version_tag(t, a)
        for t, a in zip(t_names, a_names)
    ]

    result["version_tag"] = primary_tags_series
    result["version_tags"] = ["; ".join(tags) for tags in version_tags_series]

    return result


def normalize_file(
    input_path: Path | str = PROCESSED_DATA_PATH,
    output_path: Path | str = PROCESSED_NORMALIZED_PATH,
) -> Path:
    """
    Read aggregated tracks, apply text normalization, and write normalized dataset.

    Parameters
    ----------
    input_path : Path or str
        Source aggregated dataset path.
    output_path : Path or str
        Destination path for normalized dataset.

    Returns
    -------
    Path
        Destination path of written CSV.
    """
    in_p = Path(input_path)
    out_p = Path(output_path)

    if not in_p.exists():
        raise FileNotFoundError(f"Input dataset not found at: {in_p}")

    df = pd.read_csv(in_p)
    normalized = normalize_dataset(df)

    out_p.parent.mkdir(parents=True, exist_ok=True)
    normalized.to_csv(out_p, index=False)
    return out_p
