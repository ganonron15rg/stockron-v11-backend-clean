import math, pandas as pd, yfinance as yf
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional

app = FastAPI(title="Stockron Analyzer Backend (Clean)", version="v11-basic-1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def sma(s, w): return s.rolling(window=w).mean()
def rsi(s, w=14):
    delta = s.diff(); up, down = delta.clip(lower=0), -delta.clip(upper=0)
    ma_up, ma_down = up.ewm(com=w-1, adjust=False).mean(), down.ewm(com=w-1, adjust=False).mean()
    rs = ma_up / (ma_down + 1e-9)
    return 100 - (100 / (1 + rs))

def atr(h,l,c,w=14):
    prev = c.shift(1)
    tr = pd.concat([(h-l).abs(), (h-prev).abs(), (l-prev).abs()], axis=1).max(axis=1)
    return tr.rolling(window=w).mean()

class AnalyzeIn(BaseModel):
    ticker: str
    timeframe: Optional[str] = Field(default="6mo")

@app.get("/healthz")
def healthz(): return {"status": "ok", "version": "v11-basic-1.0.0"}

@app.post("/analyze")
def analyze(inp: AnalyzeIn):
    t = inp.ticker.upper().strip()
    if not t: raise HTTPException(400, "ticker required")
    df = yf.download(t, period=inp.timeframe, interval="1d", auto_adjust=True, progress=False)
    if df.empty: raise HTTPException(404, "No data")
    price = float(df["Close"].iloc[-1])
    sma50, rsi14 = float(sma(df["Close"],50).iloc[-1]), float(rsi(df["Close"]).iloc[-1])
    atr14 = float(atr(df["High"],df["Low"],df["Close"]).iloc[-1])
    buy = [round(sma50-atr14,2), round(sma50,2)]
    sell = [round(price+atr14,2), round(price+2*atr14,2)]
    return {"ticker":t,"price":price,"metrics":{"SMA50":sma50,"RSI14":rsi14,"ATR14":atr14},
            "buy_zone":buy,"sell_zone":sell,"ai_stance":"Buy" if rsi14<60 else ("Hold" if rsi14<75 else "Wait")}
