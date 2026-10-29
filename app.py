import streamlit as st

st.set_page_config(page_title="Valtide", layout="wide")

home = st.Page("views/home.py", title="Home", default=True)
ticker = st.Page("views/ticker.py", title="Ticker")
valuation = st.Page("views/valuation.py", title="Valuation")
banks = st.Page("views/banks.py", title="Banks")

nav = st.navigation([home, ticker, valuation, banks])