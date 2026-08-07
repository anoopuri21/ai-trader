# AI Trader - Requirements Document v2.0
## Multi-AI Architecture with ARTH's Central Brain

---

## Required: Multi-AI Provider Setup

The system uses multiple free AI providers in rotation. You don't need all of them - start with what you have!

---

### 1. Groq (PRIMARY - Fastest Free AI)

**Purpose:** Primary AI for fast analysis

**Speed:** ~30 tokens/second (blazing fast)

**How to get API key:**
1. Go to https://console.groq.com/
2. Sign up with Google/GitHub
3. Go to API Keys section
4. Create a new key
5. Copy and save securely

**Free Tier:**
- 14 requests/minute
- 30 tokens/minute
- Unlimited per day if spread out

```env
GROQ_API_KEY=gsk_your_key_here
```

**Status:** ✅ HIGHLY RECOMMENDED - Fastest free AI

---

### 2. Cohere (Chart & Analysis)

**Purpose:** Chart analysis, detailed reasoning

**How to get API key:**
1. Go to https://dashboard.cohere.com/api-keys
2. Sign up with email
3. Create API key
4. Copy and save

**Free Tier:**
- 1000 requests/month
- Great for chart analysis

```env
COHERE_API_KEY=your_key_here
```

**Status:** ✅ Recommended

---

### 3. Mistral AI (Backup)

**Purpose:** Backup AI provider

**How to get API key:**
1. Go to https://console.mistral.ai/api-keys
2. Sign up
3. Create API key

**Free Tier:** Limited requests

```env
MISTRAL_API_KEY=your_key_here
```

**Status:** ⚠️ Optional - Backup only

---

### 4. HuggingFace (Vision & Local)

**Purpose:** Chart image analysis, local models

**How to get API key:**
1. Go to https://huggingface.co/settings/tokens
2. Sign up/login
3. Create new token (read permission)
4. Copy token

**Free Tier:** Unlimited (no rate limits for most models)

```env
HUGGINGFACE_API_KEY=hf_your_key_here
```

**Status:** ✅ Recommended - For chart vision models

---

### 5. Ollama (Offline/Local) - Optional

**Purpose:** Run AI locally (no cloud needed)

**How to install:**
```bash
# macOS/Linux
curl -fsSL https://ollama.com/install.sh | sh

# Windows - Download from https://ollama.com/download
```

**Then pull models:**
```bash
# Pull a good model for trading
ollama pull llama3.1
ollama pull mixtral

# Check it's running
ollama list
```

**No API key needed** - runs locally on your machine

**Status:** ✅ HIGHLY RECOMMENDED - Best fallback, unlimited

---

### 6. OpenAI (Optional - More Powerful)

**Purpose:** Best quality analysis (paid)

**How to get API key:**
1. Go to https://platform.openai.com/api-keys
2. Create account
3. Add billing (required)
4. Create API key

**Cost:** ~$0.01-0.05 per analysis

```env
OPENAI_API_KEY=sk-your_key_here
```

**Status:** ⚠️ Optional - Only if you want premium AI

---

### 7. Anthropic Claude (Optional)

**Purpose:** Alternative premium AI

**How to get API key:**
1. Go to https://console.anthropic.com/
2. Sign up
3. Create API key

**Cost:** Pay-per-use

```env
ANTHROPIC_API_KEY=sk-ant-your_key_here
```

**Status:** ⚠️ Optional

---

## Complete .env Template

Copy this to your `.env` file:

```env
# ============================================
# AI TRADER - Environment Configuration
# ============================================

# ===================
# APP SETTINGS
# ===================
APP_NAME=AI Trader
DEBUG=true
PORT=8000
FRONTEND_URL=http://localhost:3000

# ===================
# FREE AI PROVIDERS (Recommended)
# ===================

# Groq - PRIMARY (Fastest free AI)
# Get: https://console.groq.com/keys
GROQ_API_KEY=

# Cohere - Charts & Analysis
# Get: https://dashboard.cohere.com/api-keys
COHERE_API_KEY=

# Mistral - Backup
# Get: https://console.mistral.ai/api-keys
MISTRAL_API_KEY=

# HuggingFace - Vision & Local
# Get: https://huggingface.co/settings/tokens
HUGGINGFACE_API_KEY=

# ===================
# OPTIONAL PAID AI
# ===================

# OpenAI GPT-4 (Most capable)
# Get: https://platform.openai.com/api-keys
OPENAI_API_KEY=

# Anthropic Claude (Alternative)
# Get: https://console.anthropic.com/
ANTHROPIC_API_KEY=

# ===================
# AI SETTINGS
# ===================
# Priority order for AI router
AI_PRIORITY=groq,cohere,huggingface,ollama,mistral

# Fallback to rule-based if all AI fail
ENABLE_FALLBACK_SIGNALS=true

# ===================
# TRADING SETTINGS
# ===================
RSI_PERIOD=14
SMA_SHORT=20
SMA_MID=50
SMA_LONG=200
MACD_FAST=12
MACD_SLOW=26
MACD_SIGNAL=9

# Signal confidence threshold
MIN_SIGNAL_CONFIDENCE=60

# ===================
# DATA SETTINGS
# ===================
# Yahoo Finance is FREE and works automatically
# No API key needed for stock data!

# ===================
# DATABASE
# ===================
DATABASE_URL=sqlite:///./ai_trader.db

# ===================
# LEARNING & BACKTESTING
# ===================
ENABLE_BACKTESTING=true
BACKTEST_SCHEDULE=daily
BACKTEST_START_DATE=2020-01-01

# ===================
# LOGGING
# ===================
LOG_LEVEL=INFO
```

---

