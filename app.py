from altair import param
import streamlit as st
import yfinance as yf
import requests
import pandas as pd
from datetime import date, timedelta, datetime
from zoneinfo import ZoneInfo


api_key = st.secrets.get("FINNHUB_API_KEY")

def show_stat(label,value):
    if value:
        st.write(f"{label}: {value:,}")
    else:
        st.write(f"{label}: Not Available")

def day_suffix(day):
    if day in [11, 12, 13]:
        return "th"
    elif day % 10 == 1:
        return "st"
    elif day % 10 == 2:
        return "nd"
    elif day % 10 == 3:
        return "rd"
    else:
        return "th"
    
def format_date(d):
    return f"{d.day}{day_suffix(d.day)} {d.strftime('%B %Y')}"

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

    return {"longName": profile.get("name"), "currency": profile.get("currency"), "marketCap": market_cap, "sharesOutstanding": shares, "trailingPE": m.get("peTTM"), "fiftyTwoWeekHigh": m.get("52WeekHigh"), "dividendYield": m.get("dividendYieldIndicatedAnnual")}





st.title("Stock Tracker")
st.write(format_date(date.today()))

ticker = st.text_input("Enter a ticker", "AAPL")
ticker = ticker.strip().upper()

if ticker:
    stock = yf.Ticker(ticker)
    history = stock.history(period="6mo")

    if history.empty:
        st.error("Ticker not found.")
    else:
        info = stock.info
        if not info.get("currency"):
            info = finnhub_info(ticker)
            st.warning("Yahoo Finance isn't responding, so this data comes from Finnhub (US stocks only).")
        industry = info.get("industry")
        currency = info.get("currency")
        st.subheader(f"{ticker} ({info.get('longName')})")
        latest_price = history["Close"].iloc[-1]
        st.write(f"Latest price: {latest_price:.2f} {currency}")
        st.line_chart(history["Close"])
        st.write("Company Info:")
        market_cap = info.get("marketCap")
        pe = info.get("trailingPE")
        if pe:
            pe = round(pe, 2)
        show_stat("P/E Ratio", pe)
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




        st.subheader("DCF Inputs")

        if "Free Cash Flow" in stock.cashflow.index:
            fcf = int(stock.cashflow.loc["Free Cash Flow"].iloc[0])
        else:
            fcf = None
        shares_outstanding = info.get("sharesOutstanding")
        total_cash = info.get("totalCash")
        total_debt = info.get("totalDebt")
        if total_cash is None:
            total_cash = 0
            st.warning("Total cash isn't available, so it's treated as zero. The DCF may be less accurate.")
        if total_debt is None:
            total_debt = 0
            st.warning("Total debt isn't available, so it's treated as zero. The DCF may be less accurate.")

        show_stat("Free Cash Flow (FCF)", fcf)
        show_stat("Shares outstanding", shares_outstanding)
        show_stat("Total Cash", total_cash)
        show_stat("Total Debt", total_debt)

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
                st.write(f"Year {year}: FCF {projected_fcf:,.0f} {cap_currency} · PV {pv:,.0f} {cap_currency}")
            st.write(f"Sum of PVs: {total_pv:,.0f} {cap_currency}")

            terminal_rate = terminal_growth / 100
            if wacc > terminal_growth:
                terminal_value = projected_fcf * (1 + terminal_rate) / (wacc_rate - terminal_rate)
                st.write(f"Terminal value: {terminal_value:,.0f} {cap_currency}")
                pv_terminal = terminal_value / (1 + wacc_rate) ** 5
                st.write(f"PV of terminal value: {pv_terminal:,.0f} {cap_currency}")
                enterprise_value = total_pv + pv_terminal
                st.write(f"Enterprise value: {enterprise_value:,.0f} {cap_currency}")
                equity_value = enterprise_value + total_cash - total_debt
                st.write(f"Equity Value: {equity_value:,.0f} {cap_currency}")
                if shares_outstanding:
                    value_per_share = equity_value / shares_outstanding
                    if currency == "GBp":
                        value_per_share = value_per_share * 100
                    st.write(f"Value per share: {value_per_share:.2f} {currency}")
                    st.write(f"Current price: {latest_price:.2f} {currency}")
                    upside = (value_per_share - latest_price) / latest_price * 100
                    if upside > 0:
                        st.success(f"Upside: {upside:.1f}%. The stock looks undervalued.")
                    else:
                        st.error(f"Downside: {upside:.1f}%. The stock looks overvalued.")
                    
                    wacc_values = [wacc - 2, wacc - 1, wacc, wacc + 1, wacc + 2]
                    tg_values = [terminal_growth - 1, terminal_growth - 0.5, terminal_growth, terminal_growth + 0.5, terminal_growth + 1]

                    def dcf_value(wacc_rate, terminal_rate):
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
                    
                    
                    st.subheader("Sensitivity Analysis Table")

                    table = []
                    for w in wacc_values:
                        row = []
                        for t in tg_values:
                            cell = dcf_value(w / 100, t / 100)
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
                    styled = sensitivity.style.format("{:.2f}", na_rep="n/a").set_properties(subset=centre, **{"background-color": "#1F3864", "color": "white"})
                    st.dataframe(styled)
                

                



                else:
                    st.info("Value per share can't be calculated. Shares outstanding is missing.")
            else:
                st.error("Terminal growth must be lower than WACC.")

        elif fcf:
            st.warning("FCF is negative, so a DCF isn't meaningful for cash-burning companies. These are usually valued with revenue multiples instead.") 

        else:
            st.info("DCF isn't available for this ticker. Funds and ETFs don't have Free Cash Flow (FCF)")


        st.subheader("Comparable Companies")
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

        row_ticker = get_multiples(ticker)
        comps_table.append(row_ticker)
        
        comps = pd.DataFrame(comps_table, index=clean_peers + [ticker], columns=["P/E", "EV/EBITDA", "EV/Revenue"])
        highlight = ([ticker], comps.columns)
        styled = comps.style.format("{:.2f}", na_rep="n/a").set_properties(subset=highlight, **{"background-color": "#1F3864", "color": "white"})
        st.dataframe(styled)


        st.subheader("Latest Earnings")

        earnings = stock.earnings_dates

        if earnings is None:
            st.info("Earnings data isn't available for this ticker. Funds and ETFs don't report earnings.")
        else:
            past_earnings = earnings.dropna().head(4)
            latest_date = past_earnings.index.date[0]
            days_old = (date.today()-latest_date).days

            if days_old > 365:
                st.info(f"The most recent earnings data is from {format_date(latest_date)}, so it's too old to show.")
            else:
                beats = 0
                for earnings_date, row in past_earnings.iterrows():
                    nice_date = format_date(earnings_date)

                    if row["Reported EPS"] > row["EPS Estimate"]:
                        result = "Beat"
                        beats = beats + 1
                    elif row["Reported EPS"] == row["EPS Estimate"]:
                        result = "In line"
                    else:
                        result = "Miss"

                    st.markdown(f"**{nice_date}** · Estimate {row['EPS Estimate']} · Reported {row['Reported EPS']} · **{result}**")
                st.write(f"Beat {beats} of the last {len(past_earnings)} quarters")



        today = date.today()
        week_ago = today - timedelta(days=7)

        params = {"symbol": ticker, "from": str(week_ago), "to": str(today), "token": api_key}
        response = requests.get("https://finnhub.io/api/v1/company-news", params=params)
        news = response.json()




        st.subheader("Latest News")
        if "error" in news:
            st.info("News isn't available for this ticker. News is currently only supported for companies listed in North America.")
        elif len(news) == 0:
            st.info("No news for this ticker in the last 7 days.")
        else:
            for article in news[:5]:
                st.markdown(f"**{article.get('headline')}**")
                published = datetime.fromtimestamp(article.get("datetime"), ZoneInfo("Europe/London"))
                published = f"{format_date(published)}, {published.strftime('%H:%M')}"
                st.write(f"{article.get('source')} · {published}")
                st.write(article.get("summary"))
                st.markdown(f"[Read more]({article.get('url')})")
