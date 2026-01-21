import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf
import requests
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base
from streamlit_autorefresh import st_autorefresh
import os

st.set_page_config(page_title="Morning Alpha Dashboard", layout="wide")

REFRESH_INTERVALS = {
    "Kapalı": 0,
    "30 Saniye": 30000,
    "1 Dakika": 60000,
    "2 Dakika": 120000,
    "5 Dakika": 300000
}

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
    portfolio_name = Column(String(100), default='Portföy 1')
    time_period = Column(String(20), default='5 Gün')

class PriceAlert(Base):
    __tablename__ = 'price_alerts'
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False)
    alert_type = Column(String(20), nullable=False)
    target_price = Column(Float, nullable=False)
    is_triggered = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    triggered_at = Column(DateTime, nullable=True)

Base.metadata.create_all(engine, checkfirst=True)
Session = sessionmaker(bind=engine)

def get_session():
    return Session()

NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_message(message):
    """Send a message via Telegram bot"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        st.sidebar.error("Token veya Chat ID eksik")
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        response = requests.post(url, data=data, timeout=10)
        if response.status_code != 200:
            error_info = response.json().get("description", "Bilinmeyen hata")
            st.sidebar.error(f"Telegram hatası: {error_info}")
        return response.status_code == 200
    except Exception as e:
        st.sidebar.error(f"Bağlantı hatası: {str(e)}")
        return False

@st.cache_data(ttl=900)
def fetch_market_news(market="US"):
    """Fetch financial news for the selected market in Turkish (cached for 15 minutes)"""
    if not NEWSAPI_KEY:
        return None
    
    try:
        if market == "US":
            url = f"https://newsapi.org/v2/everything?q=ABD+borsası+OR+Wall+Street+OR+Fed+OR+nasdaq+OR+S%26P500&language=tr&sortBy=publishedAt&pageSize=5&apiKey={NEWSAPI_KEY}"
        else:
            url = f"https://newsapi.org/v2/everything?q=borsa+istanbul+OR+BIST+OR+türk+ekonomi&language=tr&sortBy=publishedAt&pageSize=5&apiKey={NEWSAPI_KEY}"
        
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            articles = data.get("articles", [])
            news_items = []
            for article in articles[:5]:
                title = article.get("title", "")
                if title and title != "[Removed]":
                    news_items.append(title[:100] + "..." if len(title) > 100 else title)
            return news_items if news_items else None
        return None
    except Exception:
        return None

@st.cache_data(ttl=60)
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

@st.cache_data(ttl=60)
def get_bist100_data():
    try:
        xu100 = yf.Ticker("XU100.IS")
        hist = xu100.history(period="5d")
        if len(hist) >= 2:
            current = hist['Close'].iloc[-1]
            previous = hist['Close'].iloc[-2]
            change = ((current - previous) / previous) * 100
            return current, change
        elif len(hist) == 1:
            return hist['Close'].iloc[-1], 0
        return 10000, 0
    except:
        return 10000, 0

@st.cache_data(ttl=60)
def get_usdtry_data():
    try:
        usdtry = yf.Ticker("USDTRY=X")
        hist = usdtry.history(period="5d")
        if len(hist) >= 2:
            current = hist['Close'].iloc[-1]
            previous = hist['Close'].iloc[-2]
            change = ((current - previous) / previous) * 100
            return current, change
        elif len(hist) == 1:
            return hist['Close'].iloc[-1], 0
        return 35.0, 0
    except:
        return 35.0, 0

PERIOD_OPTIONS = {
    "1 Gün": ("2d", 1),
    "5 Gün": ("7d", 5),
    "15 Gün": ("20d", 15),
    "1 Ay": ("35d", 22),
    "3 Ay": ("100d", 63),
    "6 Ay": ("200d", 126),
    "1 Yıl": ("400d", 252)
}

MARKET_OPTIONS = {
    "ABD Borsaları": "US",
    "BIST (Borsa İstanbul)": "BIST"
}

US_SECTOR_ETFS = {
    "Temel Malzemeler (XLB)": "XLB",
    "İletişim Hizmetleri (XLC)": "XLC",
    "Döngüsel Tüketici (XLY)": "XLY",
    "Savunmacı Tüketici (XLP)": "XLP",
    "Enerji (XLE)": "XLE",
    "Finans (XLF)": "XLF",
    "Sağlık (XLV)": "XLV",
    "Sanayi (XLI)": "XLI",
    "Gayrimenkul (XLRE)": "XLRE",
    "Teknoloji (XLK)": "XLK",
    "Kamu Hizmetleri (XLU)": "XLU"
}

BIST_SECTORS = {
    "Bankacılık": "BANK",
    "Holding": "HOLD",
    "Demir Çelik": "STEEL",
    "Havacılık": "AIR",
    "Otomotiv": "AUTO",
    "Perakende": "RETAIL",
    "Enerji": "ENERGY",
    "Telekomünikasyon": "TELCO",
    "İnşaat & GYO": "CONST",
    "Gıda & İçecek": "FOOD"
}

BIST_SECTOR_HOLDINGS = {
    "BANK": ["GARAN.IS", "AKBNK.IS", "YKBNK.IS", "ISCTR.IS", "HALKB.IS", "VAKBN.IS", "TSKB.IS", "ALBRK.IS"],
    "HOLD": ["SAHOL.IS", "KCHOL.IS", "DOHOL.IS", "TAVHL.IS", "TKFEN.IS", "AGHOL.IS", "KOZAL.IS", "ECZYT.IS"],
    "STEEL": ["EREGL.IS", "KRDMD.IS", "KRDMA.IS", "KRDMB.IS", "CELHA.IS", "BRSAN.IS", "BURCE.IS", "CEMTS.IS"],
    "AIR": ["THYAO.IS", "PGSUS.IS", "CLEBI.IS", "TAVHL.IS"],
    "AUTO": ["TOASO.IS", "FROTO.IS", "DOAS.IS", "OTKAR.IS", "ASUZU.IS", "TTRAK.IS"],
    "RETAIL": ["BIMAS.IS", "MGROS.IS", "SOKM.IS", "BIZIM.IS", "MAVI.IS", "VAKKO.IS"],
    "ENERGY": ["TUPRS.IS", "PETKM.IS", "AYEN.IS", "AKSEN.IS", "ODAS.IS", "ZOREN.IS", "AYDEM.IS", "ENJSA.IS"],
    "TELCO": ["TCELL.IS", "TTKOM.IS", "NETAS.IS"],
    "CONST": ["EKGYO.IS", "ISGYO.IS", "ENKAI.IS", "KLGYO.IS", "HLGYO.IS", "TRGYO.IS"],
    "FOOD": ["ULKER.IS", "CCOLA.IS", "AEFES.IS", "BANVT.IS", "TATGD.IS", "KERVT.IS", "PENGD.IS"]
}

SECTOR_ETFS = US_SECTOR_ETFS

SECTOR_HOLDINGS = {
    "XLB": ["LIN", "APD", "SHW", "ECL", "DD", "FCX", "NEM", "DOW", "NUE", "VMC"],
    "XLC": ["META", "GOOGL", "NFLX", "DIS", "T", "VZ", "CMCSA", "CHTR", "TMUS", "EA"],
    "XLY": ["AMZN", "TSLA", "HD", "MCD", "NKE", "LOW", "SBUX", "TJX", "BKNG", "CMG"],
    "XLP": ["PG", "KO", "PEP", "COST", "WMT", "PM", "MO", "CL", "MDLZ", "KHC"],
    "XLE": ["XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY", "HAL"],
    "XLF": ["BRK-B", "JPM", "V", "MA", "BAC", "WFC", "GS", "MS", "AXP", "C"],
    "XLV": ["UNH", "JNJ", "LLY", "PFE", "ABBV", "MRK", "TMO", "DHR", "ABT", "BMY"],
    "XLI": ["CAT", "UNP", "HON", "BA", "GE", "RTX", "DE", "LMT", "UPS", "MMM"],
    "XLRE": ["PLD", "AMT", "EQIX", "CCI", "SPG", "PSA", "O", "DLR", "WELL", "AVB"],
    "XLK": ["AAPL", "MSFT", "NVDA", "AVGO", "CRM", "ADBE", "CSCO", "ACN", "ORCL", "IBM"],
    "XLU": ["NEE", "DUK", "SO", "D", "AEP", "SRE", "EXC", "XEL", "PEG", "ED"]
}

st.sidebar.header("🌍 Pazar Seçimi")
selected_market_name = st.sidebar.radio(
    "Hangi borsayı takip etmek istiyorsunuz?",
    options=list(MARKET_OPTIONS.keys()),
    index=0
)
selected_market = MARKET_OPTIONS[selected_market_name]

if selected_market == "US":
    st.sidebar.success("🇺🇸 ABD Borsaları aktif")
    CURRENT_SECTOR_MAP = US_SECTOR_ETFS
    CURRENT_HOLDINGS = SECTOR_HOLDINGS
    CURRENCY_SYMBOL = "$"
    PRICE_COL_NAME = "Fiyat ($)"
else:
    st.sidebar.success("🇹🇷 BIST (Borsa İstanbul) aktif")
    CURRENT_SECTOR_MAP = BIST_SECTORS
    CURRENT_HOLDINGS = BIST_SECTOR_HOLDINGS
    CURRENCY_SYMBOL = "₺"
    PRICE_COL_NAME = "Fiyat (₺)"

st.sidebar.divider()

st.sidebar.header("👤 Yatırımcı Profiline Göre Hisse Seçimi")
investor_profile = st.sidebar.selectbox(
    "Yatırımcı Profilinizi Seçin:",
    options=["Seçiniz", "Muhafazakar", "Orta Riskli", "Riski Seven"],
    index=0
)

INVESTOR_PROFILES = {
    "Muhafazakar": {
        "description": "Sermaye Koruma ve Düzenli Gelir",
        "beta_min": 0.50, "beta_max": 0.85,
        "pe_max": 15,
        "dividend_min": 3.0,
        "debt_equity_max": 0.50,
        "preferred": "Blue-Chip, Temettü Aristokratları"
    },
    "Orta Riskli": {
        "description": "Dengeli Büyüme ve Enflasyon Üstü Getiri",
        "beta_min": 0.90, "beta_max": 1.10,
        "pe_min": 10, "pe_max": 25,
        "peg_min": 1.0, "peg_max": 1.5,
        "dividend_min": 1.0, "dividend_max": 2.0,
        "debt_equity_max": 1.20,
        "preferred": "Mega-Cap Growth ve Value Hisseleri"
    },
    "Riski Seven": {
        "description": "Maksimum Sermaye Değerlemesi (Alfa)",
        "beta_min": 1.20, "beta_max": 3.00,
        "pe_min": 25,
        "peg_max": 1.0,
        "dividend_max": 0.5,
        "preferred": "Small-Cap, Teknoloji, Biyoteknoloji"
    }
}

st.sidebar.divider()

st.title("📊 Yatırım Karar Destek Paneli")
market_label = "ABD Borsaları" if selected_market == "US" else "BIST (Borsa İstanbul)"
st.subheader(f"Piyasa Analizi ve Sektörel Fırsatlar - {market_label}")

@st.cache_data(ttl=60)
def calculate_mfi(hist, period=14):
    """Finviz tarzı Money Flow Index hesaplar"""
    if len(hist) < period + 1:
        return 50.0
    
    typical_prices = (hist['High'] + hist['Low'] + hist['Close']) / 3
    money_flow = typical_prices * hist['Volume']
    
    positive_mf = 0
    negative_mf = 0
    
    for i in range(-period, 0):
        if typical_prices.iloc[i] > typical_prices.iloc[i-1]:
            positive_mf += money_flow.iloc[i]
        elif typical_prices.iloc[i] < typical_prices.iloc[i-1]:
            negative_mf += money_flow.iloc[i]
    
    if negative_mf == 0:
        return 100.0
    
    money_ratio = positive_mf / negative_mf
    mfi = 100 - (100 / (1 + money_ratio))
    return round(mfi, 2)

def get_sector_data(period_key="1 Gün", market="US"):
    if market == "US":
        sector_map = US_SECTOR_ETFS
    else:
        sector_map = BIST_SECTORS
    
    fetch_period, lookback_days = PERIOD_OPTIONS.get(period_key, ("2d", 1))
    
    results = []
    for name, symbol in sector_map.items():
        try:
            if market == "US":
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="1mo")
                if len(hist) > lookback_days:
                    current = hist['Close'].iloc[-1]
                    previous = hist['Close'].iloc[-(lookback_days + 1)]
                    change = ((current - previous) / previous) * 100
                    
                    current_vol = hist['Volume'].iloc[-lookback_days:].sum()
                    previous_vol = hist['Volume'].iloc[-lookback_days*2:-lookback_days].sum() if len(hist) > lookback_days*2 else hist['Volume'].iloc[0]
                    vol_change = ((current_vol - previous_vol) / previous_vol * 100) if previous_vol > 0 else 0
                    
                    mfi = calculate_mfi(hist, period=14)
                    mfi_normalized = mfi - 50
                    
                    results.append({"Sektör": name, "Değişim (%)": round(change, 2), "Hacim Değişim (%)": round(vol_change, 2), "Para Akışı (%)": round(mfi_normalized, 2), "MFI": mfi})
                elif len(hist) >= 2:
                    current = hist['Close'].iloc[-1]
                    previous = hist['Close'].iloc[0]
                    change = ((current - previous) / previous) * 100
                    current_vol = hist['Volume'].iloc[-1]
                    previous_vol = hist['Volume'].iloc[0]
                    vol_change = ((current_vol - previous_vol) / previous_vol * 100) if previous_vol > 0 else 0
                    mfi = calculate_mfi(hist, period=min(14, len(hist)-1))
                    mfi_normalized = mfi - 50
                    results.append({"Sektör": name, "Değişim (%)": round(change, 2), "Hacim Değişim (%)": round(vol_change, 2), "Para Akışı (%)": round(mfi_normalized, 2), "MFI": mfi})
                else:
                    results.append({"Sektör": name, "Değişim (%)": 0, "Hacim Değişim (%)": 0, "Para Akışı (%)": 0, "MFI": 50})
            else:
                holdings = BIST_SECTOR_HOLDINGS.get(symbol, [])
                if not holdings:
                    results.append({"Sektör": name, "Değişim (%)": 0, "Hacim Değişim (%)": 0, "Para Akışı (%)": 0, "MFI": 50})
                    continue
                sector_changes = []
                sector_vol_changes = []
                sector_mfi_values = []
                for stock_symbol in holdings[:5]:
                    try:
                        ticker = yf.Ticker(stock_symbol)
                        hist = ticker.history(period="1mo")
                        if len(hist) > lookback_days:
                            current = hist['Close'].iloc[-1]
                            previous = hist['Close'].iloc[-(lookback_days + 1)]
                            change = ((current - previous) / previous) * 100
                            sector_changes.append(change)
                            
                            current_vol = hist['Volume'].iloc[-lookback_days:].sum()
                            previous_vol = hist['Volume'].iloc[-lookback_days*2:-lookback_days].sum() if len(hist) > lookback_days*2 else hist['Volume'].iloc[0]
                            vol_change = ((current_vol - previous_vol) / previous_vol * 100) if previous_vol > 0 else 0
                            sector_vol_changes.append(vol_change)
                            
                            mfi = calculate_mfi(hist, period=14)
                            sector_mfi_values.append(mfi)
                        elif len(hist) >= 2:
                            current = hist['Close'].iloc[-1]
                            previous = hist['Close'].iloc[0]
                            change = ((current - previous) / previous) * 100
                            sector_changes.append(change)
                            current_vol = hist['Volume'].iloc[-1]
                            previous_vol = hist['Volume'].iloc[0]
                            vol_change = ((current_vol - previous_vol) / previous_vol * 100) if previous_vol > 0 else 0
                            sector_vol_changes.append(vol_change)
                            mfi = calculate_mfi(hist, period=min(14, len(hist)-1))
                            sector_mfi_values.append(mfi)
                    except:
                        pass
                if sector_changes:
                    avg_change = sum(sector_changes) / len(sector_changes)
                    avg_vol_change = sum(sector_vol_changes) / len(sector_vol_changes) if sector_vol_changes else 0
                    avg_mfi = sum(sector_mfi_values) / len(sector_mfi_values) if sector_mfi_values else 50
                    mfi_normalized = avg_mfi - 50
                    results.append({"Sektör": name, "Değişim (%)": round(avg_change, 2), "Hacim Değişim (%)": round(avg_vol_change, 2), "Para Akışı (%)": round(mfi_normalized, 2), "MFI": round(avg_mfi, 2)})
                else:
                    results.append({"Sektör": name, "Değişim (%)": 0, "Hacim Değişim (%)": 0, "Para Akışı (%)": 0, "MFI": 50})
        except:
            results.append({"Sektör": name, "Değişim (%)": 0, "Hacim Değişim (%)": 0, "Para Akışı (%)": 0, "MFI": 50})
    
    return pd.DataFrame(results)

@st.cache_data(ttl=60)
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

def normalize_score(values):
    if not values or max(values) == min(values):
        return [50] * len(values)
    min_val, max_val = min(values), max(values)
    return [(v - min_val) / (max_val - min_val) * 100 for v in values]

@st.cache_data(ttl=60)
def get_sector_holdings_data(sector_key, market="US"):
    if market == "US":
        holdings = SECTOR_HOLDINGS.get(sector_key, [])
        currency = "$"
        price_col = "Fiyat ($)"
    else:
        holdings = BIST_SECTOR_HOLDINGS.get(sector_key, [])
        currency = "₺"
        price_col = "Fiyat (₺)"
    
    raw_data = []
    
    for symbol in holdings:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="10d")
            info = ticker.info
            company_name = info.get("shortName", symbol.replace(".IS", ""))
            
            forward_pe = info.get("forwardPE", 0) or 0
            revenue_growth = info.get("revenueGrowth", 0) or 0
            profit_margin = info.get("profitMargins", 0) or 0
            
            rec_mean = info.get("recommendationMean", 3) or 3
            revision_score = (5 - rec_mean) / 4 * 100
            
            if len(hist) >= 2:
                current = hist['Close'].iloc[-1]
                previous = hist['Close'].iloc[-2]
                daily_change = ((current - previous) / previous) * 100
                
                if len(hist) >= 5:
                    week_ago = hist['Close'].iloc[0]
                    momentum = ((current - week_ago) / week_ago) * 100
                else:
                    momentum = daily_change
                
                valuation_score = 100 - min(forward_pe, 100) if forward_pe > 0 else 50
                
                raw_data.append({
                    "Sembol": symbol.replace(".IS", "") if market == "BIST" else symbol,
                    "Şirket": company_name[:20],
                    price_col: round(current, 2),
                    "Değişim (%)": round(daily_change, 2),
                    "_valuation": valuation_score,
                    "_growth": revenue_growth * 100,
                    "_profitability": profit_margin * 100,
                    "_momentum": momentum,
                    "_revision": revision_score
                })
        except:
            pass
    
    if not raw_data:
        return pd.DataFrame()
    
    valuations = normalize_score([d["_valuation"] for d in raw_data])
    growths = normalize_score([d["_growth"] for d in raw_data])
    profits = normalize_score([d["_profitability"] for d in raw_data])
    momentums = normalize_score([d["_momentum"] for d in raw_data])
    revisions = normalize_score([d["_revision"] for d in raw_data])
    
    final_data = []
    for i, d in enumerate(raw_data):
        val_puan = round(valuations[i] * 0.20, 2)
        buy_puan = round(growths[i] * 0.20, 2)
        kar_puan = round(profits[i] * 0.20, 2)
        mom_puan = round(momentums[i] * 0.20, 2)
        rev_puan = round(revisions[i] * 0.20, 2)
        toplam = round(val_puan + buy_puan + kar_puan + mom_puan + rev_puan, 2)
        
        final_data.append({
            "Sembol": d["Sembol"],
            "Şirket": d["Şirket"],
            price_col: d[price_col],
            "Değişim (%)": d["Değişim (%)"],
            "Değerleme": val_puan,
            "Büyüme": buy_puan,
            "Karlılık": kar_puan,
            "Momentum": mom_puan,
            "Revizyonlar": rev_puan,
            "Toplam Puan": toplam
        })
    
    df = pd.DataFrame(final_data)
    df = df.sort_values(by="Toplam Puan", ascending=False).head(5)
    return df

@st.cache_data(ttl=60)
def get_top_stocks_from_sector(sector_key, sector_name, count=2, market="US"):
    """Belirli bir sektörden en yüksek puanlı hisseleri seçer"""
    if market == "US":
        holdings = SECTOR_HOLDINGS.get(sector_key, [])
        price_col = "Fiyat ($)"
    else:
        holdings = BIST_SECTOR_HOLDINGS.get(sector_key, [])
        price_col = "Fiyat (₺)"
    
    raw_data = []
    
    for symbol in holdings:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="10d")
            info = ticker.info
            company_name = info.get("shortName", symbol.replace(".IS", ""))
            
            forward_pe = info.get("forwardPE", 0) or 0
            revenue_growth = info.get("revenueGrowth", 0) or 0
            profit_margin = info.get("profitMargins", 0) or 0
            
            rec_mean = info.get("recommendationMean", 3) or 3
            revision_score = (5 - rec_mean) / 4 * 100
            
            if len(hist) >= 2:
                current = hist['Close'].iloc[-1]
                previous = hist['Close'].iloc[-2]
                daily_change = ((current - previous) / previous) * 100
                
                if len(hist) >= 5:
                    week_ago = hist['Close'].iloc[0]
                    momentum = ((current - week_ago) / week_ago) * 100
                else:
                    momentum = daily_change
                
                valuation_score = 100 - min(forward_pe, 100) if forward_pe > 0 else 50
                
                raw_data.append({
                    "Sembol": symbol.replace(".IS", "") if market == "BIST" else symbol,
                    "Şirket": company_name[:20],
                    "Sektör": sector_name,
                    price_col: round(current, 2),
                    "Günlük Değişim (%)": round(daily_change, 2),
                    "_valuation": valuation_score,
                    "_growth": revenue_growth * 100,
                    "_profitability": profit_margin * 100,
                    "_momentum": momentum,
                    "_revision": revision_score
                })
        except:
            pass
    
    if not raw_data:
        return []
    
    valuations = normalize_score([d["_valuation"] for d in raw_data])
    growths = normalize_score([d["_growth"] for d in raw_data])
    profits = normalize_score([d["_profitability"] for d in raw_data])
    momentums = normalize_score([d["_momentum"] for d in raw_data])
    revisions = normalize_score([d["_revision"] for d in raw_data])
    
    final_data = []
    for i, d in enumerate(raw_data):
        val_puan = round(valuations[i] * 0.20, 2)
        buy_puan = round(growths[i] * 0.20, 2)
        kar_puan = round(profits[i] * 0.20, 2)
        mom_puan = round(momentums[i] * 0.20, 2)
        rev_puan = round(revisions[i] * 0.20, 2)
        toplam = round(val_puan + buy_puan + kar_puan + mom_puan + rev_puan, 2)
        
        final_data.append({
            "Sembol": d["Sembol"],
            "Şirket": d["Şirket"],
            "Sektör": d["Sektör"],
            price_col: d[price_col],
            "Günlük Değişim (%)": d["Günlük Değişim (%)"],
            "Toplam Puan": toplam
        })
    
    sorted_data = sorted(final_data, key=lambda x: x["Toplam Puan"], reverse=True)
    return sorted_data[:count]

@st.cache_data(ttl=60)
def get_all_sector_candidates(sector_key, sector_name, market="US", sort_by="score"):
    """Bir sektördeki tüm adayları puanlarıyla döndürür
    sort_by: 'score' = 5 kriter ortalaması, 'money_flow' = hacim/para akışı
    """
    if market == "US":
        holdings = SECTOR_HOLDINGS.get(sector_key, [])
        price_col = "Fiyat ($)"
    else:
        holdings = BIST_SECTOR_HOLDINGS.get(sector_key, [])
        price_col = "Fiyat (₺)"
    
    raw_data = []
    
    for symbol in holdings:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="10d")
            info = ticker.info
            company_name = info.get("shortName", symbol.replace(".IS", ""))
            
            forward_pe = info.get("forwardPE", 0) or 0
            revenue_growth = info.get("revenueGrowth", 0) or 0
            profit_margin = info.get("profitMargins", 0) or 0
            rec_mean = info.get("recommendationMean", 3) or 3
            revision_score = (5 - rec_mean) / 4 * 100
            
            if len(hist) >= 2:
                current = hist['Close'].iloc[-1]
                previous = hist['Close'].iloc[-2]
                daily_change = ((current - previous) / previous) * 100
                
                current_volume = hist['Volume'].iloc[-1]
                prev_volume = hist['Volume'].iloc[-2] if hist['Volume'].iloc[-2] > 0 else 1
                volume_change = ((current_volume - prev_volume) / prev_volume) * 100
                
                current_money_flow = current * current_volume
                prev_money_flow = previous * prev_volume
                money_flow_change = ((current_money_flow - prev_money_flow) / prev_money_flow) * 100 if prev_money_flow > 0 else 0
                
                if len(hist) >= 5:
                    week_ago = hist['Close'].iloc[0]
                    momentum = ((current - week_ago) / week_ago) * 100
                else:
                    momentum = daily_change
                
                valuation_score = 100 - min(forward_pe, 100) if forward_pe > 0 else 50
                
                raw_data.append({
                    "Sembol": symbol.replace(".IS", "") if market == "BIST" else symbol,
                    "Şirket": company_name[:20],
                    "Sektör": sector_name,
                    price_col: round(current, 2),
                    "Günlük Değişim (%)": round(daily_change, 2),
                    "_valuation": valuation_score,
                    "_growth": revenue_growth * 100,
                    "_profitability": profit_margin * 100,
                    "_momentum": momentum,
                    "_revision": revision_score,
                    "_money_flow": money_flow_change,
                    "_volume_change": volume_change
                })
        except:
            pass
    
    if not raw_data:
        return []
    
    valuations = normalize_score([d["_valuation"] for d in raw_data])
    growths = normalize_score([d["_growth"] for d in raw_data])
    profits = normalize_score([d["_profitability"] for d in raw_data])
    momentums = normalize_score([d["_momentum"] for d in raw_data])
    revisions = normalize_score([d["_revision"] for d in raw_data])
    money_flows = normalize_score([d["_money_flow"] for d in raw_data])
    
    final_data = []
    for i, d in enumerate(raw_data):
        val_puan = round(valuations[i] * 0.20, 2)
        buy_puan = round(growths[i] * 0.20, 2)
        kar_puan = round(profits[i] * 0.20, 2)
        mom_puan = round(momentums[i] * 0.20, 2)
        rev_puan = round(revisions[i] * 0.20, 2)
        toplam = round(val_puan + buy_puan + kar_puan + mom_puan + rev_puan, 2)
        mf_puan = round(money_flows[i], 2)
        
        final_data.append({
            "Sembol": d["Sembol"],
            "Şirket": d["Şirket"],
            "Sektör": d["Sektör"],
            price_col: d[price_col],
            "Günlük Değişim (%)": d["Günlük Değişim (%)"],
            "Toplam Puan": toplam,
            "Para Akışı Puanı": mf_puan
        })
    
    if sort_by == "money_flow":
        return sorted(final_data, key=lambda x: x["Para Akışı Puanı"], reverse=True)
    return sorted(final_data, key=lambda x: x["Toplam Puan"], reverse=True)

@st.cache_data(ttl=60)
def get_portfolio_data(period_key="1 Gün", market="US"):
    sector_df = get_sector_data(period_key, market)
    
    sector_df = sector_df[sector_df["Değişim (%)"] > 0]
    
    if len(sector_df) == 0:
        return pd.DataFrame()
    
    sector_df = sector_df.sort_values(by="Değişim (%)", ascending=False)
    
    if market == "US":
        sector_map = US_SECTOR_ETFS
    else:
        sector_map = BIST_SECTORS
    
    top_6_sectors = sector_df.head(6)
    
    sector_candidates = {}
    sector_quotas = {}
    
    for idx, row in top_6_sectors.iterrows():
        sector_name = row["Sektör"]
        sector_key = sector_map.get(sector_name, "")
        rank = list(top_6_sectors.index).index(idx) + 1
        
        candidates = get_all_sector_candidates(sector_key, sector_name, market)
        sector_candidates[sector_name] = candidates
        sector_quotas[sector_name] = 2 if rank <= 4 else 1
    
    symbol_best_sector = {}
    for sector_name, candidates in sector_candidates.items():
        for candidate in candidates:
            symbol = candidate["Sembol"]
            score = candidate["Toplam Puan"]
            if symbol not in symbol_best_sector or score > symbol_best_sector[symbol]["score"]:
                symbol_best_sector[symbol] = {"sector": sector_name, "score": score}
    
    final_picks = []
    used_symbols = set()
    
    for sector_name in sector_quotas.keys():
        quota = sector_quotas[sector_name]
        candidates = sector_candidates[sector_name]
        selected = 0
        
        for candidate in candidates:
            if selected >= quota:
                break
            symbol = candidate["Sembol"]
            
            if symbol in used_symbols:
                continue
            
            if symbol_best_sector[symbol]["sector"] == sector_name:
                final_picks.append(candidate)
                used_symbols.add(symbol)
                selected += 1
            else:
                continue
        
        for candidate in candidates:
            if selected >= quota:
                break
            symbol = candidate["Sembol"]
            if symbol not in used_symbols:
                final_picks.append(candidate)
                used_symbols.add(symbol)
                selected += 1
    
    if not final_picks:
        return pd.DataFrame()
    
    return pd.DataFrame(final_picks)

@st.cache_data(ttl=60)
def get_money_flow_portfolio(period_key="1 Gün", market="US"):
    """Sadece para akışına göre hisse seçimi yapar - hem sektörler hem hisseler para akışına göre sıralanır"""
    sector_df = get_sector_data(period_key, market)
    
    if "Para Akışı (%)" not in sector_df.columns:
        return pd.DataFrame()
    
    sector_df = sector_df[sector_df["Para Akışı (%)"] > 0]
    
    if len(sector_df) == 0:
        return pd.DataFrame()
    
    sector_df = sector_df.sort_values(by="Para Akışı (%)", ascending=False)
    
    if market == "US":
        sector_map = US_SECTOR_ETFS
    else:
        sector_map = BIST_SECTORS
    
    top_6_sectors = sector_df.head(6)
    
    sector_candidates = {}
    sector_quotas = {}
    
    for idx, row in top_6_sectors.iterrows():
        sector_name = row["Sektör"]
        sector_key = sector_map.get(sector_name, "")
        rank = list(top_6_sectors.index).index(idx) + 1
        
        candidates = get_all_sector_candidates(sector_key, sector_name, market, sort_by="money_flow")
        sector_candidates[sector_name] = candidates
        sector_quotas[sector_name] = 2 if rank <= 4 else 1
    
    symbol_best_sector = {}
    for sector_name, candidates in sector_candidates.items():
        for candidate in candidates:
            symbol = candidate["Sembol"]
            score = candidate.get("Para Akışı Puanı", 0)
            if symbol not in symbol_best_sector or score > symbol_best_sector[symbol]["score"]:
                symbol_best_sector[symbol] = {"sector": sector_name, "score": score}
    
    final_picks = []
    used_symbols = set()
    
    for sector_name in sector_quotas.keys():
        quota = sector_quotas[sector_name]
        candidates = sector_candidates[sector_name]
        selected = 0
        
        for candidate in candidates:
            if selected >= quota:
                break
            symbol = candidate["Sembol"]
            
            if symbol in used_symbols:
                continue
            
            if symbol_best_sector[symbol]["sector"] == sector_name:
                final_picks.append(candidate)
                used_symbols.add(symbol)
                selected += 1
            else:
                continue
        
        for candidate in candidates:
            if selected >= quota:
                break
            symbol = candidate["Sembol"]
            if symbol not in used_symbols:
                final_picks.append(candidate)
                used_symbols.add(symbol)
                selected += 1
    
    if not final_picks:
        return pd.DataFrame()
    
    result_df = pd.DataFrame(final_picks)
    if "Para Akışı Puanı" in result_df.columns:
        result_df = result_df.drop(columns=["Para Akışı Puanı"])
    return result_df

@st.cache_data(ttl=120)
def get_profile_based_stocks(profile_name, market="US"):
    """Yatırımcı profiline göre hisse seçimi yapar"""
    if profile_name not in INVESTOR_PROFILES:
        return pd.DataFrame()
    
    profile = INVESTOR_PROFILES[profile_name]
    
    if market == "US":
        all_symbols = []
        for symbols in SECTOR_HOLDINGS.values():
            all_symbols.extend(symbols)
        all_symbols = list(set(all_symbols))
        currency = "$"
        price_col = "Fiyat ($)"
    else:
        all_symbols = []
        for symbols in BIST_SECTOR_HOLDINGS.values():
            all_symbols.extend(symbols)
        all_symbols = list(set(all_symbols))
        currency = "₺"
        price_col = "Fiyat (₺)"
    
    matching_stocks = []
    
    for symbol in all_symbols[:50]:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            hist = ticker.history(period="5d")
            
            if len(hist) < 2:
                continue
            
            beta = info.get("beta", 1.0) or 1.0
            pe = info.get("forwardPE") or info.get("trailingPE") or 0
            peg = info.get("pegRatio") or 0
            dividend_yield = (info.get("dividendYield") or 0) * 100
            debt_equity = info.get("debtToEquity") or 0
            if debt_equity > 10:
                debt_equity = debt_equity / 100
            
            current_price = hist['Close'].iloc[-1]
            prev_price = hist['Close'].iloc[-2]
            daily_change = ((current_price - prev_price) / prev_price) * 100
            
            company_name = info.get("shortName", symbol.replace(".IS", ""))
            
            score = 0
            max_score = 0
            
            if "beta_min" in profile and "beta_max" in profile:
                max_score += 1
                if profile["beta_min"] <= beta <= profile["beta_max"]:
                    score += 1
            
            if "pe_max" in profile:
                max_score += 1
                if pe > 0 and pe <= profile["pe_max"]:
                    score += 1
            elif "pe_min" in profile:
                max_score += 1
                if pe >= profile["pe_min"]:
                    score += 1
            
            if "dividend_min" in profile:
                max_score += 1
                if dividend_yield >= profile["dividend_min"]:
                    score += 1
            elif "dividend_max" in profile:
                max_score += 1
                if dividend_yield <= profile["dividend_max"]:
                    score += 1
            
            if "debt_equity_max" in profile:
                max_score += 1
                if debt_equity <= profile["debt_equity_max"]:
                    score += 1
            
            if "peg_max" in profile:
                max_score += 1
                if peg > 0 and peg <= profile["peg_max"]:
                    score += 1
            elif "peg_min" in profile and "peg_max" in profile:
                max_score += 1
                if profile["peg_min"] <= peg <= profile["peg_max"]:
                    score += 1
            
            match_percent = (score / max_score * 100) if max_score > 0 else 0
            
            if match_percent >= 40:
                matching_stocks.append({
                    "Sembol": symbol,
                    "Şirket": company_name[:25],
                    price_col: round(current_price, 2),
                    "Günlük Değişim (%)": round(daily_change, 2),
                    "Beta": round(beta, 2),
                    "F/K": round(pe, 1) if pe else "-",
                    "Temettü (%)": round(dividend_yield, 2),
                    "Borç/Özkaynak": round(debt_equity, 2),
                    "Uyum (%)": round(match_percent, 0)
                })
        except:
            continue
    
    if not matching_stocks:
        return pd.DataFrame()
    
    df = pd.DataFrame(matching_stocks)
    df = df.sort_values(by="Uyum (%)", ascending=False).head(10)
    return df

BACKTEST_INTERVALS = {
    "Haftalık": 7,
    "2 Haftalık": 14,
    "Aylık": 30,
    "2 Aylık": 60,
    "3 Aylık": 90
}

FMP_API_KEY = os.environ.get("FMP_API_KEY", "")

@st.cache_data(ttl=3600)
def get_fmp_historical_ratios(symbol):
    """FMP API'den tarihsel finansal rasyoları çeker (P/E, PS, vb.)"""
    if not FMP_API_KEY:
        return None
    try:
        url = f"https://financialmodelingprep.com/api/v3/ratios/{symbol}?limit=40&apikey={FMP_API_KEY}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                df = pd.DataFrame(data)
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date', ascending=False)
                return df
        return None
    except:
        return None

