# Spotify Track Recommender

پروژه‌ای برای ساخت سیستم پیشنهاد ۱۰ آهنگ مشابه با دیتاست Spotify Tracks Dataset و استفاده از **Random Forest Proximity**.

> نکته‌ی طراحی: Random Forest به‌تنهایی الگوریتم استاندارد توصیه‌گر نیست. در این اسکلت، مدل با `track_genre` آموزش می‌بیند و شباهت دو آهنگ از میزان هم‌افتادن آن‌ها در برگ‌های درخت‌های جنگل (Random Forest leaf proximity) محاسبه می‌شود. این یک baseline قابل‌آزمایش است؛ در ادامه باید آن را با KNN/Cosine Similarity مقایسه کنیم.

## ساختار پروژه

```text
spotify_track_recommender/
├── data/
│   ├── raw/                 # فایل CSV دانلودشده (در Git ذخیره نمی‌شود)
│   └── processed/
├── models/                  # مدل و leaf indices
├── notebooks/
│   └── 01_eda_template.ipynb
├── reports/
├── src/
│   └── spotify_recommender/
│       ├── __init__.py
│       ├── config.py
│       ├── data.py
│       ├── features.py
│       ├── model.py
│       ├── recommender.py
│       └── cli.py
├── tests/
│   └── test_features.py
├── .gitignore
├── Makefile
├── pyproject.toml
└── requirements.txt
```

## 1) نصب

Python 3.10 یا بالاتر پیشنهاد می‌شود.

```bash
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows PowerShell
# .venv\Scripts\Activate.ps1

pip install -r requirements.txt
pip install -e .
```

## 2) دریافت دیتاست از Kaggle

ابتدا دسترسی Kaggle را روی سیستم تنظیم کن. `kagglehub` باید بتواند با حساب Kaggle تو احراز هویت کند.

```bash
python -m spotify_recommender.cli download
```

دیتاست از این شناسه دریافت می‌شود:

`maharshipandya/-spotify-tracks-dataset`

CSV در مسیر `data/raw/spotify_tracks.csv` قرار می‌گیرد. این دستور فایل CSV بزرگ‌تر را از پوشه‌ی دانلودشده انتخاب می‌کند.

## 3) آموزش مدل

```bash
python -m spotify_recommender.cli train
```

مدل در `models/random_forest_recommender.joblib` ذخیره می‌شود. هنگام آموزش:
- داده‌ها از نظر ستون‌های موردنیاز اعتبارسنجی می‌شوند.
- یک ارزیابی اولیه‌ی طبقه‌بندی ژانر روی holdout انجام می‌شود.
- مدل نهایی روی کل داده‌ها fit می‌شود.
- شناسه‌ی برگ هر آهنگ در تمام درخت‌ها ذخیره می‌شود تا پیشنهاددهی سریع‌تر باشد.

## 4) پیشنهاد آهنگ

برای پیشنهاد آهنگ، `track_id` یکی از ردیف‌های دیتاست را بده:

```bash
python -m spotify_recommender.cli recommend \
  --track-id "SPOTIFY_TRACK_ID" \
  --top-k 10
```

در Windows می‌توان دستور را در یک خط اجرا کرد.

## ویژگی‌های ورودی مدل

- عددی: `danceability`, `energy`, `loudness`, `speechiness`, `acousticness`,
  `instrumentalness`, `liveness`, `valence`, `tempo`, `duration_ms`
- دسته‌ای: `key`, `mode`, `time_signature`, `explicit`
- برچسب آموزش: `track_genre`

شناسه، نام آهنگ، نام هنرمند، آلبوم و محبوبیت به‌عنوان ویژگی شباهت وارد مدل نمی‌شوند؛ این اطلاعات برای نمایش/شناخت آهنگ هستند یا ممکن است باعث سوگیری نامرتبط شوند.

## نکات مهم برای ادامه‌ی پروژه

1. امتیاز Random Forest proximity به‌تنهایی تضمین‌کننده‌ی «شباهت شنیداری» نیست؛ چون مدل با ژانر آموزش دیده است.
2. در مرحله‌ی بعد baselineهای `NearestNeighbors` با فاصله‌ی cosine و euclidean را هم پیاده‌سازی می‌کنیم.
3. برای ارزیابی توصیه‌ها می‌توانیم معیارهایی مثل genre consistency، diversity و بررسی انسانی نمونه‌ها را اضافه کنیم.
4. قبل از نتیجه‌گیری، باید duplicateهای `track_id`، مقادیر گمشده، توزیع ژانرها و outlierها را روی CSV واقعی بررسی کنیم.

## اجرای تست‌ها

```bash
pytest
```
