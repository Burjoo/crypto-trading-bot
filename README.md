# 🤖 CryptoBot Pro — Automated Trading Platform




![CryptoBot Pro](https://img.shields.io/badge/CryptoBot-Pro-00d4ff?style=for-the-badge&logo=bitcoin&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18+-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

**A startup-grade automated cryptocurrency trading platform with live market data, strategy backtesting, risk management, and Telegram alerts.**

[Features](#features) · [Quick Start](#quick-start) · [Architecture](#architecture) · [API Docs](#api-documentation) · [Contributing](#contributing)

</div>

---

## 📸 Screenshots

| Dashboard | Backtesting | Trading Journal |
|-----------|-------------|-----------------|
| ![Dashboard](<img width="1248" height="599" alt="Dashboard" src="https://github.com/user-attachments/assets/6bda9ce3-0039-44e9-a5a9-230f01b40f3a" />) | ![Backtest](<img width="1261" height="594" alt="Backtest" src="https://github.com/user-attachments/assets/17f81ee7-fd70-43b9-a02b-53ce97271a14" />) | ![Journal](<img width="1257" height="599" alt="Journal" src="https://github.com/user-attachments/assets/7c9ea01e-0be8-4715-b12a-2ef5cedbef8d" />
) |

---

## ✨ Features

### 🔐 Authentication & Security
- JWT access/refresh token system
- Bcrypt password hashing
- AES-256 encrypted API key storage
- Rate limiting & CORS protection
- Role-based access control

### 📡 Exchange Integration
- **Binance**, **Bybit**, **Coinbase Pro** via CCXT
- Secure API key management
- Real-time balance & position syncing
- Paper trading mode (zero-risk simulation)
- WebSocket price feeds

### 🤖 Trading Engine
| Strategy | Description |
|----------|-------------|
| Moving Average Crossover | Golden/Death cross signals |
| RSI Mean Reversion | Oversold/overbought detection |
| MACD Momentum | Signal line crossover entries |
| Breakout | Support/resistance level breaks |

- Configurable parameters per strategy
- Multi-symbol support
- Start/stop bots via dashboard
- Position sizing rules enforced per bot

### 📊 Backtesting System
- Vectorized Pandas-based backtester
- Historical OHLCV data from exchanges
- Performance metrics: Sharpe ratio, max drawdown, win rate, avg RR
- Interactive equity curve chart
- Exportable trade log (CSV/JSON)

### 🛡️ Risk Management
- Per-trade stop-loss & take-profit
- Trailing stop-loss
- Max daily loss circuit breaker
- Position size calculator
- Risk/reward ratio enforcement

### 📈 Real-Time Dashboard
- WebSocket price ticker
- Live PnL updates
- Active bot status
- Portfolio value tracking
- Market overview (top gainers/losers)

### 📓 Trading Journal
- Full trade history with tags & notes
- Strategy performance breakdown
- Win rate by setup
- Emotional tagging system
- CSV export

### 🔔 Telegram Notifications
- Trade opened/closed alerts
- Stop-loss & take-profit hits
- Error alerts
- Daily performance summary
- Configurable alert filters

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Nginx (Reverse Proxy)                │
└──────────────┬──────────────────────────┬───────────────┘
               │                          │
     ┌─────────▼──────────┐   ┌──────────▼──────────┐
     │   React Frontend   │   │  FastAPI Backend     │
     │   (Port 3000)      │   │  (Port 8000)         │
     │                    │   │                      │
     │  - TailwindCSS     │   │  ┌────────────────┐  │
     │  - Recharts        │   │  │  WebSocket Mgr │  │
     │  - Zustand Store   │   │  │  Trading Engine│  │
     │  - React Query     │   │  │  Backtest Eng. │  │
     └────────────────────┘   │  │  Risk Manager  │  │
                               │  └────────────────┘  │
                               └──────────┬────────────┘
                                          │
              ┌───────────────────────────┼──────────────┐
              │                           │              │
   ┌──────────▼──────┐       ┌───────────▼────┐  ┌─────▼──────┐
   │   PostgreSQL    │       │     Redis       │  │  CCXT API  │
   │   (Port 5432)  │       │   (Port 6379)   │  │  Exchanges │
   └─────────────────┘       └────────────────┘  └────────────┘
```

### Clean Architecture Layers
```
backend/app/
├── api/v1/endpoints/   # HTTP route handlers (thin controllers)
├── services/           # Business logic layer
├── repositories/       # Data access layer
├── models/             # SQLAlchemy ORM models
├── schemas/            # Pydantic validation schemas
├── core/               # Config, security, dependencies
├── websockets/         # WebSocket connection manager
├── middleware/         # Rate limiting, logging, auth
└── utils/              # Shared utilities
```

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Git

### 1. Clone & Configure
```bash
git clone https://github.com/yourusername/crypto-trading-bot.git
cd crypto-trading-bot
cp .env.example .env
```

### 2. Configure Environment
Edit `.env` with your settings:
```env
# Required
SECRET_KEY=your-super-secret-key-min-32-chars
DATABASE_URL=postgresql://user:pass@db:5432/cryptobot
REDIS_URL=redis://redis:6379

# Optional — for live trading
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_CHAT_ID=your-chat-id

# Exchange keys (encrypted at rest)
ENCRYPTION_KEY=your-32-byte-fernet-key
```

### 3. Launch
```bash
docker compose up --build
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Adminer (DB UI) | http://localhost:8080 |

### 4. Create Admin Account
```bash
docker compose exec backend python scripts/create_admin.py
```

---

## 📖 API Documentation

Interactive Swagger UI: `http://localhost:8000/docs`
ReDoc: `http://localhost:8000/redoc`

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/auth/register` | Create account |
| `POST` | `/api/v1/auth/login` | Get JWT tokens |
| `GET` | `/api/v1/portfolio/summary` | Portfolio overview |
| `GET` | `/api/v1/market/prices` | Live prices |
| `POST` | `/api/v1/bots` | Create trading bot |
| `POST` | `/api/v1/bots/{id}/start` | Start bot |
| `POST` | `/api/v1/backtest/run` | Run backtest |
| `GET` | `/api/v1/trades` | Trade history |
| `WS` | `/ws/prices` | Live price feed |
| `WS` | `/ws/portfolio` | Live PnL updates |

---

## 🔧 Development Setup

### Backend Only
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend Only
```bash
cd frontend
npm install
npm run dev
```

### Running Tests
```bash
# Backend
cd backend && pytest --cov=app tests/ -v

# Frontend
cd frontend && npm run test
```

---

## 🐳 Docker Services

```yaml
services:
  backend:    FastAPI + Uvicorn (port 8000)
  frontend:   React + Nginx (port 3000)
  db:         PostgreSQL 15 (port 5432)
  redis:      Redis 7 (port 6379)
  nginx:      Reverse proxy (port 80/443)
  adminer:    DB management UI (port 8080)
  celery:     Async task worker
  flower:     Celery monitoring (port 5555)
```

---

## 🔄 CI/CD Pipeline

GitHub Actions workflows:
- `.github/workflows/test.yml` — Run tests on every PR
- `.github/workflows/deploy.yml` — Deploy to VPS on main push
- `.github/workflows/security.yml` — Dependency vulnerability scan

---

## 📦 Project Structure

```
crypto-trading-bot/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/
│   │   │   ├── auth.py
│   │   │   ├── bots.py
│   │   │   ├── backtest.py
│   │   │   ├── exchanges.py
│   │   │   ├── market.py
│   │   │   ├── portfolio.py
│   │   │   ├── trades.py
│   │   │   ├── journal.py
│   │   │   └── alerts.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   └── dependencies.py
│   │   ├── db/
│   │   │   ├── base.py
│   │   │   └── session.py
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── bot.py
│   │   │   ├── trade.py
│   │   │   ├── exchange.py
│   │   │   └── journal.py
│   │   ├── schemas/
│   │   ├── services/
│   │   │   ├── trading_engine.py
│   │   │   ├── backtest_engine.py
│   │   │   ├── risk_manager.py
│   │   │   ├── exchange_service.py
│   │   │   └── telegram_service.py
│   │   ├── repositories/
│   │   ├── websockets/
│   │   │   └── manager.py
│   │   └── main.py
│   ├── alembic/
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── store/
│   │   └── services/
│   ├── Dockerfile
│   └── package.json
├── nginx/
│   └── nginx.conf
├── docker-compose.yml
├── docker-compose.prod.yml
└── .env.example
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit: `git commit -m 'feat: add amazing feature'`
4. Push: `git push origin feature/amazing-feature`
5. Open a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for full guidelines.

---

## ⚠️ Disclaimer

This software is for **educational purposes**. Cryptocurrency trading involves substantial risk. Never trade with money you cannot afford to lose. The authors are not responsible for financial losses.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">
Built with ❤️ by developers, for developers. Star ⭐ if this helped you!
</div>
