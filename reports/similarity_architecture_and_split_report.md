# Spotify Track Recommender — Similarity Architecture & Data Split Report

**Date:** November 2026  
**Status:** Feature Architecture V1 Finalized · Train / Validation / Test Split Complete  
**Artifact Location:** `reports/similarity_architecture_and_split_report.md`  

---

## 1. Executive Summary

This report documents the second engineering phase of the **Spotify Track Recommender**: redefining the product goal, designing the multi-dimensional similarity architecture, and producing a leakage-safe Train / Validation / Test split of the normalized catalog.

### Key Outcomes:
1. **Scope Reset:** The previous model implementation (Random Forest leaf proximity pipeline, its preprocessing, evaluation, and serialization) is retired. It imposes no constraints on the new design. The preprocessing layer (`data.py`, `normalization.py`) is retained as the data foundation.
2. **Product Goal:** Given a song, return the **10 most similar tracks**, where the user chooses *which aspects* of similarity matter (mood, rhythm, genre, …). Target is perceptual / musical similarity, not minimal raw numeric distance.
3. **Feature Architecture V1:** Five independent **Similarity Dimensions** (Mood, Acoustic, Rhythm, Harmonic, Genre), each feature assigned to **exactly one** dimension. Content and metadata columns (`explicit`, `is_remastered`, `artists`, `popularity`, `duration_ms`) are separated into **Filters & Metadata** and never contribute to a similarity score. Encoded and validated in `src/spotify_recommender/feature_schema.py`.
4. **Score Combination:** Weighted average over the user-selected dimensions. **V1 uses equal weights** (e.g., 3 dimensions → 33.3% each); later versions expose per-dimension sliders.
5. **Data Split:** A **group-aware multi-label stratified** split (70 / 15 / 15) over **89,740 tracks** in **81,205 song groups**. Zero group leakage, all **114 genres present in every split**, mean per-genre share deviation **0.07%**.
6. **Open Finding:** **188 audio-identical clusters (520 tracks, 0.58%)** still cross split boundaries because their titles differ (translated soundtrack titles, white-noise re-uploads). An audio-aware group extension is proposed (Section 7).

---

## 2. Product Goal & Design Principles

### A) Goal
The user names a song; the system recommends the top-10 most similar tracks. Similarity is **multi-aspect**: two songs can be very close in one dimension and far apart in another. A track that matches strongly on a single selected aspect can be a valid recommendation.

### B) Design Principles

| Principle | Rationale |
| :--- | :--- |
| One feature → one dimension | Prevents double counting when several dimensions are selected. |
| Dimensions are pluggable engines | Each dimension scores the catalog independently; new dimensions are added without touching others. |
| Filters ≠ similarity | Filters narrow **candidate selection**; they never change a **similarity score**. |
| Comparable score scales | Weights only mean what the slider says if every dimension scores on the same scale (see Section 4). |
| Train-only data decisions | Any data-driven decision (feature removal, transforms, learned similarities) is made on the training split only. Test stays untouched until final evaluation. |

---

## 3. Feature Architecture — V1

### A) Similarity Dimensions

| Dimension | Features | Captures |
| :--- | :--- | :--- |
| **Mood** | `energy`, `loudness`, `valence` | Emotional feel and intensity |
| **Acoustic** | `acousticness`, `instrumentalness`, `liveness`, `speechiness` | Timbre and sonic texture |
| **Rhythm** | `tempo`, `danceability`, `time_signature` | Pulse, groove, and meter |
| **Harmonic** | `key`, `mode` | Tonal center and major / minor modality |
| **Genre** | `genres` | Shared or closely related genres |

> **Note:** This categorization is a **design hypothesis** grounded in domain knowledge. It is revisited after the correlation analysis on the training split (Section 8).

### B) Statistical Feature Types

The type of each feature determines which correlation method and encoding apply downstream.

| Type | Features | Correlation Method |
| :--- | :--- | :--- |
| Numeric | `energy`, `loudness`, `valence`, `acousticness`, `instrumentalness`, `liveness`, `speechiness`, `tempo`, `danceability` | Spearman (primary, robust to skew) and Pearson |
| Categorical | `time_signature`, `key`, `mode` | Cramér's V (categorical–categorical), correlation ratio η (categorical–numeric) |
| Multi-label | `genres` | Set-based (overlap / co-occurrence) |

