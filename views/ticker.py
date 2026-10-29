import altair as alt
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









st.title("Stock Tracker")

st.write(format_date(date.today()))

source = st.radio("Pick a source", ["Yahoo Finance", "Finnhub"], horizontal=True)

display_currency = st.session_state.get("currency", "Original")

ticker = st.session_state.get("ticker")

if not ticker:
    st.info("Search a company in the sidebar to get started.")
    st.stop()

if ticker:
    stock = yf.Ticker(ticker)

    periods = {"1 month": "1mo", "3 months": "3mo", "6 months": "6mo", "1 year": "1y", "5 years": "5y"}
    ch_period = st.selectbox("Pick a chart period", periods, index=2)
    history = stock.history(period=periods[ch_period])


    if history.empty:
        st.error("Ticker not found.")
    else:
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
        st.subheader(f"{ticker} ({info.get('longName')})")
        latest_price = history["Close"].dropna().iloc[-1]

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

        st.write(f"Latest price: {latest_price * fx_rate:.2f} {shown_currency}")
        st.line_chart(history["Close"] * fx_rate)
        st.write("Company Info:")
        market_cap = info.get("marketCap")
        pe = info.get("trailingPE")
        if pe:
            pe = round(pe, 2)
        
        show_stat("P/E Ratio", pe)
        
        fifty_two_week_high = info.get("fiftyTwoWeekHigh")
        if fifty_two_week_high is None:
            st.write("52-week high: Not Available")
        else:
            st.write(f"52-week high: {fifty_two_week_high * fx_rate:.2f} {shown_currency}")


        show_stat("Dividend Yield (%)", info.get("dividendYield"))


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
        if market_cap:
            st.write(f"Market Cap: {market_cap * cap_rate:,.0f} {cap_label}")
        else:
            st.write("Market Cap: Not Available")

        fin_currency = info.get("financialCurrency") or cap_currency
        fin_rate = get_fx_rate(fin_currency, cap_currency)
        if fin_rate is None:
            st.warining("The company's accounts couldn't be converted into its share currency, so the DCF may be inaccurate.")
            fin_rate = 1
        


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
                    
                    wacc_values = [wacc - 2, wacc - 1, wacc, wacc + 1, wacc + 2]
                    tg_values = [terminal_growth - 1, terminal_growth - 0.5, terminal_growth, terminal_growth + 0.5, terminal_growth + 1]


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

                else:
                    st.info("Value per share can't be calculated. Shares outstanding is missing.")
            else:
                st.error("Terminal Growth must be lower than WACC.")

        elif fcf:
            st.warning("FCF is negative, so a DCF isn't meaningful for cash-burning companies. These are usually valued with revenue multiples instead.") 

        else:
            st.info("DCF isn't available for this ticker. Funds and ETFs don't have Free Cash Flow (FCF)")



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




        st.subheader("Latest Earnings")

        try:
            earnings = stock.earnings_dates
        except Exception:
            earnings = None

        if earnings is None:
            st.info("Earnings data isn't available for this ticker right now. Funds and ETFs don't report earnings, and for companies the data source may be temporarily unavailable.")
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

        from_date = st.date_input("News from", week_ago)
        to_date = st.date_input("News until", today)

        num_articles = st.slider("Number of articles", 1, 20, 5)
        sort_order = st.radio("Sort articles", ["Newest first", "Oldest first"], horizontal=True)

        st.subheader("Latest News")

        if from_date > to_date:
            st.error("The 'News from' date must be on or before the 'News until' date. Please adjust your dates.")
        else:
            params = {"symbol": ticker, "from": str(from_date), "to": str(to_date), "token": api_key}
            response = requests.get("https://finnhub.io/api/v1/company-news", params=params)
            news = response.json()


            if "error" in news:
                st.info("News isn't available for this ticker. News is currently only supported for companies listed in North America.")
            elif len(news) == 0:
                st.info(f"No news for this ticker between {format_date(from_date)} and {format_date(to_date)}.")
            else:
                if sort_order == "Newest first":
                    news = sorted(news, key=lambda article: article["datetime"], reverse=True)
                else:
                    news = sorted(news, key=lambda article: article["datetime"])
                for article in news[:num_articles]:
                    st.markdown(f"**{article.get('headline')}**".replace("$", "\\$"))
                    published = datetime.fromtimestamp(article.get("datetime"), ZoneInfo("Europe/London"))
                    published = f"{format_date(published)}, {published.strftime('%H:%M')}"
                    st.write(f"{article.get('source')} · {published}")
                    st.write(article.get("summary").replace("$", "\\$"))
                    st.markdown(f"[Read more]({article.get('url')})")
