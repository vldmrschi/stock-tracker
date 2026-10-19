import streamlit as st
import yfinance as yf
import requests
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
        currency = info.get("currency")
        st.subheader(f"{ticker} ({info.get('longName')})")
        latest_price = history["Close"].iloc[-1]
        st.write(f"Latest price: {latest_price:.2f} {currency}")
        st.line_chart(history["Close"])
        st.write("Company Info:")
        market_cap = info.get("marketCap")
        show_stat("P/E Ratio",info.get("trailingPE"))
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
            fcf = stock.cashflow.loc["Free Cash Flow"].iloc[0]
        else:
            fcf = None
        shares_outstanding = info.get("sharesOutstanding")
        total_cash = info.get("totalCash")
        total_debt = info.get("totalDebt")
        if total_cash is None:
            total_cash = 0
        if total_debt is None:
            total_debt = 0

        show_stat("Free Cash Flow (FCF)", fcf)
        show_stat("Shares outstanding", shares_outstanding)
        show_stat("Total Cash", total_cash)
        show_stat("Total Debt", total_debt)
        if fcf and fcf > 0:
            growth = st.slider("FCF growth rate (%)", 0, 20, 5)
            st.write(f"Growth rate: {growth}%")
            wacc = st.slider("WACC (%)", 5, 15, 9)
            st.write(f"WACC: {wacc}%")
            terminal_growth = st.slider("Terminal growth rate (%)", 0, 5, 2)
            st.write(f"Terminal growth rate: {terminal_growth}%")
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
                else:
                    st.info("Value per share can't be calculated. Shares outstanding is missing.")
            else:
                st.error("Terminal growth must be lower than WACC.")

        elif fcf:
            st.warning("FCF is negative, so a DCF isn't meaningful for cash-burning companies. These are usually valued with revenue multiples instead.") 

        else:
            st.info("DCF isn't available for this ticker. Funds and ETFs don't have Free Cash Flow (FCF)")

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
