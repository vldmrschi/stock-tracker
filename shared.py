import yfinance as yf
import streamlit as st
import requests

api_key = st.secrets.get("FINNHUB_API_KEY")


def show_stat(label,value):
    if value:
        st.write(f"{label}: {value:,}")
    else:
        st.write(f"{label}: Not Available")


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


def load_company(ticker, source, display_currency, period="6mo"):
    stock = yf.Ticker(ticker)
    history = stock.history(period=period)
    if history.empty:
        return None

    used_finnhub = False
    status = yahoo_status()
    if source == "Finnhub":
        info = finnhub_info(ticker)
        used_finnhub = True
    else:
        info = stock.info
        if not info.get("currency"):
            info = finnhub_info(ticker)
            used_finnhub = True
            st.warning("Yahoo Finance isn't responding, so this data comes from Finnhub (US stocks only).")
            status["was_down"] = True
        elif status["was_down"]:
            st.success("Yahoo Finance is back online, so data is from Yahoo again.")
            status["was_down"] = False

    industry = info.get("industry")
    currency = info.get("currency")
    if display_currency == "Original":
        fx_rate = 1
        shown_currency = currency
    else:
        if currency == "GBp":
            base = "GBP"
        else:
            base = currency
        fx_rate = get_fx_rate(base, display_currency)
        if fx_rate is None:
            st.warning("The exchange rate isn't available right now, so prices are shown in the original currency.")
            fx_rate = 1
            shown_currency = currency
        else:
            if currency == "GBp":
                fx_rate = fx_rate / 100
            shown_currency = display_currency
    latest_price = history["Close"].dropna().iloc[-1]

    if currency == "GBp":
        cap_currency = "GBP"
    else:
        cap_currency = currency
    cap_rate = fx_rate
    if currency == "GBp" and shown_currency != "GBp":
        cap_rate = fx_rate * 100
    if shown_currency == "GBp":
        cap_label ="GBP"
    else:
        cap_label = shown_currency
    fin_currency = info.get("financialCurrency") or cap_currency
    fin_rate = get_fx_rate(fin_currency, cap_currency)
    if fin_rate is None:
        st.warning("The company's accounts couldn't be converted into its share currency, so the DCF may be inaccurate.")
        fin_rate = 1



    return {
        "stock": stock, "history": history, "info": info,
        "used_finnhub": used_finnhub, "industry": industry, "currency": currency,
        "fx_rate": fx_rate, "shown_currency": shown_currency, "latest_price": latest_price,
        "cap_rate": cap_rate, "cap_label": cap_label, "fin_rate": fin_rate,
    }
