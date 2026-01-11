import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf
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

st.title("☀️ Morning Alpha: Yatırım Karar Destek Paneli")
st.subheader("Piyasa Analizi ve Sektörel Fırsatlar")

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

PERIOD_OPTIONS = {
    "1 Gün": ("2d", 1),
    "5 Gün": ("7d", 5),
    "15 Gün": ("20d", 15),
    "1 Ay": ("35d", 22),
    "3 Ay": ("100d", 63),
    "6 Ay": ("200d", 126),
    "1 Yıl": ("400d", 252)
}

SECTOR_ETFS = {
    "Yapay Zeka (BOTZ)": "BOTZ",
    "Siber Güvenlik (HACK)": "HACK",
    "Yenilenebilir Enerji (ICLN)": "ICLN",
    "Fintech (FINX)": "FINX",
    "Biyoteknoloji (XBI)": "XBI",
    "Teknoloji (XLK)": "XLK",
    "Sağlık (XLV)": "XLV",
    "Finans (XLF)": "XLF",
    "Enerji (XLE)": "XLE",
    "Tüketici (XLY)": "XLY",
    "Sanayi (XLI)": "XLI",
    "Malzeme (XLB)": "XLB",
    "Gayrimenkul (XLRE)": "XLRE",
    "İletişim (XLC)": "XLC",
    "Yarı İletken (SMH)": "SMH"
}

SECTOR_HOLDINGS = {
    "BOTZ": ["NVDA", "ISRG", "INTC", "TER", "IRBT", "PATH", "CGNX", "ALGN", "ROK", "EMR"],
    "HACK": ["CRWD", "PANW", "FTNT", "ZS", "OKTA", "CYBR", "S", "NET", "TENB", "RPD"],
    "ICLN": ["ENPH", "FSLR", "SEDG", "RUN", "PLUG", "NEE", "BE", "CSIQ", "JKS", "NOVA"],
    "FINX": ["SQ", "PYPL", "INTU", "FIS", "FISV", "COIN", "HOOD", "SOFI", "AFRM", "UPST"],
    "XBI": ["MRNA", "VRTX", "REGN", "BIIB", "GILD", "AMGN", "ILMN", "EXAS", "SGEN", "ALNY"],
    "XLK": ["AAPL", "MSFT", "NVDA", "AVGO", "CRM", "ADBE", "CSCO", "ACN", "ORCL", "IBM"],
    "XLV": ["UNH", "JNJ", "LLY", "PFE", "ABBV", "MRK", "TMO", "DHR", "ABT", "BMY"],
    "XLF": ["BRK-B", "JPM", "V", "MA", "BAC", "WFC", "GS", "MS", "AXP", "C"],
    "XLE": ["XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY", "HAL"],
    "XLY": ["AMZN", "TSLA", "HD", "MCD", "NKE", "LOW", "SBUX", "TJX", "BKNG", "CMG"],
    "XLI": ["CAT", "UNP", "HON", "BA", "GE", "RTX", "DE", "LMT", "UPS", "MMM"],
    "XLB": ["LIN", "APD", "SHW", "ECL", "DD", "FCX", "NEM", "DOW", "NUE", "VMC"],
    "XLRE": ["PLD", "AMT", "EQIX", "CCI", "SPG", "PSA", "O", "DLR", "WELL", "AVB"],
    "XLC": ["META", "GOOGL", "NFLX", "DIS", "T", "VZ", "CMCSA", "CHTR", "TMUS", "EA"],
    "SMH": ["NVDA", "TSM", "AVGO", "ASML", "AMD", "QCOM", "TXN", "INTC", "MU", "AMAT"]
}

