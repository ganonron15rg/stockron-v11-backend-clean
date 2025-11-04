#!/usr/bin/env bash
set -e

# שדרוג כלי בנייה
python -m pip install --upgrade pip setuptools wheel

# נתקין גרסאות קלות ויציבות שמגיעות עם wheels מוכנים מראש
pip install --only-binary=:all: numpy==1.24.4
pip install --only-binary=:all: pandas==2.0.3
pip install fastapi==0.110.0 uvicorn==0.29.0 pydantic==2.7.4 yfinance==0.2.38