## Quick Setup Guide

### Minimum Viable Setup (0 API Keys)

Even with NO API keys, the system works:

```bash
# 1. Install Ollama (optional but recommended)
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.1

# 2. Run with rule-based signals
cd ai-trader/backend
pip install -r requirements.txt
uvicorn main:app --reload

# 3. Frontend
cd ../frontend
npm install
npm run dev
```

**What works without API keys:**
- ✅ Live prices from Yahoo Finance
- ✅ Technical indicators (SMA, RSI, MACD)
- ✅ Rule-based BUY/SELL/HOLD signals
- ✅ Interactive charts
- ✅ ARTH's brain (stores patterns)

---

### Recommended Setup (With Free AI)

```bash
# 1. Get these FREE API keys:
# - Groq: https://console.groq.com/keys
# - Cohere: https://dashboard.cohere.com/api-keys

# 2. Add to .env file

# 3. Run normally
```

**What additional works with free AI:**
- ✅ AI-powered chart analysis
- ✅ ARTH explains signals
- ✅ Pattern recognition
- ✅ Multi-AI fallback
- ✅ Better accuracy

---

### Best Setup (With Ollama + Free AI)

```bash
# 1. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.1
ollama pull mixtral

# 2. Get FREE API keys:
# - Groq: https://console.groq.com/keys
# - HuggingFace: https://huggingface.co/settings/tokens

# 3. Add to .env

# 4. Run
```

**What works with best setup:**
- ✅ Everything from free AI
- ✅ Offline AI fallback (Ollama)
- ✅ Local vision models
- ✅ Zero AI costs
- ✅ Maximum reliability

---

## System Requirements

### Minimum
| Component | Requirement |
|-----------|-------------|
| Python | 3.10+ |
| Node.js | 18+ |
| RAM | 4 GB |
| Storage | 2 GB |
| Internet | Stable |

### Recommended (with Ollama)
| Component | Requirement |
|-----------|-------------|
| Python | 3.10+ |
| Node.js | 18+ |
| RAM | 8 GB (for Ollama) |
| Storage | 10 GB |
| GPU | Optional (NVIDIA CUDA for faster) |

### Ollama GPU Support (Optional)
```bash
# Install NVIDIA CUDA drivers first
# Then Ollama automatically uses GPU

# Check GPU is being used
ollama run llama3.1 "Hello"
# Should see "CUDA" in output
```

---

## Security Checklist

### DO ✅
- [ ] Store ALL API keys in `.env` file
- [ ] Add `.env` to `.gitignore`
- [ ] Use environment variables
- [ ] Keep keys private
- [ ] Rotate keys periodically

### DON'T ❌
- [ ] Commit `.env` to GitHub
- [ ] Hardcode keys in code
- [ ] Share keys publicly
- [ ] Use default key names
- [ ] Trust unknown sources

### .gitignore (Must Include)
```
.env
.env.local
.env.production
*.env
```

---

## Cost Comparison

| Setup | Monthly Cost | Capabilities |
|-------|--------------|--------------|
| **Rule-based Only** | $0 | Basic signals |
| **+ Free AI** | $0 | AI analysis |
| **+ Ollama** | $0 | Offline capable |
| **+ OpenAI** | $5-20 | Premium AI |
| **+ Claude** | $5-20 | Premium AI |

**Total: FREE is achievable!**

---

## Getting Started Checklist

```
┌────────────────────────────────────────────────────────────┐
│                     SETUP CHECKLIST                         │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  [ ] 1. Clone project: git clone <repo-url>                │
│                                                             │
│  [ ] 2. Copy env: cp .env.example .env                     │
│                                                             │
│  [ ] 3. Get API keys (optional):                           │
│         [ ] Groq (recommended) - console.groq.com          │
│         [ ] Cohere (recommended) - dashboard.cohere.com   │
│         [ ] HuggingFace (optional) - huggingface.co        │
│                                                             │
│  [ ] 4. Install Ollama (optional but recommended):        │
│         curl -fsSL https://ollama.com/install.sh | sh     │
│         ollama pull llama3.1                               │
│                                                             │
│  [ ] 5. Install dependencies:                              │
│         pip install -r backend/requirements.txt           │
│         npm install (in frontend)                          │
│                                                             │
│  [ ] 6. Start backend:                                     │
│         cd backend && uvicorn main:app --reload            │
│                                                             │
│  [ ] 7. Start frontend:                                    │
│         cd frontend && npm run dev                         │
│                                                             │
│  [ ] 8. Open: http://localhost:3000                        │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

---

## Troubleshooting

### "All AI providers failed"
**Solution:** 
1. Check API keys are correct
2. Check internet connection
3. Ollama fallback should work if installed
4. System falls back to rule-based signals

### "Ollama not responding"
**Solution:**
```bash
# Start Ollama service
ollama serve

# Check if running
curl http://localhost:11434/api/tags
```

### "Chart not loading"
**Solution:**
1. Check internet (for chart data)
2. Try different timeframe
3. Check browser console for errors

### "Signals not showing"
**Solution:**
1. Market may be closed (NSE: 9:15 AM - 3:30 PM IST)
2. Check backend logs
3. Yahoo Finance may be down (wait)

---

## Next Steps After Setup

1. **Watch the dashboard** - See live prices and signals
2. **Click on a stock** - View interactive charts
3. **Ask ARTH** - Type questions about signals
4. **Monitor ARTH** - Watch it learn over time
5. **Backtest** - Run historical analysis

---

## Questions?

1. Which API keys do you have?
2. Will you install Ollama?
3. Any specific features you want first?

---

*AI Trader v2.0 - Multi-AI with ARTH's Brain*
