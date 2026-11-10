.PHONY: install download prepare normalize inspect train test

install:
	pip install -r requirements.txt
	pip install -e .

download:
	python -m spotify_recommender.cli download

prepare:
	python -m spotify_recommender.cli prepare

normalize:
	python -m spotify_recommender.cli normalize

inspect:
	python -m spotify_recommender.cli inspect

train:
	python -m spotify_recommender.cli train

test:
	pytest

