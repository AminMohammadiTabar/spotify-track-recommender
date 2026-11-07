import argparse
import json

from pathlib import Path
from .config import MODEL_PATH, PROCESSED_DATA_PATH, RAW_DATA_PATH
from .data import download_dataset, load_tracks, prepare_aggregated_tracks
from .model import train_and_save
from .recommender import recommend_by_track_id


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="spotify-recommender",
        description="Spotify track similarity recommender",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("download", help="Download the Kaggle dataset")

    prepare_parser = subparsers.add_parser(
        "prepare", help="Clean and aggregate raw tracks into unique multi-genre dataset"
    )
    prepare_parser.add_argument("--data", default=str(RAW_DATA_PATH))
    prepare_parser.add_argument("--output", default=str(PROCESSED_DATA_PATH))

    train_parser = subparsers.add_parser("train", help="Train the Random Forest")
    train_parser.add_argument("--data", default=str(RAW_DATA_PATH))
    train_parser.add_argument("--model", default=str(MODEL_PATH))

    recommend_parser = subparsers.add_parser(
        "recommend", help="Recommend similar tracks for a Spotify track ID"
    )
    recommend_parser.add_argument("--track-id", required=True)
    recommend_parser.add_argument("--top-k", type=int, default=10)
    recommend_parser.add_argument("--model", default=str(MODEL_PATH))

    inspect_parser = subparsers.add_parser(
        "inspect", help="Print a quick dataset summary"
    )
    inspect_parser.add_argument("--data", default=str(RAW_DATA_PATH))

    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.command == "download":
        destination = download_dataset()
        print(f"Dataset saved to: {destination}")

    elif args.command == "prepare":
        raw = load_tracks(args.data)
        agg = prepare_aggregated_tracks(raw)
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        agg.to_csv(out_path, index=False)
        print(f"Processed dataset saved to: {out_path}")
        print(f"Total unique tracks: {len(agg):,}")
        print(f"Multi-genre tracks: {(agg['genres'].apply(len) > 1).sum():,}")
        print(f"Remastered tracks: {agg['is_remastered'].sum():,}")

    elif args.command == "train":
        metrics = train_and_save(args.data, args.model)
        print(json.dumps(metrics, indent=2, ensure_ascii=False))

    elif args.command == "recommend":
        recommendations = recommend_by_track_id(
            args.track_id, args.top_k, args.model
        )
        print(recommendations.to_string(index=False))

    elif args.command == "inspect":
        df = load_tracks(args.data)
        agg = prepare_aggregated_tracks(df)
        print("Raw Tracks Shape:", df.shape)
        print("Unique Tracks Shape:", agg.shape)
        print("\nMissing values:\n", df.isna().sum().to_string())
        print("\nExact duplicate rows removed:", int(df.duplicated().sum()))
        print("Unique track IDs:", int(agg["track_id"].nunique()))
        print("Multi-genre tracks count:", int((agg["genres"].apply(len) > 1).sum()))
        print("Remastered tracks count:", int(agg["is_remastered"].sum()))


if __name__ == "__main__":
    main()
