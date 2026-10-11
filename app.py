import streamlit as st
import yfinance as yf
import requests

api_key = st.secrets.get("FINNHUB_API_KEY")

def show_stat(label,value):
    if value:
        st.write(f"{label}: {value}")
    else:
        st.write(f"{label}: Not Available")


st.title("Stock Tracker")

ticker = st.text_input("Enter a ticker", "AAPL")
ticker = ticker.strip().upper()

if ticker:
    stock = yf.Ticker(ticker)
    history = stock.history(period="6mo")

    if history.empty:
        st.error("Ticker not found.")
    else:
        info = stock.info
        currency = info.get("currency")
        st.subheader(f"{ticker} ({info.get('longName')})")
        latest_price = history["Close"].iloc[-1]
        st.write(f"Latest price: {latest_price:.2f} {currency}")
        st.line_chart(history["Close"])
        st.write("Company Info:")
        market_cap = info.get("marketCap")
        show_stat("P/E ratio",info.get("trailingPE"))
        show_stat("52-week high", info.get("fiftyTwoWeekHigh"))
        show_stat("Dividend Yield (%)", info.get("dividendYield"))

        if currency == "GBp":
            cap_currency = "GBP"
        else:
            cap_currency = currency
        
        if market_cap:
            st.write(f"Market Cap: {market_cap:,} {cap_currency}")
        else:
            st.write("Market Cap: Not Available")

        calendar = stock.calendar
        earnings_date = calendar.get("Earnings Date")
        
        if earnings_date:
            st.write(f"Next earnings date: {earnings_date[0]}")
        else:
            st.write("Next earnings date: Not Available")

        params = {"symbol": ticker, "from": "2026-10-01", "to": "2026-10-10", "token": api_key}
        response = requests.get("https://finnhub.io/api/v1/company-news", params=params)
        news = response.json()

        st.subheader("Latest News")
        for article in news[:5]:
            st.markdown(f"**{article.get('headline')}**")
            st.write(article.get("summary"))
            st.markdown(f"[Read more]({article.get('url')})")

