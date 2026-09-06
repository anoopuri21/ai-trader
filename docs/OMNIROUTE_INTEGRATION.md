# OmniRoute Integration — AI Trader × OmniRoute

> **OmniRoute** is a unified AI gateway that multiplexes **356 providers** (≈150 free tiers, ~1.47B free tokens/mo) behind one OpenAI-compatible endpoint.  
> Reference repo: **https://github.com/diegosouzapw/OmniRoute** (cloned at `/tmp/OmniRoute` for implementation)

AI Trader integrates OmniRoute as a **first-class ARTH provider** called `omniroute`. When configured, ARTH routes its `analyze` + `chat` calls through OmniRoute’s gateway first, falling back to direct Groq / Cohere / HuggingFace / Ollama only if the gateway is unreachable. This gives ARTH automatic fallback, 19 routing strategies, and resilience across hundreds of models with a **single API key**.

---

## Architecture

```
ARTH (ai_agent/arth.py)
  │
  ▼
AIRouter (ai_agent/router.py)
  ├─ 1) omniroute  ──►  OmniRoute Gateway  ──►  356 providers
  │                       http://localhost:20128/v1  (default)
  │                       • auto / auto/fast / auto/cheap / auto/smart ...
  │                       • 19 strategies: priority, weighted, lkgp, auto, fusion ...
  │                       • 3 resilience layers: circuit breaker, cooldown, model lockout
  │                       • X-OmniRoute-Decision header for routing trace
  ├─ 2) groq       ──►  Groq Llama 3.1 70B (direct)
  ├─ 3) cohere     ──►  Cohere Command R (direct)
  ├─ 4) huggingface──►  Mistral 7B (direct)
  ├─ 5) ollama     ──►  Local LLM (http://localhost:11434)
  └─ 6) rule-based ──►  SMA+RSI+MACD+Bollinger (always available)
```

**Provider implementation:** `backend/ai_agent/providers/omniroute_provider.py`  
**Router integration:** `backend/ai_agent/router.py` (priority order from `AI_PRIORITY`)  
**Config:** `backend/config.py` (`OMNIROUTE_*` env vars)  
**Gateway health:** `backend/api/routes/omniroute.py` (`/api/omniroute/*`)

---

## Quick Start (3 minutes)

### 1. Install & run OmniRoute

Pick one:

**npm (recommended)**
```bash
npm install -g omniroute
omniroute
# Dashboard → http://localhost:20128 — create an API key at /dashboard/api-manager
```

**Docker**
```bash
docker run -d --name omniroute -p 20128:20128 diegosouzapw/omniroute:latest
```

**From source (reference clone)**
```bash
git clone https://github.com/diegosouzapw/OmniRoute.git
cd OmniRoute
npm install
npm run dev
# same dashboard at http://localhost:20128
```

> See also the cloned reference at `/tmp/OmniRoute/docs/getting-started/QUICK-START.md` for free-provider onboarding (Kiro, OpenCode Free, Pollinations — no key needed).

### 2. Configure AI Trader

Copy the env template and fill OmniRoute vars:

```bash
cp .env.example .env
# Edit .env:
OMNIROUTE_API_KEY=sk-...            # from OmniRoute dashboard (or leave empty for keyless local dev)
OMNIROUTE_BASE_URL=http://localhost:20128/v1
OMNIROUTE_MODEL=auto                # try auto/fast, auto/cheap, auto/smart, auto/coding
AI_PRIORITY=omniroute,groq,cohere,huggingface,ollama
```

Notes:
- **Keyless local dev:** If OmniRoute runs with `REQUIRE_API_KEY=false` (default dev), you can leave `OMNIROUTE_API_KEY` empty — the provider sends a dummy bearer and still works.
- **Docker Compose:** When both services run in Docker, set `OMNIROUTE_BASE_URL=http://omniroute:20128/v1` (service name, not localhost). See `docker-compose.omniroute.yml`.

### 3. Install backend deps & restart

```bash
cd backend
pip install -r requirements.txt   # now includes openai>=1.12.0 for OmniRoute
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Verify

```bash
# ARTH should report omniroute as first provider
curl http://localhost:8000/api/arth/status | jq .providers
# Probe gateway directly via AI Trader
curl http://localhost:8000/api/omniroute/status | jq .
curl http://localhost:8000/api/omniroute/test -X POST -H "Content-Type: application/json" -d '{"prompt":"Say PONG"}'
# Full stock analysis (now routed via OmniRoute)
curl http://localhost:8000/api/arth/analyze/RELIANCE | jq .ai_provider
# Expect "omniroute" when gateway is reachable, else fallback provider
```

Check logs for:
```
✅ omniroute: available — model=auto base=http://localhost:20128/v1
```

---

## Configuration Reference

All vars are read from `.env` (or process env) via `backend/config.py`.

| Variable | Default | Description |
|---|---|---|
| `OMNIROUTE_API_KEY` | `None` | API key from OmniRoute Dashboard → API Manager. Leave empty for keyless local gateway. |
| `OMNIROUTE_BASE_URL` | `http://localhost:20128/v1` | Gateway base URL. Trailing `/v1` is normalized automatically. |
| `OMNIROUTE_MODEL` | `auto` | OmniRoute model / combo ID. See below. |
| `OMNIROUTE_TIMEOUT` | `90` | HTTP timeout (seconds) for `POST /v1/chat/completions`. |
| `AI_PRIORITY` | `omniroute,groq,cohere,huggingface,ollama` | Comma-ordered fallback chain. Put preferred provider first. |

### OmniRoute model IDs

