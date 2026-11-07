from pathlib import Path
import shutil

import pandas as pd

try:
    from .config import (
        DATASET_SLUG,
        NUMERIC_FEATURES,
        PROCESSED_DATA_PATH,
        RAW_DATA_PATH,
        REQUIRED_COLUMNS,
    )
except (ImportError, ValueError):
    # pyrefly: ignore[missing-import]
    from config import (
        DATASET_SLUG,
        NUMERIC_FEATURES,
        PROCESSED_DATA_PATH,
        RAW_DATA_PATH,
        REQUIRED_COLUMNS,
    )


def download_dataset(destination: Path = RAW_DATA_PATH) -> Path:
    """Download the latest Kaggle dataset using kagglehub and copy its CSV locally."""
    try:
        # pyrefly: ignore[missing-import]
        import kagglehub
    except ImportError as exc:
        raise RuntimeError(
            "kagglehub is not installed. Please run `pip install kagglehub` first."
        ) from exc

    downloaded_dir = Path(kagglehub.dataset_download(DATASET_SLUG))
    csv_files = list(downloaded_dir.rglob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(
            f"No CSV file found in downloaded directory: {downloaded_dir}"
        )

    # The dataset is expected to contain one main CSV; choosing the largest
    # file avoids accidentally selecting a small metadata CSV.
    source_csv = max(csv_files, key=lambda file_path: file_path.stat().st_size)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_csv, destination)
    return destination


def load_tracks(csv_path: Path | str | None = None) -> pd.DataFrame:
    """Load and minimally validate the raw Spotify tracks CSV."""
    if csv_path is None:
        csv_path = RAW_DATA_PATH
    else:
        csv_path = Path(csv_path)

    if (
        not csv_path.exists()
        and csv_path.name == "spotify_tracks.csv"
        and (csv_path.parent / "dataset.csv").exists()
    ):
        csv_path = csv_path.parent / "dataset.csv"

    if not csv_path.exists():
        raise FileNotFoundError(
            f"Dataset file not found: {csv_path}. Run the download command or place dataset.csv in data/raw."
        )

    df = pd.read_csv(csv_path)

    # Kaggle CSV may include an exported dataframe index.
    unnamed = [column for column in df.columns
               if str(column).lower().startswith("unnamed:")]
    if unnamed:
        df = df.drop(columns=unnamed)

    # Drop corrupted records (missing metadata or invalid zero duration)
    df = df.dropna(subset=["track_id", "artists", "album_name", "track_name"])
    df = df[df["duration_ms"] > 0].reset_index(drop=True)

    # Drop 100% exact duplicate rows (identical track_id and identical genre)
    df = df.drop_duplicates().reset_index(drop=True)

    missing = sorted(REQUIRED_COLUMNS.difference(df.columns))
    if missing:
        raise ValueError(
            "Missing required columns in CSV: " + ", ".join(missing)
        )

    return df


def add_remastered_feature(df: pd.DataFrame) -> pd.DataFrame:
    """Detect remastered tracks from track_name or album_name via regex."""
    df = df.copy()
    remaster_pattern = r"(?i)\bremaster(?:ed)?\b"
    name_match = df["track_name"].fillna("").str.contains(remaster_pattern, regex=True)
    album_match = df["album_name"].fillna("").str.contains(remaster_pattern, regex=True)
    df["is_remastered"] = (name_match | album_match).astype(int)
    return df


def prepare_aggregated_tracks(raw_df: pd.DataFrame | None = None) -> pd.DataFrame:
    """
    Aggregate tracks by unique track_id, preserving multi-genres and audio features.

    - Extracts `is_remastered` feature
    - Takes `max` of popularity across duplicate genre rows
    - Aggregates all genres per track into a sorted list and semicolon-joined string
    - Returns exactly one unique row per track_id
    """
    if raw_df is None:
        raw_df = load_tracks()

    df = add_remastered_feature(raw_df)

    feature_cols = [
        c for c in NUMERIC_FEATURES + ["key", "mode", "time_signature", "explicit"]
        if c in df.columns
    ]
    meta_cols = ["track_name", "artists", "album_name", "is_remastered"]

    agg_dict = {col: "first" for col in feature_cols + meta_cols}
    agg_dict["popularity"] = "max"
    agg_dict["track_genre"] = lambda g: sorted(set(g.dropna()))

    agg_df = df.groupby("track_id", as_index=False).agg(agg_dict)
    agg_df = agg_df.rename(columns={"track_genre": "genres"})
    agg_df["genres_str"] = agg_df["genres"].apply(lambda g: "; ".join(g))

    return agg_df


if __name__ == "__main__":
    print("Loading raw dataset from RAW_DATA_PATH...")
    raw_tracks = load_tracks()
    print(f"Raw tracks loaded (after dropping exact duplicates): {len(raw_tracks):,}")

    print("\nAggregating multi-genre tracks by unique track_id...")
    agg_tracks = prepare_aggregated_tracks(raw_tracks)
    print(f"Unique tracks: {len(agg_tracks):,}")
    print(f"Remastered tracks: {agg_tracks['is_remastered'].sum():,}")

    multi_genre_cnt = (agg_tracks["genres"].apply(len) > 1).sum()
    print(f"Tracks with multiple genres: {multi_genre_cnt:,}")

    print("\nSample aggregated preview:")
    sample_cols = ["track_name", "artists", "genres_str", "is_remastered", "popularity"]
    print(agg_tracks[sample_cols].head())
