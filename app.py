import streamlit as st
import yfinance as yf

st.title("Stock Tracker")

ticker = st.text_input("Enter a ticker", "AAPL")

if ticker:
    stock = yf.Ticker(ticker)
    history = stock.history(period="6mo")

    if history.empty:
        st.error("Ticker not found.")
    else:
        latest_price = history["Close"].iloc[-1]
        st.write(f"Latest price: {latest_price:.2f}")
        st.line_chart(history["Close"])
        info = stock.info
        st.write("Company Info:")
        market_cap = info.get("marketCap")
        st.write(f"P/E ratio: {info.get('trailingPE')}")
        st.write(f"52-week high: {info.get('fiftyTwoWeekHigh')}")

        if market_cap:
            st.write(f"Market Cap: {market_cap:,}")
        else:
          st.write("Market Cap: Not available")
    