@st.cache_data(ttl=3600)
def get_fmp_historical_growth(symbol):
    """FMP API'den tarihsel büyüme verilerini çeker (gelir büyümesi, EPS büyümesi)"""
    if not FMP_API_KEY:
        return None
    try:
        url = f"https://financialmodelingprep.com/api/v3/financial-growth/{symbol}?limit=40&apikey={FMP_API_KEY}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                df = pd.DataFrame(data)
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date', ascending=False)
                return df
        return None
    except:
        return None

@st.cache_data(ttl=3600)
def get_fmp_analyst_estimates(symbol):
    """FMP API'den analist tahminlerini çeker"""
    if not FMP_API_KEY:
        return None
    try:
        url = f"https://financialmodelingprep.com/api/v3/analyst-estimates/{symbol}?limit=40&apikey={FMP_API_KEY}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                df = pd.DataFrame(data)
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date', ascending=False)
                return df
        return None
    except:
        return None

def get_fmp_metrics_for_date(symbol, ref_date):
    """Belirli bir tarih için FMP'den en yakın finansal metrikleri döndürür"""
    ratios_df = get_fmp_historical_ratios(symbol)
    growth_df = get_fmp_historical_growth(symbol)
    analyst_df = get_fmp_analyst_estimates(symbol)
    
    metrics = {
        'pe_ratio': None,
        'ps_ratio': None,
        'revenue_growth': None,
        'profit_margin': None,
        'analyst_revision': None
    }
    
    ref_date_dt = pd.Timestamp(ref_date)
    
    if ratios_df is not None and len(ratios_df) > 0:
        past_ratios = ratios_df[ratios_df['date'] <= ref_date_dt]
        if len(past_ratios) > 0:
            latest = past_ratios.iloc[0]
            metrics['pe_ratio'] = latest.get('priceEarningsRatio', None)
            metrics['ps_ratio'] = latest.get('priceToSalesRatio', None)
            metrics['profit_margin'] = latest.get('netProfitMargin', None)
    
    if growth_df is not None and len(growth_df) > 0:
        past_growth = growth_df[growth_df['date'] <= ref_date_dt]
        if len(past_growth) > 0:
            latest = past_growth.iloc[0]
            metrics['revenue_growth'] = latest.get('revenueGrowth', None)
    
    if analyst_df is not None and len(analyst_df) > 0:
        past_estimates = analyst_df[analyst_df['date'] <= ref_date_dt]
        if len(past_estimates) >= 2:
            current = past_estimates.iloc[0]
            previous = past_estimates.iloc[1]
            curr_eps = current.get('estimatedEpsAvg', None)
            prev_eps = previous.get('estimatedEpsAvg', None)
            if curr_eps is not None and prev_eps is not None and prev_eps != 0:
                revision_change = ((curr_eps - prev_eps) / abs(prev_eps)) * 100
                metrics['analyst_revision'] = revision_change
        elif len(past_estimates) == 1:
            curr_eps = past_estimates.iloc[0].get('estimatedEpsAvg', None)
            if curr_eps is not None:
                metrics['analyst_revision'] = 0
    
    return metrics

