# 🏗️ AI Trader — System Architecture

> **For Developers & AI Agents** — Read this before making any changes.

Last updated: 2026-08-08 | Version: 2.1.0

---

## 1. System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (Next.js 14)                         │
│  Dashboard (/) • ARTH (/arth) • Backtest (/backtest)            │
│  Brain (/brain) • Paper Trade (/paper)                          │
│  → API calls via Next.js rewrites → /api/* → Backend           │
└───────────────────────────┬─────────────────────────────────────┘
                            │ REST + WebSocket
┌───────────────────────────▼─────────────────────────────────────┐
│                    BACKEND (FastAPI)                              │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │  API LAYER (37 endpoints)                                  │   │
│  │  prices • signals • arth • backtest • analysis • paper • ws│   │
│  └──────────────────────────┬────────────────────────────────┘   │
│                              │                                    │
│  ┌──────────────────────────▼────────────────────────────────┐   │
│  │  ARTH — AI Trading Agent                                   │   │
│  │  arth.py (orchestrator) → brain.py → router.py → providers │   │
│  │  analyzer.py (signal enhancement)                          │   │
│  │  scheduler.py (periodic self-learning)                     │   │
│  │  sentiment.py (market sentiment from VIX, trends)          │   │
│  └──────────────────────────┬────────────────────────────────┘   │
│                              │                                    │
│  ┌──────────────────────────▼────────────────────────────────┐   │
│  │  SERVICES LAYER                                            │   │
│  │  signal_generator.py — Rule-based signals (core logic)     │   │
│  │  indicators.py — RSI, MACD, SMA, ATR (basic)              │   │
│  │  advanced_indicators.py — Bollinger, ADX, OBV, Fibonacci  │   │
│  │  price_fetcher.py — Yahoo Finance (cached)                │   │
│  │  paper_trader.py — Virtual portfolio                      │   │
│  └──────────────────────────┬────────────────────────────────┘   │
│                              │                                    │
│  ┌──────────────────────────▼────────────────────────────────┐   │
│  │  DATABASE (database/manager.py)                            │   │
│  │  Single SQLite file: backend/data/ai_trader.db             │   │
│  │  WAL mode • Thread-safe writes • All data in ONE file      │   │
│  │  Tables: predictions • patterns • learning_rules •         │   │
│  │          market_context • strategy_performance •           │   │
│  │          paper_portfolio • paper_positions • paper_trades   │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
                            │
┌───────────────────────────▼───────────────────────────────────────┐
│  EXTERNAL DATA (ALL FREE)                                         │
│  Yahoo Finance — Prices, historical data, indices                 │
│  Groq — Llama 3.1 70B (optional, fastest free AI)                │
│  Cohere — Command R (optional, best reasoning)                    │
│  HuggingFace — Mistral 7B (optional, vision models)              │
│  Ollama — Local AI (optional, offline, unlimited)                 │
└───────────────────────────────────────────────────────────────────┘
```

---

## 2. Key Architectural Decisions

### 2.1 Single Database File

**Decision:** All data (ARTH brain, paper trading, backtest results, market context) lives in ONE SQLite file at `backend/data/ai_trader.db`.

**Why:** Previous architecture had 3 separate SQLite files created by brain.py, paper_trader.py, and backtest.py with relative paths. This caused:
- Data written to one file but read from another
- Different CWD creating orphan databases
- No atomic transactions across files

**Implementation:** `database/manager.py` provides a `DatabaseManager` singleton with:
- Thread-safe writes via `threading.Lock`
- WAL journal mode for concurrent reads
- Fixed path relative to project root (not CWD)

### 2.2 No Global Singletons for Stateful Services

**Decision:** ArthBrain, PaperTrader, and BacktestEngine each get their own instance but all share the same DatabaseManager.

**Why:** Module-level singletons (old `brain = ArthBrain()`) caused multiple instances to be created. Now each component creates an ArthBrain that delegates to the centralized DatabaseManager.

### 2.3 Data Fetched Once, Passed Through

**Decision:** ARTH's `analyze_stock()` fetches price + historical data ONCE, then passes it to both `signal_generator.generate_signal()` and `indicators.calculate_all()`.

**Why:** Previous code fetched the same data twice (once in arth.py, once in signal_generator.py), doubling Yahoo Finance API calls.

### 2.4 IST Timezone for Market Hours

**Decision:** Market hours check uses `zoneinfo.ZoneInfo("Asia/Kolkata")` instead of UTC.

**Why:** NSE operates 9:15 AM – 3:30 PM IST. The previous UTC-based check (`3.75 <= now.hour`) was mathematically broken (hour is always integer, never 3.75).

---

## 3. Trading Logic — Signal Generation

The signal generator (`services/signal_generator.py`) uses **weighted multi-factor scoring**:

```
┌──────────────────────────────────────────────────────┐
│         WEIGHTED SCORING SYSTEM                       │
├──────────────────────────┬──────────┬────────────────┤
│ Factor                   │ Weight   │ Range          │
├──────────────────────────┼──────────┼────────────────┤
│ Trend (SMA structure)    │ 3        │ [-3, +3]       │
│ RSI (contextual)         │ 2        │ [-2, +2]       │
│ MACD (crossover event)   │ 2        │ [-2, +2]       │
│ Support/Resistance       │ 2        │ [-2, +2]       │
│ Market context (Nifty)   │ 2        │ [-2, +2]       │
│ Volume confirmation      │ 1        │ [-1, +1]       │
│ Candlestick pattern      │ 1        │ [-1, +1]       │
├──────────────────────────┼──────────┼────────────────┤
│ TOTAL                    │ 13       │ [-13, +13]     │
└──────────────────────────┴──────────┴────────────────┘

Signal determination:
  normalized_score = (total / 13) * 100

  normalized >= +25  → BUY  (confidence: 50-95%)
  normalized <= -25  → SELL (confidence: 50-95%)
  else               → HOLD (confidence: 20-50%)
```

### 3.1 Contextual RSI (NOT contrarian)

```
PREVIOUS (WRONG):
  RSI < 30 → BUY (+2)     ← Always buy when oversold
  RSI > 70 → SELL (-2)    ← Always sell when overbought
  → Problem: In strong uptrend, RSI stays 60-70 → constant false SELL signals

CURRENT (CORRECT):
  In BULLISH trend:
    RSI 40-70 → +1 (momentum continuation)
    RSI < 30  → +2 (deep oversold in uptrend = strong buy)
    RSI > 80  → -1 (exhausted)
  
  In BEARISH trend:
    RSI 30-50 → -1 (momentum continuation)
    RSI > 70  → -2 (overbought in downtrend = strong sell)
    RSI < 20  → +1 (deeply oversold = bounce)
  
  In NEUTRAL:
    RSI < 30  → +2 (traditional oversold)
    RSI > 70  → -2 (traditional overbought)
```

### 3.2 MACD Crossover Detection (NOT state)

```
PREVIOUS (WRONG):
  macd > macd_signal → bullish  ← Being above for 20 days ≠ signal

CURRENT (CORRECT):
  Detect crossover EVENT (MACD crossing signal line in last 2-3 bars):
    Fresh bullish crossover → +2
    Recent bullish crossover → +1
    MACD expanding above signal → +1
    Fresh bearish crossover → -2
    No fresh crossover → 0
```

### 3.3 ATR-Based Stop-Loss & Target

```
PREVIOUS (WRONG):
  stop_loss = price × 0.985  (fixed 1.5%)
  target = price × 1.03      (fixed 3%)
  → Problem: 1.5% stop on NSE stocks triggers on normal daily noise

CURRENT (CORRECT):
  stop_distance = ATR × 1.5
  target_distance = ATR × 3.0
  
  stop_pct = clamp(stop_distance / price, 1%, 5%)
  target_pct = clamp(target_distance / price, 1.5× stop, 10%)
  
  → High-volatility stocks (Adani): ~3-4% stop, ~6-8% target
  → Low-volatility stocks (HUL): ~1.5-2% stop, ~3-4% target
```

### 3.4 Market Context

Every signal factors in Nifty 50's daily change:
```
Nifty > +1.5% → STRONG_BULLISH (+2 to every BUY signal)
Nifty > +0.3% → BULLISH (+1)
Nifty < -0.3% → BEARISH (-1)
Nifty < -1.5% → STRONG_BEARISH (-2 to every BUY signal)
```

### 3.5 Transaction Costs in Backtesting

All backtests deduct realistic costs:
```
Slippage: 0.1% + STT: 0.04% + Brokerage: 0.03% = 0.17% per side
Round trip cost: 0.34%
```

---

## 4. Data Flow

### 4.1 Signal Generation Flow

```
Request: GET /api/signals/RELIANCE
  │
  ├── 1. price_fetcher.get_price("RELIANCE")
  │      └── Yahoo Finance API (cached 30s)
  │
  ├── 2. price_fetcher.get_historical_data("RELIANCE")
  │      └── Yahoo Finance API (cached 60s)
  │
  ├── 3. indicators.calculate_all(df)
  │      └── SMA, RSI, MACD, S/R, Volume, ATR
  │
  ├── 4. signal_generator.generate_signal(symbol, df_override=df, stock_override=stock)
  │      ├── _score_trend() → SMA alignment
  │      ├── _score_rsi_contextual() → RSI in trend context
  │      ├── _score_macd_crossover() → Fresh crossover events
  │      ├── _score_support_resistance() → Price position in range
  │      ├── _score_market_context() → Nifty trend
  │      ├── _score_volume() → Volume confirms direction
  │      ├── _score_pattern() → Candlestick patterns
  │      └── Aggregate → BUY/SELL/HOLD + confidence
  │
  └── 5. Return TradingSignal with entry/target/stop
```

### 4.2 ARTH AI Analysis Flow

```
Request: GET /api/arth/analyze/RELIANCE
  │
  ├── 1. Fetch data ONCE (price + historical)
  │
  ├── 2. Calculate indicators (from pre-fetched df)
  │
  ├── 3. Generate rule-based signal (pass pre-fetched data)
  │
  ├── 4. Detect candlestick patterns
  │
  ├── 5. IF AI available:
  │      ├── Build prompt with indicators + learned patterns
  │      ├── Route to best AI provider (Groq → Cohere → HF → Ollama)
  │      └── Get AI analysis
  │
  ├── 6. Blend rule-based + AI confidence
  │      └── Early stage: 70% rule + 30% AI
  │          Mature: scales AI weight based on accuracy
  │
  ├── 7. Calculate win probability
  │
  ├── 8. Store prediction in brain
  │
  └── 9. Return comprehensive analysis
```

### 4.3 Self-Learning Loop

```
┌─────────────────────────────────────────────────────┐
│ SCHEDULER (every 30 minutes)                         │
│                                                      │
│ 1. RESOLVE                                           │
│    Get unresolved predictions older than 1 day       │
│    Fetch current price → Calculate actual return     │
│    Mark as WIN/LOSS/NEUTRAL                          │
│    Update pattern success rates                      │
│                                                      │
│ 2. REFLECT                                           │
│    Calculate accuracy by signal type (last 7 days)   │
│    If BUY accuracy >= 70%: Create "boost_BUY" rule   │
│    If BUY accuracy <= 35%: Create "reduce_BUY" rule  │
│                                                      │
│ 3. BACKTEST                                          │
│    Run combined strategy on RELIANCE, HDFCBANK, INFY │
│    Store results in brain                            │
│    Extract winning patterns                          │
│                                                      │
│ 4. WAIT 30 minutes → repeat                          │
└─────────────────────────────────────────────────────┘
```

---

## 5. Database Schema

All tables live in `backend/data/ai_trader.db`:

```sql
-- ARTH's Knowledge
predictions      — Every signal generated (track & resolve)
patterns         — Learned trading patterns with success rates
learning_rules   — Self-generated improvement rules
market_context   — Daily market conditions
strategy_performance — Backtest results over time

-- Paper Trading
paper_portfolio  — Virtual account (₹1,00,000 starting)
paper_positions  — Open positions
paper_trades     — Closed trade history
```

---

## 6. File Responsibilities

| File | Purpose | Key Functions |
|------|---------|---------------|
| `main.py` | App entry, lifespan, CORS, routers | `lifespan()`, `health()` |
| `config.py` | All settings, market hours check | `settings`, `is_market_open()` |
| `database/manager.py` | Single DB connection, thread-safe writes | `get_db()`, `execute()`, `execute_insert()` |
| `services/price_fetcher.py` | Yahoo Finance data (cached) | `get_price()`, `get_historical_data()` |
| `services/indicators.py` | Core indicators (SMA, RSI, MACD, ATR) | `calculate_all()` |
| `services/signal_generator.py` | **Core trading logic** — weighted scoring | `_analyze()`, `_score_*()`, `_calculate_levels()` |
| `services/advanced_indicators.py` | Bollinger, ADX, OBV, Fibonacci | `get_all_advanced()` |
| `services/paper_trader.py` | Virtual portfolio | `open_position()`, `close_position()` |
| `ai_agent/arth.py` | Main AI orchestrator | `analyze_stock()`, `chat()` |
| `ai_agent/brain.py` | Knowledge base (delegates to DB) | `store_prediction()`, `get_stats()` |
| `ai_agent/router.py` | Multi-AI provider routing | `analyze()` with fallback chain |
| `ai_agent/analyzer.py` | Signal enhancement, pattern detection | `enhance_signal_with_ai()`, `detect_patterns()` |
| `ai_agent/backtest.py` | Historical strategy validation | `run_backtest()`, 4 strategies |
| `ai_agent/scheduler.py` | Periodic self-learning | `_resolve_predictions()`, `_self_reflect()` |
| `ai_agent/sentiment.py` | Market sentiment from VIX/trends | `get_market_sentiment()` |

---

## 7. Configuration

All settings in `config.py`, loaded from `.env`:

```env
# Trading Parameters
RSI_PERIOD=14
SMA_SHORT=20, SMA_MID=50, SMA_LONG=200
MACD_FAST=12, MACD_SLOW=26, MACD_SIGNAL=9

# Risk Management (ATR-based)
ATR_STOP_MULTIPLIER=1.5     # Stop = Entry - 1.5 × ATR
ATR_TARGET_MULTIPLIER=3.0   # Target = Entry + 3.0 × ATR
MAX_STOP_PCT=0.05           # Never more than 5% stop
MIN_RR_RATIO=1.5            # Minimum 1.5:1 risk:reward

# Transaction Costs (backtesting)
SLIPPAGE_PCT=0.001          # 0.1%
STT_PCT=0.0004              # 0.04%
BROKERAGE_PCT=0.0003        # 0.03%

# AI Provider Keys (all optional)
GROQ_API_KEY=
COHERE_API_KEY=
HUGGINGFACE_API_KEY=
```

---

## 8. Running & Testing

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Frontend (new terminal)
cd frontend
npm install && npm run dev

# Tests
cd backend && pytest tests/ -v

# API Docs
open http://localhost:8000/docs
```

---

## 9. Adding New Features

### New Technical Indicator
1. Add calculation to `services/indicators.py` or `services/advanced_indicators.py`
2. If used in signals: add field to `TechnicalIndicators` model
3. Add scoring function to `signal_generator.py`
4. Register in the weighted scoring `_analyze()` method

### New AI Provider
1. Create `ai_agent/providers/your_provider.py` with `analyze()` method returning JSON
2. Register in `ai_agent/router.py`
3. Add API key to `config.py` and `.env.example`

### New API Endpoint
1. Create route in `api/routes/`
2. Register router in `main.py`
3. Add TypeScript types in `frontend/src/types/index.ts`
4. Add API method in `frontend/src/lib/api.ts`

### New Backtest Strategy
1. Add method `_backtest_your_strategy()` to `BacktestEngine`
2. Register in `run_backtest()` strategy dict
3. Include transaction costs: `pnl_pct -= self.total_cost * 200`

---

## 10. Known Limitations & Future Work

See `FUTURE_IMPROVEMENTS.md` for the complete roadmap. Key priorities:
- Multi-model AI consensus (run 3 providers, take majority vote)
- LangChain/CrewAI multi-agent orchestration
- Real ML models (XGBoost, LSTM) for signal classification
- WebSocket real-time signal streaming
- Telegram/Discord alert integration

---

*This architecture document should be updated whenever significant structural changes are made.*
