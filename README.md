# AlgoTrader - NSE Algorithmic Trading Platform

Production-grade algo trading application for NSE (India) using Angel One SmartAPI.

## Project Structure

```
algo-trading-app/
├── backend/
│   ├── main.py                    # FastAPI app entry point
│   ├── api/                       # API route handlers
│   │   ├── auth_routes.py         # Login/logout/session
│   │   ├── market_routes.py       # LTP, historical data, instrument search
│   │   ├── order_routes.py        # Place/modify/cancel orders
│   │   ├── strategy_routes.py     # Strategy CRUD and execution
│   │   ├── dashboard_routes.py    # PnL, stats, trade log, risk status
│   │   └── backtest_routes.py     # Backtest execution and results
│   ├── core/
│   │   ├── config.py              # Pydantic settings from .env
│   │   ├── database.py            # Async SQLAlchemy engine/session
│   │   └── logging_config.py      # JSON structured logging
│   ├── models/
│   │   └── models.py              # ORM models (User, Order, Trade, etc.)
│   ├── services/
│   │   ├── smartapi_auth.py       # Angel One authentication (singleton)
│   │   ├── order_service.py       # Order placement/management
│   │   ├── market_data.py         # Historical + LTP data fetching
│   │   ├── instrument_service.py  # ScripMaster download and lookup
│   │   ├── risk_manager.py        # Daily loss/trade/drawdown limits
│   │   ├── notification_service.py# Telegram + email alerts
│   │   └── websocket_service.py   # Angel One live WebSocket feed
│   ├── strategies/
│   │   ├── base_strategy.py       # Abstract base class + Signal enum
│   │   ├── indicators.py          # EMA, RSI, MACD, Bollinger, VWAP, ATR, SuperTrend, S/R levels
│   │   ├── ma_crossover.py        # Moving Average Crossover strategy
│   │   ├── rsi_macd_strategy.py   # RSI + MACD combined strategy
│   │   ├── bollinger_breakout.py  # Bollinger Bands breakout/mean-reversion
│   │   ├── vwap_strategy.py       # VWAP intraday strategy
│   │   ├── breakout_strategy.py   # Support/Resistance breakout strategy
│   │   └── strategy_engine.py     # Orchestrates all strategies
│   └── backtesting/
│       └── engine.py              # Backtest simulator with metrics (CAGR, Sharpe, etc.)
├── frontend/
│   ├── public/index.html          # HTML template with Tailwind CDN
│   ├── package.json
│   └── src/
│       ├── index.js               # React entry point
│       ├── App.js                 # Router + protected routes
│       ├── services/api.js        # Axios API client
│       ├── hooks/useWebSocket.js  # WebSocket hook with reconnect
│       ├── components/
│       │   ├── Navbar.js          # Collapsible sidebar navigation
│       │   ├── PnLCard.js         # Metric card component
│       │   └── TradeTable.js      # Sortable, paginated table
│       ├── pages/
│       │   ├── LoginPage.js       # SmartAPI login form
│       │   ├── DashboardPage.js   # PnL cards, candlestick chart, live tickers, risk meters
│       │   ├── StrategiesPage.js  # Strategy cards with toggle/config/run
│       │   ├── OrdersPage.js      # Order form + order book/positions/holdings
│       │   └── BacktestPage.js    # Backtest config, metrics, equity curve
│       └── styles/index.css       # Dark theme styles
├── config/
│   └── default_strategies.json    # Default strategy configurations
├── logs/                          # Auto-created log directory
├── .env.example                   # Environment variable template
└── requirements.txt               # Python dependencies
```

## Prerequisites

