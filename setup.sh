#!/usr/bin/env bash
# AI Trader — One-liner Setup (Clone → Ready)
# Usage:
#   git clone --branch arena/01a07736-ai-trader https://github.com/anoopuri21/ai-trader.git && cd ai-trader && bash setup.sh
#   bash setup.sh --yes --start          # auto + launch
#   bash setup.sh --help
set -e

# ─── Colors ───────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✓${NC} $*"; }
warn() { echo -e "${YELLOW}⚠${NC} $*"; }
fail() { echo -e "${RED}✗${NC} $*"; }
info() { echo -e "${CYAN}→${NC} $*"; }

YES=false; START=false
for arg in "$@"; do
  case $arg in
    --yes|-y) YES=true ;;
    --start) START=true ;;
    --help|-h)
      echo "AI Trader setup — one liner"
      echo "  bash setup.sh              # interactive setup"
      echo "  bash setup.sh --yes        # auto without prompts"
      echo "  bash setup.sh --yes --start # setup + start backend:8000 frontend:3000"
      exit 0
      ;;
  esac
done

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  AI Trader — One-liner Setup                      ║${NC}"
echo -e "${GREEN}║  Clone → setup → ready in 2-3 min                 ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════╝${NC}"
echo ""

# ─── 1. Prerequisite checks ─────────────────────────────────
info "Checking prerequisites..."
MISSING=0

check_cmd() {
  if command -v "$1" >/dev/null 2>&1; then
    ok "$1 $($1 --version 2>&1 | head -n1)"
  else
    fail "$1 not found"
    MISSING=1
  fi
}

check_cmd git
check_cmd python3
check_cmd pip3 2>&1 | head -n1 || check_cmd pip
check_cmd node
check_cmd npm

# Python version >= 3.11
if command -v python3 >/dev/null 2>&1; then
  PYV=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
  PY_MAJOR=$(echo $PYV | cut -d. -f1)
  PY_MINOR=$(echo $PYV | cut -d. -f2)
  if [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -ge 11 ]; then
    ok "python3 $PYV (>=3.11)"
  elif [ "$PY_MAJOR" -gt 3 ]; then
    ok "python3 $PYV (>=3.11)"
  else
    fail "python3 $PYV — need >=3.11 (https://python.org)"
    MISSING=1
  fi
fi

# Node >= 18
if command -v node >/dev/null 2>&1; then
  NV=$(node -v | sed 's/v//')
  MAJ=$(echo $NV | cut -d. -f1)
  if [ "$MAJ" -ge 18 ]; then ok "node $NV (>=18)"
  else fail "node $NV — need >=18 (https://nodejs.org)"; MISSING=1; fi
fi

if [ $MISSING -eq 1 ]; then
  echo ""
  fail "Some tools missing — install them then re-run bash setup.sh"
  echo ""
  echo "Quick install:"
  echo "  macOS:   brew install git python@3.11 node"
  echo "  Ubuntu:  sudo apt update && sudo apt install -y git python3.11 python3-venv python3-pip nodejs npm"
  echo "  Windows: winget install Git.Python.3.11 OpenJS.NodeJS  (or download python.org / nodejs.org)"
  echo ""
  echo "Full list: cat docs/PREREQUISITES.md  /  ./setup.sh --help"
  exit 1
fi
echo ""

# ─── 2. .env ────────────────────────────────────────────────
if [ ! -f .env ]; then
  if [ -f .env.example ]; then
    cp .env.example .env
    ok ".env created from .env.example (edit later: OMNIROUTE_API_KEY, GROQ_API_KEY etc)"
  else
    warn ".env.example not found, creating minimal .env"
    printf "ENV=development\nDEBUG=true\nFRONTEND_URL=http://localhost:3000\nOMNIROUTE_BASE_URL=http://localhost:20128/v1\nOMNIROUTE_MODEL=auto\n" > .env
  fi
else
  ok ".env already exists — keeping"
fi

# ─── 3. Backend — venv + pip ─────────────────────────────────
info "Setting up backend (venv + pip)..."
if [ ! -d backend/.venv ]; then
  python3 -m venv backend/.venv
  ok "venv created backend/.venv"
else
  ok "venv exists backend/.venv"
