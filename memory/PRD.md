# Kaelum.AI - PRD

## Original Problem Statement
AI agent multi-user "Kaelum.AI" (renomeado de "Mordomo Virtual" em Feb 18, 2026) para VPS de 48GB sem GPU. Requisitos: PWA responsivo, chat streaming, Telegram, agência de marketing automatizada, mentorias com export, dual LLM (Ollama 7B/32B), monitoramento do sistema, voz hands-free 100% local, painel administrativo completo. Sem dependência da plataforma Emergent — tudo roda na VPS do cliente com custo zero.

## Brand & UI (Feb 18, 2026)
- **Nome**: Kaelum.AI
- **Paleta**: `#0a0a0a` (preto), `#1c204f` (azul escuro), `#2d3694` (azul royal — accent), `#a9d1ec` (azul claro — text secondary), `#ffffff` (branco)
- **Logos**: `/frontend/public/kaelum-logo-horizontal.png`, `kaelum-logo-text.png`, `kaelum-icon.png`, `kaelum-favicon.png`
- **Temas**: Light + Dark (toggle no Sidebar/LoginPage), persistido em `localStorage.kaelum_theme`. CSS vars via `[data-theme]` attribute.

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

### FASE 3 — TikTok OAuth + Content Posting API (Apr 18, 2026) ✅
- **OAuth v2**: admin configura Client Key/Secret no painel (Fernet encrypted), usuário conecta via botão "Conectar com TikTok"
- **Scopes**: user.info.basic, video.upload, video.publish
- **Auto-refresh** de access_token (24h) com refresh_token (365d) armazenado criptografado
- **Content Posting API**: publicação via PULL_FROM_URL (TikTok baixa vídeo de URL pública)
- REST: `/api/admin/integrations/tiktok` (CRUD config), `/integrations/tiktok/start|status|disconnect`, `/oauth/tiktok/callback`
- Integrado no `social_publisher.py` — `/api/social/publish` agora aceita `networks=["tiktok"]` quando `media_url` for fornecido
- Frontend: card TikTok em Minhas Integrações (rosa #ff0050) + aba config admin com redirect URI copiável
- Mobile UI bug fix: `WakeWordListener` não sobrepõe mais o input em telas <lg; ChatPage adota `h-dvh`

### FASE 2 — Meta Ecosystem (Feb 18, 2026) ✅
- Meta OAuth v21.0 (admin config + user connect, long-lived 60d, Fernet encryption)
- 3 skills novas: `[SKILL:instagram]`, `[SKILL:facebook]`, `[SKILL:whatsapp]`
- REST: `/api/meta/instagram/publish`, `/meta/facebook/post`, `/meta/whatsapp/send`, `/meta/dm-rules` CRUD
- Social Unified agora publica em Facebook automaticamente
- Frontend: card Meta em Minhas Integrações (Facebook blue button) + aba config admin
- 27 skills total no catálogo

### FASE 6 — Voice Profile + Watchdog (Feb 18, 2026) ✅
- 4 vozes Piper pt_BR (faber/edresson/cadu/jeff)
- `/api/voice/voices` + `/speak?voice=X&speed=1.5`
- Settings salva `voice_profile` e `voice_speed` por usuário
- VoiceProfileSelector no SettingsPanel com dropdown + slider + botão testar
- System Watchdog monitora Mongo/Ollama/Disk/RAM a cada 60s → `system_alerts`
- Aba "Alertas" nova no AdminPanel

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
