from fastapi import FastAPI
from pydantic import BaseModel
import yfinance as yf
from datetime import datetime

app = FastAPI(title="Stockron Analyzer v11", version="1.0.0")

# ====== Models ======

class StockRequest(BaseModel):
    ticker: str
    timeframe: str = "6mo"
    dsl: str | None = None
    notes: str | None = None


# ====== Helper Functions ======

def calculate_scores(info: dict):
    """חישוב מדדים בסיסי עבור מניה לפי נתוני yfinance"""
    pe = info.get("trailingPE") or 0
    growth = info.get("earningsGrowth") or 0
    debt = info.get("debtToEquity") or 0
    beta = info.get("beta") or 1

    quant = max(0, min(100, 70 - (pe * 1.5)))
    quality = max(0, min(100, 50 + (growth * 100)))
    catalyst = max(0, min(100, 40 + (1 / beta * 10)))
    overall = round((quant * 0.4) + (quality * 0.4) + (catalyst * 0.2), 2)

    return quant, quality, catalyst, overall


def determine_stance(overall_score: float):
    """קובע אם ההמלצה היא קנייה, החזקה או המתנה"""
    if overall_score >= 70:
        return "Buy"
    elif overall_score >= 50:
        return "Hold"
    else:
        return "Wait"


def determine_risk_level(beta: float | None):
    """קובע רמת סיכון לפי Beta"""
    if beta is None:
        return "Unknown"
    if beta < 0.8:
        return "Low"
    elif beta < 1.2:
        return "Medium"
    elif beta < 1.6:
        return "High"
    else:
        return "Very High"


# ====== Routes ======

@app.get("/healthz")
def health_check():
    return {"status": "ok", "version": "v11-basic-1.0.0"}


@app.post("/analyze")
def analyze_stock(request: StockRequest):
    ticker = request.ticker.upper()
    data = yf.Ticker(ticker)
    info = data.info

    # Fundamentals
    fundamentals = {
        "PE Ratio": info.get("trailingPE"),
        "Forward PE": info.get("forwardPE"),
        "PS Ratio": info.get("priceToSalesTrailing12Months"),
        "PEG Ratio": info.get("pegRatio"),
        "Revenue Growth": info.get("revenueGrowth"),
        "EPS Growth": info.get("earningsGrowth"),
        "Beta": info.get("beta"),
        "Debt/Equity": info.get("debtToEquity")
    }

    # Scores
    quant, quality, catalyst, overall = calculate_scores(info)
    stance = determine_stance(overall)
    risk_level = determine_risk_level(info.get("beta"))

    # Buy/Sell Zones (מבוסס על מחיר נוכחי)
    price = info.get("currentPrice") or 0
    buy_zone = [round(price * 0.9, 2), round(price * 0.97, 2)] if price else [None, None]
    sell_zone = [round(price * 1.05, 2), round(price * 1.15, 2)] if price else [None, None]

    buy_sell_zones = {
        "buy_zone": buy_zone,
        "sell_zone": sell_zone,
        "rationale": "אזורי קנייה ומכירה מבוססי תנועת מחיר ±10%"
    }

    # Educational Notes
    educational_notes = [
        "בדוק את מגמת ההכנסות ביחס לרווחיות.",
        "מכפיל רווח גבוה עשוי להעיד על תמחור יתר.",
        "מומלץ להשוות את ה-Beta לסקטור כדי להבין תנודתיות."
    ]

    # Build response
    result = {
        "ticker": ticker,
        "company_name": info.get("longName"),
        "sector": info.get("sector"),
        "price": price,
        "stance": stance,
        "quant_score": quant,
        "quality_score": quality,
        "catalyst_score": catalyst,
        "overall_score": overall,
        "ai_summary": f"המניה {ticker} מדורגת '{stance}' עם ניקוד כולל של {overall}.",
        "quant_summary": "הציון הכמותי משקלל מכפילים ויחסים פיננסיים.",
        "quality_summary": "איכות החברה מוערכת לפי צמיחה, יציבות ורווחיות.",
        "catalyst_summary": "פוטנציאל צמיחה מבוסס על קטליזטורים עסקיים וחיצוניים.",
        "fundamentals_json": fundamentals,
        "buy_sell_zones": buy_sell_zones,
        "risk_level": risk_level,
        "educational_notes": educational_notes,
        "last_updated": datetime.utcnow().isoformat()
    }

    return result


# ====== Screener Placeholder ======
@app.post("/screener")
def screener(strategy: dict):
    """גרסה פשוטה לסורק – placeholder"""
    return {
        "strategy": strategy.get("strategy", "growth"),
        "results": [
            {"ticker": "NVDA", "overall_score": 88, "stance": "Buy"},
            {"ticker": "AAPL", "overall_score": 74, "stance": "Hold"},
            {"ticker": "PLX", "overall_score": 53, "stance": "Wait"}
        ]
    }
