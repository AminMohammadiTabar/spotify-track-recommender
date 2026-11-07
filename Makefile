.PHONY: install download prepare inspect train test

install:
	pip install -r requirements.txt
	pip install -e .

download:
	python -m spotify_recommender.cli download

prepare:
	python -m spotify_recommender.cli prepare

inspect:
	python -m spotify_recommender.cli inspect

train:
	python -m spotify_recommender.cli train

test:
	pytest

