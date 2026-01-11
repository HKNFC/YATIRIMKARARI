# Morning Alpha Dashboard

## Overview

Morning Alpha is an investment decision support dashboard built with Streamlit. The application provides market analysis, sector opportunities tracking, portfolio management, and price alerts for investors. It's designed as a Turkish-language financial dashboard that helps users monitor market health (via VIX index), track sector performance, manage stock portfolios, and set price alerts.

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
1. Market data fetched via yfinance library
2. Data processed and displayed through Streamlit components
3. User portfolio and alerts persisted to PostgreSQL database
4. Dashboard auto-refreshes based on user-selected interval

### Key Features
- Market health indicator (VIX-based risk assessment)
- Sector analysis with money flow tracking
- Portfolio management with buy price tracking
- Price alert system with trigger notifications

## External Dependencies

### Database
- **PostgreSQL**: Primary data store accessed via DATABASE_URL environment variable
- **SQLAlchemy**: ORM layer for database operations

### Market Data
- **yfinance**: Yahoo Finance API wrapper for real-time stock and market data (VIX, SPY, individual stocks)

### Environment Variables
- `DATABASE_URL`: PostgreSQL connection string (required)

### Python Packages
- streamlit: Web dashboard framework
- pandas: Data manipulation
- plotly: Interactive visualizations
- yfinance: Market data fetching
- sqlalchemy: Database ORM
- streamlit-autorefresh: Auto-refresh functionality