def calculate_fmp_stock_scores_for_sector(symbols, ref_date):
    """Bir sektördeki tüm hisseler için 5 kriterli ham puanları hesaplar ve normalize eder"""
    raw_data = []
    
    for symbol in symbols:
        metrics = get_fmp_metrics_for_date(symbol, ref_date)
        momentum = get_historical_momentum_score(symbol, ref_date)
        
        pe = metrics.get('pe_ratio')
        valuation_raw = 100 - min(pe, 100) if pe is not None and pe > 0 else 50
        
        rev_growth = metrics.get('revenue_growth')
        growth_raw = rev_growth * 100 if rev_growth is not None else 0
        
        profit = metrics.get('profit_margin')
        profit_raw = profit * 100 if profit is not None else 0
        
        momentum_raw = momentum if momentum is not None else 0
        
        revision = metrics.get('analyst_revision')
        revision_raw = revision if revision is not None else 0
        
        raw_data.append({
            'symbol': symbol,
            '_valuation': valuation_raw,
            '_growth': growth_raw,
            '_profitability': profit_raw,
            '_momentum': momentum_raw,
            '_revision': revision_raw
        })
    
    if not raw_data:
        return []
    
    valuations = normalize_score([d['_valuation'] for d in raw_data])
    growths = normalize_score([d['_growth'] for d in raw_data])
    profits = normalize_score([d['_profitability'] for d in raw_data])
    momentums = normalize_score([d['_momentum'] for d in raw_data])
    revisions = normalize_score([d['_revision'] for d in raw_data])
    
    scored_data = []
    for i, d in enumerate(raw_data):
        val_puan = valuations[i] * 0.20
        buy_puan = growths[i] * 0.20
        kar_puan = profits[i] * 0.20
        mom_puan = momentums[i] * 0.20
        rev_puan = revisions[i] * 0.20
        toplam = val_puan + buy_puan + kar_puan + mom_puan + rev_puan
        
        scored_data.append({
            'symbol': d['symbol'],
            'score': toplam
        })
    
    return sorted(scored_data, key=lambda x: x['score'], reverse=True)

