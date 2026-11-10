# Spotify Track Recommender

A similarity-based music recommendation system using the **Spotify Tracks Dataset** and **Random Forest Leaf Proximity**.

> **Design Note:** Random Forest alone is not a traditional recommender algorithm. In this system, the model is trained on `track_genre`, and similarity between two songs is computed from the fraction of trees in which both tracks land in the same leaf node (Random Forest leaf proximity). This serves as a supervised metric learning baseline to be benchmarked against Unsupervised Nearest Neighbors / Cosine Similarity.

---

## Project Structure

```text
spotify_track_recommender/
├── data/
│   ├── raw/                 # Raw Kaggle CSV dataset (ignored in Git)
│   └── processed/           # Processed datasets (ignored in Git)
│       ├── tracks_aggregated.csv  # Lossless multi-genre aggregated tracks
│       └── tracks_normalized.csv  # Text-normalized catalog with version tags
├── models/                  # Serialized models and leaf indices (ignored in Git)
├── notebooks/
│   └── 01_eda_template.ipynb
├── reports/                 # Analysis reports and figures (tracked in Git)
│   ├── duplicate_track_feature_analysis.md  # Deep dive on title+artist duplicates
│   ├── feature_importance.md                # RF Gini feature importance ranking
│   ├── feature_importance.png               # Visual plot of feature importances
│   └── project_progress_report.md           # Engineering progress & milestone report
├── src/
│   └── spotify_recommender/
│       ├── __init__.py
│       ├── config.py        # Configuration, paths, and feature definitions
│       ├── data.py          # Data downloading, cleaning, and multi-genre aggregation
│       ├── features.py      # Feature engineering and input validation
│       ├── normalization.py # NFKC unicode, casefold, genre deduplication, version tagging
│       ├── model.py         # Pipeline setup and Random Forest leaf extraction
│       ├── recommender.py   # Similarity inference and recommendation engine
│       └── cli.py           # Command-Line Interface
├── tests/
│   ├── test_features.py     # Unit tests for feature extraction and aggregation
│   └── test_normalization.py# Unit tests for text normalization and metadata preservation
├── .gitignore
├── Makefile
├── pyproject.toml
└── requirements.txt
```

---

## 1. Installation

Python 3.10+ is recommended.

```bash
# Create and activate virtual environment
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1

# Install dependencies and project in editable mode
pip install -r requirements.txt
pip install -e .
```

You can also use the `Makefile`:
```bash
make install
```

---

## 2. Dataset Setup & Preprocessing Pipeline

### Step A: Download Dataset
Configure your Kaggle credentials, then run:

```bash
python -m spotify_recommender.cli download
# or: make download
```

Dataset source: `maharshipandya/-spotify-tracks-dataset`.  
The file is saved under `data/raw/` (automatically resolves `spotify_tracks.csv` or `dataset.csv`).

### Step B: Lossless Multi-Genre Aggregation
Clean corrupted records, extract the `is_remastered` feature, and aggregate multi-genre tracks by unique `track_id`:

```bash
python -m spotify_recommender.cli prepare
# or: make prepare
```

This generates `data/processed/tracks_aggregated.csv` containing **89,740 unique tracks** without data leakage or genre loss.

### Step C: Categorical Text Normalization & Version Extraction
Apply Unicode NFKC normalization, casefolding (`casefold()`), whitespace collapsing, genre list deduplication, and version tag extraction while preserving original titles:

```bash
python -m spotify_recommender.cli normalize
# or: make normalize
```

This generates `data/processed/tracks_normalized.csv`:
* Preserves raw track, artist, and album names intact.
* Preserves raw genre strings in `genres_raw`.
* Stores deduplicated, sorted normalized genre lists in `genres` and `genres_str`.
* Derives `version_tag` (`original`, `live`, `remix`, `remaster`, `deluxe`, `radio_edit`, `acoustic`, `instrumental`, `demo`) and `version_tags`.

### Step D: Inspect Dataset
View dataset summary, genre distributions, and cleaning statistics:

```bash
python -m spotify_recommender.cli inspect
# or: make inspect
```

---

## 3. Analysis & Reports

Detailed technical documentation and analytical reports are tracked in `reports/`:

* **[Duplicate Track Feature Analysis](reports/duplicate_track_feature_analysis.md):** Comprehensive empirical analysis of 13,054 rows across 4,657 identical title + artist groups, multi-album root causes, duration variance distributions, acoustic divergence (live/acoustic/remix), and architectural recommendations against premature record merging.
* **[Engineering Progress Report](reports/project_progress_report.md):** Complete summary of dataset profiling, missing value audits, 3-layer duplicate resolution, domain bounds validation, and feature engineering.
* **[Feature Importance Analysis](reports/feature_importance.md):** Empirical Gini importance ranking and insights derived from 100 Random Forest decision trees across 114 genres.
* **[Feature Importance Chart](reports/feature_importance.png):** High-resolution horizontal bar chart visualizing the top discriminators.

---

## 4. Training the Model

Train the Random Forest classifier and extract leaf proximities:

```bash
python -m spotify_recommender.cli train
# or: make train
```

The model pipeline and leaf indices matrix are saved to `models/random_forest_recommender.joblib`.

---

## 5. Recommending Similar Tracks

Provide a Spotify `track_id` to retrieve the top $k$ most similar tracks:

```bash
python -m spotify_recommender.cli recommend --track-id "SPOTIFY_TRACK_ID" --top-k 10
```

---

## Feature Definitions

* **Continuous Audio Features (10):** `danceability`, `energy`, `loudness`, `speechiness`, `acousticness`, `instrumentalness`, `liveness`, `valence`, `tempo`, `duration_ms`
* **Categorical Features (5):** `key` (pitch class 0-11), `mode` (major/minor), `time_signature`, `explicit`, `is_remastered`
* **Metadata & Derived Tags:** `version_tag`, `version_tags`, `genres`, `genres_raw`
* **Target / Grouping Labels:** `track_genre` / `genres`

Identifiers, artist names, album titles, and popularity are strictly excluded from the model feature matrix to prevent data leakage and popularity bias.

---

## Running Tests

Run the automated test suite with pytest:

```bash
pytest
# or: make test
```
