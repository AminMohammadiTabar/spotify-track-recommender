.PHONY: install download train test

install:
	pip install -r requirements.txt
	pip install -e .

download:
	python -m spotify_recommender.cli download

train:
	python -m spotify_recommender.cli train

test:
	pytest