def run_fmp_backtest_simulation(start_date, interval_days, period_key):
    """FMP verileriyle tam 5 kriterli backtesting simülasyonu - canlı sistemle aynı mantık"""
    results = []
    portfolio_value = 100.0
    current_date = start_date
    today = datetime.now().date()
    
    lookback_days = PERIOD_LOOKBACK_DAYS.get(period_key, 30)
    
    while current_date < today:
        next_date = current_date + timedelta(days=interval_days)
        if next_date > today:
            next_date = today
        
        sector_performances = []
        for name, symbol in SECTOR_ETFS.items():
            lookback_start = current_date - timedelta(days=lookback_days)
            perf = get_historical_sector_performance(symbol, lookback_start, current_date)
            sector_performances.append({"Sektör": name, "Performans": perf, "ETF": symbol})
        
        sector_df = pd.DataFrame(sector_performances)
        sector_df = sector_df.sort_values(by="Performans", ascending=False)
        top_6 = sector_df.head(6)
        
        sector_candidates = {}
        sector_quotas = {}
        
        for idx, (_, row) in enumerate(top_6.iterrows()):
            sector_name = row["Sektör"]
            etf_symbol = row["ETF"]
            holdings = SECTOR_HOLDINGS.get(etf_symbol, [])
            
            scored_stocks = calculate_fmp_stock_scores_for_sector(holdings, current_date)
            sector_candidates[sector_name] = scored_stocks
            sector_quotas[sector_name] = 2 if idx < 4 else 1
        
        symbol_best_sector = {}
        for sector_name, candidates in sector_candidates.items():
            for candidate in candidates:
                symbol = candidate['symbol']
                score = candidate['score']
                if symbol not in symbol_best_sector or score > symbol_best_sector[symbol]['score']:
                    symbol_best_sector[symbol] = {'sector': sector_name, 'score': score}
        
        final_picks = []
        used_symbols = set()
        
        for sector_name in sector_quotas.keys():
            quota = sector_quotas[sector_name]
            candidates = sector_candidates[sector_name]
            selected = 0
            
            for candidate in candidates:
                if selected >= quota:
                    break
                symbol = candidate['symbol']
                
                if symbol in used_symbols:
                    continue
                
                if symbol_best_sector[symbol]['sector'] == sector_name:
                    final_picks.append(symbol)
                    used_symbols.add(symbol)
                    selected += 1
            
            for candidate in candidates:
                if selected >= quota:
                    break
                symbol = candidate['symbol']
                if symbol not in used_symbols:
                    final_picks.append(symbol)
                    used_symbols.add(symbol)
                    selected += 1
        
        if final_picks:
            returns = []
            for symbol in final_picks:
                ret = get_historical_stock_return(symbol, current_date, next_date)
                if ret is not None:
                    returns.append(ret)
            
            if returns:
                avg_return = sum(returns) / len(returns)
                portfolio_value = portfolio_value * (1 + avg_return / 100)
        
        results.append({
            "Tarih": current_date,
            "Portföy Değeri": round(portfolio_value, 2),
            "Seçilen Hisse": len(final_picks)
        })
        
        current_date = next_date
    
    return pd.DataFrame(results)

def get_historical_sector_performance(etf_symbol, start_date, end_date):
    """Belirli tarih aralığında sektör performansını hesaplar (bir gün önceki veri)"""
    try:
        ticker = yf.Ticker(etf_symbol)
        adj_end = end_date - timedelta(days=1)
        hist = ticker.history(start=start_date, end=adj_end)
        if len(hist) >= 2:
            start_price = hist['Close'].iloc[0]
            end_price = hist['Close'].iloc[-1]
            return ((end_price - start_price) / start_price) * 100
        return 0
    except:
        return 0

def get_historical_stock_return(symbol, start_date, end_date):
    """Belirli tarih aralığında hisse getirisini hesaplar"""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(start=start_date, end=end_date)
        if len(hist) >= 2:
            start_price = hist['Close'].iloc[0]
            end_price = hist['Close'].iloc[-1]
            return ((end_price - start_price) / start_price) * 100
        return None
    except:
        return None

PERIOD_LOOKBACK_DAYS = {
    "1 Gün": 1,
    "5 Gün": 5,
    "15 Gün": 15,
    "1 Ay": 30,
    "3 Ay": 90,
    "6 Ay": 180,
    "1 Yıl": 365
}

