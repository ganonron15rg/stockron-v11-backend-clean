# Stockron Analyzer v11 - Clean Backend

**Render Setup:**
- Build Command: ./build.sh
- Start Command: uvicorn ai_analyzer_server:app --host 0.0.0.0 --port $PORT
- Environment: Python 3.10.13 (forced via runtime.txt)
- Plan: Free

Endpoints:
- GET /healthz
- POST /analyze { "ticker": "NVDA", "timeframe": "6mo" }
