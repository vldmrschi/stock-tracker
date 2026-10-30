import altair as alt
import pandas as pd
import streamlit as st
from shared import load_company, get_multiples, show_stat

st.title("Valuation")

source = st.session_state.get("source", "Yahoo Finance")
display_currency = st.session_state.get("currency", "Original")
ticker = st.session_state.get("ticker")

if not ticker:
    st.info("Search a company in the sidebar to get started.")
    st.stop()

company = load_company(ticker, source, display_currency)
if company is None:
    st.error("Ticker not found.")
    st.stop()

stock = company["stock"]
history = company["history"]
info = company["info"]
used_finnhub = company["used_finnhub"]
industry = company["industry"]
currency = company["currency"]
fx_rate = company["fx_rate"]
shown_currency = company["shown_currency"]
latest_price = company["latest_price"]
cap_rate = company["cap_rate"]
cap_label = company["cap_label"]
fin_rate = company["fin_rate"]

st.subheader(f"{ticker} ({info.get('longName')})")

def cell_color(value):
    if value is None:
        return ""
    cell_upside = (value - latest_price) / latest_price * 100
    if cell_upside > 10:
        return "background-color: #1E5631; color: white"
    elif cell_upside < -10:
        return "background-color: #8B1A1A; color: white"
    else:
        return "background-color: #4A4A4A; color: white"


def dcf_value(wacc_rate, terminal_rate, growth_rate):
    if wacc_rate <= terminal_rate:
        return None
    projected_fcf = fcf
    total_pv = 0
    for year in range(1, 6):
        projected_fcf = projected_fcf * (1 + growth_rate)
        pv = projected_fcf / (1 + wacc_rate) ** year
        total_pv = total_pv + pv
    terminal_value = projected_fcf * (1 + terminal_rate) / (wacc_rate - terminal_rate)
    pv_terminal = terminal_value / (1 + wacc_rate) ** 5
    enterprise_value = total_pv + pv_terminal
    equity_value = enterprise_value + total_cash - total_debt
    value_per_share = equity_value / shares_outstanding
    if currency == "GBp":
        value_per_share = value_per_share * 100
    return value_per_share



dcf_ready = False

tab_dcf, tab_comparables, tab_sensitivity, tab_tornado = st.tabs(["DCF", "Comparable Table", "Sensitivity Table", "Tornado Chart"])