def get_historical_momentum_score(symbol, ref_date):
    """Belirli bir tarihteki hisse momentum skorunu hesaplar (bir gün önceki veri)"""
    try:
        ticker = yf.Ticker(symbol)
        start = ref_date - timedelta(days=35)
        adj_end = ref_date - timedelta(days=1)
        hist = ticker.history(start=start, end=adj_end)
        
        if len(hist) >= 5:
            current = hist['Close'].iloc[-1]
            week_ago = hist['Close'].iloc[-5] if len(hist) >= 5 else hist['Close'].iloc[0]
            month_ago = hist['Close'].iloc[0]
            
            weekly_momentum = ((current - week_ago) / week_ago) * 100
            monthly_momentum = ((current - month_ago) / month_ago) * 100
            
            return (weekly_momentum * 0.6 + monthly_momentum * 0.4)
        return None
    except:
        return None

def run_backtest_simulation(start_date, interval_days, period_key):
    """Backtesting simülasyonu - momentum bazlı (tarihsel veri sınırlaması nedeniyle)"""
    results = []
    portfolio_value = 100.0
    current_date = start_date
    today = datetime.now().date()
    
    lookback_days = PERIOD_LOOKBACK_DAYS.get(period_key, 30)
    
    while current_date < today:
        next_date = current_date + timedelta(days=interval_days)
        if next_date > today:
            next_date = today
        
        sector_performances = []
        for name, symbol in SECTOR_ETFS.items():
            lookback_start = current_date - timedelta(days=lookback_days)
            perf = get_historical_sector_performance(symbol, lookback_start, current_date)
            sector_performances.append({"Sektör": name, "Performans": perf, "ETF": symbol})
        
        sector_df = pd.DataFrame(sector_performances)
        sector_df = sector_df.sort_values(by="Performans", ascending=False)
        top_6 = sector_df.head(6)
        
        all_candidates = []
        used_symbols = set()
        
        for idx, (_, row) in enumerate(top_6.iterrows()):
            etf_symbol = row["ETF"]
            holdings = SECTOR_HOLDINGS.get(etf_symbol, [])
            quota = 2 if idx < 4 else 1
            
            sector_stocks = []
            for symbol in holdings:
                if symbol in used_symbols:
                    continue
                score = get_historical_momentum_score(symbol, current_date)
                if score is not None:
                    sector_stocks.append({"symbol": symbol, "score": score})
            
            sector_stocks.sort(key=lambda x: x["score"], reverse=True)
            
            for stock in sector_stocks[:quota]:
                all_candidates.append(stock["symbol"])
                used_symbols.add(stock["symbol"])
        
        if all_candidates:
            returns = []
            for symbol in all_candidates:
                ret = get_historical_stock_return(symbol, current_date, next_date)
                if ret is not None:
                    returns.append(ret)
            
            if returns:
                avg_return = sum(returns) / len(returns)
                portfolio_value = portfolio_value * (1 + avg_return / 100)
        
        results.append({
            "Tarih": current_date,
            "Portföy Değeri": round(portfolio_value, 2),
            "Seçilen Hisse": len(all_candidates)
        })
        
        current_date = next_date
    
    return pd.DataFrame(results)

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

def get_alerts():
    session = get_session()
    try:
        alerts = session.query(PriceAlert).filter(PriceAlert.is_triggered == False).all()
        return alerts
    finally:
        session.close()

def get_triggered_alerts():
    session = get_session()
    try:
        alerts = session.query(PriceAlert).filter(PriceAlert.is_triggered == True).order_by(PriceAlert.triggered_at.desc()).limit(10).all()
        return alerts
    finally:
        session.close()

def add_alert(symbol, alert_type, target_price):
    session = get_session()
    try:
        alert = PriceAlert(
            symbol=symbol.upper(),
            alert_type=alert_type,
            target_price=target_price
        )
        session.add(alert)
        session.commit()
        return True
    except:
        session.rollback()
        return False
    finally:
        session.close()

def remove_alert(alert_id):
    session = get_session()
    try:
        alert = session.query(PriceAlert).filter(PriceAlert.id == alert_id).first()
        if alert:
            session.delete(alert)
            session.commit()
            return True
        return False
    except:
        session.rollback()
        return False
    finally:
        session.close()

def check_and_trigger_alerts():
    session = get_session()
    triggered = []
    try:
        alerts = session.query(PriceAlert).filter(PriceAlert.is_triggered == False).all()
        for alert in alerts:
            current_price, _ = get_stock_price(alert.symbol)
            if current_price:
                should_trigger = False
                if alert.alert_type == "above" and current_price >= alert.target_price:
                    should_trigger = True
                elif alert.alert_type == "below" and current_price <= alert.target_price:
                    should_trigger = True
                
                if should_trigger:
                    alert.is_triggered = True
                    alert.triggered_at = datetime.now()
                    triggered.append({
                        "symbol": alert.symbol,
                        "type": alert.alert_type,
                        "target": alert.target_price,
                        "current": current_price
                    })
        session.commit()
        return triggered
    except:
        session.rollback()
        return []
    finally:
        session.close()

triggered_alerts = check_and_trigger_alerts()
if triggered_alerts:
    for alert in triggered_alerts:
        direction = "yukari cikti" if alert["type"] == "above" else "asagi dustu"
        st.toast(f"🚨 ALARM: {alert['symbol']} ${alert['target']:.2f} seviyesinin {direction}! Guncel: ${alert['current']:.2f}", icon="🔔")

with st.spinner("Piyasa verileri yükleniyor..."):
    if selected_market == "US":
        vix_val, vix_change = get_vix_data()
        if vix_val < 15:
            market_status = "REHAVET"
            strategy = "Dikkatli Ol"
            strategy_detail = "Piyasa 'pahalı' olabilir. Yeni büyük pozisyonlar için riskli."
        elif vix_val < 20:
            market_status = "STABIL"
            strategy = "Stratejik Alım"
            strategy_detail = "Kaliteli şirketlerde pozisyon artırmak için ideal bölge."
        elif vix_val < 30:
            market_status = "BELİRSİZLİK"
            strategy = "Seçici Alım"
            strategy_detail = "Volatilite artmış. Kademeli alım (DCA) için fırsatlar başlar."
        else:
            market_status = "PANİK"
            strategy = "Fırsat Alımı"
            strategy_detail = "Kontrariyan yatırımcılar için en güvenli alım bölgesi."
    else:
        bist_val, bist_change = get_bist100_data()
        usd_val, usd_change = get_usdtry_data()
        market_status = "POZİTİF" if bist_change > 0 else "NEGATİF"
        strategy = "Stratejik Alım" if bist_change > 0 else "Temkinli Ol"
        strategy_detail = ""

from datetime import time as dt_time
import pytz

def is_market_open(market):
    """Check if market is currently open"""
    now = datetime.now(pytz.UTC)
    if market == "US":
        ny_tz = pytz.timezone('America/New_York')
        ny_time = now.astimezone(ny_tz)
        if ny_time.weekday() >= 5:
            return False
        market_open = dt_time(9, 30)
        market_close = dt_time(16, 0)
        return market_open <= ny_time.time() <= market_close
    else:
        ist_tz = pytz.timezone('Europe/Istanbul')
        ist_time = now.astimezone(ist_tz)
        if ist_time.weekday() >= 5:
            return False
        market_open = dt_time(10, 0)
        market_close = dt_time(18, 0)
        return market_open <= ist_time.time() <= market_close

market_open = is_market_open(selected_market)
market_status_icon = "🟢" if market_open else "🔴"
market_status_text = "AÇIK" if market_open else "KAPALI"

col1, col2, col3, col4 = st.columns(4)
col1.metric("Borsa Durumu", f"{market_status_icon} {market_status_text}")
col2.metric("Piyasa Durumu", market_status, delta=None)

if selected_market == "US":
    col3.metric("VIX (Korku Endeksi)", f"{vix_val:.2f}", delta=f"{vix_change:+.2f}%")
    col4.metric("Önerilen Strateji", strategy)
    if strategy_detail:
        st.info(f"💡 **{strategy}:** {strategy_detail}")
    if not market_open:
        st.caption("⏰ ABD Borsası: 16:30 - 23:00 (TR saati) | Veriler son kapanışı gösteriyor")
else:
    col3.metric("BIST-100", f"{bist_val:,.0f}", delta=f"{bist_change:+.2f}%")
    col4.metric("USD/TRY", f"₺{usd_val:.2f}", delta=f"{usd_change:+.2f}%")
    if not market_open:
        st.caption("⏰ BIST: 10:00 - 18:00 (TR saati) | Veriler son kapanışı gösteriyor")

if investor_profile != "Seçiniz":
    st.divider()
    st.header(f"👤 {investor_profile} Yatırımcı Profili")
    
    profile_info = INVESTOR_PROFILES[investor_profile]
    st.info(f"**Hedef:** {profile_info['description']} | **Tercih:** {profile_info['preferred']}")
    
    with st.expander("📋 Profil Kriterleri", expanded=False):
        crit_col1, crit_col2, crit_col3 = st.columns(3)
        with crit_col1:
            if "beta_min" in profile_info:
                st.write(f"**Beta:** {profile_info['beta_min']} - {profile_info['beta_max']}")
            if "pe_max" in profile_info:
                st.write(f"**F/K:** < {profile_info['pe_max']}")
            elif "pe_min" in profile_info:
                st.write(f"**F/K:** > {profile_info['pe_min']}")
        with crit_col2:
            if "dividend_min" in profile_info:
                st.write(f"**Temettü:** > %{profile_info['dividend_min']}")
            elif "dividend_max" in profile_info:
                st.write(f"**Temettü:** < %{profile_info['dividend_max']}")
            if "debt_equity_max" in profile_info:
                st.write(f"**Borç/Özkaynak:** < {profile_info['debt_equity_max']}")
        with crit_col3:
            if "peg_max" in profile_info:
                st.write(f"**PEG:** < {profile_info['peg_max']}")
            if "peg_min" in profile_info and "peg_max" in profile_info:
                st.write(f"**PEG:** {profile_info['peg_min']} - {profile_info['peg_max']}")
    
    with st.spinner(f"{investor_profile} profiline uygun hisseler aranıyor..."):
        profile_stocks = get_profile_based_stocks(investor_profile, selected_market)
    
    if not profile_stocks.empty:
        st.success(f"**{len(profile_stocks)} hisse bulundu** - Kriterlere uyum yüzdesine göre sıralanmış")
        
        def color_profile_stocks(val):
            if isinstance(val, (int, float)):
                color = 'green' if val > 0 else 'red' if val < 0 else 'gray'
                return f'color: {color}'
            return ''
        
        numeric_cols_pf = profile_stocks.select_dtypes(include=['float64', 'float32', 'int64', 'int32']).columns.tolist()
        format_dict_pf = {col: "{:.2f}" for col in numeric_cols_pf}
        if "Uyum (%)" in format_dict_pf:
            format_dict_pf["Uyum (%)"] = "{:.0f}"
        styled_profile = profile_stocks.style.format(format_dict_pf).map(color_profile_stocks, subset=['Günlük Değişim (%)'])
        st.dataframe(styled_profile, hide_index=True, use_container_width=True)
        
        st.subheader("💼 Profil Portföyünü Kaydet")
        session = get_session()
        existing_pf = session.query(UserPortfolio.portfolio_name).distinct().all()
        existing_pf_names = [p[0] for p in existing_pf if p[0]]
        session.close()
        next_pf_num = len(existing_pf_names) + 1
        default_pf_name = f"{investor_profile} Portföy {next_pf_num}"
        
        with st.form("save_profile_portfolio_form"):
            col_prf1, col_prf2 = st.columns(2)
            with col_prf1:
                profile_pf_name = st.text_input("Portföy Adı", value=default_pf_name, key="profile_pf_name")
            with col_prf2:
                profile_investment = st.text_input("Toplam Yatırım (USD)", value="10.000", key="profile_investment")
            save_profile_btn = st.form_submit_button("💾 Profil Portföyü Oluştur", type="primary")
            
            if save_profile_btn:
                try:
                    pf_amount = int(profile_investment.replace(".", "").replace(",", ""))
                    if pf_amount < 100:
                        st.error("Minimum yatırım tutarı $100 olmalıdır.")
                        st.stop()
                except ValueError:
                    st.error("Geçerli bir tutar girin (örn: 10.000)")
                    st.stop()
                
                if not profile_pf_name.strip():
                    st.error("Portföy adı boş olamaz.")
                    st.stop()
                
                session = get_session()
                try:
                    stock_count_pf = len(profile_stocks)
                    per_stock_pf = pf_amount / stock_count_pf
                    price_col = "Fiyat ($)" if selected_market == "US" else "Fiyat (₺)"
                    
                    for _, row in profile_stocks.iterrows():
                        symbol = row['Sembol']
                        current_price = row[price_col] if price_col in row else 100
                        quantity = per_stock_pf / current_price if current_price > 0 else 0
                        
                        new_holding = UserPortfolio(
                            symbol=symbol,
                            sector=investor_profile,
                            quantity=quantity,
                            buy_price=current_price,
                            portfolio_name=profile_pf_name.strip()
                        )
                        session.add(new_holding)
                    
                    session.commit()
                    st.success(f"✅ '{profile_pf_name}' portföyü {stock_count_pf} hisse ile oluşturuldu!")
                    st.rerun()
                except Exception as e:
                    session.rollback()
                    st.error(f"Hata: {str(e)}")
                finally:
                    session.close()
    else:
        st.warning("Bu kriterlere uygun hisse bulunamadı. Lütfen farklı bir profil deneyin.")

