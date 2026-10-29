import yfinance as yf
import streamlit as st
import requests

api_key = st.secrets.get("FINNHUB_API_KEY")


def finnhub_multiples(symbol):
    params = {"symbol": symbol, "metric": "all", "token": api_key}
    response = requests.get("https://finnhub.io/api/v1/stock/metric", params=params)
    m = response.json().get("metric", {})
    return [m.get("peTTM"), m.get("evEbitdaTTM"), m.get("evRevenueTTM")]

def get_multiples(symbol):
    y_info = yf.Ticker(symbol).info
    yahoo = [y_info.get("trailingPE"), y_info.get("enterpriseToEbitda"), y_info.get("enterpriseToRevenue")]
    if yahoo != [None, None, None]:
        return yahoo
    return finnhub_multiples(symbol)

def finnhub_info(symbol):
    params = {"symbol": symbol, "token": api_key}
    profile = requests.get("https://finnhub.io/api/v1/stock/profile2", params=params).json()

    market_cap = profile.get("marketCapitalization")
    if market_cap:
        market_cap = int(market_cap * 1_000_000)

    shares = profile.get("shareOutstanding")
    if shares:
        shares = int(shares * 1_000_000)

    metric_params = {"symbol": symbol, "metric": "all", "token": api_key}
    m = requests.get("https://finnhub.io/api/v1/stock/metric", params=metric_params).json().get("metric", {})
    
    return {"longName": profile.get("name"), "currency": profile.get("currency"), "marketCap": market_cap, "sharesOutstanding": shares, "trailingPE": m.get("peTTM"), "fiftyTwoWeekHigh": m.get("52WeekHigh"), "dividendYield": m.get("dividendYieldIndicatedAnnual"), "trailingEps": m.get("epsTTM")}

def get_fx_rate(from_cur, to_cur):
    if from_cur == to_cur:
        return 1
    fx = yf.Ticker(f"{from_cur}{to_cur}=X").history(period="5d")
    if not fx.empty:
        return fx["Close"].dropna().iloc[-1]
    params = {"from": from_cur, "to": to_cur}
    data = requests.get("https://api.frankfurter.app/latest", params=params).json()
    return data.get("rates", {}).get(to_cur)

@st.cache_resource
def yahoo_status():
    return {"was_down": False}
