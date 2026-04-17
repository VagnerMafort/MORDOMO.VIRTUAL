# Mordomo Virtual - PRD

## Original Problem Statement
AI agent multi-user "Mordomo Virtual" para VPS de 48GB sem GPU. Requisitos: PWA responsivo, chat streaming, Telegram, agência de marketing automatizada, mentorias com export, dual LLM (Ollama 7B/32B), monitoramento do sistema, voz hands-free 100% local, painel administrativo completo. Sem dependência da plataforma Emergent — tudo roda na VPS do cliente com custo zero.

## User Language
Portuguese (pt-BR) — SEMPRE responder em português.

## Deployment Status (Feb 17-18, 2026)
✅ **PRODUÇÃO NA VPS**: https://mordomo.virtual.grupomafort.com
- VPS Ubuntu 48GB (vmi3061018), SSL Let's Encrypt auto-renovável
- 6 containers Docker: mongodb, ollama, backend, frontend, nginx, certbot
- Ollama com qwen2.5:7b + qwen2.5:32b (~24GB)
- Admin: ministerioprvagner@gmail.com / admin123
- Repositório: https://github.com/VagnerMafort/MORDOMO.VIRTUAL
- **100% INDEPENDENTE**: sem Emergent/OpenAI/Anthropic. Custo zero API.

## Architecture
```
/app/
├── backend/
│   ├── server.py        Auth, chat, skills, telegram, agents, notes, tasks
│   ├── admin.py         FASE 4 — user mgmt, modules, quota, audit, sessions
│   ├── agency.py        Marketing agency
│   ├── mentorship.py    Mentoria + PDF/DOCX export
│   ├── rules_engine.py  Cron loop
│   ├── smart_llm.py     Dual LLM + cache
│   ├── voice.py         STT Whisper + TTS Piper (100% local)
│   └── web_search.py    DuckDuckGo + Brave fallback
├── frontend/src/
│   ├── pages/           LoginPage (+forgot/reset), ChatPage
│   └── components/
│       ├── AdminPanel.js (NOVO FASE 4) — 7 abas admin
│       ├── Sidebar.js   (filtra por allowed_modules)
│       └── ...          (Agency, Mentorship, Monitor, etc.)
├── docker-compose.yml
└── deploy.sh
```

## Implemented Features (consolidated)
### Core
- PWA (manifest, SW, icons), JWT auth + CORS multi-user
- SSE Chat streaming via Ollama local (sem fallback)
- Telegram Bot integration per-user
- Hands-free voice 100% local (Whisper large-v3-turbo + Piper pt_BR-faber)
- Marketing Agency (products, campaigns, rules, approvals)
- Mentorship Generator (visual editor + PDF/DOCX export)
- Smart dual-LLM (7B fast + 32B smart)
- Background task worker + response cache
- System monitoring dashboard
- 14 skills (code, scraping, web_search, summarizer, files, calc, API, system, datetime, browser, cron, email)

### FASE 4 — Painel Admin Pro (Feb 18, 2026) ✅
- **User Manager**: CRUD completo, block/unblock, promote to admin
- **Password Recovery**: admin reseta direto + self-service com token
- **Module Access Control**: 14 módulos granulares por usuário
- **Quota Controller**: limites diários de mensagens/tasks/uploads
- **Audit Log**: todas ações críticas registradas
- **Session Monitor**: sessões online em tempo real (IP + UA + last_seen)
- **Dashboard Admin**: KPIs + RAM/Disk
- **Frontend**: 7 abas (Dashboard, Usuários, Módulos, Uso, Logs, Sessões, Sistema)

### FASE 1 — Google Ecosystem (Feb 18, 2026) ✅
- **OAuth2**: admin configura Client ID/Secret no painel (Fernet encrypted), usuário conecta via botão
- **Auto-refresh** de access_token, state JWT assinado, PKCE, `access_type=offline`
- **5 skills** integradas no chat + endpoints REST:
  - Gmail: list/read/send
  - Drive: list/create_folder/upload/rename/trash
  - Sheets: create (com dados)/read/write/append
  - Calendar: list/create (+ attendees)
  - YouTube: my_videos/search/comments/upload
- **Frontend**: aba Integrações no AdminPanel + IntegrationsPanel para usuário
- Callback handler detecta `?google=connected` e mostra toast

### FASE 5 — Workflow Engine + Playwright (Feb 18, 2026) ✅
- **Workflow Engine**: CRUD + execução + histórico + variáveis entre passos
- **21 skills** no total (14 base + 5 Google + workflow + social_publish + browser_automation)
- **Playwright Chromium**: skill `browser_automation` com 9 actions (goto, fill, click, press, wait, wait_for, extract, screenshot, scroll)
- **Chat Command Executor**: LLM roteia qualquer pedido natural pras skills via SYSTEM_PROMPT
- Frontend: painel "Fluxos de Trabalho" com editor visual + aba Histórico
- Dockerfile com Chromium + deps instalados automaticamente

### FASE 3 — Social Unified PARCIAL (Feb 18, 2026) ✅🟡
- Endpoint `/api/social/publish` distribui conteúdo pra múltiplas redes
- Skill `[SKILL:social_publish]` no chat
- YouTube funcional hoje (via Google OAuth da FASE 1)
- Frontend: modal "Publicar em Redes" com status por rede
- 🟡 TikTok/Instagram/Facebook/WhatsApp como placeholders — depende de FASE 2 (Meta) e TikTok for Developers

## DB Schema
- `users` (+allowed_modules, blocked, quota, login_count, last_login)
- `settings`, `conversations`, `messages`
- `telegram_connections`, `telegram_messages`
- `products`, `campaigns`, `rules`, `approvals`, `agency_access`
- `mentorships`, `knowledge_base`
- `agents`, `agent_messages`, `execution_log`
- `response_cache`, `conversation_summaries`, `background_tasks`
- **NOVOS (FASE 4)**: `audit_log`, `sessions`, `usage_metering`, `password_resets`

## Key API Endpoints
### Admin (require admin)
- `GET /api/admin/dashboard` — KPIs + system
- `GET/POST/PUT/DELETE /api/admin/users[/id]`
- `POST /api/admin/users/{id}/reset-password`
- `PUT /api/admin/users/{id}/quota`
- `GET /api/admin/modules` (14 módulos)
- `GET /api/admin/usage?days=N`
- `GET /api/admin/audit?limit=N`
- `GET /api/admin/sessions` (online/recent)
- `GET /api/admin/password-resets` (tokens ativos)

### Public Auth
- `POST /api/auth/forgot-password` — gera token (sempre 200)
- `POST /api/auth/reset-password` — reseta com token

## Testing Status
- 14 iterações de testing agent
- **FASE 4**: 30/30 backend PASS, frontend 100% PASS, 0 bugs

## 3rd Party Integrations
- ✅ Ollama (local) — PRIMARY LLM
- ✅ Telegram Bot API — per-user
- ✅ DuckDuckGo + Brave Search (free, sem key)
- ✅ Faster-Whisper + Piper TTS (local)
- ❌ Emergent/OpenAI/Anthropic — ZERO custo
