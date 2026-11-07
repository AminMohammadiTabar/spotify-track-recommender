from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from .config import MODEL_PATH


def load_artifact(model_path: Path = MODEL_PATH) -> dict:
    model_path = Path(model_path)
    if not model_path.exists():
        raise FileNotFoundError(
            f"Trained model not found at: {model_path}. Please run 'train' command first."
        )
    return joblib.load(model_path)


def recommend_by_track_id(
    track_id: str,
    top_k: int = 10,
    model_path: Path = MODEL_PATH,
) -> pd.DataFrame:
    """Recommend tracks using the fraction of RF trees sharing the same leaf."""
    if top_k < 1:
        raise ValueError("top_k must be at least 1.")

    artifact = load_artifact(model_path)
    tracks = artifact["tracks"]
    leaf_indices = artifact["leaf_indices"]

    matches = np.flatnonzero(
        tracks["track_id"].astype(str).to_numpy() == str(track_id)
    )
    if len(matches) == 0:
        raise ValueError(
            f"track_id not found in dataset: {track_id}"
        )

    query_index = int(matches[0])
    query_leaves = leaf_indices[query_index]

    # Similarity = proportion of trees in which both tracks reach the same leaf.
    scores = np.mean(leaf_indices == query_leaves, axis=1, dtype=np.float32)

    # Exclude every row with the same Spotify track ID (not just the query row).
    same_track = tracks["track_id"].astype(str).to_numpy() == str(track_id)
    scores[same_track] = -1.0

    candidate_indices = np.argsort(scores)[::-1]
    candidate_indices = [
        int(index) for index in candidate_indices
        if scores[index] >= 0
    ][:top_k]

    results = tracks.iloc[candidate_indices].copy()
    results.insert(0, "similarity_score", scores[candidate_indices])
    return results.reset_index(drop=True)
