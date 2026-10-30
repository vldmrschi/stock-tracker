import streamlit as st
import requests
from datetime import date, timedelta, datetime
from zoneinfo import ZoneInfo
from shared import load_company, show_stat

api_key = st.secrets.get("FINNHUB_API_KEY")


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









st.title("Ticker")

st.write(format_date(date.today()))

source = st.session_state.get("source", "Yahoo Finance")
display_currency = st.session_state.get("currency", "Original")
ticker = st.session_state.get("ticker")

if not ticker:
    st.info("Search a company in the sidebar to get started.")
    st.stop()

periods = {"1 month": "1mo", "3 months": "3mo", "6 months": "6mo", "1 year": "1y", "5 years": "5y"}
ch_period = st.selectbox("Pick a chart period", periods, index=2)

company = load_company(ticker, source, display_currency, periods[ch_period])
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


if market_cap:
    st.write(f"Market Cap: {market_cap * cap_rate:,.0f} {cap_label}")
else:
    st.write("Market Cap: Not Available")


calendar = stock.calendar
earnings_date = calendar.get("Earnings Date")
if earnings_date:
    st.write(f"Next earnings date: {earnings_date[0]}")
else:
    st.write("Next earnings date: Not Available")




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