@st.cache_data(ttl=60)
def get_sector_data(period_key="1 Gün"):
    sector_etfs = SECTOR_ETFS
    
    fetch_period, lookback_days = PERIOD_OPTIONS.get(period_key, ("2d", 1))
    
    results = []
    for name, symbol in sector_etfs.items():
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=fetch_period)
            if len(hist) > lookback_days:
                current = hist['Close'].iloc[-1]
                previous = hist['Close'].iloc[-(lookback_days + 1)]
                change = ((current - previous) / previous) * 100
                results.append({"Sektör": name, "Değişim (%)": round(change, 2)})
            elif len(hist) >= 2:
                current = hist['Close'].iloc[-1]
                previous = hist['Close'].iloc[0]
                change = ((current - previous) / previous) * 100
                results.append({"Sektör": name, "Değişim (%)": round(change, 2)})
            else:
                results.append({"Sektör": name, "Değişim (%)": 0})
        except:
            results.append({"Sektör": name, "Değişim (%)": 0})
    
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
def get_sector_holdings_data(etf_symbol):
    holdings = SECTOR_HOLDINGS.get(etf_symbol, [])
    raw_data = []
    
    for symbol in holdings:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="10d")
            info = ticker.info
            company_name = info.get("shortName", symbol)
            
            forward_pe = info.get("forwardPE", 0) or 0
            peg_ratio = info.get("pegRatio", 0) or 0
            revenue_growth = info.get("revenueGrowth", 0) or 0
            profit_margin = info.get("profitMargins", 0) or 0
            
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
                    "Sembol": symbol,
                    "Şirket": company_name[:20],
                    "Fiyat ($)": round(current, 2),
                    "Değişim (%)": round(daily_change, 2),
                    "_valuation": valuation_score,
                    "_growth": revenue_growth * 100,
                    "_profitability": profit_margin * 100,
                    "_momentum": momentum
                })
        except:
            pass
    
    if not raw_data:
        return pd.DataFrame()
    
    valuations = normalize_score([d["_valuation"] for d in raw_data])
    growths = normalize_score([d["_growth"] for d in raw_data])
    profits = normalize_score([d["_profitability"] for d in raw_data])
    momentums = normalize_score([d["_momentum"] for d in raw_data])
    
    final_data = []
    for i, d in enumerate(raw_data):
        val_puan = round(valuations[i] * 0.25, 1)
        buy_puan = round(growths[i] * 0.25, 1)
        kar_puan = round(profits[i] * 0.25, 1)
        mom_puan = round(momentums[i] * 0.25, 1)
        toplam = round(val_puan + buy_puan + kar_puan + mom_puan, 1)
        
        final_data.append({
            "Sembol": d["Sembol"],
            "Şirket": d["Şirket"],
            "Fiyat ($)": d["Fiyat ($)"],
            "Değişim (%)": d["Değişim (%)"],
            "Değerleme": val_puan,
            "Büyüme": buy_puan,
            "Karlılık": kar_puan,
            "Momentum": mom_puan,
            "Toplam Puan": toplam
        })
    
    df = pd.DataFrame(final_data)
    df = df.sort_values(by="Toplam Puan", ascending=False).head(5)
    return df

@st.cache_data(ttl=60)
def get_top_stocks_from_sector(etf_symbol, sector_name, count=2):
    """Belirli bir sektörden en yüksek puanlı hisseleri seçer"""
    holdings = SECTOR_HOLDINGS.get(etf_symbol, [])
    raw_data = []
    
    for symbol in holdings:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="10d")
            info = ticker.info
            company_name = info.get("shortName", symbol)
            
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
                    "Sembol": symbol,
                    "Şirket": company_name[:20],
                    "Sektör": sector_name,
                    "Fiyat ($)": round(current, 2),
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
        val_puan = round(valuations[i] * 0.20, 1)
        buy_puan = round(growths[i] * 0.20, 1)
        kar_puan = round(profits[i] * 0.20, 1)
        mom_puan = round(momentums[i] * 0.20, 1)
        rev_puan = round(revisions[i] * 0.20, 1)
        toplam = round(val_puan + buy_puan + kar_puan + mom_puan + rev_puan, 1)
        
        final_data.append({
            "Sembol": d["Sembol"],
            "Şirket": d["Şirket"],
            "Sektör": d["Sektör"],
            "Fiyat ($)": d["Fiyat ($)"],
            "Günlük Değişim (%)": d["Günlük Değişim (%)"],
            "Toplam Puan": toplam
        })
    
    sorted_data = sorted(final_data, key=lambda x: x["Toplam Puan"], reverse=True)
    return sorted_data[:count]

