FROM python:3.11-slim

WORKDIR /app

COPY . /app

# התקנות (הכי חשוב לשים כאן את הספריות המעודכנות)
RUN pip install --no-cache-dir fastapi uvicorn yfinance pandas numpy pydantic requests python-dateutil

EXPOSE 10000

CMD ["uvicorn", "ai_analyzer_server:app", "--host", "0.0.0.0", "--port", "10000"]
