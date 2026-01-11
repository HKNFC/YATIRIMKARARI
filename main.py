import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, text
from sqlalchemy.orm import sessionmaker, declarative_base
import os

st.set_page_config(page_title="Morning Alpha Dashboard", layout="wide")

DATABASE_URL = os.environ.get("DATABASE_URL")
engine = create_engine(DATABASE_URL)
Base = declarative_base()

class UserPortfolio(Base):
    __tablename__ = 'user_portfolio'
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False)
    sector = Column(String(100))
    quantity = Column(Float, default=1)
    buy_price = Column(Float)
    added_at = Column(DateTime, default=datetime.now)

Base.metadata.create_all(engine, checkfirst=True)
Session = sessionmaker(bind=engine)

def get_session():
    return Session()

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
def get_stock_price(symbol):
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="5d")
        if len(hist) >= 2:
            current = hist['Close'].iloc[-1]
            previous = hist['Close'].iloc[-2]
            change = ((current - previous) / previous) * 100
            return round(current, 2), round(change, 2)
        elif len(hist) == 1:
            return round(hist['Close'].iloc[-1], 2), 0
        return None, None
    except:
        return None, None

@st.cache_data(ttl=300)
def get_portfolio_data():
    symbols = ["NVDA", "VRT", "CRWD", "LLY", "GEHC", "FSLR", "TSLA", "AVAV", "RKLB", "SOFI"]
    sectors = ["Yapay Zeka", "Veri Altyapısı", "Siber Güvenlik", "Biyoteknoloji", "Sağlık Tek.", "Enerji", "EV", "Savunma", "Uzay", "Fintech"]
    risk_scores = ["Düşük", "Düşük", "Orta", "Düşük", "Düşük", "Orta", "Yüksek", "Orta", "Yüksek", "Yüksek"]
    stop_losses = ["-10%", "-8%", "-10%", "-7%", "-5%", "-12%", "-15%", "-10%", "-20%", "-15%"]
    
    data = []
    for i, symbol in enumerate(symbols):
        price, change = get_stock_price(symbol)
        data.append({
            "Sembol": symbol,
            "Sektör": sectors[i],
            "Fiyat ($)": price if price else "-",
            "Günlük Değişim (%)": change if change is not None else "-",
            "Risk Puanı": risk_scores[i],
            "Stop-Loss": stop_losses[i]
        })
    
    return pd.DataFrame(data)

def get_user_portfolio():
    session = get_session()
    try:
        stocks = session.query(UserPortfolio).all()
        return stocks
    finally:
        session.close()

def add_stock_to_portfolio(symbol, sector, quantity, buy_price):
    session = get_session()
    try:
        stock = UserPortfolio(
            symbol=symbol.upper(),
            sector=sector,
            quantity=quantity,
            buy_price=buy_price
        )
        session.add(stock)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        return False
    finally:
        session.close()

def remove_stock_from_portfolio(stock_id):
    session = get_session()
    try:
        stock = session.query(UserPortfolio).filter(UserPortfolio.id == stock_id).first()
        if stock:
            session.delete(stock)
            session.commit()
            return True
        return False
    except:
        session.rollback()
        return False
    finally:
        session.close()

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

styled_portfolio = portfolio.style.map(color_change, subset=['Günlük Değişim (%)'])
st.dataframe(styled_portfolio, hide_index=True, use_container_width=True)

st.divider()

st.header("💼 Benim Portföyüm")

user_stocks = get_user_portfolio()