st.divider()

st.header("🔥 Sektörel Performans")

selected_period = st.radio(
    "Zaman Aralığı Seçin:",
    options=list(PERIOD_OPTIONS.keys()),
    horizontal=True,
    index=1
)

with st.spinner("Sektör verileri yükleniyor..."):
    sector_data = get_sector_data(selected_period, selected_market)

sorted_sector_data = sector_data.sort_values(by="Değişim (%)", ascending=False)

if "selected_sector_name" not in st.session_state or st.session_state.get("last_market") != selected_market or st.session_state.get("last_period") != selected_period:
    if "Para Akışı (%)" in sector_data.columns:
        top_mf_sector = sector_data.sort_values(by="Para Akışı (%)", ascending=False).iloc[0]["Sektör"]
        st.session_state.selected_sector_name = top_mf_sector
    else:
        st.session_state.selected_sector_name = list(CURRENT_SECTOR_MAP.keys())[0]
    st.session_state.last_market = selected_market
    st.session_state.last_period = selected_period

price_max = sorted_sector_data["Değişim (%)"].max()
price_min = sorted_sector_data["Değişim (%)"].min()
price_y_max = price_max * 1.3 if price_max > 0 else price_max
price_y_min = price_min * 1.3 if price_min < 0 else price_min

fig_price = go.Figure(go.Bar(
    x=sorted_sector_data["Sektör"],
    y=sorted_sector_data["Değişim (%)"],
    marker_color=['green' if x > 0 else 'red' for x in sorted_sector_data["Değişim (%)"]],
    text=[f"{x:+.1f}%" for x in sorted_sector_data["Değişim (%)"]],
    textposition='outside',
    textfont=dict(size=10),
    hovertemplate="<b>%{x}</b><br>Fiyat Değişim: %{y:.2f}%<extra></extra>"
))

price_title = f"Fiyat Değişimi ({selected_period})"
if selected_market == "US":
    price_title = f"ABD Sektör Fiyat Değişimi ({selected_period})"
else:
    price_title = f"BIST Sektör Fiyat Değişimi ({selected_period})"

fig_price.update_layout(
    title=price_title,
    yaxis_title="Fiyat Değişimi (%)",
    showlegend=False,
    height=400,
    yaxis=dict(range=[price_y_min, price_y_max]),
    margin=dict(t=60, b=80)
)

price_event = st.plotly_chart(fig_price, use_container_width=True, on_select="rerun", key="sector_price_chart")

if price_event and price_event.selection and len(price_event.selection.points) > 0:
    price_clicked_idx = price_event.selection.points[0].get("point_index", None)
    if price_clicked_idx is not None:
        price_clicked_sector = sorted_sector_data.iloc[price_clicked_idx]["Sektör"]
        if price_clicked_sector in CURRENT_SECTOR_MAP:
            st.session_state.selected_sector_name = price_clicked_sector

if "Para Akışı (%)" in sorted_sector_data.columns:
    mf_sorted = sorted_sector_data.sort_values(by="Para Akışı (%)", ascending=False)
    mf_max = mf_sorted["Para Akışı (%)"].max()
    mf_min = mf_sorted["Para Akışı (%)"].min()
    mf_y_max = mf_max * 1.3 if mf_max > 0 else mf_max
    mf_y_min = mf_min * 1.3 if mf_min < 0 else mf_min
    
    fig_mf = go.Figure(go.Bar(
        x=mf_sorted["Sektör"],
        y=mf_sorted["Para Akışı (%)"],
        marker_color=['#00CED1' if x > 0 else '#FF6B6B' for x in mf_sorted["Para Akışı (%)"]],
        text=[f"{x:+.1f}%" for x in mf_sorted["Para Akışı (%)"]],
        textposition='outside',
        textfont=dict(size=10),
        hovertemplate="<b>%{x}</b><br>Para Akışı: %{y:.2f}%<extra></extra>"
    ))
    
    mf_title = f"Sektöre Giren Para Değişimi ({selected_period})"
    if selected_market == "US":
        mf_title = f"ABD Sektör Para Akışı ({selected_period})"
    else:
        mf_title = f"BIST Sektör Para Akışı ({selected_period})"
    
    fig_mf.update_layout(
        title=mf_title,
        yaxis_title="Para Akışı Değişimi (%)",
        showlegend=False,
        height=400,
        yaxis=dict(range=[mf_y_min, mf_y_max]),
        margin=dict(t=60, b=80)
    )
    
    event = st.plotly_chart(fig_mf, use_container_width=True, on_select="rerun", key="sector_mf_chart")
else:
    event = None

if event and event.selection and len(event.selection.points) > 0:
    clicked_idx = event.selection.points[0].get("point_index", None)
    if clicked_idx is not None:
        clicked_sector = mf_sorted.iloc[clicked_idx]["Sektör"]
        if clicked_sector in CURRENT_SECTOR_MAP:
            st.session_state.selected_sector_name = clicked_sector

st.subheader("🔍 Sektör Detayı")
selected_sector = st.session_state.selected_sector_name
st.success(f"**Seçili Sektör:** {selected_sector}")

if selected_sector:
    sector_key = CURRENT_SECTOR_MAP.get(selected_sector, "")
    with st.spinner(f"{selected_sector} şirketleri yükleniyor..."):
        holdings_data = get_sector_holdings_data(sector_key, selected_market)
    
    if not holdings_data.empty:
        def color_holdings(val):
            if isinstance(val, (int, float)):
                color = 'green' if val > 0 else 'red' if val < 0 else 'gray'
                return f'color: {color}'
            return ''
        
        numeric_cols = holdings_data.select_dtypes(include=['float64', 'float32', 'int64', 'int32']).columns.tolist()
        format_dict = {col: "{:.2f}" for col in numeric_cols}
        styled_holdings = holdings_data.style.format(format_dict).map(color_holdings, subset=['Değişim (%)'])
        st.dataframe(styled_holdings, hide_index=True, use_container_width=True)
    else:
        st.info("Bu sektör için şirket verisi bulunamadı.")

st.divider()

st.header("🎯 Sistemin Sizin İçin Seçtikleri")
market_name = "ABD" if selected_market == "US" else "BIST"
st.success(f"**{market_name} için en iyi 10 hisse önerisi**")

with st.spinner("Hisse verileri yükleniyor..."):
    portfolio = get_portfolio_data(selected_period, selected_market)

if not portfolio.empty:
    def color_portfolio(val):
        if isinstance(val, (int, float)):
            color = 'green' if val > 0 else 'red' if val < 0 else 'gray'
            return f'color: {color}'
        return ''
    
    numeric_cols = portfolio.select_dtypes(include=['float64', 'float32', 'int64', 'int32']).columns.tolist()
    format_dict = {col: "{:.2f}" for col in numeric_cols}
    styled_portfolio = portfolio.style.format(format_dict).map(color_portfolio, subset=['Günlük Değişim (%)'])
    st.dataframe(styled_portfolio, hide_index=True, use_container_width=True)
    
    st.subheader("💼 Portföyüm Olarak Kaydet")
    
    session = get_session()
    existing_portfolios = session.query(UserPortfolio.portfolio_name).distinct().all()
    existing_names = [p[0] for p in existing_portfolios if p[0]]
    session.close()
    next_portfolio_num = len(existing_names) + 1
    default_name = f"Portföy {next_portfolio_num}"
    
    with st.form("save_system_portfolio_form"):
        col_pf1, col_pf2 = st.columns(2)
        with col_pf1:
            portfolio_name_input = st.text_input(
                "Portföy Adı",
                value=default_name,
                help="Bu portföye bir isim verin (örn: Portföy 1, Agresif, Temkinli)"
            )
        with col_pf2:
            investment_input = st.text_input(
                "Toplam Yatırım (USD)",
                value="10.000",
                help="Binlik ayırıcı olarak nokta kullanın (örn: 10.000)"
            )
        save_portfolio_btn = st.form_submit_button("💾 Yeni Portföy Oluştur", type="primary")
        
        if save_portfolio_btn:
            try:
                investment_amount = int(investment_input.replace(".", "").replace(",", ""))
                if investment_amount < 100:
                    st.error("Minimum yatırım tutarı $100 olmalıdır.")
                    st.stop()
            except ValueError:
                st.error("Geçerli bir tutar girin (örn: 10.000)")
                st.stop()
            
            if not portfolio_name_input.strip():
                st.error("Portföy adı boş olamaz.")
                st.stop()
                
            session = get_session()
            try:
                stock_count = len(portfolio)
                per_stock_amount = investment_amount / stock_count
                
                for _, row in portfolio.iterrows():
                    symbol = row['Sembol']
                    price_col = PRICE_COL_NAME
                    current_price = row[price_col] if price_col in row else row.get('Fiyat ($)', row.get('Fiyat (₺)', 100))
                    quantity = per_stock_amount / current_price if current_price > 0 else 0
                    sector = row.get('Sektör', 'Bilinmiyor')
                    
                    new_holding = UserPortfolio(
                        symbol=symbol,
                        sector=sector,
                        quantity=quantity,
                        buy_price=current_price,
                        portfolio_name=portfolio_name_input.strip(),
                        time_period=selected_period
                    )
                    session.add(new_holding)
                
                session.commit()
                st.success(f"✅ '{portfolio_name_input}' adlı portföy {stock_count} hisse ile oluşturuldu! Toplam: ${investment_amount:,}")
                st.rerun()
            except Exception as e:
                session.rollback()
                st.error(f"Portföy oluşturulurken hata: {str(e)}")
            finally:
                session.close()
else:
    st.info("Portföy verisi bulunamadı.")

st.divider()

st.header("💰 Para Akışına Göre Seçimler")
market_name_mf = "ABD" if selected_market == "US" else "BIST"
st.success(f"**{market_name_mf} için para girişi en yüksek sektörlerden 10 hisse**")

