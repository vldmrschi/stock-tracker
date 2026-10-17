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

        fcf = info.get("freeCashflow")
        shares_outstanding = info.get("sharesOutstanding")
        total_cash = info.get("totalCash")
        total_debt = info.get("totalDebt")


        show_stat("Free Cash Flow (FCF)", fcf)
        show_stat("Shares outstanding", shares_outstanding)
        show_stat("Total Cash", total_cash)
        show_stat("Total Debt", total_debt)
        if fcf:
            growth = st.slider("FCF growth rate (%)", 0, 20, 5)
            st.write(f"Growth rate: {growth}%")
            wacc = st.slider("WACC (%)", 5, 15, 9)
            st.write(f"WACC: {wacc}%")
            terminal_growth = st.slider("Terminal growth rate (%)", 0, 5, 2)
            st.write(f"Terminal growth rate: {terminal_growth}%")
            growth_rate = growth / 100
            projected_fcf = fcf
            for year in range(1, 6):
                projected_fcf = projected_fcf * (1 + growth_rate)
                st.write(f"Year {year}: {projected_fcf:,.0f}")

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
