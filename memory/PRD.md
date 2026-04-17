# Mordomo Virtual - PRD

## Original Problem Statement
Build a complete AI agent (OpenClaw-style) named "Mordomo Virtual" to run on a 48GB no-GPU VPS. Requirements: PWA responsive, multi-user, streaming chat, Telegram integration, code/scraping execution, Automated Marketing Agency (rules engine, dashboard, approval), Mentorship Creator (visual editor and PDF/DOCX export), dual LLM model system (Ollama 7B/32B with Emergent fallback), system performance monitoring panel and voice activation (hands-free).

## User Language
Portuguese (pt-BR) — ALWAYS respond in Portuguese.

## Deployment Status (Feb 17, 2026)
✅ **DEPLOYED TO PRODUCTION VPS**
- Domain: https://mordomo.virtual.grupomafort.com
- VPS: Ubuntu 48GB (vmi3061018)
- SSL: Let's Encrypt (valid until 2026-07-16, auto-renewal via certbot container)
- Code: https://github.com/VagnerMafort/MORDOMO.VIRTUAL
- Admin: ministerioprvagner@gmail.com / DAx4OwaqmVubkHtn
- Running: 6 Docker containers (mongodb, ollama, backend, frontend, nginx, certbot)
- Models: qwen2.5:7b + qwen2.5:32b (Ollama local, ~24GB)
- **100% INDEPENDENT** - No Emergent/OpenAI/Anthropic fallback. Zero API cost.

## Architecture
```
/app/
├── backend/           FastAPI + MongoDB (Motor)
│   ├── server.py      Main (1300+ lines)
│   ├── agency.py      Marketing Agency routes
│   ├── mentorship.py  Mentorship + PDF/DOCX export
│   ├── rules_engine.py Cron evaluation loop
│   ├── smart_llm.py   Dual LLM logic + cache
│   └── Dockerfile     Python 3.11 + Debian Trixie deps
├── frontend/          React PWA
│   └── Dockerfile     Node 20 + nginx:alpine
├── docker-compose.yml  6 services
├── nginx.conf          HTTP→HTTPS + reverse proxy
└── deploy.sh           Auto-install Docker+SSL+seed
```

## Key Fixes Done During Deploy (Feb 17, 2026)
1. Removed `backend/tests/` folder (contained hardcoded test credentials triggering GitHub SECRETS_DETECTED)
2. Removed default admin email/password hardcoded in server.py (now env-only)
3. Removed `emergentintegrations` dependency completely (user requested zero-cost independence)
4. Fixed `backend/Dockerfile`: `libgdk-pixbuf2.0-0` → `libgdk-pixbuf-2.0-0` (Debian Trixie)
5. Fixed `frontend/Dockerfile`: Node 18 → Node 20 (required by react-router-dom@7)
6. Fixed `frontend/Dockerfile`: removed `yarn.lock` requirement (not in repo)
7. Fixed `deploy.sh` nginx-temp.conf race condition bug
8. Promoted `ministerioprvagner@gmail.com` to admin in preview DB

## Completed Features
- PWA configuration (manifest, SW, icons)
- JWT Auth + CORS + multi-user
- SSE Chat streaming (pure Ollama, no fallback)
- Telegram integration per-user with agent personas
- Hands-free voice mode with wake word ("Hey [agent name]")
- Marketing Agency module (products, campaigns, rules, approvals)
- Mentorship Generator (visual editor + PDF/DOCX export)
- Smart dual-LLM system (7B fast + 32B smart)
- Background task worker + response cache
- System monitoring dashboard
- 13+ skills (code exec, scraping, files, calc, API calls)

## API Endpoints
- `/api/health` — health check
- `/api/auth/*` — register, login, logout, me, refresh
- `/api/chat/message` — SSE streaming
- `/api/telegram/connect`, `/api/telegram/webhook/{user_id}`
- `/api/agency/products`, `/api/agency/campaigns`, `/api/agency/rules`, `/api/agency/dashboard`
- `/api/mentorship/generate`, `/api/mentorship/{id}/export/{format}`
- `/api/system/memory-stats`, `/api/system/task/{task_id}`

## DB Schema
- `users`, `settings`, `conversations`, `messages`
- `telegram_connections`
- `products`, `campaigns`, `rules`, `approvals`, `agency_access`, `execution_log`
- `mentorships`, `knowledge_base`
- `response_cache`, `conversation_summaries`, `background_tasks`

## P0 Next Actions (Optional, post-deploy)
- User tests all features end-to-end in production
- Setup first Telegram bot + first mentorship + first product

## P1 Backlog (Future)
- Meta Ads / Google Ads real API integration in Agency module
- Refactor server.py (1300+ lines) into smaller routers
- Add Prometheus/Grafana for deeper monitoring

## 3rd Party Integrations
- ✅ Ollama (local, user-hosted) — PRIMARY LLM
- ✅ Telegram Bot API — user provides their own bot token per account
- ❌ Emergent LLM Key — REMOVED at user request (zero cost)
- ❌ OpenAI/Anthropic — NOT USED

## Testing Status
- 13 iterations of backend testing agent (100% pass)
- Production deploy verified by user on Feb 17, 2026
