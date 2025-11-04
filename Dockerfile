# Dockerfile for Stockron Analyzer v11 - Clean Render Deploy
FROM python:3.10-slim

WORKDIR /app
COPY . /app

RUN pip install --upgrade pip setuptools wheel
RUN pip install fastapi==0.110.0 uvicorn==0.29.0 pandas==2.0.3 pydantic==2.7.4 yfinance==0.2.38 numpy==1.24.4

EXPOSE 10000
CMD ["uvicorn", "ai_analyzer_server:app", "--host", "0.0.0.0", "--port", "10000"]
