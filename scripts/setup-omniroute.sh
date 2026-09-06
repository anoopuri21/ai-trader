#!/usr/bin/env bash
# setup-omniroute.sh — Install & run OmniRoute gateway for AI Trader
# Reference: https://github.com/diegosouzapw/OmniRoute
# Usage:
#   ./scripts/setup-omniroute.sh              # npm global install + start
#   ./scripts/setup-omniroute.sh --docker      # docker run
#   ./scripts/setup-omniroute.sh --from-source # clone & run from source
#   ./scripts/setup-omniroute.sh --status      # probe gateway
set -euo pipefail

OMNIROUTE_PORT="${OMNIROUTE_PORT:-20128}"
OMNIROUTE_BASE_URL="${OMNIROUTE_BASE_URL:-http://localhost:${OMNIROUTE_PORT}/v1}"
REF_REPO="${REF_REPO:-https://github.com/diegosouzapw/OmniRoute.git}"
REF_DIR="${REF_DIR:-/tmp/OmniRoute}"

red() { printf "\033[31m%s\033[0m\n" "$*"; }
green() { printf "\033[32m%s\033[0m\n" "$*"; }
yellow() { printf "\033[33m%s\033[0m\n" "$*"; }
blue() { printf "\033[34m%s\033[0m\n" "$*"; }

probe() {
  local url="${1:-$OMNIROUTE_BASE_URL}/models"
  echo "→ Probing $url ..."
  if command -v curl >/dev/null 2>&1; then
    if curl -sf "$url" -H "Authorization: Bearer ${OMNIROUTE_API_KEY:-dummy}" >/dev/null 2>&1; then
      green "✓ Gateway reachable at $OMNIROUTE_BASE_URL"
      return 0
    else
      # Try without auth (keyless dev mode)
      if curl -sf "$url" >/dev/null 2>&1; then
        green "✓ Gateway reachable (keyless) at $OMNIROUTE_BASE_URL"
        return 0
      fi
      yellow "✗ Gateway not reachable at $OMNIROUTE_BASE_URL"
      return 1
    fi
  else
    yellow "curl not installed — skipping probe"
    return 1
  fi
}

install_npm() {
  blue "Installing OmniRoute via npm (global)..."
  if ! command -v npm >/dev/null 2>&1; then
    red "npm not found. Install Node.js 20+ first: https://nodejs.org"
    exit 1
  fi
  npm install -g omniroute
  green "✓ npm install complete — run 'omniroute' to start"
}

start_npm() {
  blue "Starting OmniRoute (npm)..."
  if ! command -v omniroute >/dev/null 2>&1; then
    install_npm
  fi
  # Start in background if not already running
  if probe >/dev/null 2>&1; then
    yellow "Gateway already running — skipping start"
  else
    # Launch as background process; user can Ctrl+C the dashboard later
    nohup omniroute >/tmp/omniroute.log 2>&1 &
    echo $! > /tmp/omniroute.pid
    blue "OmniRoute PID $! — log: /tmp/omniroute.log — dashboard http://localhost:${OMNIROUTE_PORT}"
    sleep 2
    probe || yellow "Give it a few seconds and retry probe"
  fi
}

install_docker() {
  blue "Starting OmniRoute via Docker..."
  if ! command -v docker >/dev/null 2>&1; then
    red "docker not found. Install Docker Desktop: https://docs.docker.com/get-docker/"
    exit 1
  fi
  docker pull diegosouzapw/omniroute:latest
  docker rm -f omniroute 2>/dev/null || true
  docker run -d --name omniroute -p "${OMNIROUTE_PORT}:20128" diegosouzapw/omniroute:latest
  green "✓ Docker container 'omniroute' running — dashboard http://localhost:${OMNIROUTE_PORT}"
  sleep 3
  probe || yellow "Container starting — wait a moment and rerun --status"
}

install_from_source() {
  blue "Cloning & running OmniRoute from source..."
  if [ -d "$REF_DIR/.git" ]; then
    yellow "Reference repo already at $REF_DIR — pulling latest"
    git -C "$REF_DIR" pull --ff-only || true
  else
    git clone --depth 1 "$REF_REPO" "$REF_DIR"
  fi
  if ! command -v npm >/dev/null 2>&1; then
    red "npm not found"
    exit 1
  fi
  (cd "$REF_DIR" && npm install && npm run dev) &
  echo $! > /tmp/omniroute-source.pid
  blue "Source dev server PID $! — dashboard http://localhost:${OMNIROUTE_PORT}"
  sleep 4
  probe || true
}

configure_env() {
  local env_file=".env"
  if [ -f ".env.example" ] && [ ! -f ".env" ]; then
    cp .env.example .env
    blue "Created .env from .env.example"
  fi
  if [ -f "$env_file" ]; then
    if grep -q "OMNIROUTE_BASE_URL" "$env_file" 2>/dev/null; then
      green "✓ .env already has OMNIROUTE_* vars"
    else
      yellow "Add OMNIROUTE_* to .env manually — see docs/OMNIROUTE_INTEGRATION.md"
    fi
    echo ""
    blue "Current .env OmniRoute block:"
    grep -A2 -B1 "OMNIROUTE" "$env_file" || yellow "(none found)"
  fi
}

usage() {
  cat <<'EOF'
Usage: ./scripts/setup-omniroute.sh [option]

Options:
  (no args)     npm global install + start gateway
  --docker      run via Docker (diegosouzapw/omniroute:latest)
  --from-source clone & run OmniRoute from source (/tmp/OmniRoute)
  --status      probe gateway liveness
  --env         show .env OmniRoute config
  --help        this help

After the gateway is running:
  1. Open http://localhost:20128 → Providers → add a free provider (Kiro / OpenCode Free)
  2. Dashboard → API Manager → create API key → put it in AI Trader .env as OMNIROUTE_API_KEY
  3. Restart AI Trader backend: uvicorn main:app --reload (or docker compose up)

More docs: docs/OMNIROUTE_INTEGRATION.md  and  /tmp/OmniRoute/docs/getting-started/QUICK-START.md
EOF
}

case "${1:-}" in
  --docker)       install_docker; configure_env ;;
  --from-source)  install_from_source; configure_env ;;
  --status)       probe; exit $? ;;
  --env)          configure_env ;;
  --help|-h)      usage ;;
  "")             install_npm; start_npm; configure_env; echo ""; probe; echo ""; green "Done. Next: set OMNIROUTE_API_KEY in .env and restart backend." ;;
  *)              red "Unknown option: $1"; usage; exit 1 ;;
esac
