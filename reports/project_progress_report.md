# Spotify Track Recommender — Project Progress & Engineering Report

**Date:** November 2026  
**Status:** Preprocessing, Validation & Feature Engineering Complete  
**Artifact Location:** `reports/project_progress_report.md`  

---

## 1. Executive Summary

This report documents the architectural and data engineering milestones completed for the **Spotify Track Recommender** project. The system is designed to provide top-$k$ similar music recommendations using **Random Forest Leaf Proximity** as a supervised metric learning baseline, benchmarked against unsupervised distance metrics.

All preliminary stages—from raw data profiling and data cleaning to feature engineering, domain validation, multi-genre lossless aggregation, and feature importance extraction—have been executed with automated test coverage and professional engineering hygiene.

---

## 2. Dataset Profiling & Initial Inspection

* **Raw Data Source:** Kaggle (`maharshipandya/-spotify-tracks-dataset`)
* **Raw Dimensions:** 114,000 rows × 21 columns (~20 MB)
* **Initial Genre Distribution:** Exactly 114 distinct genres, perfectly balanced with 1,000 records per genre.
* **Feature Schema:**
  * 10 continuous audio features (`danceability`, `energy`, `loudness`, `speechiness`, `acousticness`, `instrumentalness`, `liveness`, `valence`, `tempo`, `duration_ms`)
  * 4 original categorical features (`key`, `mode`, `time_signature`, `explicit`)
  * Metadata & Identifiers (`track_id`, `artists`, `album_name`, `track_name`, `popularity`)
  * Target Label (`track_genre`)

---

## 3. Data Cleaning & Integrity Audits

### A) Missing Values (Explicit & Implicit)
* **Explicit `NaN`s:** In the entire 114,000-row dataset, only **one single record** (index `65900`, `track_id: 1kR4gIb7nGxHPI3D2ifs59`) had missing values (`artists`, `album_name`, and `track_name` were null).
* **Corrupted Durations:** The exact same row was also the only track with `duration_ms == 0`.
* **Action:** Pruned this corrupted record in `load_tracks()`. Clean baseline: 113,999 rows.

### B) Investigation of Zero-Tempo & Zero-Danceability
* **Observation:** Exactly 157 tracks had both `tempo == 0` and `danceability == 0`.
* **Domain Investigation:** 138 of these tracks belonged to the `sleep` genre (white noise, rain sounds, soundscapes) with the rest in unmetered ambient and vocal intro recordings.
* **Conclusion:** These represent genuine acoustic characteristics of non-pulsed audio, not system errors or missing data.

---

## 4. Multi-Layer Duplicate Analysis & Resolution

The dataset exhibited duplicate entries across three distinct dimensions:

```text
114,000 Raw Tracks
├── Layer 1: 100% Exact Duplicates (Same track_id & identical genre): 450 rows
├── Layer 2: Cross-Genre Duplicate Track IDs (Same track in multiple genres): 24,259 rows
└── Layer 3: Title + Artist Duplicates (Alternate releases / remasters): 32,656 rows
```

* **Resolution for Layer 1:** Pruned the 450 redundant duplicate rows via `drop_duplicates()`, reducing valid raw rows to **113,549**.
* **Resolution for Layer 2 (Lossless Aggregation):** Rather than arbitrarily discarding genres or suffering from data leakage, tracks were aggregated by unique `track_id`.

---

## 5. Feature Engineering: `is_remastered`

To capture historical vintage signal and explain mastering dynamic compression (loudness wars) without an explicit release year column:
* **Detection Mechanism:** Built regex pattern `(?i)\bremaster(?:ed)?\b` applied against `track_name` and `album_name`.
* **Output:** Engineered categorical binary feature `is_remastered` (`1` or `0`).
* **Yield:** Identified **1,601 unique remastered tracks** in the deduplicated pool.

---

## 6. Lossless Multi-Genre Aggregation Pipeline

Implemented `prepare_aggregated_tracks()` in `src/spotify_recommender/data.py`:
1. Grouped the dataset by unique `track_id`.
2. Preserved identical audio features using `first`.
3. Kept the maximum popularity score across duplicate rows (`max`).
4. Aggregated all associated genres into a sorted unique list (`genres`) and formatted string (`genres_str`).

### Pipeline Output:
* **Unique Track Count:** **89,740 unique tracks** (exactly 1 row per physical song).
* **Multi-Genre Songs:** **16,299 tracks** now retain their complete multi-genre identity (e.g., `['rock', 'alt-rock', 'indie']`).
* **Stored Processed Dataset:** Exported to `data/processed/tracks_aggregated.csv`.
* **Data Leakage Prevention:** Completely eliminates sample contamination between Train and Test splits.

