APP=-BOQ-
IMAGE=$(APP):latest
RUN_DIR=outputs/run_$(shell date +%Y%m%d_%H%M%S)

.PHONY: setup run test clean docker-build docker-run ui

setup:
	python -m venv .venv
	. .venv/bin/activate && pip install -U pip && pip install -r requirements.txt && pre-commit install

run:
	mkdir -p $(RUN_DIR)
	. .venv/bin/activate && python -m src.extract_zones_codes \
	  --pdf input/sample.pdf \
	  --out $(RUN_DIR) \
	  --config config/default.yml

ui:
	. .venv/bin/activate && streamlit run src/ui/streamlit_app.py

test:
	. .venv/bin/activate && pytest -q

docker-build:
	docker build -t $(IMAGE) -f docker/Dockerfile .

docker-run:
	mkdir -p $(RUN_DIR)
	docker run --rm -v $(PWD):/work -w /work $(IMAGE) \
	  python -m src.extract_zones_codes \
	    --pdf /work/input/sample.pdf \
	    --out /work/$(RUN_DIR) \
	    --config /work/config/default.yml

clean:
	rm -rf outputs/*
