# Stockron Analyzer v11.2 – Clean Backend

## Render Setup
- **Build Command:** ./build.sh
- **Start Command:** uvicorn ai_analyzer_server:app --host 0.0.0.0 --port $PORT
- **Python:** 3.11 (runtime.txt)
- **Plan:** Free
- **Ports:** 10000

---

### ✅ Endpoints
- **GET** `/healthz` → Returns `{ "status": "ok", "version": "v11.2-prod" }`
- **POST** `/analyze`
```json
{
  "ticker": "PLX",
  "timeframe": "6mo",
  "style": "swing"
}