with st.spinner("Para akışı verileri yükleniyor..."):
    mf_portfolio = get_money_flow_portfolio(selected_period, selected_market)

if not mf_portfolio.empty:
    def color_mf_portfolio(val):
        if isinstance(val, (int, float)):
            color = 'green' if val > 0 else 'red' if val < 0 else 'gray'
            return f'color: {color}'
        return ''
    
    numeric_cols_mf = mf_portfolio.select_dtypes(include=['float64', 'float32', 'int64', 'int32']).columns.tolist()
    format_dict_mf = {col: "{:.2f}" for col in numeric_cols_mf}
    styled_mf_portfolio = mf_portfolio.style.format(format_dict_mf).map(color_mf_portfolio, subset=['Günlük Değişim (%)'])
    st.dataframe(styled_mf_portfolio, hide_index=True, use_container_width=True)
    
    st.subheader("💼 Para Akışı Portföyünü Kaydet")
    
    session = get_session()
    existing_portfolios_mf = session.query(UserPortfolio.portfolio_name).distinct().all()
    existing_names_mf = [p[0] for p in existing_portfolios_mf if p[0]]
    session.close()
    next_portfolio_num_mf = len(existing_names_mf) + 1
    default_name_mf = f"Para Akışı {next_portfolio_num_mf}"
    
    with st.form("save_mf_portfolio_form"):
        col_mf1, col_mf2 = st.columns(2)
        with col_mf1:
            mf_portfolio_name = st.text_input(
                "Portföy Adı",
                value=default_name_mf,
                help="Bu portföye bir isim verin",
                key="mf_portfolio_name"
            )
        with col_mf2:
            mf_investment = st.text_input(
                "Toplam Yatırım (USD)",
                value="10.000",
                help="Binlik ayırıcı olarak nokta kullanın",
                key="mf_investment"
            )
        save_mf_btn = st.form_submit_button("💾 Para Akışı Portföyü Oluştur", type="primary")
        
        if save_mf_btn:
            try:
                mf_amount = int(mf_investment.replace(".", "").replace(",", ""))
                if mf_amount < 100:
                    st.error("Minimum yatırım tutarı $100 olmalıdır.")
                    st.stop()
            except ValueError:
                st.error("Geçerli bir tutar girin (örn: 10.000)")
                st.stop()
            
            if not mf_portfolio_name.strip():
                st.error("Portföy adı boş olamaz.")
                st.stop()
                
            session = get_session()
            try:
                stock_count_mf = len(mf_portfolio)
                per_stock_mf = mf_amount / stock_count_mf
                
                for _, row in mf_portfolio.iterrows():
                    symbol = row['Sembol']
                    price_col = PRICE_COL_NAME
                    current_price = row[price_col] if price_col in row else row.get('Fiyat ($)', row.get('Fiyat (₺)', 100))
                    quantity = per_stock_mf / current_price if current_price > 0 else 0
                    sector = row.get('Sektör', 'Bilinmiyor')
                    
                    new_holding = UserPortfolio(
                        symbol=symbol,
                        sector=sector,
                        quantity=quantity,
                        buy_price=current_price,
                        portfolio_name=mf_portfolio_name.strip()
                    )
                    session.add(new_holding)
                
                session.commit()
                st.success(f"✅ '{mf_portfolio_name}' adlı portföy {stock_count_mf} hisse ile oluşturuldu! Toplam: ${mf_amount:,}")
                st.rerun()
            except Exception as e:
                session.rollback()
                st.error(f"Portföy oluşturulurken hata: {str(e)}")
            finally:
                session.close()
else:
    st.info("Para akışı verisi bulunamadı.")

st.divider()

st.header("📈 Strateji Performans Testi")

backtest_method = st.radio(
    "Test Yöntemi Seçin:",
    options=["5 Kriterli Tam Analiz (FMP API)", "Momentum Bazlı Basit Test"],
    horizontal=True,
    help="5 Kriterli analiz FMP API kullanır ve daha doğru sonuçlar verir"
)

if backtest_method == "5 Kriterli Tam Analiz (FMP API)":
    if FMP_API_KEY:
        st.success("✅ FMP API bağlantısı aktif - Tam 5 kriterli analiz kullanılacak")
        st.info("""**5 Kriter:** Değerleme (P/E), Büyüme (gelir), Karlılık (net marj), Momentum (fiyat), Revizyonlar (EPS büyümesi)
        
Bu test, canlı sistemdeki aynı kriterleri tarihsel verilere uygular.""")
    else:
        st.error("❌ FMP API anahtarı bulunamadı. Lütfen FMP_API_KEY ortam değişkenini ayarlayın.")
else:
    st.warning("""**Momentum Bazlı Test:** Sadece sektör performansı + fiyat momentumu kullanır.
    
Tarihsel P/E, gelir büyümesi gibi temel veriler dahil edilmez.""")

col_bt1, col_bt2, col_bt3 = st.columns(3)

with col_bt1:
    min_date = datetime.now().date() - timedelta(days=365*2)
    max_date = datetime.now().date() - timedelta(days=30)
    backtest_start = st.date_input(
        "Başlangıç Tarihi",
        value=datetime.now().date() - timedelta(days=180),
        min_value=min_date,
        max_value=max_date
    )

with col_bt2:
    backtest_interval = st.selectbox(
        "Portföy Yenileme Aralığı",
        options=list(BACKTEST_INTERVALS.keys()),
        index=2
    )

with col_bt3:
    st.write("")
    st.write("")
    run_backtest = st.button("🚀 Simülasyonu Başlat", type="primary")

if run_backtest:
    interval_days = BACKTEST_INTERVALS[backtest_interval]
    
    if backtest_method == "5 Kriterli Tam Analiz (FMP API)" and FMP_API_KEY:
        with st.spinner("5 kriterli simülasyon çalışıyor... FMP verileri çekiliyor, bu işlem biraz zaman alabilir."):
            backtest_results = run_fmp_backtest_simulation(backtest_start, interval_days, selected_period)
    else:
        with st.spinner("Momentum simülasyonu çalışıyor..."):
            backtest_results = run_backtest_simulation(backtest_start, interval_days, selected_period)
    
    if not backtest_results.empty:
        final_value = backtest_results["Portföy Değeri"].iloc[-1]
        total_return = ((final_value - 100) / 100) * 100
        
        col_res1, col_res2, col_res3 = st.columns(3)
        col_res1.metric("Başlangıç Değeri", "$100.00")
        col_res2.metric("Son Değer", f"${final_value:.2f}")
        col_res3.metric("Toplam Getiri", f"%{total_return:.2f}", delta=f"{total_return:.2f}%")
        
        fig_backtest = go.Figure()
        fig_backtest.add_trace(go.Scatter(
            x=backtest_results["Tarih"],
            y=backtest_results["Portföy Değeri"],
            mode='lines+markers',
            name='Portföy Değeri',
            line=dict(color='#00D4AA', width=2),
            marker=dict(size=6)
        ))
        
        fig_backtest.add_hline(y=100, line_dash="dash", line_color="gray", annotation_text="Başlangıç: $100")
        
        method_label = "5 Kriterli" if (backtest_method == "5 Kriterli Tam Analiz (FMP API)" and FMP_API_KEY) else "Momentum"
        fig_backtest.update_layout(
            title=f"{method_label} Strateji Performansı ({backtest_start} - Bugün)",
            xaxis_title="Tarih",
            yaxis_title="Portföy Değeri ($)",
            template="plotly_dark",
            height=400
        )
        
        st.plotly_chart(fig_backtest, use_container_width=True)
        
        st.subheader("Dönemsel Detaylar")
        numeric_cols = backtest_results.select_dtypes(include=['float64', 'float32', 'int64', 'int32']).columns.tolist()
        format_dict = {col: "{:.2f}" for col in numeric_cols}
        styled_backtest = backtest_results.style.format(format_dict)
        st.dataframe(styled_backtest, hide_index=True, use_container_width=True)
    else:
        st.warning("Simülasyon sonuçları oluşturulamadı. Lütfen farklı bir tarih aralığı seçin.")

st.divider()

st.header("💼 Benim Portföylerim")

session = get_session()
all_portfolio_names = session.query(UserPortfolio.portfolio_name).distinct().all()
portfolio_names = [p[0] for p in all_portfolio_names if p[0]]
session.close()

if portfolio_names:
    selected_portfolio_name = st.selectbox(
        "📂 Portföy Seçin",
        options=portfolio_names,
        index=0
    )
    
    session = get_session()
    user_stocks = session.query(UserPortfolio).filter(UserPortfolio.portfolio_name == selected_portfolio_name).all()
    session.close()
    
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
                daily_pnl = current_value * (daily_change / 100) if daily_change else 0
                total_value += current_value
                total_cost += cost_basis
                
                portfolio_data.append({
                    "ID": stock.id,
                    "Sembol": stock.symbol,
                    "Sektör": stock.sector or "-",
                    "Adet": round(stock.quantity, 4),
                    "Maliyet ($)": round(cost_basis, 2),
                    "Güncel Fiyat ($)": round(current_price, 2),
                    "Günlük (%)": round(daily_change, 2) if daily_change else 0,
                    "Günlük K/Z ($)": round(daily_pnl, 2),
                    "Toplam (%)": round(profit_loss_pct, 2),
                    "Toplam K/Z ($)": round(profit_loss, 2)
                })
            else:
                portfolio_data.append({
                    "ID": stock.id,
                    "Sembol": stock.symbol,
                    "Sektör": stock.sector or "-",
                    "Adet": round(stock.quantity, 4),
                    "Maliyet ($)": "-",
                    "Güncel Fiyat ($)": "-",
                    "Günlük (%)": "-",
                    "Günlük K/Z ($)": "-",
                    "Toplam (%)": "-",
                    "Toplam K/Z ($)": "-"
                })
        
        user_df = pd.DataFrame(portfolio_data)
        
        col_summary1, col_summary2, col_summary3 = st.columns(3)
        col_summary1.metric("Toplam Değer", f"${total_value:,.2f}")
        col_summary2.metric("Toplam Maliyet", f"${total_cost:,.2f}")
        total_profit = total_value - total_cost
        col_summary3.metric("Toplam Kar/Zarar", f"${total_profit:,.2f}", delta=f"{(total_profit/total_cost*100) if total_cost > 0 else 0:.2f}%")
        
        display_df = user_df.drop(columns=['ID'])
        numeric_cols = display_df.select_dtypes(include=['float64', 'float32', 'int64', 'int32']).columns.tolist()
        format_dict = {col: "{:.2f}" for col in numeric_cols}
        styled_user_df = display_df.style.format(format_dict, na_rep="-")
        st.dataframe(styled_user_df, hide_index=True, use_container_width=True)
        
        col_action1, col_action2 = st.columns(2)
        
        with col_action1:
            st.subheader("Hisse Sil")
            col_del1, col_del2 = st.columns([3, 1])
            with col_del1:
                stock_to_delete = st.selectbox(
                    "Silinecek hisse seçin",
                    options=[(s.id, f"{s.symbol} - {s.quantity:.4f} adet") for s in user_stocks],
                    format_func=lambda x: x[1]
                )
            with col_del2:
                st.write("")
                if st.button("🗑️ Sil", type="secondary"):
                    if stock_to_delete:
                        if remove_stock_from_portfolio(stock_to_delete[0]):
                            st.success(f"Hisse silindi!")
                            st.cache_data.clear()
                            st.rerun()
        
        with col_action2:
            st.subheader("Portföyü Sil")
            if st.button(f"🗑️ '{selected_portfolio_name}' Portföyünü Tamamen Sil", type="secondary"):
                session = get_session()
                try:
                    session.query(UserPortfolio).filter(UserPortfolio.portfolio_name == selected_portfolio_name).delete()
                    session.commit()
                    st.success(f"'{selected_portfolio_name}' portföyü silindi!")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    session.rollback()
                    st.error(f"Hata: {str(e)}")
                finally:
                    session.close()