if user_stocks:
    portfolio_data = []
    total_value = 0
    total_cost = 0
    
    for stock in user_stocks:
        current_price, daily_change = get_stock_price(stock.symbol)
        if current_price:
            current_value = current_price * stock.quantity
            cost_basis = stock.buy_price * stock.quantity if stock.buy_price else 0
            profit_loss = current_value - cost_basis if cost_basis > 0 else 0
            profit_loss_pct = ((current_price - stock.buy_price) / stock.buy_price * 100) if stock.buy_price else 0
            total_value += current_value
            total_cost += cost_basis
            
            portfolio_data.append({
                "ID": stock.id,
                "Sembol": stock.symbol,
                "Sektör": stock.sector or "-",
                "Adet": stock.quantity,
                "Alış Fiyatı ($)": stock.buy_price or "-",
                "Güncel Fiyat ($)": current_price,
                "Günlük (%)": daily_change,
                "Kar/Zarar ($)": round(profit_loss, 2),
                "Kar/Zarar (%)": round(profit_loss_pct, 2)
            })
        else:
            portfolio_data.append({
                "ID": stock.id,
                "Sembol": stock.symbol,
                "Sektör": stock.sector or "-",
                "Adet": stock.quantity,
                "Alış Fiyatı ($)": stock.buy_price or "-",
                "Güncel Fiyat ($)": "-",
                "Günlük (%)": "-",
                "Kar/Zarar ($)": "-",
                "Kar/Zarar (%)": "-"
            })
    
    user_df = pd.DataFrame(portfolio_data)
    
    col_summary1, col_summary2, col_summary3 = st.columns(3)
    col_summary1.metric("Toplam Değer", f"${total_value:,.2f}")
    col_summary2.metric("Toplam Maliyet", f"${total_cost:,.2f}")
    total_profit = total_value - total_cost
    col_summary3.metric("Toplam Kar/Zarar", f"${total_profit:,.2f}", delta=f"{(total_profit/total_cost*100) if total_cost > 0 else 0:.2f}%")
    
    st.dataframe(user_df.drop(columns=['ID']), hide_index=True, use_container_width=True)
    
    st.subheader("Hisse Sil")
    col_del1, col_del2 = st.columns([3, 1])
    with col_del1:
        stock_to_delete = st.selectbox(
            "Silinecek hisse seçin",
            options=[(s.id, f"{s.symbol} - {s.quantity} adet") for s in user_stocks],
            format_func=lambda x: x[1]
        )
    with col_del2:
        if st.button("🗑️ Sil", type="secondary"):
            if stock_to_delete:
                if remove_stock_from_portfolio(stock_to_delete[0]):
                    st.success(f"{stock_to_delete[1]} silindi!")
                    st.cache_data.clear()
                    st.rerun()
else:
    st.info("Henüz portföyünüze hisse eklemediniz. Aşağıdan ekleyebilirsiniz.")

st.subheader("Yeni Hisse Ekle")

with st.form("add_stock_form"):
    col_form1, col_form2 = st.columns(2)
    
    with col_form1:
        new_symbol = st.text_input("Hisse Sembolü (örn: AAPL)", max_chars=10)
        new_quantity = st.number_input("Adet", min_value=0.01, value=1.0, step=0.01)
    
    with col_form2:
        new_sector = st.selectbox("Sektör", [
            "Yapay Zeka", "Siber Güvenlik", "Yenilenebilir Enerji", "Fintech", 
            "Biyoteknoloji", "Sağlık", "Enerji", "EV", "Savunma", "Uzay", 
            "Teknoloji", "Finans", "Perakende", "Diğer"
        ])
        new_buy_price = st.number_input("Alış Fiyatı ($)", min_value=0.01, value=100.0, step=0.01)
    
    submitted = st.form_submit_button("➕ Portföye Ekle", type="primary")
    
    if submitted:
        if new_symbol:
            price, _ = get_stock_price(new_symbol.upper())
            if price:
                if add_stock_to_portfolio(new_symbol, new_sector, new_quantity, new_buy_price):
                    st.success(f"{new_symbol.upper()} portföye eklendi!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Hisse eklenirken bir hata oluştu.")
            else:
                st.error(f"{new_symbol.upper()} sembolü bulunamadı. Geçerli bir sembol girin.")
        else:
            st.warning("Lütfen hisse sembolü girin.")

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
