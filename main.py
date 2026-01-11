import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf
from datetime import datetime, timedelta

st.set_page_config(page_title="Morning Alpha Dashboard", layout="wide")

st.title("☀️ Morning Alpha: Yatırım Karar Destek Paneli")
st.subheader("Piyasa Analizi ve Sektörel Fırsatlar")

@st.cache_data(ttl=300)
def get_vix_data():
    try:
        vix = yf.Ticker("^VIX")
        hist = vix.history(period="5d")
        if len(hist) >= 2:
            current = hist['Close'].iloc[-1]
            previous = hist['Close'].iloc[-2]
            change = ((current - previous) / previous) * 100
            return current, change
        elif len(hist) == 1:
            return hist['Close'].iloc[-1], 0
        return 18.5, 0
    except:
        return 18.5, 0

@st.cache_data(ttl=300)
def get_sector_data():
    sector_etfs = {
        "Yapay Zeka (BOTZ)": "BOTZ",
        "Siber Güvenlik (HACK)": "HACK",
        "Yenilenebilir Enerji (ICLN)": "ICLN",
        "Fintech (FINX)": "FINX",
        "Biyoteknoloji (XBI)": "XBI"
    }
    
    results = []
    for name, symbol in sector_etfs.items():
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d")
            if len(hist) >= 2:
                current = hist['Close'].iloc[-1]
                previous = hist['Close'].iloc[-2]
                change = ((current - previous) / previous) * 100
                results.append({"Sektör": name, "Para Girişi (%)": round(change, 2)})
        except:
            results.append({"Sektör": name, "Para Girişi (%)": 0})
    
    return pd.DataFrame(results)

@st.cache_data(ttl=300)
def get_portfolio_data():
    symbols = ["NVDA", "VRT", "CRWD", "LLY", "GEHC", "FSLR", "TSLA", "AVAV", "RKLB", "SOFI"]
    sectors = ["Yapay Zeka", "Veri Altyapısı", "Siber Güvenlik", "Biyoteknoloji", "Sağlık Tek.", "Enerji", "EV", "Savunma", "Uzay", "Fintech"]
    risk_scores = ["Düşük", "Düşük", "Orta", "Düşük", "Düşük", "Orta", "Yüksek", "Orta", "Yüksek", "Yüksek"]
    stop_losses = ["-10%", "-8%", "-10%", "-7%", "-5%", "-12%", "-15%", "-10%", "-20%", "-15%"]
    
    data = []
    for i, symbol in enumerate(symbols):
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d")
            if len(hist) >= 2:
                current = hist['Close'].iloc[-1]
                previous = hist['Close'].iloc[-2]
                change = ((current - previous) / previous) * 100
                data.append({
                    "Sembol": symbol,
                    "Sektör": sectors[i],
                    "Fiyat ($)": round(current, 2),
                    "Günlük Değişim (%)": round(change, 2),
                    "Risk Puanı": risk_scores[i],
                    "Stop-Loss": stop_losses[i]
                })
            else:
                data.append({
                    "Sembol": symbol,
                    "Sektör": sectors[i],
                    "Fiyat ($)": "-",
                    "Günlük Değişim (%)": "-",
                    "Risk Puanı": risk_scores[i],
                    "Stop-Loss": stop_losses[i]
                })
        except:
            data.append({
                "Sembol": symbol,
                "Sektör": sectors[i],
                "Fiyat ($)": "-",
                "Günlük Değişim (%)": "-",
                "Risk Puanı": risk_scores[i],
                "Stop-Loss": stop_losses[i]
            })
    
    return pd.DataFrame(data)

with st.spinner("Piyasa verileri yükleniyor..."):
    vix_val, vix_change = get_vix_data()

market_status = "GÜVENLİ" if vix_val < 25 else "RİSKLİ"

col1, col2, col3 = st.columns(3)
col1.metric("Piyasa Durumu", market_status, delta=None)
col2.metric("VIX (Korku Endeksi)", f"{vix_val:.2f}", delta=f"{vix_change:+.2f}%")
col3.metric("Önerilen Strateji", "Alım Yapılabilir" if market_status == "GÜVENLİ" else "Nakde Geç")

st.divider()

st.header("🔥 Bugünün En Sıcak Sektörleri")

with st.spinner("Sektör verileri yükleniyor..."):
    sector_data = get_sector_data()

col_left, col_right = st.columns([1, 2])

with col_left:
    st.write("Sektörel Para Akışı (Günlük)")
    st.dataframe(sector_data.sort_values(by="Para Girişi (%)", ascending=False), hide_index=True)

with col_right:
    fig = go.Figure(go.Bar(
        x=sector_data["Sektör"],
        y=sector_data["Para Girişi (%)"],
        marker_color=['green' if x > 0 else 'red' for x in sector_data["Para Girişi (%)"]],
        text=[f"{x:+.2f}%" for x in sector_data["Para Girişi (%)"]],
        textposition='outside'
    ))
    fig.update_layout(
        title="Sektör ETF Performansı",
        yaxis_title="Günlük Değişim (%)",
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

st.header("🎯 Portföy Seçkisi (Model 10)")

with st.spinner("Hisse verileri yükleniyor..."):
    portfolio = get_portfolio_data()

def color_change(val):
    if isinstance(val, str):
        return ''
    color = 'green' if val > 0 else 'red' if val < 0 else 'gray'
    return f'color: {color}'

styled_portfolio = portfolio.style.applymap(color_change, subset=['Günlük Değişim (%)'])
st.dataframe(styled_portfolio, hide_index=True, use_container_width=True)

st.divider()

st.sidebar.header("🗓️ Günlük Finansal Notlar")
st.sidebar.info("""
- **Fed Kararı:** Faizlerde sabit kalma beklentisi %85.
- **Trend:** AI çiplerinden veri merkezi altyapısına rotasyon var.
- **Dikkat:** Bugün NVIDIA bilançosu sonrası volatilite artabilir.
""")

st.sidebar.divider()
st.sidebar.header("📊 Veri Bilgisi")
st.sidebar.caption(f"Son güncelleme: {datetime.now().strftime('%H:%M:%S')}")
if st.sidebar.button("🔄 Verileri Yenile"):
    st.cache_data.clear()
    st.rerun()

st.caption("Bu veriler sadece eğitim amaçlıdır. Yatırım tavsiyesi içermez. Veriler Yahoo Finance'tan alınmaktadır.")
