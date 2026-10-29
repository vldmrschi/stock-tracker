import streamlit as st




st.title("Valuation")

display_currency = st.session_state.get("currency", "Original")
ticker = st.session_state.get("ticker")

if not ticker:
    st.info("Search a company in the sidebar to get started.")
    st.stop()




tab_dcf, tab_comparables, tab_sensitivity, tab_tornado = st.tabs(["DCF", "Comparable Table", "Sensitivity Table", "Tornado Chart"])

with tab_dcf:
    st.write(f"DCF for {ticker}")
with tab_comparables:
    st.write(f"Comparable Table for {ticker}")
with tab_sensitivity:
    st.write(f"Sensitivity Table for {ticker}")
with tab_tornado:
    st.write(f"Tornado Chart for {ticker}")