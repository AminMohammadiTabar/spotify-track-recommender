# Spotify Track Recommender

A similarity-based music recommendation system using the **Spotify Tracks Dataset** and **Random Forest Leaf Proximity**.

> **Design Note:** Random Forest alone is not a traditional recommender algorithm. In this system, the model is trained on `track_genre`, and similarity between two songs is computed from the fraction of trees in which both tracks land in the same leaf node (Random Forest leaf proximity). This serves as a supervised metric learning baseline to be benchmarked against Unsupervised Nearest Neighbors / Cosine Similarity.

---

## Project Structure

```text
spotify_track_recommender/
├── data/
│   ├── raw/                 # Raw Kaggle CSV dataset (ignored in Git)
│   └── processed/           # Aggregated, deduplicated dataset (ignored in Git)
├── models/                  # Serialized models and leaf indices (ignored in Git)
├── notebooks/
│   └── 01_eda_template.ipynb
├── reports/                 # Analysis reports and figures (tracked in Git)
│   ├── feature_importance.md
│   ├── feature_importance.png
│   └── project_progress_report.md
├── src/
│   └── spotify_recommender/
│       ├── __init__.py
│       ├── config.py        # Configuration, paths, and feature definitions
│       ├── data.py          # Data downloading, cleaning, and multi-genre aggregation
│       ├── features.py      # Feature engineering and input validation
│       ├── model.py         # Pipeline setup and Random Forest leaf extraction
│       ├── recommender.py   # Similarity inference and recommendation engine
│       └── cli.py           # Command-Line Interface
├── tests/
│   └── test_features.py     # Automated unit tests
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

## 2. Dataset Setup & Preprocessing

### Download Dataset
Configure your Kaggle credentials, then run:

```bash
python -m spotify_recommender.cli download
# or: make download
```

Dataset source: `maharshipandya/-spotify-tracks-dataset`.  
The file is saved under `data/raw/` (automatically resolves `spotify_tracks.csv` or `dataset.csv`).

### Data Preparation & Lossless Multi-Genre Aggregation
Clean corrupted rows, extract the `is_remastered` feature, and aggregate multi-genre tracks by unique `track_id`:

```bash
python -m spotify_recommender.cli prepare
# or: make prepare
```

This generates `data/processed/tracks_aggregated.csv` containing **89,740 unique tracks** without data leakage or genre loss.

### Inspect Dataset
View dataset summary, genre distributions, and cleaning statistics:

```bash
python -m spotify_recommender.cli inspect
# or: make inspect
```

---

## 3. Analysis & Reports

Detailed technical documentation and analytical reports are tracked in `reports/`:

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
* **Target / Grouping Labels:** `track_genre` / `genres`

Identifiers, artist names, album titles, and popularity are strictly excluded from the model feature matrix to prevent data leakage and popularity bias.

---

## Running Tests

Run the automated test suite with pytest:

```bash
pytest
# or: make test
```


