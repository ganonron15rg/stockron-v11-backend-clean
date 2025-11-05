#!/usr/bin/env bash
set -o errexit

pip install --no-cache-dir \
    fastapi \
    uvicorn \
    yfinance \
    pandas \
    numpy \
    pydantic \
    requests \
    python-dateutil