`auto` and its variants are **virtual combos** built from your connected providers (no manual combo needed):

| Model | Optimizes for |
|---|---|
| `auto` | Balanced (LKGP — sticks to last good provider) |
| `auto/fast` | Lowest latency first |
| `auto/cheap` | Cheapest per token first |
| `auto/smart` | Quality-first + 10% exploration |
| `auto/coding` | Code-generation weights |
| `auto/offline` | Most quota headroom |
| `auto/lkgp` | Explicit last-known-good-provider pinning |
| `auto/chaos` | Fault-injection (resilience testing) |

Or point at a concrete provider model: `cc/claude-opus-4-6`, `openai/gpt-5.5`, `groq/llama-3.3-70b-8192`, etc. List them via:

```bash
curl http://localhost:20128/v1/models -H "Authorization: Bearer $OMNIROUTE_API_KEY"
# or via AI Trader proxy:
curl http://localhost:8000/api/omniroute/models | jq '.data[].id'
```

### Other AI providers (fallback)

If OmniRoute is unreachable, ARTH falls through to direct providers in `AI_PRIORITY` order. Configure them as before:

```
GROQ_API_KEY=...
COHERE_API_KEY=...
HUGGINGFACE_API_KEY=...
```

Leave `OMNIROUTE_*` empty to disable OmniRoute and use direct providers only.

---

## API Routes (new)

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/omniroute/config` | Current gateway config (key masked) |
| `GET` | `/api/omniroute/status` | Probe `GET {base_url}/models` — reachable? model count? |
| `GET` | `/api/omniroute/models` | Passthrough `GET {base_url}/models` listing |
| `POST` | `/api/omniroute/test` | Smoke test `POST {base_url}/chat/completions` with tiny prompt |

Body for `/test` (all optional):
```json
{ "prompt": "Say PONG", "model": "auto" }
```

---

## Frontend

The ARTH Brain dashboard (`/brain`) and ARTH Chat already show `ai_provider` per prediction. When OmniRoute is active you’ll see `omniroute` + the routing trace (from `X-OmniRoute-Decision`) in the reasoning.

To surface gateway status in your UI, add a fetch to `/api/omniroute/status` (see `frontend/src/lib/api.ts`):

```ts
export const api = {
  omniroute: {
    status: () => fetchApi<any>('/api/omniroute/status'),
    models: () => fetchApi<any>('/api/omniroute/models'),
  },
  // ...
};
```

---

## Docker Compose

A ready-to-use compose file is included at the repo root:

```bash
docker compose -f docker-compose.yml -f docker-compose.omniroute.yml up -d
```

It wires `ai-trader-backend` → `omniroute:20128` via the internal `ai-trader` network and auto-sets `OMNIROUTE_BASE_URL=http://omniroute:20128/v1`. See `docker-compose.omniroute.yml` at top level.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `omniroute: Connection refused` in backend logs | OmniRoute not running. Run `omniroute` or `docker run -p 20128:20128 diegosouzapw/omniroute`. Check `GET http://localhost:20128/v1/models` in a browser. |
| `401 Unauthorized` from OmniRoute | Set `OMNIROUTE_API_KEY` to a key from Dashboard → API Manager. Or run gateway with `REQUIRE_API_KEY=false` for keyless dev. |
| `404 model not found` | Wrong `OMNIROUTE_MODEL`. Try `auto`. List models via `GET /api/omniroute/models`. |
| ARTH falling back to `groq` though OmniRoute is set | Check `AI_PRIORITY` — `omniroute` must be first. Verify `GET /api/omniroute/status` shows `"reachable": true`. |
| Timeout after 90s | Some free-tier models are slow. Try `OMNIROUTE_MODEL=auto/fast` or raise `OMNIROUTE_TIMEOUT=120`. |
| CORS / preview host blocked | OmniRoute dashboard sets strict `frame-ancestors`. Not related to AI Trader API — use direct `http://localhost:20128` in browser. |

More help: `/tmp/OmniRoute/docs/guides/TROUBLESHOOTING.md`, Discord `https://discord.gg/U47eFqAXCn`.

---

## Development Notes

- The reference clone at `/tmp/OmniRoute` is **read-only** for implementation guidance — do not modify it. The authoritative provider source is `backend/ai_agent/providers/omniroute_provider.py`.
- `omniroute_provider.py` uses `httpx` (already in `requirements.txt`) + `openai>=1.12.0` (optional; provider works even without it via raw httpx).
- JSON extraction handles three cases: direct `json.loads`, regex-extracted `{...}`, and raw-text fallback.
- The gateway’s `response_format: {type: json_object}` is tried first; if the model rejects it, the provider retries without it.
- Keep the gateway out of Git: `DATA_DIR` / `~/.omniroute` is git-ignored; only `.env.example` documents the vars.

---

## References

- OmniRoute repo: https://github.com/diegosouzapw/OmniRoute
- Quick Start: https://github.com/diegosouzapw/OmniRoute/blob/main/docs/getting-started/QUICK-START.md
- API Reference (Chat Completions: `POST /v1/chat/completions`): https://github.com/diegosouzapw/OmniRoute/blob/main/docs/reference/API_REFERENCE.md
- Free Tiers: https://github.com/diegosouzapw/OmniRoute/blob/main/docs/reference/FREE_TIERS.md
- Auto-Combo routing: https://github.com/diegosouzapw/OmniRoute/blob/main/docs/routing/AUTO-COMBO.md
- Provider Catalog: https://github.com/diegosouzapw/OmniRoute/blob/main/docs/reference/PROVIDER_REFERENCE.md
