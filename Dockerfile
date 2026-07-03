FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffer logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p uploads

ENV TESSERACT_CMD=/usr/bin/tesseract

EXPOSE 8000

CMD ["sh", "-c", "uvicorn main1:app --host 0.0.0.0 --port ${PORT:-8000}"]