* **`key`** is a circular pitch class (11 is adjacent to 0). It must never be treated as ordinal or used in Pearson / Spearman.
* **`time_signature`** is a meter category (`0` = unmetered ambient), not a magnitude.

### C) Additional Filters & Metadata

| Column | Role | Notes |
| :--- | :--- | :--- |
| `explicit` | Filter | All tracks · Clean only · Explicit only |
| `is_remastered` | Filter | All versions · Remastered only · Non-remastered only. Regex-derived, so detection errors are possible. |
| `artists` | Metadata / Filter | Restrict to or exclude specific artists. Same artist ≠ same artistic style. |
| `popularity` | Metadata / Optional Ranking | Controls popularity range; not a measure of musical similarity. |
| `duration_ms` | Metadata only | Excluded from similarity by design decision. |
| `version_tag` | Metadata (proposed) | Candidate for a future version filter (e.g., exclude live versions). |

### D) Enforcement in Code

`feature_schema.py` is the single source of truth. `validate_schema()` runs at import time and raises if:
* a feature appears in more than one dimension,
* a filter, ranking, or metadata column is used inside a dimension,
* a dimension feature has no declared statistical type.

---

## 4. Score Combination Strategy

$$\text{score}(q, c) = \sum_{i \in \text{selected}} w_i \cdot s_i(q, c), \qquad \sum_i w_i = 1$$

| Version | Weights | Example (Rhythm + Genre + Mood) |
| :--- | :--- | :--- |
| **V1** | Equal: $w_i = 1/n$ | 33.3% · 33.3% · 33.3% |
| **Later** | Per-dimension sliders, normalized to 100% | Genre 70% · Mood 20% · Rhythm 10% |

