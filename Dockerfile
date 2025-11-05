# Dockerfile for Stockron v11.2
FROM python:3.11-slim

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    yfinance \
    pandas \
    numpy \
    pydantic \
    requests \
    python-dateutil

EXPOSE 10000
CMD ["uvicorn", "ai_analyzer_server:app", "--host", "0.0.0.0", "--port", "10000"]
