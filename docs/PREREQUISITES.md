# Prerequisites — Local Setup se pehle kya chahiye

> **Goal:** Repo clone karne se pehle ye tools ready rakho, fir `bash setup.sh` ek command me sab ho jayega.

## 1) Must-have (nahi to setup fail hoga)

| Tool | Version | Check | Install |
|------|---------|-------|---------|
| **Git** | any | `git --version` | macOS `brew install git` / Ubuntu `sudo apt install git` / Windows `winget install Git.Git` |
| **Python** | **3.11+** (3.11/3.12/3.13) | `python3 --version` | python.org → 3.11, or `pyenv`, `brew install python@3.11`, `sudo apt install python3.11 python3-venv python3-pip` |
| **pip + venv** | pip 23+ | `pip3 --version` `python3 -m venv --help` | bundled with Python 3.11 |
| **Node.js** | **18+** (18/20/22) | `node -v` | nodejs.org, `brew install node`, `sudo apt install nodejs npm`, `winget install OpenJS.NodeJS` |
| **npm** | 9+ (bundled with Node) | `npm -v` | same as Node |

**Hardware:** 4 GB RAM, 2 GB free disk, Windows 10/11 / macOS 12+ / Ubuntu 22.04+.

**Browser:** Chrome/Edge/Firefox latest (for http://localhost:3000).

## 2) Optional (app bina inke bhi chalta, but AI ke liye best)

| Tool | Kyun | Install |
|------|------|---------|
| **OmniRoute gateway** | ONE key → 356 providers, ~1.47B free tokens/mo, auto-fallback | `npm i -g omniroute && omniroute` → http://localhost:20128 (then `.env` me `OMNIROUTE_API_KEY`) — **repo ke andar install nahi hota**, outside rahega per your rule. Alternative: `docker run -p 20128:20128 diegosouzapw/omniroute` |
| **Docker** | OmniRoute ya DB ko container me chalana | docker.com |
| **Groq / Cohere / HuggingFace keys** | Direct fallback jab OmniRoute na ho | groq.com / cohere.com — `.env` me `GROQ_API_KEY=` |
| **NewsAPI key** | Real news sentiment (nahi to RSS fallback) | newsapi.org — `.env` `NEWSAPI_KEY=` |

## 3) Check — Clone se pehle run karo

```bash
git --version; python3 --version; pip3 --version; node -v; npm -v
# Expect: git 2.x, python 3.11.x, pip 2x.x, node v18+/v20+, npm 9+/10+
```

Agar koi missing hai to upar table se install karo, fir:

## 4) One-liner clone + setup

```bash
# Fresh machine — single command
git clone --branch arena/01a07736-ai-trader https://github.com/anoopuri21/ai-trader.git
cd ai-trader
bash setup.sh --yes --start
# → backend http://localhost:8000 + frontend http://localhost:3000 2 min me ready
```

**Already cloned?**
```bash
bash setup.sh              # interactive
bash setup.sh --yes        # auto
bash start.sh              # dono servers start (setup ke baad)
curl http://localhost:8000/api/health | jq
```

## 5) Setup.sh kya karta hai (2-3 min)

1. Prerequisites check (fail fast with fix hints)
2. `.env` → `.env.example` se banata (agar na ho)
3. `backend/.venv` venv + `pip install -r backend/requirements.txt` + `pytest` 17 pass
4. `frontend/node_modules` → `npm install`
5. OmniRoute detect (nahi to optional install hint)
6. `start.sh` banata (dono servers ek sath)

No global Python pollution — sab `backend/.venv` me.

## 6) Troubleshooting

- `python3: command not found` → `python` try karo, ya python.org se 3.11 install
- `externally-managed-environment` → `setup.sh` khud venv banata, manual me `python3 -m venv .venv && source .venv/bin/activate && pip install -r backend/requirements.txt`
- `node: command not found` → nodejs.org se 18+ install, restart terminal
- `npm i -g omniroute` permission denied → `sudo npm i -g omniroute` ya `npm config set prefix ~/.npm-global`
- Yahoo 404 in sandbox → local pe sahi chalega (sandbox me SSL blocked, graceful 404 — not bug)
- Port busy 8000/3000 → `lsof -i :8000` / `npx kill-port 8000 3000` or change `.env` PORT