@st.cache_data(ttl=60)
def get_all_sector_candidates(etf_symbol, sector_name):
    """Bir sektördeki tüm adayları puanlarıyla döndürür"""
    holdings = SECTOR_HOLDINGS.get(etf_symbol, [])
    raw_data = []
    
    for symbol in holdings:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="10d")
            info = ticker.info
            company_name = info.get("shortName", symbol)
            
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
                    "Sembol": symbol,
                    "Şirket": company_name[:20],
                    "Sektör": sector_name,
                    "Fiyat ($)": round(current, 2),
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
        val_puan = round(valuations[i] * 0.20, 1)
        buy_puan = round(growths[i] * 0.20, 1)
        kar_puan = round(profits[i] * 0.20, 1)
        mom_puan = round(momentums[i] * 0.20, 1)
        rev_puan = round(revisions[i] * 0.20, 1)
        toplam = round(val_puan + buy_puan + kar_puan + mom_puan + rev_puan, 1)
        
        final_data.append({
            "Sembol": d["Sembol"],
            "Şirket": d["Şirket"],
            "Sektör": d["Sektör"],
            "Fiyat ($)": d["Fiyat ($)"],
            "Günlük Değişim (%)": d["Günlük Değişim (%)"],
            "Toplam Puan": toplam
        })
    
    return sorted(final_data, key=lambda x: x["Toplam Puan"], reverse=True)

@st.cache_data(ttl=60)
def get_portfolio_data(period_key="1 Gün"):
    sector_df = get_sector_data(period_key)
    sector_df = sector_df.sort_values(by="Değişim (%)", ascending=False)
    
    top_6_sectors = sector_df.head(6)
    
    sector_candidates = {}
    sector_quotas = {}
    
    for idx, row in top_6_sectors.iterrows():
        sector_name = row["Sektör"]
        etf_symbol = SECTOR_ETFS.get(sector_name, "")
        rank = list(top_6_sectors.index).index(idx) + 1
        
        candidates = get_all_sector_candidates(etf_symbol, sector_name)
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

BACKTEST_INTERVALS = {
    "Haftalık": 7,
    "2 Haftalık": 14,
    "Aylık": 30,
    "2 Aylık": 60,
    "3 Aylık": 90
}

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
    vix_val, vix_change = get_vix_data()

market_status = "GÜVENLİ" if vix_val < 25 else "RİSKLİ"

col1, col2, col3 = st.columns(3)
col1.metric("Piyasa Durumu", market_status, delta=None)
col2.metric("VIX (Korku Endeksi)", f"{vix_val:.2f}", delta=f"{vix_change:+.2f}%")
col3.metric("Önerilen Strateji", "Alım Yapılabilir" if market_status == "GÜVENLİ" else "Nakde Geç")

st.divider()

st.header("🔥 Sektörel Performans")

selected_period = st.radio(
    "Zaman Aralığı Seçin:",
    options=list(PERIOD_OPTIONS.keys()),
    horizontal=True,
    index=0
)

with st.spinner("Sektör verileri yükleniyor..."):
    sector_data = get_sector_data(selected_period)

sorted_sector_data = sector_data.sort_values(by="Değişim (%)", ascending=False)

if "selected_sector_name" not in st.session_state:
    st.session_state.selected_sector_name = list(SECTOR_ETFS.keys())[0]

max_val = sorted_sector_data["Değişim (%)"].max()
min_val = sorted_sector_data["Değişim (%)"].min()
y_max = max_val * 1.25 if max_val > 0 else max_val
y_min = min_val * 1.25 if min_val < 0 else min_val