---

## 7. Comprehensive Domain & Range Validation

All 89,740 unique tracks were evaluated against official Spotify Web API specifications:

| Feature | Standard Allowed Range | Dataset Range | Validation Status |
| :--- | :---: | :---: | :---: |
| `popularity` | $[0, 100]$ | $0$ to $100$ (median: $33.0$) | Pass |
| `duration_ms` | $> 0$ | $8,586$ to $5,237,295$ ms | Pass |
| `danceability` | $[0.0, 1.0]$ | $0.0$ to $0.985$ | Pass |
| `energy` | $[0.0, 1.0]$ | $0.0$ to $1.0$ | Pass |
| `loudness` | Typically $[-60, 0]$ dB | $-49.53$ to $+4.53$ dB | Pass (68 heavily limited/clipped modern EDM/Funk tracks) |
| `speechiness` | $[0.0, 1.0]$ | $0.0$ to $0.965$ | Pass |
| `acousticness` | $[0.0, 1.0]$ | $0.0$ to $0.996$ | Pass |
| `instrumentalness` | $[0.0, 1.0]$ | $0.0$ to $1.0$ | Pass |
| `liveness` | $[0.0, 1.0]$ | $0.0$ to $1.0$ | Pass |
| `valence` | $[0.0, 1.0]$ | $0.0$ to $0.995$ | Pass |
| `tempo` | $\ge 0$ | $0.0$ to $243.37$ BPM | Pass |
| `key` | $[0, 11]$ | $0$ to $11$ (12 pitch classes) | Pass |
| `mode` | $\{0, 1\}$ | $\{0, 1\}$ (Major / Minor) | Pass |
| `explicit` | $\{0, 1\}$ | $\{0, 1\}$ | Pass |
| `is_remastered` | $\{0, 1\}$ | $\{0, 1\}$ | Pass |
| `track_id` | 22 alphanumeric chars | Exactly 22 chars for 100% of tracks | Pass |
| `time_signature` | Typically $3$ to $5$ | $0$ to $5$ (162 unmetered ambient tracks with $0$) | Pass |

---

## 8. Feature Importance Analysis (Empirical Evidence)

A 100-tree Random Forest Classifier was trained across 114 genres to extract Gini feature importances. Categorical one-hot encoded dummy variables were aggregated back to their parent features:

```text
Feature Importance Ranking:
1.  duration_ms       :  9.75%
2.  acousticness      :  9.50%
3.  danceability      :  9.20%
4.  valence           :  9.02%
5.  speechiness       :  9.01%
6.  tempo             :  8.93%
7.  loudness          :  8.68%
8.  energy            :  8.44%
9.  key (12 pitches)  :  7.89%
10. instrumentalness  :  7.49%
11. liveness          :  7.31%
12. mode              :  2.07%
13. time_signature    :  1.37%
14. explicit          :  0.88%
15. is_remastered     :  0.45%
```

* **Visual Plot:** Generated at `reports/feature_importance.png`.
* **Full Documentation:** Documented at `reports/feature_importance.md`.
* **Verdict:** The top 11 features exhibit an extraordinarily balanced contribution ($7.3\% - 9.75\%$). No feature has near-zero importance. **Retaining all 15 features is optimal** for leaf proximity resolution.

---

## 9. Codebase Modernization & Clean Code Compliance

* **Unified Language:** 100% of code, comments, docstrings (PEP 257), and error messages standardized to English.
* **CLI Additions:** Added `prepare` command and enriched `inspect` command in `src/spotify_recommender/cli.py`.
* **Makefile Integration:** Added `prepare` and `inspect` recipes.
* **Git Hygiene:** Cleaned `.gitignore` so analytical reports in `reports/` are tracked while raw data and binaries remain safely ignored.
* **Test Automation:** Added automated unit tests covering remaster detection, multi-genre aggregation, and feature frame isolation in `tests/test_features.py` (all tests passing).

---

## 10. Next Milestone Roadmap

1. **Model Training & Artifact Generation:**
   * Fit full Random Forest model on the aggregated dataset.
   * Extract and serialize the leaf indices matrix to `models/random_forest_recommender.joblib`.
   * Record holdout classification metrics (Accuracy, Macro-F1).
2. **Unsupervised Baseline (Nearest Neighbors / Cosine Distance):**
   * Implement a standard TF/Cosine or Euclidean KNN baseline on standardized audio features for comparative evaluation.
3. **Inference & Recommendation Quality Audits:**
   * Run end-to-end recommendation queries across diverse genre seed tracks.
   * Assess recommendation relevance, diversity, and consistency.
