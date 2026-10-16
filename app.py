import streamlit as st
import yfinance as yf
import requests
from datetime import date, timedelta, datetime
from zoneinfo import ZoneInfo


api_key = st.secrets.get("FINNHUB_API_KEY")

def show_stat(label,value):
    if value:
        st.write(f"{label}: {value}")
    else:
        st.write(f"{label}: Not Available")


st.title("Stock Tracker")
st.write(date.today().strftime("%d %B %Y"))

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

        st.subheader("Latest Earnings")
        earnings = stock.earnings_dates

        if earnings is None:
            st.info("Earnings data isn't available for this ticker. Funds and ETFs don't report earnings.")
        else:
            past_earnings = earnings.dropna().head(4)
            latest_date = past_earnings.index.date[0]
            days_old = (date.today()-latest_date).days

            if days_old > 365:
                st.info(f"The most recent earnings data is from {latest_date.strftime("%d %B %Y")}, so it's too old to show.")
            else:
                beats = 0
                for earnings_date, row in past_earnings.iterrows():
                    nice_date = earnings_date.strftime("%d %B %Y")

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
        else:
            for article in news[:5]:
                st.markdown(f"**{article.get('headline')}**")
                published = datetime.fromtimestamp(article.get("datetime"), ZoneInfo("Europe/London"))
                published = published.strftime("%d %B %Y, %H:%M")
                st.write(f"{article.get('source')} · {published}")
                st.write(article.get("summary"))
                st.markdown(f"[Read more]({article.get('url')})")