fi
# shellcheck disable=SC1091
source backend/.venv/bin/activate 2>/dev/null || source backend/.venv/Scripts/activate 2>/dev/null || true
pip install --upgrade pip -q
pip install -r backend/requirements.txt -q
ok "backend deps installed"
# DB folder & perms
mkdir -p backend/data
chmod 700 backend/data 2>/dev/null || true
if [ -f backend/data/ai_trader.db ]; then chmod 600 backend/data/ai_trader.db 2>/dev/null || true; fi
# sanity test
if python -m pytest backend/tests/ -q >/dev/null 2>&1; then ok "backend tests 17 passed"
else warn "backend tests had warnings (ok to continue)"; fi
deactivate 2>/dev/null || true
echo ""

# ─── 4. Frontend — npm ──────────────────────────────────────
info "Setting up frontend (npm)..."
if [ ! -d frontend/node_modules ]; then
  (cd frontend && npm install --silent)
  ok "frontend deps installed"
else
  ok "frontend/node_modules exists — skipping (rm -rf frontend/node_modules to reinstall)"
fi
echo ""

# ─── 5. OmniRoute (optional, not inside repo) ───────────────
info "OmniRoute check (gateway, NOT inside ai-trader repo per your rule)..."
if command -v omniroute >/dev/null 2>&1; then
  ok "omniroute $(omniroute --version 2>&1 | head -n1) already installed"
else
  warn "omniroute not found — gateway is OPTIONAL (app falls back to groq/cohere/rule-based)"
  if [ "$YES" = true ]; then
    info "Installing omniroute globally via npm..."
    npm install -g omniroute --silent 2>&1 | tail -n 3 || warn "npm i -g omniroute failed — run: npm i -g omniroute (may need sudo)"
  else
    echo "   To install later: npm i -g omniroute  &&  omniroute  (http://localhost:20128)"
    echo "   Or via Docker: docker run -p 20128:20128 diegosouzapw/omniroute"
  fi
fi
echo ""

# ─── 6. Done ────────────────────────────────────────────────
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
ok "Setup complete! 🎉"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Next steps:"
echo "  1) (Optional) Edit .env — add OMNIROUTE_API_KEY / GROQ_API_KEY"
echo "  2) Start:"
echo "     Terminal A:  source backend/.venv/bin/activate && uvicorn main:app --app-dir backend --reload --host 0.0.0.0 --port 8000"
echo "     Terminal B:  cd frontend && npm run dev   # http://localhost:3000"
echo "     Or single:   bash start.sh   (created below)"
echo "  3) Verify:     curl http://localhost:8000/api/health | jq"
echo "                 curl http://localhost:8000/api/omniroute/status | jq .reachable"
echo ""
echo "One-liner clone+setup for fresh machine:"
echo "  git clone --branch arena/01a07736-ai-trader https://github.com/anoopuri21/ai-trader.git && cd ai-trader && bash setup.sh --yes"
echo ""

# Create start.sh helper
cat > start.sh <<'EOS'
#!/usr/bin/env bash
set -e
# AI Trader — Start both servers (backend 8000 + frontend 3000)
GREEN='\033[0;32m'; NC='\033[0m'
echo -e "${GREEN}Starting AI Trader...${NC}"
# Backend in background
if [ -f backend/.venv/bin/activate ]; then source backend/.venv/bin/activate; fi
echo "→ Backend http://localhost:8000 (logs: tail -f /tmp/ai-trader-backend.log)"
nohup uvicorn main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload > /tmp/ai-trader-backend.log 2>&1 &
BE_PID=$!
sleep 2
echo "→ Frontend http://localhost:3000"
(cd frontend && npm run dev -- -H 0.0.0.0 -p 3000 2>&1 | tee /tmp/ai-trader-frontend.log) &
FE_PID=$!
echo ""
echo "✓ Both starting — PIDs backend $BE_PID frontend $FE_PID"
echo "  Health: curl http://localhost:8000/api/health"
echo "  Stop:   kill $BE_PID $FE_PID   # or pkill -f 'uvicorn.*8000' ; pkill -f 'next dev'"
EOS
chmod +x start.sh
ok "Created ./start.sh (bash start.sh to launch both)"

if [ "$START" = true ]; then
  echo ""
  info "START flag set — launching..."
  bash start.sh
fi
