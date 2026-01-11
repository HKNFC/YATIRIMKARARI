import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Morning Alpha Dashboard", layout="wide")

st.title("☀️ Morning Alpha: Yatırım Karar Destek Paneli")
st.subheader("Piyasa Analizi ve Sektörel Fırsatlar")

def check_market_health():
    vix = 18.5
    market_status = "GÜVENLİ" if vix < 25 else "RİSKLİ"
    color = "green" if market_status == "GÜVENLİ" else "red"
    return market_status, vix, color

status, vix_val, status_color = check_market_health()

col1, col2, col3 = st.columns(3)
col1.metric("Piyasa Durumu", status, delta=None)
col2.metric("VIX (Korku Endeksi)", vix_val, delta="-1.2%")
col3.metric("Önerilen Strateji", "Alım Yapılabilir" if status == "GÜVENLİ" else "Nakde Geç")

st.divider()

st.header("🔥 Bugünün En Sıcak Sektörleri")

sector_data = pd.DataFrame({
    "Sektör": ["Yapay Zeka", "Siber Güvenlik", "Yenilenebilir Enerji", "Fintech", "Biyoteknoloji"],
    "Para Girişi (%)": [4.2, 2.8, -1.1, 1.5, 3.2]
})

col_left, col_right = st.columns([1, 2])

with col_left:
    st.write("Sektörel Para Akışı")
    st.dataframe(sector_data.sort_values(by="Para Girişi (%)", ascending=False))

with col_right:
    fig = go.Figure(go.Bar(
        x=sector_data["Sektör"],
        y=sector_data["Para Girişi (%)"],
        marker_color=['green' if x > 0 else 'red' for x in sector_data["Para Girişi (%)"]]
    ))
    st.plotly_chart(fig, use_container_width=True)

st.divider()

st.header("🎯 Portföy Seçkisi (Model 10)")

portfolio = pd.DataFrame({
    "Sembol": ["NVDA", "VRT", "CRWD", "LLY", "GEHC", "FSLR", "TSLA", "AVAV", "RKLB", "SOFI"],
    "Sektör": ["Yapay Zeka", "Veri Altyapısı", "Siber Güvenlik", "Biyoteknoloji", "Sağlık Tek.", "Enerji", "EV", "Savunma", "Uzay", "Fintech"],
    "Büyüme (EPS)": ["%28", "%22", "%18", "%35", "%12", "%15", "%14", "%10", "%45", "%20"],
    "Risk Puanı": ["Düşük", "Düşük", "Orta", "Düşük", "Düşük", "Orta", "Yüksek", "Orta", "Yüksek", "Yüksek"],
    "Stop-Loss": ["-10%", "-8%", "-10%", "-7%", "-5%", "-12%", "-15%", "-10%", "-20%", "-15%"]
})

st.table(portfolio)

st.sidebar.header("🗓️ Günlük Finansal Notlar")
st.sidebar.info("""
- **Fed Kararı:** Faizlerde sabit kalma beklentisi %85.
- **Trend:** AI çiplerinden veri merkezi altyapısına rotasyon var.
- **Dikkat:** Bugün NVIDIA bilançosu sonrası volatilite artabilir.
""")

st.caption("Bu veriler sadece eğitim amaçlıdır. Yatırım tavsiyesi içermez.")
