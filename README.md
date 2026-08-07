# AI Trader v2.0
## Self-Learning Trading Signal Platform with Multi-AI Architecture

🤖 **ARTH** - Your AI Trading Agent with a Central Brain

---

## The Innovation

AI Trader uses **multiple free AI providers** in rotation, but stores ALL knowledge in **ONE central brain (ARTH)** that gets smarter over time.

```
┌─────────────────────────────────────────────────────────┐
│                    ARTH'S BRAIN                          │
│    ┌─────────────────────────────────────────────┐      │
│    │  Single Source of Truth                    │      │
│    │  • Learned patterns                        │      │
│    │  • Trading rules                           │      │
│    │  • Success rates                           │      │
│    │  • Historical predictions                  │      │
│    └─────────────────────────────────────────────┘      │
└─────────────────────┬───────────────────────────────────┘
                      │
     ┌────────────────┼────────────────┐
     ▼                ▼                ▼
┌─────────┐    ┌─────────┐    ┌─────────┐
│  Groq   │    │ Cohere  │    │ Hugging │
│ (Fast)  │    │ (Charts) │    │  Face   │
└─────────┘    └─────────┘    └─────────┘
     │                │                │
     └────────────────┼────────────────┘
                      ▼
              "ARTH uses many AIs
               but has ONE brain"
```

---

## Key Features

### 🤖 ARTH - The AI Agent
- **Central Brain:** All learning stored in one place
- **Multi-AI:** Uses Groq, Cohere, HuggingFace, Ollama (free)
- **Self-Learning:** Improves from every prediction
- **Chart Reader:** Analyzes charts visually
- **Backtesting:** Validates strategies historically

### 📊 Charts
- Interactive candlestick charts
- Multiple timeframes (1m to 1D)
- Technical indicators overlay
- ARTH can "see" and analyze charts

### 📈 Trading Signals
- BUY / SELL / HOLD signals
- Trade probability (e.g., 78% win rate)
- Risk-reward calculation
- Entry, target, stop-loss levels

### 🔄 Multi-AI Fallback
- Groq (fastest free AI)
- Cohere (chart analysis)
- HuggingFace (vision models)
- Ollama (offline local AI)
- Rule-based (always works)

---

## Quick Start

### 1. Zero Setup (Rule-Based Only)
```bash
git clone https://github.com/anoopuri21/ai-trader.git
cd ai-trader

# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

### 2. With Free AI (Recommended)
```bash
# Get FREE API keys:
# - Groq: https://console.groq.com/keys
# - Cohere: https://dashboard.cohere.com/api-keys

# Add to .env file
echo "GROQ_API_KEY=your_key" >> .env
echo "COHERE_API_KEY=your_key" >> .env

# Run normally
```

### 3. Best Setup (Ollama + Free AI)
```bash
# Install Ollama (offline capable)
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.1

# Get API keys, then run
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      FRONTEND                                 │
│   Charts • Signals • ARTH Chat • Dashboard                   │
└─────────────────────────┬─────────────────────────────────────┘
                          │
┌─────────────────────────▼─────────────────────────────────────┐
│                      BACKEND                                  │
│                                                          │
│   ┌───────────────────────────────────────────────────┐   │
│   │              ARTH - AI AGENT                       │   │
│   │  • Learning Engine    • Analysis Engine           │   │
│   │  • Probability Calc   • Chart Reader              │   │
│   │  • Backtest Engine    • Pattern Matcher           │   │
│   └───────────────────────────────────────────────────┘   │
│                                                          │
│   ┌───────────────────────────────────────────────────┐   │
│   │              ARTH'S BRAIN                         │   │
│   │              (SQLite Knowledge Base)              │   │
│   └───────────────────────────────────────────────────┘   │
│                                                          │
│   ┌───────────────────────────────────────────────────┐   │
│   │              AI ROUTER                            │   │
│   │  Groq → Cohere → HuggingFace → Ollama → Mistral   │   │
│   └───────────────────────────────────────────────────┘   │
│                                                          │
└───────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────▼─────────────────────────────────────┐
│                    DATA (FREE)                               │
│   Yahoo Finance • Charts • Historical Data                     │
└───────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
ai-trader/
├── backend/
│   ├── main.py                 # FastAPI entry
│   ├── config.py               # Configuration
│   │
│   ├── ai_agent/               # ARTH's modules
│   │   ├── arth.py             # Main agent
│   │   ├── brain.py            # Knowledge base
│   │   ├── router.py           # Multi-AI router
│   │   ├── analyzer.py         # Chart analysis
│   │   ├── backtest.py         # Backtesting
│   │   └── providers/          # AI providers
│   │       ├── groq.py
│   │       ├── cohere.py
│   │       ├── huggingface.py
│   │       └── ollama.py
│   │
│   ├── services/
│   │   ├── price_fetcher.py    # Yahoo Finance
│   │   ├── signal_generator.py # Rule-based signals
│   │   └── indicators.py       # Technical analysis
│   │
│   └── database/
│       ├── models.py           # SQLAlchemy models
│       └── knowledge.db        # ARTH's brain
│
├── frontend/
│   ├── src/
│   │   ├── app/                # Pages
│   │   ├── components/         # UI components
│   │   │   ├── charts/        # Chart components
│   │   │   ├── signals/       # Signal components
│   │   │   └── arth/          # ARTH chat
│   │   └── lib/
│   └── public/
│
├── .env.example               # Environment template
├── .rule                      # Pre-commit automation
└── README.md
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/prices` | Live prices |
| GET | `/api/prices/{symbol}` | Single stock price |
| GET | `/api/signals` | All trading signals |
| GET | `/api/signals/{symbol}` | Single signal with ARTH analysis |
| GET | `/api/arth/analyze/{symbol}` | ARTH's full analysis |
| POST | `/api/arth/chat` | Chat with ARTH |
| GET | `/api/backtest` | Run backtest |
| GET | `/api/probability/{symbol}` | Trade probability |

---

## Free AI Providers Used

| Provider | Model | Speed | Best For |
|----------|-------|-------|----------|
| **Groq** | llama-3.1-70b | ⚡⚡⚡ | Fast analysis |
| **Cohere** | command-r | ⚡⚡ | Chart reading |
| **HuggingFace** | Various | ⚡⚡ | Vision models |
| **Ollama** | llama3.1 | ⚡ | Offline mode |
| **Mistral** | mistral-nemo | ⚡ | Backup |

---

## How ARTH Learns

```
1. OBSERVE
   └─ Reads charts, identifies patterns

2. PREDICT
   └─ Generates BUY/SELL/HOLD signals

3. STORE
   └─ Logs prediction to brain

4. BACKTEST
   └─ Runs historical validation

5. LEARN
   └─ Updates pattern success rates

6. IMPROVE
   └─ Adjusts rules automatically
```

---

## Screenshots

*Dashboard showing live signals and ARTH analysis*

---

## Documentation

- [📋 Plan](PLAN.md) - Detailed project plan
- [📝 Requirements](REQUIREMENTS.md) - What to provide
- [📚 API Docs](http://localhost:8000/docs) - When running

---

## Disclaimer

⚠️ **IMPORTANT:**

- This is NOT financial advice
- Always do your own research
- Past performance does not guarantee future results
- Only trade with money you can afford to lose
- The creator is not responsible for any trading losses

---

## Contributing

1. Fork the repository
2. Create your feature branch
3. Make your changes
4. Run tests: `bash .rule`
5. Submit a pull request

---

## License

MIT License

---

**Built with ❤️ | AI Trader v2.0**
**Learn • Analyze • Trade Smart**