with tab_dcf:
    st.subheader("DCF Inputs")

    if "Free Cash Flow" in stock.cashflow.index:
        fcf = int(stock.cashflow.loc["Free Cash Flow"].iloc[0])
    else:
        fcf = None
    shares_outstanding = info.get("sharesOutstanding")
    total_cash = info.get("totalCash")
    total_debt = info.get("totalDebt")
    if total_cash is None and total_debt is None:
        total_cash = 0
        total_debt = 0
        if used_finnhub:
            st.warning("Total Cash and Total Debt aren't available on Finnhub, so they are treated as zero. The DCF may be less accurate.")
        else:
            st.warning("Total cash and Total Debt aren't available, so they are treated as zero. The DCF may be less accurate.")
    elif total_cash is None:
        total_cash = 0
        st.warning("Total Cash isn't available, so it's treated as zero. The DCF may be less accurate.")
    elif total_debt is None:
        total_debt = 0
        st.warning("Total Debt isn't available, so it's treated as zero. The DCF may be less accurate.")

    if fcf:
        fcf = fcf * fin_rate
    total_cash = total_cash * fin_rate 
    total_debt = total_debt * fin_rate

    if fcf:
        st.write(f"Free Cash Flow (FCF): {fcf * cap_rate:,.0f} {cap_label}")
    else:
        st.write("Free Cash Flow (FCF): Not Available")

    show_stat("Shares outstanding", shares_outstanding)
    if used_finnhub:
        st.write("Total Cash: Not available on Finnhub.")
        st.write("Total Debt: Not available on Finnhub.")
    else:
        st.write(f"Total Cash: {total_cash * cap_rate:,.0f} {cap_label}")
        st.write(f"Total Debt: {total_debt * cap_rate:,.0f} {cap_label}")


    if industry and "Banks" in industry:
        st.info("FCF isn't meaningful for banks, so a DCF would be misleading. Banks are usually valued on P/B (price-to-book) or with a dividend discount model.")

    elif fcf and fcf > 0:
        growth = st.slider("FCF Growth rate (%)", 0, 20, 5)
        st.write(f"Growth rate: {growth}%")
        wacc = st.slider("WACC (%)", 5, 15, 9)
        st.write(f"WACC: {wacc}%")
        terminal_growth = st.slider("Terminal Growth (TG) rate (%)", 0, 5, 2)
        st.write(f"Terminal Growth (TG) rate: {terminal_growth}%")
        growth_rate = growth / 100
        projected_fcf = fcf
        wacc_rate = wacc / 100
        total_pv = 0

        for year in range(1, 6):
            projected_fcf = projected_fcf * (1 + growth_rate)
            pv = projected_fcf / (1 + wacc_rate) ** year
            total_pv = total_pv + pv
            st.write(f"Year {year}: FCF {projected_fcf * cap_rate:,.0f} {cap_label} · PV {pv * cap_rate:,.0f} {cap_label}")
        st.write(f"Sum of PVs: {total_pv * cap_rate:,.0f} {cap_label}")

        terminal_rate = terminal_growth / 100
        if wacc > terminal_growth:
            terminal_value = projected_fcf * (1 + terminal_rate) / (wacc_rate - terminal_rate)
            st.write(f"Terminal value: {terminal_value * cap_rate:,.0f} {cap_label}")
            pv_terminal = terminal_value / (1 + wacc_rate) ** 5
            st.write(f"PV of terminal value: {pv_terminal * cap_rate:,.0f} {cap_label}")
            enterprise_value = total_pv + pv_terminal
            st.write(f"Enterprise value: {enterprise_value * cap_rate:,.0f} {cap_label}")
            equity_value = enterprise_value + total_cash - total_debt
            st.write(f"Equity Value: {equity_value * cap_rate:,.0f} {cap_label}")
            if shares_outstanding:
                value_per_share = equity_value / shares_outstanding
                if currency == "GBp":
                    value_per_share = value_per_share * 100
                st.write(f"Value per share: {value_per_share * fx_rate:.2f} {shown_currency}")
                st.write(f"Current price: {latest_price * fx_rate:.2f} {shown_currency}")
                upside = (value_per_share - latest_price) / latest_price * 100
                if upside > 10:
                    st.success(f"Upside: {upside:.1f}%. The stock looks undervalued.")
                elif upside < -10:
                    st.error(f"Downside: {upside:.1f}%. The stock looks overvalued.")
                else:
                    st.info(f"Upside: {upside:.1f}%. The stock looks fairly valued.")
                dcf_ready = True

            else:
                st.info("Value per share can't be calculated. Shares outstanding is missing.")
        else:
            st.error("Terminal Growth must be lower than WACC.")

    elif fcf:
        st.warning("FCF is negative, so a DCF isn't meaningful for cash-burning companies. These are usually valued with revenue multiples instead.") 

    else:
        st.info("DCF isn't available for this ticker. Funds and ETFs don't have Free Cash Flow (FCF)")




with tab_comparables:
    st.subheader("Comparable Companies Table")
    peers= st.text_input("Enter peer tickers, separated by commas", "MSFT, GOOGL, META")
    clean_peers = []
    for p in peers.split(","):
        p = p.strip().upper()
        if p:
            clean_peers.append(p)
    comps_table = []
    for peer in clean_peers:
        row = get_multiples(peer)
        comps_table.append(row)

    peers_df = pd.DataFrame(comps_table, columns=["P/E", "EV/EBITDA", "EV/Revenue"])
    median_row = peers_df.median().tolist()
    comps_table.append(median_row)


    row_ticker = get_multiples(ticker)
    comps_table.append(row_ticker)

    comps = pd.DataFrame(comps_table, index=clean_peers + ["Peer Median", ticker], columns=["P/E", "EV/EBITDA", "EV/Revenue"])
    highlight = ([ticker], comps.columns)
    styled = comps.style.format("{:.2f}", na_rep="n/a").set_properties(subset=highlight, **{"background-color": "#1F3864", "color": "white"})
    st.dataframe(styled)

    median_pe = median_row[0]
    eps = info.get("trailingEps")
    if eps is None:
        st.info("There is no EPS data, the calculation cannot happen.")
    elif eps <= 0:
        st.info("This is a loss-making company, so a P/E-based value isn't meaningful.")
    else:
        eps = eps * fin_rate
        implied_price = median_pe * eps
        if currency == "GBp":
            implied_price = implied_price * 100
        st.write(f"Implied price: {implied_price * fx_rate:.2f} {shown_currency}")
        comps_upside = (implied_price - latest_price) / latest_price * 100
        if comps_upside > 10:
            st.success(f"Upside: {comps_upside:.1f}%. Based on peer P/E.")
        elif comps_upside < -10:
            st.error(f"Downside: {comps_upside:.1f}%. Based on peer P/E.")
        else:
            st.info(f"Upside: {comps_upside:.1f}%. Looks fairly valued based on peer P/E.")





