# Spotify Track Recommender — Feature Architecture & Data Split Report

**Date:** November 2026  
**Status:** Feature Architecture (V1) Finalized · Train / Validation / Test Split Complete  
**Artifact Location:** `reports/feature_architecture_and_split_report.md`  

---

## 1. Executive Summary

This report documents the second engineering milestone of the **Spotify Track Recommender**. It covers the redefinition of the product goal, the new multi-dimensional feature architecture, and the leakage-safe Train / Validation / Test split.

Key outcomes:

1. **Model redesign from scratch.** All previous model and pipeline code (`build_pipeline()`, `train_and_save()`, the Random Forest configuration, `SimpleImputer`, `OneHotEncoder`, the `ColumnTransformer` layout, evaluation metrics, and the model save/load format) is discarded and places no constraints on the new design.
2. **Product goal redefined.** The system is a **multi-aspect similarity recommender**, not a genre classifier: given a song, it returns the 10 most similar tracks along the musical dimensions the user selects.
3. **Feature architecture V1 finalized.** The 5 similarity dimensions are kept strictly separate from filters and metadata. No feature contributes to more than one dimension. The architecture is encoded in `src/spotify_recommender/feature_schema.py` and validated automatically.
4. **Leakage-safe split produced.** A **group-aware multi-label stratified** split assigned **89,740 tracks** in **81,205 groups** to Train / Validation / Test (69.9% / 15.1% / 15.0%):
   * no group shared between splits;
   * all 114 genres present in every split;
   * mean per-genre share deviation of **0.07%**.
5. **Reproducible environment.** A Python 3.13 virtual environment was set up. All **25 automated tests pass**.

---

## 2. Product Goal & Design Principles

### A) Goal
The user names a song and receives the **top-10 most similar tracks**. Similarity is computed along one or more user-selected **similarity dimensions** (e.g. mood, rhythm, genre).

### B) Design Principles
* **Perceptual over numeric similarity.** The goal is the highest *perceived musical* similarity, not the smallest raw feature distance. Two tracks can be very similar on one dimension and completely different on another.
* **Weighted combination of dimensions.**

  $$\text{score}(q, c) = \sum_{i \in \text{selected}} w_i \cdot s_i(q, c), \qquad \sum_i w_i = 1$$

  * **V1:** equal weights. For example, Rhythm + Genre + Mood get 33% each.
  * **Later versions:** per-dimension weights set with sliders in a UI panel, e.g. Genre 70%, Mood 20%, Rhythm 10%. The API will accept weights from V1 onward, so the sliders only require UI work.
* **Comparable score scales.** Dimension scores must share one scale; otherwise equal weights are not truly equal. The planned approach is a percentile transform of each dimension's score.
* **Explainability.** Each recommendation can report which dimension contributed most, using its share $w_i \cdot s_i$ of the final score.

---

## 3. Feature Architecture — V1

### A) Similarity Dimensions

| Dimension | Features | Musical Meaning |
| :--- | :--- | :--- |
| **Mood** | `energy`, `loudness`, `valence` | Emotional feel and intensity |
| **Acoustic** | `acousticness`, `instrumentalness`, `liveness`, `speechiness` | Timbre and sonic texture |
| **Rhythm** | `tempo`, `danceability`, `time_signature` | Pulse, groove, and meter |
| **Harmonic** | `key`, `mode` | Tonal center and major/minor modality |
| **Genre** | `genres` | Shared or closely related genres |

Each feature belongs to **exactly one** dimension. This prevents double counting: in the earlier draft, `energy` and `acousticness` each appeared in two dimensions.

### B) Filters, Ranking & Metadata

These columns **never** contribute to the similarity score. Filters act on **candidate selection** only.

