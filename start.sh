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