with tab_sensitivity:
    if not dcf_ready:
        st.info("The sensitivity table needs a valid DCF. Check the DCF tab.")
    else:
        wacc_values = [wacc - 2, wacc - 1, wacc, wacc + 1, wacc + 2]
        tg_values = [terminal_growth - 1, terminal_growth - 0.5, terminal_growth, terminal_growth + 0.5, terminal_growth + 1]


        st.subheader("Sensitivity Analysis Table")

        table = []
        for w in wacc_values:
            row = []
            for t in tg_values:
                cell = dcf_value(w / 100, t / 100, growth_rate)
                row.append(cell)
            table.append(row)

        row_labels = []
        for w in wacc_values:
            row_labels.append(f"WACC {w}%")

        col_labels = []
        for t in tg_values:
            col_labels.append(f"TG {t}%")

        sensitivity = pd.DataFrame(table, index=row_labels, columns=col_labels)
        centre = ([row_labels[2]], [col_labels[2]])
        styled = sensitivity.style.format(lambda v: f"{v * fx_rate:.2f}", na_rep="n/a").map(cell_color).set_properties(subset=centre, **{"background-color": "#1F3864", "color": "white"})
        st.dataframe(styled)

with tab_tornado:
    if not dcf_ready:
        st.info("The tornado chart needs a valid DCF. Check the DCF tab.")
    else:
        growth_low = dcf_value(wacc_rate, terminal_rate, growth_rate-0.02)
        growth_high = dcf_value(wacc_rate, terminal_rate, growth_rate+0.02)
        tg_low = dcf_value(wacc_rate, terminal_rate-0.005, growth_rate)
        tg_high = dcf_value(wacc_rate, terminal_rate+0.005, growth_rate)
        wacc_low = dcf_value(wacc_rate-0.01, terminal_rate, growth_rate)
        wacc_high = dcf_value(wacc_rate+0.01, terminal_rate, growth_rate)

        st.subheader("Tornado Chart")

        if None in [growth_low, growth_high, wacc_low, wacc_high, tg_low, tg_high]:
            st.info("The Tornado Chart can't be drawn: WACC and terminal growth are too close together, so some scenarios have no valid value. Try a higher WACC or a lower terminal growth rate.")
        else:
            tornado = pd.DataFrame([[growth_low, growth_high], [wacc_high, wacc_low], [tg_low, tg_high]], index=["FCF Growth", "WACC", "Terminal Growth"], columns=["Low", "High"])
            tornado["Low"] = tornado["Low"] * fx_rate
            tornado["High"] = tornado["High"] * fx_rate
            tornado["Swing"] = tornado["High"] - tornado["Low"]
            tornado = tornado.sort_values("Swing", ascending=False)
            tornado = tornado.reset_index(names="Input")
            styled_tornado = tornado.style.format("{:.2f}", subset=["Low", "High", "Swing"])
            st.dataframe(styled_tornado, hide_index=True)

            chart = alt.Chart(tornado).mark_bar(color="#1F3864").encode(x=alt.X("Low", title=f"Value per share ({shown_currency})", scale=alt.Scale(zero=False)), x2="High", y=alt.Y("Input", sort=None, title=None),)

            base = pd.DataFrame({"Base": [value_per_share * fx_rate]})
            line = alt.Chart(base).mark_rule(color="white").encode(x="Base")

            st.altair_chart(chart + line, use_container_width=True)
