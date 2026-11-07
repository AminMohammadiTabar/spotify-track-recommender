import argparse
import json

from .config import MODEL_PATH, RAW_DATA_PATH
from .data import download_dataset, load_tracks
from .model import train_and_save
from .recommender import recommend_by_track_id


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="spotify-recommender",
        description="Spotify track similarity recommender",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("download", help="Download the Kaggle dataset")

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
        print("Shape:", df.shape)
        print("\nDtypes:\n", df.dtypes.to_string())
        print("\nMissing values:\n", df.isna().sum().to_string())
        print("\nDuplicate rows:", int(df.duplicated().sum()))
        print("\nUnique track IDs:", int(df["track_id"].nunique()))
        print("\nUnique genres:", int(df["track_genre"].nunique()))
        print("\nTop genres:\n", df["track_genre"].value_counts().head(15).to_string())


if __name__ == "__main__":
    main()