| Column | Role | Notes |
| :--- | :--- | :--- |
| `explicit` | Filter | All / Clean only / Explicit only |
| `is_remastered` | Filter | All / Remastered only / Non-remastered only. Regex-based detection, so some misclassification is possible. |
| `artists` | Filter + Metadata | Restrict to, or exclude, specific artists. Same artist ≠ same style. |
| `popularity` | Optional Ranking + Metadata | Not a musical similarity signal |
| `duration_ms` | Metadata only | Excluded from similarity by design decision |

Artist and Popularity were deliberately **not** made similarity dimensions:
* A shared artist identity does not imply a shared musical style.
* Popularity does not measure musical similarity.

### C) Statistical Feature Types

Each feature carries a `FeatureKind`, which later selects the correct correlation method:

| Kind | Features | Correlation Method |
| :--- | :--- | :--- |
| `NUMERIC` | 9 continuous audio features | Spearman (primary, robust to skew) and Pearson |
| `CATEGORICAL` | `key`, `mode`, `time_signature` | Cramér's V; correlation ratio (η) against numeric features |
| `MULTI_LABEL` | `genres` | Set-based measures |

`key` is a **circular** pitch class (11 is adjacent to 0). It must never be treated as ordinal or used in Pearson correlation.

### D) Implementation

`src/spotify_recommender/feature_schema.py` is the single source of truth for the architecture. `validate_schema()` runs on import and fails fast in two cases:
* a feature is assigned to two dimensions;
* a filter, ranking, or metadata column leaks into a dimension.

---

## 4. Train / Validation / Test Split

### A) Requirements
1. **Group-aware.** Alternate releases of the same song (same normalized title + artists, different `track_id`) frequently share identical audio. They must land in the **same** split; otherwise test tracks are effectively seen during training.
2. **Multi-label stratified.** 16,299 tracks carry several genres. Every genre, including the rarest, should keep the target share in every split.

### B) Method
* **Group key:** `normalize_text(track_name) + " || " + normalize_text(artists)`. This uses NFKC, casefold, and whitespace collapsing, so case and spacing variants share one group.
* **Algorithm:** iterative stratification (Sechidis et al., 2011) applied at group level:
  * Each group carries the summed genre counts of its tracks.
  * Genres are processed from rarest to most common.
  * Each unassigned group holding the current genre goes to the split with the largest remaining demand for that genre. Ties go to the split with the most remaining capacity, then to a seeded random draw.
* **Ratios:** 70 / 15 / 15. **Seed:** 42, which makes the split fully reproducible.
* **Fail-safe:** `split_tracks()` raises an error if any group spans more than one split.

### C) Group Structure

| Metric | Value |
| :--- | :---: |
| Total tracks | 89,740 |
| Total groups | 81,205 |
| Multi-track groups | 4,748 |
| Tracks in multi-track groups | 13,283 |
| Largest group | 45 tracks ("Rockin' Around The Christmas Tree" — Brenda Lee) |

The duplicate analysis report counted 4,657 groups using exact matching. Normalization raises this to 4,748, because it additionally merges case and whitespace variants of the same title.

### D) Split Results

| Split | Tracks | Groups | Track Share | Group Share |
| :--- | :---: | :---: | :---: | :---: |
| **Train** | 62,734 | 56,742 | 69.91% | 69.88% |
| **Validation** | 13,514 | 12,213 | 15.06% | 15.04% |
| **Test** | 13,492 | 12,250 | 15.03% | 15.09% |

### E) Verification Checklist

| Check | Result | Status |
| :--- | :--- | :---: |
| Every track assigned exactly once | 89,740 / 89,740 | Pass |
| No group shared between splits | 0 leaked groups (verified in code and independently on the saved CSV) | Pass |
| All genres present in every split | 114 / 114 | Pass |
| Per-genre share deviation | Mean 0.07%, median 0.03%; above 0.5%: 3 genres; above 1%: 1 genre | Pass |
| Worst-balanced genre | `dance`: test share 16.5% vs 15% target (1.5 pp) | Acceptable |
| Smallest genre | `romance` (904 tracks): 633 / 135 / 136 | Pass |

