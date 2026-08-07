# 🛠️ Developer Setup Guide - AI Trader v2.0

## Getting Started (Local Development)

### Prerequisites

| Tool | Version | Required |
|------|---------|----------|
| Python | 3.10+ | ✅ Required |
| Node.js | 18+ | ✅ Required |
| npm | 9+ | ✅ Required |
| Git | Any | ✅ Required |
| Ollama | Latest | ⚠️ Optional (for local AI) |

---

## Step 1: Clone the Repository

```bash
git clone https://github.com/anoopuri21/ai-trader.git
cd ai-trader
```

## Step 2: Set Up Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and add your API keys (all optional - system works without any keys):

```env
# At minimum, no keys needed for basic functionality

# For AI features (FREE):
GROQ_API_KEY=         # Get from: https://console.groq.com/keys
COHERE_API_KEY=       # Get from: https://dashboard.cohere.com/api-keys
HUGGINGFACE_API_KEY=  # Get from: https://huggingface.co/settings/tokens

# For local AI (no key needed):
# Install Ollama: https://ollama.com/download
# Then run: ollama pull llama3.1
```

## Step 3: Backend Setup

```bash
# Navigate to backend
cd backend

# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the backend server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The backend should now be running at `http://localhost:8000`
- API Docs: http://localhost:8000/docs
- Health check: http://localhost:8000/api/health

## Step 4: Frontend Setup

Open a NEW terminal window:

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Run the development server
npm run dev
```

The frontend should now be running at `http://localhost:3000`

## Step 5: Verify Everything Works

1. Open http://localhost:3000 in your browser
2. You should see the AI Trader dashboard
3. Check http://localhost:8000/api/health — should show "healthy"
4. Check http://localhost:8000/api/arth/status — should show ARTH's status

---

## Development Workflow

### Project Structure

```
ai-trader/
├── backend/                    # Python FastAPI backend
│   ├── main.py                 # App entry point
│   ├── config.py               # Settings from .env
│   │
│   ├── ai_agent/               # ARTH AI Agent
│   │   ├── arth.py             # Main agent orchestrator
│   │   ├── brain.py            # SQLite knowledge base
│   │   ├── router.py           # Multi-AI provider router
│   │   ├── analyzer.py         # Analysis engine
│   │   ├── backtest.py         # Backtesting engine
│   │   ├── scheduler.py        # Self-learning scheduler
│   │   ├── sentiment.py        # Sentiment analyzer
│   │   ├── prompts.py          # AI prompts
│   │   └── providers/          # AI provider implementations
│   │       ├── groq_provider.py
│   │       ├── cohere_provider.py
│   │       ├── huggingface_provider.py
│   │       └── ollama_provider.py
│   │
│   ├── services/               # Core services
│   │   ├── price_fetcher.py    # Yahoo Finance data
│   │   ├── signal_generator.py # Rule-based signals
│   │   ├── indicators.py       # Technical indicators
│   │   └── advanced_indicators.py # Advanced indicators
│   │
│   ├── api/routes/             # API endpoints
│   │   ├── prices.py           # Price data endpoints
│   │   ├── signals.py          # Signal endpoints
│   │   ├── arth.py             # ARTH AI endpoints
│   │   ├── backtest.py         # Backtesting endpoints
│   │   └── analysis.py         # Advanced analysis endpoints
│   │
│   ├── models/                 # Data models
│   │   └── stock.py            # Pydantic models
│   │
│   └── requirements.txt        # Python dependencies
│
├── frontend/                   # Next.js frontend
│   ├── src/
│   │   ├── app/                # Pages
│   │   │   ├── page.tsx        # Dashboard (main page)
│   │   │   ├── arth/page.tsx   # ARTH chat interface
│   │   │   ├── backtest/page.tsx # Backtesting page
│   │   │   └── brain/page.tsx  # Brain/knowledge page
│   │   ├── lib/                # Utilities
│   │   │   ├── api.ts          # API client
│   │   │   └── utils.ts        # Helper functions
│   │   └── types/              # TypeScript types
│   │       └── index.ts
│   ├── package.json
│   └── next.config.js          # Next.js config (API proxy)
│
├── .env.example                # Environment template
├── .rule                       # Pre-commit checks
├── DEVELOPER_GUIDE.md          # This file
├── FUTURE_IMPROVEMENTS.md      # Future plans
└── README.md                   # Project overview
```

### Running Tests

