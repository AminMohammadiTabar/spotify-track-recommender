from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import make_pipeline

from .config import (
    CATEGORICAL_FEATURES,
    FEATURE_COLUMNS,
    METADATA_COLUMNS,
    MODEL_PATH,
    NUMERIC_FEATURES,
)
from .data import load_tracks
from .features import build_feature_frame, validate_training_frame


def build_pipeline() -> Pipeline:
    """Create preprocessing + Random Forest genre classifier."""
    numeric_pipeline = make_pipeline(
        SimpleImputer(strategy="median")
    )
    categorical_pipeline = make_pipeline(
        SimpleImputer(strategy="most_frequent"),
        OneHotEncoder(handle_unknown="ignore"),
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, NUMERIC_FEATURES),
            ("categorical", categorical_pipeline, CATEGORICAL_FEATURES),
        ],
        remainder="drop",
    )

    forest = RandomForestClassifier(
        n_estimators=250,
        max_features="sqrt",
        max_depth=24,
        min_samples_leaf=2,
        class_weight="balanced_subsample",
        n_jobs=-1,
        random_state=42,
    )

    return Pipeline([
        ("preprocessor", preprocessor),
        ("forest", forest),
    ])


def train_and_save(
    data_path: Path,
    model_path: Path = MODEL_PATH,
) -> dict:
    """Evaluate on a holdout split, refit on all rows, and save RF proximities."""
    df = validate_training_frame(load_tracks(data_path))
    X = build_feature_frame(df)
    y = df["track_genre"].astype(str)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
        stratify=y,
    )

    evaluation_model = build_pipeline()
    evaluation_model.fit(X_train, y_train)
    predictions = evaluation_model.predict(X_test)

    metrics = {
        "holdout_accuracy": float(accuracy_score(y_test, predictions)),
        "holdout_macro_f1": float(f1_score(
            y_test, predictions, average="macro", zero_division=0
        )),
        "holdout_weighted_f1": float(f1_score(
            y_test, predictions, average="weighted", zero_division=0
        )),
        "n_tracks": int(len(df)),
        "n_genres": int(y.nunique()),
    }

    # Fit the final recommender on all available tracks.
    final_model = build_pipeline()
    final_model.fit(X, y)

    transformed_X = final_model.named_steps["preprocessor"].transform(X)
    leaf_indices = final_model.named_steps["forest"].apply(transformed_X)

    metadata_columns = [c for c in METADATA_COLUMNS if c in df.columns]
    tracks = df[metadata_columns].copy().reset_index(drop=True)

    artifact = {
        "pipeline": final_model,
        "leaf_indices": np.asarray(leaf_indices, dtype=np.int32),
        "tracks": tracks,
        "feature_columns": FEATURE_COLUMNS,
        "method": "random_forest_leaf_proximity",
    }

    model_path = Path(model_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, model_path, compress=3)

    metrics["model_path"] = str(model_path)
    metrics["n_trees"] = int(final_model.named_steps["forest"].n_estimators)
    return metrics
