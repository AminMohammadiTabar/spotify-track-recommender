from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_SLUG = "maharshipandya/-spotify-tracks-dataset"

RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"

def _resolve_raw_data_path() -> Path:
    standard_path = RAW_DATA_DIR / "spotify_tracks.csv"
    dataset_path = RAW_DATA_DIR / "dataset.csv"
    if not standard_path.exists() and dataset_path.exists():
        return dataset_path
    return standard_path

RAW_DATA_PATH = _resolve_raw_data_path()

MODEL_DIR = PROJECT_ROOT / "models"
MODEL_PATH = MODEL_DIR / "random_forest_recommender.joblib"

PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
PROCESSED_DATA_PATH = PROCESSED_DATA_DIR / "tracks_aggregated.csv"

# Continuous audio features
NUMERIC_FEATURES = [
    "danceability",
    "energy",
    "loudness",
    "speechiness",
    "acousticness",
    "instrumentalness",
    "liveness",
    "valence",
    "tempo",
    "duration_ms",
]

# Categorical features (including engineered is_remastered)
CATEGORICAL_FEATURES = [
    "key",
    "mode",
    "time_signature",
    "explicit",
    "is_remastered",
]

FEATURE_COLUMNS = NUMERIC_FEATURES + CATEGORICAL_FEATURES

METADATA_COLUMNS = [
    "track_id",
    "track_name",
    "artists",
    "album_name",
    "genres",
    "popularity",
]

RAW_REQUIRED_COLUMNS = set(
    NUMERIC_FEATURES
    + ["key", "mode", "time_signature", "explicit"]
    + ["track_id", "track_name", "artists", "album_name", "track_genre"]
)

REQUIRED_COLUMNS = RAW_REQUIRED_COLUMNS