```bash
# Backend tests
cd backend
pytest -v

# Frontend type checking
cd frontend
npx tsc --noEmit
```

### Code Formatting

```bash
# Backend formatting
cd backend
black . --line-length 100
ruff check . --fix

# Frontend formatting
cd frontend
npx prettier --write "src/**/*.{tsx,ts}"
```

---

## API Endpoints Reference

### Prices
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/prices/` | All stock prices |
| GET | `/api/prices/{symbol}` | Single stock price |
| GET | `/api/prices/indices/summary` | Nifty 50 + Bank Nifty |

### Signals
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/signals/` | All trading signals |
| GET | `/api/signals/{symbol}` | Single signal |
| GET | `/api/signals/summary/overview` | Signal overview |
| GET | `/api/signals/trending/bullish` | Top BUY signals |
| GET | `/api/signals/trending/bearish` | Top SELL signals |

### ARTH AI Agent
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/arth/analyze/{symbol}` | Full AI analysis |
| POST | `/api/arth/chat` | Chat with ARTH |
| GET | `/api/arth/brain/stats` | Brain statistics |
| GET | `/api/arth/brain/predictions` | Recent predictions |
| GET | `/api/arth/brain/patterns` | Learned patterns |
| GET | `/api/arth/brain/rules` | Active rules |
| POST | `/api/arth/reflect` | Self-reflection |
| GET | `/api/arth/status` | ARTH status |
| GET | `/api/arth/probability/{symbol}` | Trade probability |

### Backtesting
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/backtest/run` | Run backtest |
| GET | `/api/backtest/compare` | Compare strategies |
| GET | `/api/backtest/performance` | Performance history |
| GET | `/api/backtest/accuracy` | Prediction accuracy |

### Advanced Analysis
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/analysis/advanced/{symbol}` | All indicators |
| GET | `/api/analysis/sentiment/market` | Market sentiment |
| GET | `/api/analysis/sentiment/{symbol}` | Stock sentiment |
| GET | `/api/analysis/fibonacci/{symbol}` | Fibonacci levels |
| GET | `/api/analysis/pivot/{symbol}` | Pivot points |

---

## Common Issues

### "Port 8000 already in use"
```bash
# Kill existing process
lsof -i :8000 | grep LISTEN | awk '{print $2}' | xargs kill -9
```

### "Module not found" errors
```bash
# Make sure you're in the backend directory
cd backend
# Reinstall dependencies
pip install -r requirements.txt
```

### Frontend can't connect to backend
- Check backend is running on port 8000
- Check `next.config.js` has the rewrite rule
- Or set `NEXT_PUBLIC_API_URL=http://localhost:8000` in `.env`

### Yahoo Finance rate limiting
- Data is cached for 30 seconds
- If you get rate limited, wait a few minutes
- For heavy testing, consider using mock data

### Ollama not connecting
```bash
# Start Ollama
ollama serve

# Pull a model
ollama pull llama3.1

# Test
curl http://localhost:11434/api/tags
```

---

## Adding New Features

### Adding a new AI Provider

1. Create `backend/ai_agent/providers/your_provider.py`
2. Implement the `analyze()` method returning JSON
3. Register in `backend/ai_agent/router.py`
4. Add API key to `config.py` and `.env.example`

### Adding a new API endpoint

1. Create route in appropriate file under `api/routes/`
2. Register the router in `main.py`
3. Add TypeScript types in `frontend/src/types/index.ts`
4. Add API method in `frontend/src/lib/api.ts`

### Adding a new technical indicator

1. Add calculation method in `services/advanced_indicators.py`
2. Include in `get_all_advanced()` method
3. Create API endpoint in `api/routes/analysis.py`
4. Display in frontend

---

## Performance Tips

- Backend uses TTL caching (30s for prices, 60s for historical data)
- ARTH's brain uses SQLite (fast enough for single-user)
- For multi-user: Consider PostgreSQL for the brain database
- Frontend: Uses static generation where possible

## Deployment

### Backend (Docker)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt
COPY backend/ .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Frontend (Vercel)
```bash
# Just connect your GitHub repo to Vercel
# It auto-detects Next.js
# Set environment variable: NEXT_PUBLIC_API_URL=https://your-backend-url.com
```

---

## Questions?

- Check the API docs at http://localhost:8000/docs
- Read the README.md for project overview
- Read FUTURE_IMPROVEMENTS.md for planned features
- Check the ARTH brain at /api/arth/brain/stats

---

*Happy coding! 🚀*