### F) Residual Finding: Audio-Identical Tracks Across Splits

An independent audit grouped tracks by their **exact** audio feature vector. It found **188 audio-identical clusters (520 tracks, ≈0.6%)** spanning more than one split. The title-based group key cannot catch these, because the titles differ:

* **Translated titles of the same recording**, e.g. Encanto score cues: "El río" (train) vs "Der Fluss" (test); "Tenacious Mirabel" vs "Nieustępliwa Mirabel".
* **Re-uploaded white noise / sleep sounds** under different titles or artist names.

**Proposed fix (pending decision):** extend grouping with union-find so that any two groups sharing an identical audio vector merge into one group before splitting.

---

## 5. Environment & Reproducibility

### A) Environment
* Virtual environment: `.venv`, Python **3.13**. The system default, 3.15, was avoided because of package wheel availability.
* Installed: pandas 3.1, numpy 2.5, scikit-learn 1.9, scipy 1.18, pytest 9.2, plus the project in editable mode.

### B) Pipeline Commands

```bash
python -m spotify_recommender.cli prepare     # raw -> tracks_aggregated.csv
python -m spotify_recommender.cli normalize   # -> tracks_normalized.csv
python -m spotify_recommender.split           # -> split_assignments.csv + genre report
pytest                                        # 25 tests
```

Regenerating the processed data reproduced the earlier reports exactly: 89,740 tracks, 16,299 multi-genre tracks, 1,601 remastered tracks.

### C) Tracked Artifacts

So that work can continue on other machines, these processed files are tracked in Git (exceptions added to `.gitignore`):

| File | Size | Content |
| :--- | :---: | :--- |
| `data/processed/tracks_aggregated.csv` | 17 MB | One row per `track_id`, multi-genre lists |
| `data/processed/tracks_normalized.csv` | 20 MB | Normalized genres + version tags |
| `data/processed/split_assignments.csv` | 6 MB | `track_id`, `group_id`, `split` |
| `data/processed/split_genre_distribution.csv` | 10 KB | Per-genre counts, shares, and deviations |

The raw dataset (`data/raw/dataset.csv`) and the virtual environment remain untracked.

### D) New Code & Tests

| File | Purpose |
| :--- | :--- |
| `src/spotify_recommender/feature_schema.py` | Feature architecture V1 (dimensions, filters, metadata, feature kinds) |
| `src/spotify_recommender/split.py` | Group-aware multi-label stratified split, leakage check, split reports |
| `tests/test_feature_schema.py` | 6 tests: dimension contents, disjointness, filter isolation, feature kinds |
| `tests/test_split.py` | 8 tests: no leakage, ratio adherence, per-genre balance, determinism, edge cases, DataFrame layer |

---

## 6. Next Milestone Roadmap

| Step | Activity | Data Used |
| :---: | :--- | :---: |
| 1 | ~~Finalize feature categorization~~ | — |
| 2 | ~~Train / Validation / Test split~~ | — |
| 2b | Decide on audio-identical group merging (Section 4.F) | All |
| 3 | Within-dimension correlation analysis | Train |
| 4 | Between-dimension correlation analysis (feature level) | Train |
| 5 | Redundancy review and feature decisions | Train |
| 6 | Encoding and preprocessing (fit on Train only) | Train |
| 7 | Similarity engines per dimension | Train |
| 8 | Correlation of dimension **scores**, to confirm the relative independence of the engines | Validation |
| 9 | Final evaluation | Test |

Guiding rules:
* **No feature is dropped solely because of high correlation.** Results are analyzed first and decided on explicitly.
* **All data-driven decisions use Train only.** Validation checks design choices; Test stays untouched until final evaluation.
* **Duplicate versions in the output are removed at inference time.** A post-processing rule, separate from both filters and dimensions, collapses alternate releases of the same song in the top-10.