else:
    user_stocks = get_user_portfolio()
    if not user_stocks:
        st.info("Henüz portföyünüze hisse eklemediniz. Yukarıdan 'Portföyüm Olarak Kaydet' ile oluşturabilirsiniz.")

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

st.header("🔔 Fiyat Alarmları")

active_alerts = get_alerts()
triggered_history = get_triggered_alerts()

col_alerts1, col_alerts2 = st.columns(2)

with col_alerts1:
    st.subheader("Aktif Alarmlar")
    if active_alerts:
        for alert in active_alerts:
            current_price, _ = get_stock_price(alert.symbol)
            direction = "yukarı" if alert.alert_type == "above" else "aşağı"
            icon = "📈" if alert.alert_type == "above" else "📉"
            
            col_a, col_b = st.columns([4, 1])
            with col_a:
                st.write(f"{icon} **{alert.symbol}**: ${alert.target_price:.2f} {direction} (Güncel: ${current_price:.2f if current_price else 0:.2f})")
            with col_b:
                if st.button("❌", key=f"del_alert_{alert.id}"):
                    if remove_alert(alert.id):
                        st.rerun()
    else:
        st.info("Aktif alarm bulunmuyor.")

with col_alerts2:
    st.subheader("Tetiklenen Alarmlar")
    if triggered_history:
        for alert in triggered_history:
            direction = "yukarı çıktı" if alert.alert_type == "above" else "aşağı düştü"
            icon = "✅"
            triggered_time = alert.triggered_at.strftime("%d/%m %H:%M") if alert.triggered_at else "-"
            st.write(f"{icon} **{alert.symbol}**: ${alert.target_price:.2f} {direction} ({triggered_time})")
    else:
        st.info("Henüz tetiklenen alarm yok.")

st.subheader("Yeni Alarm Ekle")

with st.form("add_alert_form"):
    col_alert_form1, col_alert_form2, col_alert_form3 = st.columns(3)
    
    with col_alert_form1:
        alert_symbol = st.text_input("Hisse Sembolü", max_chars=10, key="alert_symbol")
    
    with col_alert_form2:
        alert_type = st.selectbox("Alarm Tipi", [
            ("above", "Fiyat Yukarı Çıkarsa"),
            ("below", "Fiyat Aşağı Düşerse")
        ], format_func=lambda x: x[1])
    
    with col_alert_form3:
        alert_price = st.number_input("Hedef Fiyat ($)", min_value=0.01, value=100.0, step=0.01)
    
    alert_submitted = st.form_submit_button("🔔 Alarm Ekle", type="primary")
    
    if alert_submitted:
        if alert_symbol:
            current_price, _ = get_stock_price(alert_symbol.upper())
            if current_price:
                if add_alert(alert_symbol, alert_type[0], alert_price):
                    st.success(f"{alert_symbol.upper()} için alarm eklendi! Hedef: ${alert_price:.2f}")
                    st.rerun()
                else:
                    st.error("Alarm eklenirken bir hata oluştu.")
            else:
                st.error(f"{alert_symbol.upper()} sembolü bulunamadı.")
        else:
            st.warning("Lütfen hisse sembolü girin.")

st.divider()

st.sidebar.header("📁 Portföylerim")
session_pf = get_session()
try:
    from sqlalchemy import func
    portfolio_summary = session_pf.query(
        UserPortfolio.portfolio_name,
        func.min(UserPortfolio.added_at).label('created_at'),
        func.count(UserPortfolio.id).label('stock_count'),
        func.sum(UserPortfolio.quantity * UserPortfolio.buy_price).label('total_investment')
    ).group_by(UserPortfolio.portfolio_name).all()
    
    if portfolio_summary:
        for pf in portfolio_summary:
            pf_name = pf.portfolio_name or "İsimsiz"
            created_date = pf.created_at.strftime("%d/%m/%Y") if pf.created_at else "-"
            stock_count = pf.stock_count or 0
            total_inv = pf.total_investment or 0
            
            pf_stocks = session_pf.query(UserPortfolio).filter(UserPortfolio.portfolio_name == pf_name).all()
            current_value = 0
            for stock in pf_stocks:
                price, _ = get_stock_price(stock.symbol)
                if price:
                    current_value += stock.quantity * price
            
            if total_inv > 0:
                performance = ((current_value - total_inv) / total_inv) * 100
                perf_color = "🟢" if performance >= 0 else "🔴"
                perf_text = f"{perf_color} {performance:+.1f}%"
            else:
                perf_text = "-"
            
            pf_time_period = pf_stocks[0].time_period if pf_stocks and hasattr(pf_stocks[0], 'time_period') and pf_stocks[0].time_period else "5 Gün"
            pf_symbols = set([s.symbol for s in pf_stocks])
            
            try:
                current_recommendations = get_portfolio_data(pf_time_period, selected_market)
                if not current_recommendations.empty:
                    new_symbols = set(current_recommendations['Sembol'].tolist())
                    to_remove = pf_symbols - new_symbols
                    to_add = new_symbols - pf_symbols
                    has_changes = len(to_remove) > 0 or len(to_add) > 0
                else:
                    has_changes = False
                    to_remove = set()
                    to_add = set()
            except:
                has_changes = False
                to_remove = set()
                to_add = set()
            
            alert_icon = "🔔" if has_changes else "📊"
            
            with st.sidebar.expander(f"{alert_icon} {pf_name}", expanded=False):
                st.caption(f"📅 Oluşturma: {created_date}")
                st.caption(f"⏱️ Zaman Aralığı: {pf_time_period}")
                st.caption(f"📈 Hisse Sayısı: {stock_count}")
                st.caption(f"💰 Yatırım: ${total_inv:,.0f}")
                st.caption(f"💵 Güncel: ${current_value:,.0f}")
                st.write(f"**Performans:** {perf_text}")
                
                if has_changes:
                    st.markdown("---")
                    st.warning("⚠️ **Güncelleme Önerisi**")
                    change_messages = []
                    if to_remove:
                        for sym in list(to_remove)[:3]:
                            matching_new = list(to_add)[:1]
                            if matching_new:
                                st.caption(f"🔄 **{sym}** → **{matching_new[0]}** ile değiştir")
                                change_messages.append(f"🔄 {sym} → {matching_new[0]} ile değiştir")
                            else:
                                st.caption(f"❌ **{sym}** çıkar")
                                change_messages.append(f"❌ {sym} çıkar")
                    if to_add and len(to_add) > len(to_remove):
                        extra_adds = list(to_add)[len(to_remove):len(to_remove)+2]
                        for sym in extra_adds:
                            st.caption(f"➕ **{sym}** ekle")
                            change_messages.append(f"➕ {sym} ekle")
                    
                    if st.button("📲 Telegram'a Gönder", key=f"tg_{pf_name}"):
                        msg = f"📊 <b>{pf_name}</b> Güncelleme Önerisi\n"
                        msg += f"⏱️ Zaman Aralığı: {pf_time_period}\n"
                        msg += f"📈 Performans: {perf_text}\n\n"
                        msg += "\n".join(change_messages)
                        if send_telegram_message(msg):
                            st.success("✅ Telegram'a gönderildi!")
                        else:
                            st.error("Gönderilemedi. Token/Chat ID kontrol edin.")
                
                st.markdown("---")
                st.markdown("**Hisse Detayları:**")
                for stock in pf_stocks:
                    s_price, _ = get_stock_price(stock.symbol)
                    if s_price and stock.buy_price > 0:
                        s_perf = ((s_price - stock.buy_price) / stock.buy_price) * 100
                        s_icon = "🟢" if s_perf >= 0 else "🔴"
                        st.caption(f"{s_icon} {stock.symbol}: ${stock.buy_price:.2f} → ${s_price:.2f} ({s_perf:+.1f}%)")
                    else:
                        st.caption(f"⚪ {stock.symbol}: ${stock.buy_price:.2f}")
                
                st.markdown("---")
                if st.button(f"🗑️ Portföyü Sil", key=f"del_pf_{pf_name}"):
                    try:
                        session_pf.query(UserPortfolio).filter(UserPortfolio.portfolio_name == pf_name).delete()
                        session_pf.commit()
                        st.cache_data.clear()
                        st.rerun()
                    except:
                        session_pf.rollback()
    else:
        st.sidebar.info("Henüz portföy oluşturmadınız.")
except Exception as e:
    st.sidebar.warning("Portföy bilgisi yüklenemedi.")
finally:
    session_pf.close()

st.sidebar.divider()

st.sidebar.header("🗓️ Günlük Finansal Haberler")
news_items = fetch_market_news(selected_market)
if news_items:
    news_text = "\n".join([f"- {item}" for item in news_items])
    st.sidebar.info(news_text)
    st.sidebar.caption("📡 NewsAPI - Her 15 dakikada güncellenir")
else:
    if selected_market == "US":
        st.sidebar.info("""
- **Fed Kararı:** Faizlerde sabit kalma beklentisi.
- **Trend:** AI çiplerinden veri merkezi altyapısına rotasyon var.
- **Dikkat:** Teknoloji bilançoları volatiliteyi artırabilir.
""")
    else:
        st.sidebar.info("""
- **TCMB:** Faiz kararı takip edilmeli.
- **Trend:** Bankacılık ve holding hisseleri öne çıkıyor.
- **Dikkat:** Dolar/TL paritesi volatiliteyi etkiliyor.
""")
    st.sidebar.caption("⚠️ Haber servisi bağlanamadı - varsayılan notlar")

st.sidebar.divider()

st.sidebar.header("📲 Telegram Bildirimleri")
if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
    st.sidebar.success("✅ Telegram bağlı")
    if st.sidebar.button("🔔 Test Mesajı Gönder"):
        if send_telegram_message("✅ Morning Alpha Dashboard bağlantısı başarılı!"):
            st.sidebar.success("Test mesajı gönderildi!")
        else:
            st.sidebar.error("Mesaj gönderilemedi")
else:
    st.sidebar.warning("⚠️ Telegram ayarlanmamış")

st.sidebar.divider()

active_count = len(active_alerts) if active_alerts else 0
st.sidebar.header(f"🔔 Alarmlar ({active_count} aktif)")
if active_alerts:
    for alert in active_alerts[:5]:
        direction = "↑" if alert.alert_type == "above" else "↓"
        st.sidebar.caption(f"{alert.symbol} {direction} ${alert.target_price:.2f}")

st.sidebar.divider()
st.sidebar.header("⚡ Otomatik Yenileme")
refresh_option = st.sidebar.selectbox(
    "Yenileme Aralığı",
    options=list(REFRESH_INTERVALS.keys()),
    index=4
)

refresh_interval = REFRESH_INTERVALS[refresh_option]
if refresh_interval > 0:
    count = st_autorefresh(interval=refresh_interval, limit=None, key="auto_refresh")
    st.sidebar.success(f"Her {refresh_option} yenileniyor")
else:
    st.sidebar.info("Otomatik yenileme kapalı")

st.sidebar.divider()
st.sidebar.header("📊 Veri Bilgisi")
st.sidebar.caption(f"Son güncelleme: {datetime.now().strftime('%H:%M:%S')}")
if st.sidebar.button("🔄 Verileri Yenile"):
    st.cache_data.clear()
    st.rerun()

st.caption("Bu veriler sadece eğitim amaçlıdır. Yatırım tavsiyesi içermez. Veriler Yahoo Finance'tan alınmaktadır.")