fig = go.Figure(go.Bar(
    x=sorted_sector_data["Sektör"],
    y=sorted_sector_data["Değişim (%)"],
    marker_color=['green' if x > 0 else 'red' for x in sorted_sector_data["Değişim (%)"]],
    text=[f"{x:+.2f}%" for x in sorted_sector_data["Değişim (%)"]],
    textposition='outside',
    textfont=dict(size=11),
    hovertemplate="<b>%{x}</b><br>Değişim: %{y:.2f}%<extra></extra>"
))
fig.update_layout(
    title=f"Sektör ETF Performansı ({selected_period}) - Detay için çubuğa tıklayın",
    yaxis_title=f"Değişim ({selected_period}) (%)",
    showlegend=False,
    height=500,
    yaxis=dict(range=[y_min, y_max]),
    margin=dict(t=60, b=80)
)

event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", key="sector_bar_chart")

if event and event.selection and len(event.selection.points) > 0:
    clicked_idx = event.selection.points[0].get("point_index", None)
    if clicked_idx is not None:
        clicked_sector = sorted_sector_data.iloc[clicked_idx]["Sektör"]
        if clicked_sector in SECTOR_ETFS:
            st.session_state.selected_sector_name = clicked_sector

st.subheader("🔍 Sektör Detayı")
selected_sector = st.session_state.selected_sector_name
st.success(f"**Seçili Sektör:** {selected_sector}")

if selected_sector:
    etf_symbol = SECTOR_ETFS[selected_sector]
    with st.spinner(f"{selected_sector} şirketleri yükleniyor..."):
        holdings_data = get_sector_holdings_data(etf_symbol)
    
    if not holdings_data.empty:
        def color_holdings(val):
            if isinstance(val, (int, float)):
                color = 'green' if val > 0 else 'red' if val < 0 else 'gray'
                return f'color: {color}'
            return ''
        
        styled_holdings = holdings_data.style.map(color_holdings, subset=['Değişim (%)'])
        st.dataframe(styled_holdings, hide_index=True, use_container_width=True)
    else:
        st.info("Bu sektör için şirket verisi bulunamadı.")

st.divider()

st.header("🎯 Sistemin Sizin İçin Seçtikleri")
st.success("**En iyi 10 hisse önerisi**")

with st.spinner("Hisse verileri yükleniyor..."):
    portfolio = get_portfolio_data(selected_period)

if not portfolio.empty:
    def color_portfolio(val):
        if isinstance(val, (int, float)):
            color = 'green' if val > 0 else 'red' if val < 0 else 'gray'
            return f'color: {color}'
        return ''
    
    styled_portfolio = portfolio.style.map(color_portfolio, subset=['Günlük Değişim (%)'])
    st.dataframe(styled_portfolio, hide_index=True, use_container_width=True)
else:
    st.info("Portföy verisi bulunamadı.")

st.divider()

st.header("📈 Momentum Strateji Testi")
st.warning("""**Bu Nedir?**
Sektör performansı + fiyat momentumu bazlı alternatif bir strateji testidir.

**Neden Farklı?** Tarihsel P/E, gelir büyümesi ve analist revizyonları verileri mevcut değildir. Bu nedenle canlı sistemin 5 kriterli puanlaması geçmişe uygulanamaz.

**Sonuçlar:** Sadece momentum stratejisinin performansını gösterir, canlı önerilerle karşılaştırılamaz.""")

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
    
    with st.spinner("Simülasyon çalışıyor... Bu işlem biraz zaman alabilir."):
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
        
        fig_backtest.update_layout(
            title=f"Portföy Performansı ({backtest_start} - Bugün)",
            xaxis_title="Tarih",
            yaxis_title="Portföy Değeri ($)",
            template="plotly_dark",
            height=400
        )
        
        st.plotly_chart(fig_backtest, use_container_width=True)
        
        st.subheader("Dönemsel Detaylar")
        st.dataframe(backtest_results, hide_index=True, use_container_width=True)
    else:
        st.warning("Simülasyon sonuçları oluşturulamadı. Lütfen farklı bir tarih aralığı seçin.")

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

st.sidebar.header("🗓️ Günlük Finansal Notlar")
st.sidebar.info("""
- **Fed Kararı:** Faizlerde sabit kalma beklentisi %85.
- **Trend:** AI çiplerinden veri merkezi altyapısına rotasyon var.
- **Dikkat:** Bugün NVIDIA bilançosu sonrası volatilite artabilir.
""")

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
