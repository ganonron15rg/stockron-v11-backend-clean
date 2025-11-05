# ai_analyzer_server.py — Stockron v11.2 (Production)
from __future__ import annotations

import json
import math
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

import pandas as pd
import yfinance as yf
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

APP_VERSION = "v11.2-prod"

# קאש לקבצים – Render מאשר כתיבה ל-/tmp
CACHE_PATH = "/tmp/stockron_cache.json"
ANALYSIS_TTL_HOURS = 24   # כמה זמן לשמור תוצאות ניתוח
FUND_TTL_HOURS = 24       # כמה זמן לשמור fundamentals

app = FastAPI(title="Stockron Analyzer", version=APP_VERSION, docs_url="/docs", redoc_url="/redoc")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ========================= Models =========================

class StockRequest(BaseModel):
    ticker: str
    timeframe: str = Field(default="6mo", description="1mo|3mo|6mo|1y|5y|max")
    style: str = Field(default="swing", description="swing | investor")
    notes: Optional[str] = None  # 'freeze' וכו'


# ===================== Cache Utilities ====================

def _load_cache() -> Dict[str, Any]:
    try:
        if os.path.exists(CACHE_PATH):
            with open(CACHE_PATH, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def _save_cache(data: Dict[str, Any]) -> None:
    try:
        with open(CACHE_PATH, "w") as f:
            json.dump(data, f)
    except Exception:
        pass

def _is_fresh(ts_iso: str, ttl_hours: int) -> bool:
    try:
        ts = datetime.fromisoformat(ts_iso)
        return (datetime.utcnow() - ts) < timedelta(hours=ttl_hours)
    except Exception:
        return False


# ======================= Math Helpers =====================

def _safe_float(v, fb: Optional[float] = None) -> Optional[float]:
    try:
        if v is None:
            return fb
        if isinstance(v, (int, float)) and math.isfinite(v):
            return float(v)
        if isinstance(v, str):
            s = v.replace(",", "").replace("%", "").strip()
            x = float(s)
            return x if math.isfinite(x) else fb
        return fb
    except Exception:
        return fb

def _sma(s: pd.Series, w: int) -> pd.Series:
    return s.rolling(window=w, min_periods=max(2, w // 2)).mean()

def _atr(h: pd.Series, l: pd.Series, c: pd.Series, w: int = 14) -> pd.Series:
    pc = c.shift(1)
    tr = pd.concat([(h - l).abs(), (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(window=w, min_periods=max(2, w // 2)).mean()


# =================== Market Data Fetchers =================

def _yf_period(tf: str) -> str:
    return {"1mo": "1mo", "3mo": "3mo", "6mo": "6mo", "1y": "1y", "5y": "5y", "max": "max"}.get(tf, "6mo")

def _fetch_daily_close_price(tkr: yf.Ticker) -> Optional[float]:
    """
    מחיר יציב: Close יומי אחרון (לא currentPrice) — כדי למנוע קפיצות בין קריאות.
    """
    try:
        hist = tkr.history(period="3mo", interval="1d", auto_adjust=True)
        if isinstance(hist, pd.DataFrame) and not hist.empty and "Close" in hist:
            return _safe_float(hist["Close"].iloc[-1])
    except Exception:
        pass

    # fallback אחרון: info
    try:
        info = tkr.info or {}
        return _safe_float(info.get("previousClose")) or _safe_float(info.get("currentPrice"))
    except Exception:
        return None

def _fetch_prices_df(tkr: yf.Ticker, timeframe: str) -> pd.DataFrame:
    df = tkr.history(period=_yf_period(timeframe), interval="1d", auto_adjust=True)
    if df is None or df.empty:
        raise HTTPException(status_code=404, detail="No price history available")
    return df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})

def _fetch_fundamentals(tkr: yf.Ticker) -> Dict[str, Optional[float]]:
    """
    מושך fundamentals באופן בטוח ומחזיר תמיד את כל המפתחות.
    """
    out: Dict[str, Optional[float]] = {
        "PE Ratio": None,
        "Forward PE": None,
        "PS Ratio": None,
        "PEG Ratio": None,
        "Revenue Growth": None,
        "EPS Growth": None,
        "Beta": None,
        "Debt/Equity": None,
        "Market Cap": None,
    }
    try:
        info = tkr.info or {}
        out["PE Ratio"] = _safe_float(info.get("trailingPE"))
        out["Forward PE"] = _safe_float(info.get("forwardPE"))
        out["PS Ratio"] = _safe_float(info.get("priceToSalesTrailing12Months"))
        out["PEG Ratio"] = _safe_float(info.get("pegRatio"))
        out["Revenue Growth"] = _safe_float(info.get("revenueGrowth"))  # fraction
        out["EPS Growth"] = _safe_float(info.get("earningsGrowth"))     # fraction
        out["Beta"] = _safe_float(info.get("beta"))
        out["Debt/Equity"] = _safe_float(info.get("debtToEquity"))
        out["Market Cap"] = _safe_float(info.get("marketCap"))
    except Exception:
        pass
    return out


# ===================== Scoring & Zones =====================

def _scores_from(f: Dict[str, Optional[float]]) -> Tuple[float, float, float, float]:
    pe = f.get("PE Ratio")
    growth_eps = f.get("EPS Growth")
    debt = f.get("Debt/Equity")
    beta = f.get("Beta")

    quant = 50.0
    if pe is not None:
        if pe < 15:
            quant += 12
        elif pe > 60:
            quant -= 10
    if growth_eps is not None:
        if growth_eps > 0.20:
            quant += 15
        elif growth_eps < 0:
            quant -= 10

    quality = 50.0
    if debt is not None:
        if debt < 0.5:
            quality += 15
        elif debt > 2.0:
            quality -= 10

    catalyst = 50.0
    if growth_eps and growth_eps > 0.10:
        catalyst += 5
    if beta and beta > 1.5:
        catalyst -= 5

    clamp = lambda x: float(max(0, min(100, round(x)))))
    quant = clamp(quant); quality = clamp(quality); catalyst = clamp(catalyst)
    overall = round(0.4 * quant + 0.4 * quality + 0.2 * catalyst, 2)
    return quant, quality, catalyst, overall

def _stance(overall: float) -> str:
    if overall >= 70:
        return "Buy"
    if overall >= 55:
        return "Hold"
    return "Wait"

def _risk_from_beta(beta: Optional[float]) -> str:
    if beta is None:
        return "Unknown"
    if beta < 0.8:
        return "Low"
    if beta < 1.2:
        return "Medium"
    if beta < 1.6:
        return "High"
    return "Very High"

def _compute_zones(df: pd.DataFrame, price: float, style: str) -> Dict[str, Any]:
    if style == "investor":
        ma_len, atr_len = 200, 20
    else:  # swing/default
        ma_len, atr_len = 50, 14

    ma_series = df["close"].rolling(ma_len, min_periods=max(2, ma_len // 2)).mean()
    ma = _safe_float(ma_series.iloc[-1], price)
    atr = _safe_float(_atr(df["high"], df["low"], df["close"], atr_len).iloc[-1], max(0.02 * price, 0.05))

    buy_zone = [round(ma - atr, 4), round(ma, 4)]
    sell_zone = [round(price + atr, 4), round(price + 2 * atr, 4)]

    return {
        "buy_zone": buy_zone,
        "sell_zone": sell_zone,
        "rationale": f"{style.upper()} zones: SMA{ma_len} + ATR{atr_len}"
    }

def _sell_signal(price: float, df: pd.DataFrame, style: str) -> Tuple[bool, Optional[str], Optional[float]]:
    if style == "investor":
        ma_len, thresh = 200, 0.05
    else:
        ma_len, thresh = 50, 0.03

    ma = df["close"].rolling(ma_len, min_periods=max(2, ma_len // 2)).mean().iloc[-1]
    if pd.isna(ma):
        return False, None, None

    ma = float(ma)
    if price < ma * (1 - thresh):
        reason = f"Close < SMA{ma_len} by {int(thresh * 100)}%"
        stop = round(ma * (1 - 2 * thresh), 4)
        return True, reason, stop
    return False, None, None


# =========================== Routes ========================

@app.get("/healthz")
def healthz():
    return {"status": "ok", "version": APP_VERSION}

@app.post("/analyze")
def analyze(req: StockRequest):
    ticker = (req.ticker or "").upper().strip()
    style = (req.style or "swing").lower()
    if not ticker:
        raise HTTPException(status_code=400, detail="ticker required")

    cache = _load_cache()

    # 1) Cache של תוצאת ניתוח (per ticker+style)
    analysis_key = f"analysis:{ticker}:{style}"
    if req.notes and req.notes.lower().strip() == "freeze":
        if analysis_key in cache and _is_fresh(cache[analysis_key]["ts"], ANALYSIS_TTL_HOURS):
            return cache[analysis_key]["data"]

    if analysis_key in cache and _is_fresh(cache[analysis_key]["ts"], ANALYSIS_TTL_HOURS):
        return cache[analysis_key]["data"]

    # 2) מחיר יציב: Close יומי אחרון
    tkr = yf.Ticker(ticker)
    price = _fetch_daily_close_price(tkr)
    if price is None:
        raise HTTPException(status_code=404, detail=f"Could not resolve price for {ticker}")

    # 3) היסטוריה לאינדיקטורים/אזורים
    try:
        df = _fetch_prices_df(tkr, req.timeframe)
    except HTTPException:
        # אם אין היסטוריה, נייצר DataFrame מינימלי כדי למנוע קריסה
        df = pd.DataFrame({"close": [price] * 60, "high": [price] * 60, "low": [price] * 60})

    # 4) fundamentals snapshot יומי (נפרד מהניתוח)
    fund_key = f"fund:{ticker}:{datetime.utcnow().date().isoformat()}"
    if fund_key in cache and _is_fresh(cache[fund_key]["ts"], FUND_TTL_HOURS):
        fundamentals = cache[fund_key]["data"]
    else:
        fundamentals = _fetch_fundamentals(tkr)
        cache[fund_key] = {"ts": datetime.utcnow().isoformat(), "data": fundamentals}

    # 5) ציונים/סטאנס/סיכון
    qnt, qual, cat, overall = _scores_from(fundamentals)
    stance = _stance(overall)
    risk = _risk_from_beta(fundamentals.get("Beta"))

    # 6) אזורים + איתות מכירה
    zones = _compute_zones(df, price, style)
    ss, sreason, stop = _sell_signal(price, df, style)

    # 7) מטא נתונים
    company_name, sector = None, None
    try:
        info = tkr.info or {}
        company_name = info.get("longName")
        sector = info.get("sector")
    except Exception:
        pass

    quant_summary = "איזון בין מכפילים לצמיחת EPS."
    if fundamentals.get("PEG Ratio") and fundamentals["PEG Ratio"] < 1.5:
        quant_summary = "PEG נמוך יחסית — תמחור אטרקטיבי מול הצמיחה."
    elif fundamentals.get("PE Ratio") and fundamentals["PE Ratio"] > 60:
        quant_summary = "מכפיל רווח גבוה — דורש צמיחה חזקה להצדקה."

    quality_summary = "מינוף ואיכות מאזנית."
    if fundamentals.get("Debt/Equity") is not None:
        de = fundamentals["Debt/Equity"]
        if de < 0.5:
            quality_summary = "מינוף נמוך והון עצמי יציב — איכות טובה."
        elif de > 2.0:
            quality_summary = "מינוף גבוה — רגישות לריבית ומאקרו."

    catalyst_summary = "מומנטום וצמיחה עשויים לשמש כקטליזטור."

    result = {
        "ticker": ticker,
        "style": style,
        "company_name": company_name,
        "sector": sector,
        "price": round(price, 4),
        "stance": stance,
        "quant_score": qnt,
        "quality_score": qual,
        "catalyst_score": cat,
        "overall_score": overall,
        "quant_summary": quant_summary,
        "quality_summary": quality_summary,
        "catalyst_summary": catalyst_summary,
        "ai_summary": f"{ticker}: דירוג '{stance}' עם ציון כולל {overall}.",
        "fundamentals_json": fundamentals,
        "buy_sell_zones": zones,
        "sell_signal": ss,
        "sell_reason": sreason,
        "stop_loss": stop,
        "risk_level": risk,
        "educational_notes": [
            "בדוק מגמת הכנסות ורווחיות יחד — לא נתון בודד.",
            "PEG<1.5 עשוי להצביע על תמחור אטרקטיבי.",
            "Debt/Equity נמוך מ-0.5 בדרך כלל חיובי לאיכות."
        ],
        "last_updated": datetime.utcnow().isoformat()
    }

    cache[analysis_key] = {"ts": datetime.utcnow().isoformat(), "data": result}
    _save_cache(cache)
    return result


# (אופציונלי) סורק בסיסי
@app.post("/screener")
def screener(payload: Dict[str, Any]):
    strategy = (payload or {}).get("strategy", "growth")
    limit = int((payload or {}).get("limit", 10))
    sample = [
        {"ticker": "NVDA", "overall_score": 88, "stance": "Buy"},
        {"ticker": "AAPL", "overall_score": 74, "stance": "Hold"},
        {"ticker": "PLX",  "overall_score": 58, "stance": "Hold"},
        {"ticker": "TSLA", "overall_score": 65, "stance": "Hold"},
    ][:max(1, min(limit, 50))]
    return {"strategy": strategy, "results": sample}
