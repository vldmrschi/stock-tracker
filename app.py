import streamlit as st
import yfinance as yf
import requests
from streamlit_searchbox import st_searchbox

st.set_page_config(page_title="Valtide", layout="wide")

api_key = st.secrets.get("FINNHUB_API_KEY")

def finnhub_searches(text):
    params = {"q": text, "token": api_key}
    data = requests.get("https://finnhub.io/api/v1/search", params=params).json()
    results = []
    for r in data.get("result", [])[:7]:
        if r.get("type") not in ["Common Stock", "ETP"]:
            continue
        symbol = r.get("symbol")
        name = r.get("description")
        label = f"{name} · {symbol} · via Finnhub"
        results.append((label, symbol))
    return results

exchange_countries = {"NASDAQ": "United States", "NYSE": "United States", "NYSEArca": "United States", "NYSE MKT": "United States", "London": "United Kingdom", "XETRA": "Germany", "Frankfurt": "Germany", "Stuttgart": "Germany", "Paris": "France", "Madrid Stock Exchange CATS": "Spain", "Milan": "Italy", "Amsterdam": "Netherlands", "Toronto": "Canada", "NEO": "Canada", "Stockholm": "Sweden", "São Paulo": "Brazil", "BVB": "Romania"}

def search_stocks(text):
    if len(text) < 2:
        return []
    try:
        quotes = yf.Search(text, max_results=10).quotes
    except Exception:
        return finnhub_searches(text)
    results = []

    for q in quotes:
        if q.get("typeDisp") not in ["Equity", "ETF"]:
            continue
        if q.get("exchDisp") in ["OTC Markets", "International Orderbook - London"]:
            continue
        symbol = q.get("symbol")
        name = q.get("longname") or q.get("shortname")
        exchange = q.get("exchDisp")
        country = exchange_countries.get(exchange)

        if country == "United States":
            ticker_text = f"${symbol}"
        else:
            ticker_text = symbol

        if country:
            label = f"{name} · {ticker_text} · {exchange} · {country}"
        else:
            label = f"{name} · {ticker_text} · {exchange}"
        results.append((label, symbol))
    if not results:
        return finnhub_searches(text)
    return results


currencies = ["Original", "USD", "GBP", "EUR"]

home = st.Page("views/home.py", title="Home", default=True)
ticker = st.Page("views/ticker.py", title="Ticker")
valuation = st.Page("views/valuation.py", title="Valuation")
banks = st.Page("views/banks.py", title="Banks")

nav = st.navigation([home, ticker, valuation, banks])

with st.sidebar:
    if nav.title != "Home":
        picked = st_searchbox(search_stocks, placeholder="Search a company or ticker...", key="stock_search")
        if picked:
            st.session_state["ticker"] = picked

    st.session_state["currency"] = st.selectbox("Display currency", currencies)
    st.session_state["source"] = st.radio("Pick a source", ["Yahoo Finance", "Finnhub"], horizontal=True)

nav.run()
