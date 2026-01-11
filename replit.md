# Morning Alpha Dashboard

## Overview

Morning Alpha is an investment decision support dashboard built with Streamlit. The application provides market analysis, sector opportunities tracking, portfolio management, price alerts, and strategy backtesting for investors. It's designed as a Turkish-language financial dashboard that helps users monitor market health (via VIX index), track sector performance, manage stock portfolios, set price alerts, and test investment strategies with historical data.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Framework**: Streamlit - chosen for rapid development of data-focused dashboards
- **Visualization**: Plotly for interactive charts and graphs
- **Auto-refresh**: streamlit-autorefresh for real-time data updates with configurable intervals (30s, 1m, 2m, 5m)
- **Layout**: Wide layout configuration for comprehensive data display

### Backend Architecture
- **Data Model**: SQLAlchemy ORM with declarative base pattern
- **Database Tables**:
  - `user_portfolio`: Tracks user stock holdings (symbol, sector, quantity, buy_price, added_at)
  - `price_alerts`: Manages price alert notifications (symbol, alert_type, target_price, is_triggered, timestamps)
- **Session Management**: SQLAlchemy sessionmaker for database connections

### Data Flow
1. Market data fetched via yfinance library (real-time prices, momentum)
2. Historical fundamental data fetched via Financial Modeling Prep (FMP) API
3. Data processed and displayed through Streamlit components
4. User portfolio and alerts persisted to PostgreSQL database
5. Dashboard auto-refreshes based on user-selected interval

### Key Features
- Market health indicator (VIX-based risk assessment)
- Sector analysis with money flow tracking
- Dynamic stock recommendations with 5-criterion scoring (20% each):
  - Valuation (P/E ratio)
  - Growth (Revenue growth)
  - Profitability (Net profit margin)
  - Momentum (Price momentum)
  - Revisions (Analyst EPS estimate changes)
- Portfolio management with buy price tracking and profit/loss calculation
- Price alert system with trigger notifications
- Strategy backtesting with two modes:
  - 5-Criterion Full Analysis (FMP API): Uses historical fundamental data
  - Momentum-based Simple Test: Uses only price momentum

## External Dependencies

### Database
- **PostgreSQL**: Primary data store accessed via DATABASE_URL environment variable
- **SQLAlchemy**: ORM layer for database operations

### Market Data
- **yfinance**: Yahoo Finance API wrapper for real-time stock and market data (VIX, SPY, individual stocks)
- **Financial Modeling Prep (FMP) API**: Historical financial ratios, growth metrics, and analyst estimates for backtesting

### Environment Variables
- `DATABASE_URL`: PostgreSQL connection string (required)
- `FMP_API_KEY`: Financial Modeling Prep API key (required for 5-criterion backtesting)
- `NEWSAPI_KEY`: NewsAPI key for automatic financial news fetching (optional, falls back to static notes)

### Python Packages
- streamlit: Web dashboard framework
- pandas: Data manipulation
- plotly: Interactive visualizations
- yfinance: Market data fetching
- requests: HTTP requests for FMP API
- sqlalchemy: Database ORM
- psycopg2-binary: PostgreSQL adapter
- streamlit-autorefresh: Auto-refresh functionality