.PHONY: install run-streamlit test clean docker-build docker-run

install:
	python3.11 -m venv .venv
	.venv/bin/pip install -r requirements.txt

run-streamlit:
	streamlit run app.py

test:
	python -m pytest tests/

clean:
	rm -rf .venv
	rm -rf __pycache__
	rm -rf *.pyc

docker-build:
	docker build -t pdf-extractor .

docker-run:
	docker run -p 8501:8501 pdf-extractor