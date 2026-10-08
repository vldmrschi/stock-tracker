import streamlit as st
import yfinance as yf

st.title("Stock Tracker")

ticker = st.text_input("Enter a ticker", "AAPL")

if ticker:
    stock = yf.Ticker(ticker)
    history = stock.history(period="5d")

    if history.empty:
        st.write("Ticker not found.")
    else:
        latest_price = history["Close"].iloc[-1]
        st.write(f"Latest price: {latest_price:.2f}")