FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr tesseract-ocr-eng \
    poppler-utils ghostscript \
    build-essential libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY config ./config
COPY pyproject.toml README.md Makefile ./.pre-commit-config.yaml ./

ENV PYTHONPATH=/app
ENTRYPOINT ["python", "-m", "src.extract_zones_codes"]
