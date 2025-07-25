APP=boq-extractor
IMAGE=$(APP):latest
RUN_DIR=outputs/run_$(shell date +%Y%m%d_%H%M%S)

.PHONY: setup install run test clean docker-build docker-run ui run-streamlit run-enhanced

# Enhanced setup with all dependencies
setup:
	python -m venv .venv
	. .venv/bin/activate && pip install -U pip && pip install -r requirements.txt && pre-commit install

# Simple install for enhanced application
install:
	python3.11 -m venv .venv
	.venv/bin/pip install -r requirements.txt

# Original extraction pipeline
run:
	mkdir -p $(RUN_DIR)
	. .venv/bin/activate && python -m src.extract_zones_codes \
	  --pdf input/sample.pdf \
	  --out $(RUN_DIR) \
	  --config config/default.yml

# Enhanced Streamlit application (production-grade)
run-enhanced:
	. .venv/bin/activate && streamlit run enhanced_app.py

# Basic Streamlit application
run-streamlit:
	. .venv/bin/activate && streamlit run app.py

# Original UI
ui:
	. .venv/bin/activate && streamlit run src/ui/streamlit_app.py

# Comprehensive testing
test:
	. .venv/bin/activate && pytest -q
	python test_enhanced_functionality.py
	python test_bug_fixes.py

# Docker build
docker-build:
	sudo docker build -t $(IMAGE) -f docker/Dockerfile .
	sudo docker build -t pdf-extractor .

# Docker run (original)
docker-run:
	mkdir -p $(RUN_DIR)
	sudo docker run --rm -v $(PWD):/work -w /work $(IMAGE) \
	  python -m src.extract_zones_codes \
	    --pdf /work/input/sample.pdf \
	    --out /work/$(RUN_DIR) \
	    --config /work/config/default.yml

# Docker run (enhanced)
docker-run-enhanced:
	sudo docker run -p 8501:8501 pdf-extractor

# Cleanup
clean:
	rm -rf outputs/*
	rm -rf .venv
	rm -rf __pycache__
	rm -rf *.pyc
