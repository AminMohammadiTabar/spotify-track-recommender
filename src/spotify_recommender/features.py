import pandas as pd

from .config import CATEGORICAL_FEATURES, FEATURE_COLUMNS, NUMERIC_FEATURES


def build_feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Return model inputs only; never include IDs, names, or target genre."""
    df_copy = df.copy()

    # Automatically compute is_remastered if not already present
    if "is_remastered" not in df_copy.columns:
        if "track_name" in df_copy.columns and "album_name" in df_copy.columns:
            remaster_pattern = r"(?i)\bremaster(?:ed)?\b"
            name_match = df_copy["track_name"].fillna("").str.contains(remaster_pattern, regex=True)
            album_match = df_copy["album_name"].fillna("").str.contains(remaster_pattern, regex=True)
            df_copy["is_remastered"] = (name_match | album_match).astype(int)
        else:
            df_copy["is_remastered"] = 0

    missing = [column for column in FEATURE_COLUMNS if column not in df_copy.columns]
    if missing:
        raise ValueError(f"Missing required feature columns: {missing}")

    X = df_copy[FEATURE_COLUMNS].copy()

    for column in NUMERIC_FEATURES:
        X[column] = pd.to_numeric(X[column], errors="coerce")

    # Keep categorical values categorical. The imputer/encoder handles nulls.
    for column in CATEGORICAL_FEATURES:
        X[column] = X[column].astype("object")

    return X


def validate_training_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows without target genre labels and reset row positions consistently."""
    if "genres" in df.columns:
        clean = df[df["genres"].apply(lambda g: isinstance(g, (list, tuple, set)) and len(g) > 0)].copy()
    elif "track_genre" in df.columns:
        clean = df.dropna(subset=["track_genre"]).copy()
    else:
        raise ValueError("At least one target column ('track_genre' or 'genres') is required for training.")

    if clean.empty:
        raise ValueError("No valid rows remaining after filtering out missing genres.")

    return clean.reset_index(drop=True)
