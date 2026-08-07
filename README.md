# 🤖 AI Trader v2.0 — ARTH Self-Learning AI Trading Agent

> **Self-learning trading signal platform for Indian markets (NSE) using free AI providers**

[![Tests](https://img.shields.io/badge/tests-10%20passed-green)]() [![Python](https://img.shields.io/badge/python-3.10+-blue)]() [![Next.js](https://img.shields.io/badge/next.js-14-black)]() [![License](https://img.shields.io/badge/license-MIT-green)]()

---

## ✨ What Is This?

AI Trader is a **complete AI-powered trading signal platform** that:

- 📊 Generates **BUY/SELL/HOLD signals** for Nifty 50 & Bank Nifty stocks
- 🤖 **ARTH** — AI agent that analyzes stocks using multiple free AI providers
- 🧠 **Self-learns** from every prediction — gets smarter over time
- 📉 **Backtests** strategies against historical data
- 📝 **Paper trading** simulator with virtual ₹1,00,000 portfolio
- 🔌 **Multi-AI** — Groq, Cohere, HuggingFace, Ollama (all FREE)
- 💰 **Works with ZERO API keys** — rule-based signals always work
- 📱 **Full-stack** — FastAPI backend + Next.js frontend

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (Next.js)                        │
│   Dashboard • ARTH Chat • Backtesting • Brain • Paper Trade │
└─────────────────────────┬───────────────────────────────────┘
                          │ REST API + WebSocket
┌─────────────────────────▼───────────────────────────────────┐
│                    BACKEND (FastAPI)                          │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              🤖 ARTH — AI TRADING AGENT               │   │
│  │  • Analysis Engine    • Pattern Recognition          │   │
│  │  • Probability Calc   • Chart Analysis               │   │
│  │  • Self-Learning      • Backtesting Engine           │   │
│  │  • Sentiment Analysis • Paper Trading                │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              🧠 ARTH'S BRAIN (SQLite)                 │   │
│  │  • 37 API endpoints   • Auto-resolves predictions   │   │
│  │  • Pattern library    • Learning rules engine        │   │
│  │  • Strategy tracking  • Self-reflection scheduler    │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              🔌 AI ROUTER (Multi-Provider)            │   │
│  │  Groq (Llama 3.1) → Cohere → HuggingFace → Ollama   │   │
│  │  (All FREE — automatic fallback chain)                │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    DATA (ALL FREE)                            │
│   Yahoo Finance • Technical Indicators • Sentiment Analysis  │
│   30+ indicators: RSI, MACD, Bollinger, ATR, ADX, OBV...    │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Zero Setup (Works Immediately)
```bash
git clone https://github.com/anoopuri21/ai-trader.git
cd ai-trader

# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev

# Open: http://localhost:3000
```

**What works with zero setup:**
- ✅ Live prices from Yahoo Finance
- ✅ Technical indicators (RSI, SMA, MACD, Bollinger, ATR, etc.)
- ✅ Rule-based BUY/SELL/HOLD signals
- ✅ Interactive candlestick charts
- ✅ Backtesting engine (4 strategies)
- ✅ Paper trading simulator
- ✅ ARTH's brain (learns from every prediction)

### With Free AI (Recommended)
```bash
# Add FREE API keys to .env file
cp .env.example .env

# Get free keys:
# - Groq: https://console.groq.com/keys (fastest, recommended)
# - Cohere: https://dashboard.cohere.com/api-keys
# - HuggingFace: https://huggingface.co/settings/tokens

# Then restart backend — ARTH will automatically use them!
```

---

## 📱 Pages

| Page | URL | Description |
|------|-----|-------------|
| **Dashboard** | `/` | Live signals, charts, ARTH analysis per stock |
| **ARTH Chat** | `/arth` | Chat with ARTH about markets & stocks |
| **Backtesting** | `/backtest` | Test 4 strategies, compare performance |
| **Brain** | `/brain` | View ARTH's learning — predictions, patterns, rules |
| **Paper Trade** | `/paper` | Virtual portfolio, auto-trade with ARTH |

---

## 🔌 API Endpoints (37 total)

### Prices & Signals
| Endpoint | Description |
|----------|-------------|
| `GET /api/prices/` | All stock prices |
| `GET /api/prices/{symbol}` | Single stock price |
| `GET /api/prices/indices/summary` | Nifty 50 + Bank Nifty |
| `GET /api/signals/` | All trading signals |
| `GET /api/signals/{symbol}` | Single stock signal |
| `GET /api/signals/summary/overview` | Market overview |
| `GET /api/signals/trending/bullish` | Top BUY signals |
| `GET /api/signals/trending/bearish` | Top SELL signals |

### ARTH AI Agent
| Endpoint | Description |
|----------|-------------|
| `GET /api/arth/analyze/{symbol}` | Full AI analysis with probability |
| `POST /api/arth/chat` | Chat with ARTH |
| `GET /api/arth/brain/stats` | Brain statistics |
| `GET /api/arth/brain/predictions` | Recent predictions |
| `GET /api/arth/brain/patterns` | Learned patterns |
| `GET /api/arth/brain/rules` | Active learning rules |
| `POST /api/arth/reflect` | Trigger self-reflection |
| `GET /api/arth/status` | ARTH status & providers |
| `GET /api/arth/probability/{symbol}` | Win probability |

### Backtesting
| Endpoint | Description |
|----------|-------------|
| `GET /api/backtest/run?symbol=X&strategy=Y` | Run backtest |
| `GET /api/backtest/compare?symbol=X` | Compare all strategies |
| `GET /api/backtest/performance` | Performance history |
| `GET /api/backtest/accuracy` | Prediction accuracy |

### Advanced Analysis
| Endpoint | Description |
|----------|-------------|
| `GET /api/analysis/advanced/{symbol}` | 30+ technical indicators |
| `GET /api/analysis/sentiment/market` | Market sentiment |
| `GET /api/analysis/sentiment/{symbol}` | Stock sentiment |
| `GET /api/analysis/fibonacci/{symbol}` | Fibonacci levels |
| `GET /api/analysis/pivot/{symbol}` | Pivot points |

### Paper Trading
| Endpoint | Description |
|----------|-------------|
| `GET /api/paper/portfolio` | Virtual portfolio |
| `POST /api/paper/open` | Open paper position |
| `POST /api/paper/close/{id}` | Close position |
| `POST /api/paper/auto-trade/{symbol}` | ARTH auto-trades |
| `GET /api/paper/performance` | Trading performance |

### WebSocket (Real-time)
| Endpoint | Description |
|----------|-------------|
| `WS /ws/signals` | Live signal updates |
| `WS /ws/arth` | ARTH brain updates |

---

## 🧠 How ARTH Learns

```
1. OBSERVE     → Reads market data, charts, indicators
2. PREDICT     → Generates BUY/SELL/HOLD with confidence
3. STORE       → Logs prediction to ARTH's brain (SQLite)
4. WAIT        → Scheduler checks after time passes
5. RESOLVE     → Compares prediction vs actual price
6. LEARN       → Updates pattern success rates
7. IMPROVE     → Generates new rules, adjusts confidence
8. REPEAT      → Gets smarter with every cycle
```

**ARTH's scheduler runs automatically:**
- Every 30 min: Resolves pending predictions
- Every 2 hours: Self-reflects and updates rules
- Every 6 hours: Runs quick backtests on top stocks

---

## 📊 Technical Indicators (30+)

| Category | Indicators |
|----------|-----------|
| **Trend** | SMA (9, 20, 50, 200), EMA (9, 21, 50), ADX |
| **Momentum** | RSI, MACD, Stochastic, Rate of Change |
| **Volatility** | Bollinger Bands, ATR, Bandwidth |
| **Volume** | OBV, Volume Ratio, VWAP |
| **Support/Resistance** | Pivot Points, Fibonacci, S/R levels |
| **Patterns** | Hammer, Shooting Star, Doji, Engulfing, Morning/Evening Star |

---

## 🔌 AI Providers (All FREE)

| Provider | Model | Speed | Best For |
|----------|-------|-------|----------|
| **Groq** | Llama 3.1 70B | ⚡⚡⚡ | Fast analysis (recommended) |
| **Cohere** | Command R | ⚡⚡ | Detailed reasoning |
| **HuggingFace** | Mistral 7B | ⚡⚡ | Vision models |
| **Ollama** | Llama 3.1 | ⚡ | Offline, unlimited |

All providers are optional — the system falls back to rule-based if none are configured.

---

## 📈 Backtesting Strategies

| Strategy | Description |
|----------|-------------|
| **Rule-Based** | SMA crossover + RSI + MACD + Bollinger |
| **Momentum** | RSI + Volume momentum |
| **Mean Reversion** | Bollinger Bands reversion |
| **Combined** | All strategies with ARTH's learned weights |

---

## 📁 Project Structure

```
ai-trader/
├── backend/
│   ├── main.py                     # FastAPI entry (37 routes)
│   ├── config.py                   # Settings from .env
│   ├── ai_agent/                   # ARTH AI Agent
│   │   ├── arth.py                 # Main agent orchestrator
│   │   ├── brain.py                # SQLite knowledge base
│   │   ├── router.py               # Multi-AI provider router
│   │   ├── analyzer.py             # Analysis + pattern detection
│   │   ├── backtest.py             # Backtesting engine (4 strategies)
│   │   ├── scheduler.py            # Self-learning scheduler
│   │   ├── sentiment.py            # Market sentiment analyzer
│   │   ├── prompts.py              # AI prompts for trading
│   │   └── providers/              # AI provider implementations
│   ├── services/
│   │   ├── price_fetcher.py        # Yahoo Finance (FREE)
│   │   ├── signal_generator.py     # Rule-based signals
│   │   ├── indicators.py           # Core technical indicators
│   │   ├── advanced_indicators.py  # 30+ advanced indicators
│   │   └── paper_trader.py         # Paper trading simulator
│   ├── api/routes/                 # API endpoints
│   ├── models/                     # Pydantic data models
│   └── tests/                      # Test suite (10 tests)
│
├── frontend/
│   ├── src/app/
│   │   ├── page.tsx                # Dashboard with ARTH analysis
│   │   ├── arth/page.tsx           # ARTH chat interface
│   │   ├── backtest/page.tsx       # Backtesting visualization
│   │   ├── brain/page.tsx          # Brain/knowledge dashboard
│   │   └── paper/page.tsx          # Paper trading simulator
│   ├── src/lib/
│   │   ├── api.ts                  # API client (all endpoints)
│   │   └── utils.ts                # Formatting helpers
│   └── src/types/index.ts          # TypeScript types
│
├── .env.example                    # Environment template
├── DEVELOPER_GUIDE.md              # Developer setup guide
├── FUTURE_IMPROVEMENTS.md          # Roadmap (free tier only)
└── README.md                       # This file
```

---

## 🧪 Testing

```bash
cd backend
pytest tests/ -v
```

---

## 📚 Documentation

| File | Description |
|------|-------------|
| [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) | Setup instructions, API reference, troubleshooting |
| [FUTURE_IMPROVEMENTS.md](FUTURE_IMPROVEMENTS.md) | Roadmap using only free AI services |
| [REQUIREMENTS.md](REQUIREMENTS.md) | Detailed requirements for API keys |
| [API Docs](http://localhost:8000/docs) | Interactive Swagger docs (when running) |

---

## ⚠️ Disclaimer

This is **NOT financial advice**. This software is for **educational purposes only**.
- Always do your own research before trading
- Past performance does not guarantee future results
- Only trade with money you can afford to lose
- The creator is not responsible for any trading losses

---

## 📄 License

MIT License

---

**Built with ❤️ | AI Trader v2.0 — ARTH Self-Learning AI Agent**
**37 API Endpoints • 10 Tests • 5 Frontend Pages • 30+ Indicators • 100% FREE**
