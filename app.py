import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import plotly.graph_objects as go
import io

st.set_page_config(
    page_title="Nifty Midcap 250 Stock Analyzer", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

st.title("📊 Nifty Midcap 250 - Daily Price, Valuation & Fundamentals")
st.write("Live CMP, P/E, P/B, ROE, ROCE aur Financial Health ka complete tracker.")

# 1. Fetch Official Tickers from NSE or Fallback
@st.cache_data(ttl=86400)
def load_midcap250_tickers():
    url = "https://archives.nseindia.com/content/indices/ind_nifty_midcap_250_list.csv"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            df_nse = pd.read_csv(io.StringIO(response.text))
            if 'Symbol' in df_nse.columns:
                return df_nse['Symbol'].dropna().tolist()
    except Exception:
        pass
    
    # Fallback popular stocks list
    return [
        "DIXON", "POLYCAB", "PERSISTENT", "COFORGE", "ASTRAL", "FEDERALBNK",
        "IDFCFIRSTB", "ASHOKLEY", "MAXHEALTH", "BATAINDIA", "VOLTAS", "APOLLOTYRE",
        "JUBLFOOD", "MPHASIS", "BALKRISIND", "GUJGASLTD", "SUPREMEIND", "LTTS",
        "DEEPAKNTR", "AUROPHARMA", "CONCOR", "ESCORTS", "ABCAPITAL", "PAGEIND"
    ]

# 2. Fetch stock data with safe null-handling
@st.cache_data(ttl=1800)
def fetch_stock_details(symbol_list):
    results = []
    
    for sym in symbol_list:
        try:
            ticker_str = f"{sym}.NS"
            t = yf.Ticker(ticker_str)
            info = t.info
            
            # Safe numeric conversion
            def safe_num(val, multiplier=1.0):
                if val is not None and isinstance(val, (int, float)):
                    return round(val * multiplier, 2)
                return None

            cmp = safe_num(info.get("currentPrice") or info.get("regularMarketPrice") or 0.0)
            prev_close = safe_num(info.get("previousClose") or cmp)
            
            pct_change = 0.0
            if prev_close and cmp:
                pct_change = round(((cmp - prev_close) / prev_close) * 100, 2)

            mcap_val = info.get("marketCap")
            mcap = round(mcap_val / 1e7, 2) if mcap_val else None

            results.append({
                "Symbol": sym,
                "Company Name": info.get("shortName", sym),
                "CMP (₹)": cmp,
                "Change (%)": pct_change,
                "Market Cap (₹ Cr)": mcap,
                "P/E": safe_num(info.get("trailingPE")),
                "P/B": safe_num(info.get("priceToBook")),
                "ROE (%)": safe_num(info.get("returnOnEquity"), 100.0),
                "ROA (%)": safe_num(info.get("returnOnAssets"), 100.0),
                "Debt/Equity": safe_num(info.get("debtToEquity"), 0.01),
                "52W High (₹)": safe_num(info.get("fiftyTwoWeekHigh")),
                "52W Low (₹)": safe_num(info.get("fiftyTwoWeekLow")),
                "Sector": info.get("sector", "N/A")
            })
        except Exception:
            continue
            
    return pd.DataFrame(results)

# Load Symbols
with st.spinner("Nifty Midcap list load ho rahi hai..."):
    all_symbols = load_midcap250_tickers()

# Sidebar: Controls
st.sidebar.header("🔍 Filters & Options")
search = st.sidebar.text_input("Stock Name ya Symbol search karein:")

stock_count = st.sidebar.slider(
    "Kitne stocks load karne hain?", 
    min_value=10, 
    max_value=min(250, len(all_symbols)), 
    value=50, 
    step=10
)

selected_symbols = all_symbols[:stock_count]

with st.spinner(f"{stock_count} stocks ka data fetch ho raha hai..."):
    df = fetch_stock_details(selected_symbols)

if df.empty:
    st.error("Data load nahi ho saka, kripya page refresh karein.")
    st.stop()

# Search Filter
if search:
    df_display = df[df["Symbol"].str.contains(search, case=False) | df["Company Name"].str.contains(search, case=False)]
else:
    df_display = df

# Max P/E Filter
max_pe = st.sidebar.slider("Maximum P/E Filter:", min_value=5.0, max_value=150.0, value=90.0)
df_display = df_display[(df_display["P/E"] <= max_pe) | (df_display["P/E"].isna())]

# Top Metrics Row
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Loaded", len(df_display))
c2.metric("Gainers Today", len(df_display[df_display["Change (%)"] > 0]))
c3.metric("Losers Today", len(df_display[df_display["Change (%)"] < 0]))
avg_pe = round(df_display["P/E"].dropna().mean(), 1) if not df_display["P/E"].dropna().empty else 0
c4.metric("Avg P/E Ratio", avg_pe)

# Clean, safe Streamlit Table display (No TypeError)
st.subheader("📋 Stocks Valuation & Fundamental Table")
st.dataframe(
    df_display,
    column_config={
        "CMP (₹)": st.column_config.NumberColumn(format="₹%.2f"),
        "Change (%)": st.column_config.NumberColumn(format="%.2f%%"),
        "Market Cap (₹ Cr)": st.column_config.NumberColumn(format="₹%d"),
        "P/E": st.column_config.NumberColumn(format="%.2f"),
        "P/B": st.column_config.NumberColumn(format="%.2f"),
        "ROE (%)": st.column_config.NumberColumn(format="%.2f%%"),
        "ROA (%)": st.column_config.NumberColumn(format="%.2f%%"),
        "Debt/Equity": st.column_config.NumberColumn(format="%.2f"),
        "52W High (₹)": st.column_config.NumberColumn(format="₹%.2f"),
        "52W Low (₹)": st.column_config.NumberColumn(format="₹%.2f"),
    },
    use_container_width=True,
    height=450
)

# Detailed Candlestick Chart
st.markdown("---")
st.subheader("📈 Stock Price Chart (1 Year)")

stock_picked = st.selectbox("Stock select karein:", df["Symbol"].tolist())

if stock_picked:
    ticker_obj = yf.Ticker(f"{stock_picked}.NS")
    hist_data = ticker_obj.history(period="1y")
    
    if not hist_data.empty:
        fig = go.Figure(data=[go.Candlestick(
            x=hist_data.index,
            open=hist_data['Open'],
            high=hist_data['High'],
            low=hist_data['Low'],
            close=hist_data['Close'],
            name="Price"
        )])
        fig.update_layout(
            title=f"{stock_picked} - 1 Year Candlestick Chart",
            yaxis_title="Price (₹)",
            xaxis_rangeslider_visible=False,
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)
