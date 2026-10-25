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

# Custom Styling for clean UI
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 12px;
        border: 1px solid #dee2e6;
    }
</style>
""", unsafe_allow_html=True)

st.title("📊 Nifty Midcap 250 - Daily Price, Valuation & Fundamentals")
st.write("Live CMP, P/E, P/B, ROE, ROCE aur Financial Health ka complete tracker.")

# 1. Official NSE website se Nifty Midcap 250 tickers fetch karna
@st.cache_data(ttl=86400) # Din me ek baar refresh hoga
def load_midcap250_tickers():
    url = "https://archives.nseindia.com/content/indices/ind_nifty_midcap_250_list.csv"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            df_nse = pd.read_csv(io.StringIO(response.text))
            symbols = df_nse['Symbol'].tolist()
            return symbols
    except Exception:
        pass
    
    # Fallback popular midcap stocks agar NSE blocked/rate-limited ho
    return [
        "DIXON", "POLYCAB", "PERSISTENT", "COFORGE", "ASTRAL", "FEDERALBNK",
        "IDFCFIRSTB", "ASHOKLEY", "MAXHEALTH", "BATAINDIA", "VOLTAS", "APOLLOTYRE",
        "JUBLFOOD", "MPHASIS", "BALKRISIND", "GUJGASLTD", "SUPREMEIND", "LTTS",
        "DEEPAKNTR", "AUROPHARMA", "CONCOR", "ESCORTS", "ABCAPITAL", "PAGEIND"
    ]

# 2. Stock fundamentals aur price fetch karne ka function
@st.cache_data(ttl=1800) # Har aadhe ghante (30 min) me price refresh hoga
def fetch_stock_details(symbol_list):
    results = []
    
    # Yahoo Finance ke liye NSE format symbol.NS
    tickers = [f"{s}.NS" for s in symbol_list]
    
    for sym, ticker in zip(symbol_list, tickers):
        try:
            t = yf.Ticker(ticker)
            info = t.info
            
            cmp = info.get("currentPrice") or info.get("regularMarketPrice") or 0.0
            prev_close = info.get("previousClose") or cmp
            pct_change = round(((cmp - prev_close) / prev_close) * 100, 2) if prev_close else 0.0
            
            pe = round(info.get("trailingPE", 0), 2) if info.get("trailingPE") else None
            pb = round(info.get("priceToBook", 0), 2) if info.get("priceToBook") else None
            roe = round(info.get("returnOnEquity", 0) * 100, 2) if info.get("returnOnEquity") else None
            roa = round(info.get("returnOnAssets", 0) * 100, 2) if info.get("returnOnAssets") else None
            mcap = round(info.get("marketCap", 0) / 1e7, 2) if info.get("marketCap") else 0
            debt_to_eq = round(info.get("debtToEquity", 0) / 100, 2) if info.get("debtToEquity") else 0
            
            results.append({
                "Symbol": sym,
                "Company Name": info.get("shortName", sym),
                "CMP (₹)": cmp,
                "Change (%)": pct_change,
                "Market Cap (₹ Cr)": mcap,
                "P/E": pe,
                "P/B": pb,
                "ROE (%)": roe,
                "ROA (%)": roa,
                "Debt/Equity": debt_to_eq,
                "52W High (₹)": info.get("fiftyTwoWeekHigh", 0),
                "52W Low (₹)": info.get("fiftyTwoWeekLow", 0),
                "Sector": info.get("sector", "N/A")
            })
        except Exception:
            continue
            
    return pd.DataFrame(results)

# Load Symbols
with st.spinner("Nifty Midcap 250 company list load ho rahi hai..."):
    all_symbols = load_midcap250_tickers()

# Sidebar: Controls & Filters
st.sidebar.header("🔍 Filters & Search")
search = st.sidebar.text_input("Stock Name ya Symbol search karein:")

# Limit initial batch for quick loading
st.sidebar.subheader("Data Load Options")
stock_count = st.sidebar.slider("Kitne stocks load karne hain?", min_value=10, max_value=min(250, len(all_symbols)), value=50, step=10)

selected_symbols = all_symbols[:stock_count]

with st.spinner(f"{stock_count} stocks ka daily price aur fundamentals fetch ho rahe hain..."):
    df = fetch_stock_details(selected_symbols)

if df.empty:
    st.error("Data load nahi ho paya. Kripya thodi der baad dobara koshish karein.")
    st.stop()

# Search Filter logic
if search:
    df_display = df[df["Symbol"].str.contains(search, case=False) | df["Company Name"].str.contains(search, case=False)]
else:
    df_display = df

# P/E Filter
max_pe = st.sidebar.slider("Maximum P/E (Valuation filter):", min_value=5.0, max_value=120.0, value=80.0)
df_display = df_display[(df_display["P/E"] <= max_pe) | (df_display["P/E"].isna())]

# Top Metrics Row
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Loaded", len(df_display))
c2.metric("Gainers", len(df_display[df_display["Change (%)"] > 0]))
c3.metric("Losers", len(df_display[df_display["Change (%)"] < 0]))
avg_pe = round(df_display["P/E"].dropna().mean(), 1) if not df_display["P/E"].dropna().empty else 0
c4.metric("Avg P/E Ratio", avg_pe)

# Stocks Data Table
st.subheader("📋 Stocks Valuation & Fundamental Table")
st.dataframe(
    df_display.style.format({
        "CMP (₹)": "₹{:,.2f}",
        "Market Cap (₹ Cr)": "₹{:,.0f}",
        "Change (%)": "{:+.2f}%",
        "P/E": "{:.2f}",
        "P/B": "{:.2f}",
        "ROE (%)": "{:.2f}%",
        "ROA (%)": "{:.2f}%",
        "Debt/Equity": "{:.2f}",
        "52W High (₹)": "₹{:,.2f}",
        "52W Low (₹)": "₹{:,.2f}"
    }),
    use_container_width=True,
    height=450
)

# Detailed Stock Deep Dive & Chart
st.markdown("---")
st.subheader("📈 Stock Chart & Deep-Dive Analysis")

stock_picked = st.selectbox("Kisi bhi stock ka detailed chart dekhne ke liye select karein:", df["Symbol"].tolist())

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
            title=f"{stock_picked} - 1 Year Candlestick Price Chart",
            yaxis_title="Price (₹)",
            xaxis_rangeslider_visible=False,
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)