- Python 3.11+
- Node.js 18+
- Angel One SmartAPI account (https://smartapi.angelone.in/)

## Setup Instructions

### 1. Clone and Configure

```bash
cd /Users/aadityasinha/code/algo-trading-app

# Create .env from template
cp .env.example .env
```

Edit `.env` with your Angel One credentials:

```env
ANGEL_API_KEY=your_api_key_here
ANGEL_CLIENT_ID=your_client_id_here
ANGEL_PASSWORD=your_password_here
ANGEL_TOTP_SECRET=your_totp_secret_here
```

### 2. Backend Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Frontend Setup

```bash
cd frontend
npm install
cd ..
```

### 4. Run the Application

**Backend (Terminal 1):**
```bash
source venv/bin/activate
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend (Terminal 2):**
```bash
cd frontend
npm start
```

The app will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## .env Configuration Guide

### Required Settings

| Variable | Description | Example |
|----------|-------------|---------|
| `ANGEL_API_KEY` | SmartAPI API key from Angel One dashboard | `abc123xyz` |
| `ANGEL_CLIENT_ID` | Your Angel One client ID | `A12345` |
| `ANGEL_PASSWORD` | Your trading password | `mypassword` |
| `ANGEL_TOTP_SECRET` | TOTP secret for 2FA (from QR code setup) | `JBSWY3DPEHPK3PXP` |

### Optional Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_URL` | Database connection string | `sqlite+aiosqlite:///./trading.db` |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token for alerts | None |
| `TELEGRAM_CHAT_ID` | Telegram chat ID for alerts | None |
| `EMAIL_HOST` | SMTP host for email alerts | None |
| `EMAIL_PORT` | SMTP port | None |
| `EMAIL_USER` | SMTP username/email | None |
| `EMAIL_PASSWORD` | SMTP password (use app password for Gmail) | None |
| `MAX_LOSS_PER_DAY` | Maximum daily loss limit (INR) | `5000` |
| `MAX_TRADES_PER_DAY` | Maximum trades per day | `20` |
| `CAPITAL_PER_TRADE` | Capital allocated per trade (INR) | `50000` |
| `MAX_DRAWDOWN_PCT` | Maximum drawdown percentage | `5.0` |
| `REDIS_URL` | Redis URL for caching | None |
| `LOG_LEVEL` | Logging level | `INFO` |

### PostgreSQL Setup (Optional)

For production, switch from SQLite to PostgreSQL:

```env
DB_URL=postgresql+asyncpg://user:password@localhost:5432/trading
```

Install the driver: `pip install asyncpg`

## Trading Strategies

### 1. Moving Average Crossover (`ma_crossover`)
- BUY: Fast EMA crosses above Slow EMA
- SELL: Fast EMA crosses below Slow EMA
- Parameters: fast_period (9), slow_period (21), ATR-based stop loss

### 2. RSI + MACD (`rsi_macd`)
- BUY: RSI oversold (<30) AND MACD bullish crossover
- SELL: RSI overbought (>70) AND MACD bearish crossover
- Parameters: rsi_period (14), rsi_oversold (30), rsi_overbought (70)

### 3. Bollinger Bands Breakout (`bollinger_breakout`)
- **Breakout mode**: BUY on upper band break with volume, SELL on lower band break
- **Mean reversion mode**: BUY at lower band, SELL at upper band
- Includes bandwidth squeeze detection
- Parameters: bb_period (20), bb_std_dev (2.0), mode

### 4. VWAP Intraday (`vwap_intraday`)
- BUY: Price crosses above VWAP with volume confirmation
- SELL: Price crosses below VWAP
- Auto-exits before 3:15 PM IST
- Parameters: volume_multiplier (1.2), ATR-based stop loss

### 5. Support/Resistance Breakout (`sr_breakout`)
- Identifies swing high/low levels
- BUY: Breakout above resistance with volume surge
- SELL: Breakdown below support with volume surge
- Parameters: lookback (20), volume_surge_multiplier (1.5)

## Profitability Suggestions

### Risk Management
- Never risk more than 2% of capital per trade
- Use ATR-based dynamic stop losses (adapts to volatility)
- Maintain minimum 1:2 risk-reward ratio
- Hard daily loss limits prevent catastrophic drawdowns

### Strategy Diversification
- Run multiple uncorrelated strategies simultaneously
- Mix trend-following (MA, Breakout) with mean-reversion (Bollinger)
- Mix timeframes (5min VWAP + 15min RSI-MACD)

### Market Regime Detection
- Use Bollinger Band bandwidth to detect low-volatility squeezes
- Monitor VIX (India VIX) to adjust position sizing
- Reduce exposure during high-volatility periods
- Avoid trading first 15 minutes (opening volatility) and last 15 minutes

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | Login with SmartAPI credentials |
| POST | `/api/auth/logout` | Logout and terminate session |
| GET | `/api/auth/status` | Check session status |
| GET | `/api/market/ltp/{ticker}` | Get last traded price |
| GET | `/api/market/historical/{ticker}` | Get historical OHLCV data |
| GET | `/api/market/instruments/search` | Search instruments |
| POST | `/api/orders/place` | Place a new order |
| PUT | `/api/orders/{id}/modify` | Modify an order |
| DELETE | `/api/orders/{id}/cancel` | Cancel an order |
| GET | `/api/orders/book` | Get order book |
| GET | `/api/orders/positions` | Get positions |
| GET | `/api/orders/holdings` | Get holdings |
| GET | `/api/strategies` | List all strategies |
| PUT | `/api/strategies/{name}/toggle` | Enable/disable strategy |
| PUT | `/api/strategies/{name}/config` | Update strategy parameters |
| POST | `/api/strategies/run` | Run strategy cycle |
| GET | `/api/dashboard/pnl` | Get daily PnL data |
| GET | `/api/dashboard/stats` | Get overall statistics |
| GET | `/api/dashboard/trade-log` | Get paginated trade log |
| GET | `/api/dashboard/risk-status` | Get risk management status |
| POST | `/api/backtest/run` | Run a backtest |
| GET | `/api/backtest/results` | List past backtest results |
| WS | `/ws` | WebSocket for live data |
