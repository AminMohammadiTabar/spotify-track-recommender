import pandas as pd

from spotify_recommender.features import build_feature_frame
from spotify_recommender.config import FEATURE_COLUMNS


def test_feature_frame_excludes_target_and_metadata():
    row = {column: 0 for column in FEATURE_COLUMNS}
    row.update({
        "track_id": "example-id",
        "track_name": "Example",
        "artists": "Artist",
        "album_name": "Album",
        "track_genre": "pop",
    })

    X = build_feature_frame(pd.DataFrame([row]))

    assert list(X.columns) == FEATURE_COLUMNS
    assert "track_genre" not in X.columns
    assert "track_id" not in X.columns


def test_remastered_feature_detection():
    from spotify_recommender.data import add_remastered_feature

    df = pd.DataFrame([
        {"track_name": "Layla - Remastered", "album_name": "Layla", "artists": "Eric"},
        {"track_name": "Hotel California", "album_name": "Hotel California (2013 Remaster)", "artists": "Eagles"},
        {"track_name": "Yesterday", "album_name": "Help!", "artists": "The Beatles"},
    ])
    result = add_remastered_feature(df)
    assert result["is_remastered"].tolist() == [1, 1, 0]


def test_prepare_aggregated_tracks_groups_multi_genres():
    from spotify_recommender.data import prepare_aggregated_tracks
    from spotify_recommender.config import NUMERIC_FEATURES

    base = {col: 0.5 for col in NUMERIC_FEATURES}
    base.update({"key": 1, "mode": 1, "time_signature": 4, "explicit": False})

    row1 = dict(base, track_id="song_1", track_name="Song 1", artists="Artist", album_name="Album", track_genre="pop", popularity=60)
    row2 = dict(base, track_id="song_1", track_name="Song 1", artists="Artist", album_name="Album", track_genre="rock", popularity=75)
    row3 = dict(base, track_id="song_2", track_name="Song 2", artists="Artist 2", album_name="Album 2", track_genre="jazz", popularity=40)

    raw_df = pd.DataFrame([row1, row2, row3])
    agg_df = prepare_aggregated_tracks(raw_df)

    assert len(agg_df) == 2
    song1 = agg_df[agg_df["track_id"] == "song_1"].iloc[0]
    assert song1["genres"] == ["pop", "rock"]
    assert song1["popularity"] == 75
    assert song1["genres_str"] == "pop; rock"
