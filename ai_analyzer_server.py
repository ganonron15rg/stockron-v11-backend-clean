# ==============================================================
#  ai_analyzer_server.py — Stockron Analyzer v11.3 (Stable)
#  Full Production Backend for Base44 / Next.js Frontend
# ==============================================================

from __future__ import annotations
import json, math, os, random
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ==============================================================
# 🔧 FastAPI Setup
# ==============================================================

app = FastAPI(title="Stockron Analyzer Backend v11.3")

# CORS Middleware (מאפשר גישה מה-Frontend של Base44)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================================================
# 🩺 Health Check Endpoint
# ==============================================================

@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": "v11.3",
        "service": "Stockron Backend",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

# ==============================================================
# 📦 Request Schema
# ==============================================================

class AnalyzeRequest(BaseModel):
    ticker: str
    timeframe: Optional[str] = "6mo"
    notes: Optional[str] = None
    dsl: Optional[str] = None  # לשלב הבא - DSL formulas


# ==============================================================
# 🤖 Core Analysis Logic (Demo / Mock)
# ==============================================================
# בגרסה מלאה זה מתחבר ל-Stockron Engine / Yahoo API / AI Agent

def mock_quant_analysis() -> Dict[str, Any]:
    return {
        "pe_ratio": round(random.uniform(5, 30), 2),
        "eps_growth": round(random.uniform(0, 25), 2),
        "rev_growth": round(random.uniform(0, 20), 2),
        "overall_score": round(random.uniform(40, 95), 1)
    }

def mock_quality_analysis() -> Dict[str, Any]:
    return {
        "debt_equity": round(random.uniform(0.1, 2.5), 2),
        "profit_margin": round(random.uniform(5, 40), 2),
        "roe": round(random.uniform(5, 30), 2),
        "quality_score": round(random.uniform(40, 90), 1)
    }

def mock_catalyst_analysis() -> Dict[str, Any]:
    return {
        "news_sentiment": random.choice(["Positive", "Neutral", "Negative"]),
        "sector_momentum": round(random.uniform(-5, 10), 1),
        "ai_signal": random.choice(["Strong Buy", "Buy", "Hold", "Sell"])
    }


# ==============================================================
# 🔍 /analyze Endpoint
# ==============================================================

@app.post("/analyze")
async def analyze_stock(request: AnalyzeRequest):
    ticker = request.ticker.upper()

    # סימולציה של עיבוד — בגרסה הבאה יחובר למנוע ה-AI האמיתי
    quant = mock_quant_analysis()
    quality = mock_quality_analysis()
    catalyst = mock_catalyst_analysis()

    ai_summary = (
        f"{ticker} shows balanced fundamentals with P/E={quant['pe_ratio']} "
        f"and EPS growth of {quant['eps_growth']}%. "
        f"Profit margin at {quality['profit_margin']}% "
        f"indicates moderate efficiency. "
        f"Sector momentum: {catalyst['sector_momentum']}%, sentiment: {catalyst['news_sentiment']}."
    )

    # קביעת stance לפי הנתונים
    avg_score = (quant["overall_score"] * 0.4 + quality["quality_score"] * 0.4 + random.uniform(40, 90) * 0.2)
    if avg_score >= 70:
        ai_stance = "Buy"
    elif avg_score >= 55:
        ai_stance = "Hold"
    else:
        ai_stance = "Wait"

    # JSON תקין ל-Frontend
    return {
        "ticker": ticker,
        "quant": quant,
        "quality": quality,
        "catalyst": catalyst,
        "ai_summary": ai_summary,
        "ai_stance": ai_stance,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


# ==============================================================
# 🚀 Local Run (Render auto-detects this port)
# ==============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