* **Scale requirement:** Each dimension score $s_i$ is converted to a **percentile** over the catalog ("closer than X% of all tracks"). Without this, a dimension with naturally wide score spread would dominate even under equal weights.
* **Explainability:** The per-dimension contribution $w_i \cdot s_i$ provides a "reason for similarity" for each recommendation.
* **Post-processing:** Alternate releases of the same song (same title + artist group, including the query's own group) must be collapsed in the final top-10.

---

## 5. Train / Validation / Test Split

### A) Method: Group-Aware Multi-Label Stratification

| Constraint | Why |
| :--- | :--- |
| **Group-aware** | Alternate releases of one song often have identical audio. Placing them in different splits leaks test information into training. |
| **Multi-label stratified** | 16,299 tracks carry multiple genres. Every genre, including rare ones, must keep the same share in each split. |

* **Group key:** normalized `track_name` + normalized `artists` (NFKC, casefold, whitespace collapse via `normalize_text`).
* **Algorithm:** Iterative stratification (Sechidis et al., 2011) applied at group level. Each group carries the summed genre counts of its tracks; labels are processed from rarest to most common, and each group goes to the split with the largest remaining demand for that label (ties: remaining capacity, then a seeded random draw).
* **Parameters:** ratios 70 / 15 / 15, `seed = 42` (fully reproducible).

### B) Group Structure

| Metric | Value |
| :--- | :---: |
| Total tracks | **89,740** |
| Total groups | **81,205** |
| Multi-track groups | **4,748** (13,283 tracks) |
| Largest group | 45 tracks (*Rockin' Around the Christmas Tree* — Brenda Lee) |

### C) Split Sizes

| Split | Tracks | Groups | Track Share | Group Share |
| :--- | :---: | :---: | :---: | :---: |
| **Train** | 62,734 | 56,742 | 69.91% | 69.88% |
| **Validation** | 13,514 | 12,213 | 15.06% | 15.04% |
| **Test** | 13,492 | 12,250 | 15.03% | 15.09% |

### D) Genre Balance

| Metric | Value |
| :--- | :---: |
| Genres missing from any split | **0 / 114** |
| Mean per-genre share deviation | **0.07%** |
| Max per-genre share deviation | **1.48%** (`dance`) |

Worst-balanced genres:

| Genre | Train | Validation | Test | Total | Max Deviation |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `dance` | 69.2% | 14.3% | 16.5% | 965 | 1.5% |
| `blues` | 70.9% | 14.5% | 14.5% | 998 | 0.9% |
| `synth-pop` | 69.8% | 14.7% | 15.5% | 1,000 | 0.5% |
| `country` | 69.9% | 15.4% | 14.7% | 1,000 | 0.4% |
| `latin` | 69.8% | 15.4% | 14.8% | 990 | 0.4% |

---

## 6. Verification

| Check | Method | Result |
| :--- | :--- | :---: |
| Group leakage (built-in) | `split_tracks()` raises if any group spans more than one split | Pass |
| Group leakage (independent) | Re-read `split_assignments.csv`, count groups with > 1 split | **0** — Pass |
| Coverage | Every `track_id` in `tracks_normalized.csv` assigned exactly once | Pass |
| Genre presence | All 114 genres present in train, validation, and test | Pass |
| Determinism | Same seed → identical assignment (unit test) | Pass |
| Scale benchmark | Simulated 89,740 tracks / 114 genres | 1.2 s, 0 leaks |
| Audio-identical leakage | Identical similarity-feature vectors across splits | **188 clusters / 520 tracks** — see Section 7 |

---

## 7. Residual Leakage: Audio-Identical Tracks with Different Titles

Title + artist grouping cannot catch identical recordings published under different names. **188 clusters (520 tracks, 0.58% of the catalog)** have identical similarity-feature vectors (all 12 audio features, compared at 6 decimals) but span more than one split. 77% of these clusters share a single artist string.

| Pattern | Example | Splits |
| :--- | :--- | :--- |
| Translated soundtrack titles | *El río* / *Der Fluss* — Germaine Franco | Train / Test |
| Translated soundtrack titles | *Tenacious Mirabel* / *Nieustępliwa Mirabel* — Germaine Franco | Validation / Train |
| White-noise re-uploads | *Air Conditioner - Loopable With No Fade* (4 artist / title variants) | Train / Validation |
| Ambient re-uploads | *Rough Day* (Rain Sounds) / *Bedtime* (Baby Sound Library XL) | Train / Validation |

**Proposed fix (pending decision):** extend groups with a union-find pass that merges any two title + artist groups sharing an identical audio vector. This changes the agreed group definition, so it requires approval before implementation.

---

## 8. Engineering Summary

### A) New Modules & Tests

| File | Purpose |
| :--- | :--- |
| `src/spotify_recommender/feature_schema.py` | Feature Architecture V1, feature types, filters / metadata, schema validation |
| `src/spotify_recommender/split.py` | Group-aware multi-label split, leakage check, size and genre reports, CLI entry point |
| `tests/test_feature_schema.py` | 6 tests: dimension contents, single ownership, filter isolation, type routing |
| `tests/test_split.py` | 8 tests: no leakage, ratio adherence, per-label balance, determinism, DataFrame layer |

Full suite: **25 tests passed**.

### B) Environment

* Python **3.13** virtual environment (`.venv`, not tracked).
* pandas 3.1.1 · numpy 2.5.4 · scikit-learn 1.9.1 · pytest 9.2.0.

### C) Reproduction

```bash
python -m spotify_recommender.cli prepare     # data/raw/dataset.csv -> tracks_aggregated.csv
python -m spotify_recommender.cli normalize   # -> tracks_normalized.csv
python -m spotify_recommender.split           # -> split_assignments.csv, split_genre_distribution.csv
pytest
```

### D) Tracked Data Artifacts

The following processed files are now tracked in Git so work can continue on other machines (raw data remains ignored):

| File | Size | Content |
| :--- | :---: | :--- |
| `data/processed/tracks_aggregated.csv` | 17 MB | One row per `track_id`, multi-genre aggregated |
| `data/processed/tracks_normalized.csv` | 20 MB | Normalized genres and version tags |
| `data/processed/split_assignments.csv` | 6 MB | `track_id`, `group_id`, `split` |
| `data/processed/split_genre_distribution.csv` | 10 KB | Per-genre counts and shares by split |

---

## 9. Next Milestone Roadmap

| Step | Activity | Data |
| :---: | :--- | :--- |
| 0 | Decide on audio-aware group extension (Section 7) and re-run the split if approved | All |
| 1 | Within-dimension correlation analysis | Train |
| 2 | Between-dimension correlation analysis | Train |
| 3 | Redundancy review and feature decisions (no feature is dropped on correlation alone) | Train |
| 4 | Encoding and dimension-specific preprocessing (e.g., tempo half / double-time handling, quantile transforms for skewed features) | Fit on Train |
| 5 | Similarity engines per dimension + percentile normalization + weighted combiner | Fit on Train |
| 6 | Dimension-score correlation (relative independence of engines) | Validation |
| 7 | Output deduplication of alternate releases; filters | — |
| 8 | Final evaluation | Test |
