# 🗺️ ROADMAP MORDOMO VIRTUAL

Status: Feb 2026 · Deploy em produção na VPS `mordomo.virtual.grupomafort.com`

---

## 🎯 LEGENDA

- ✅ **Pronto** — implementado e funcionando
- 🟡 **Parcial** — base existe, precisa finalizar
- 🔴 **Não iniciado**
- ⭐ **P0** (crítico/próximo)
- 🔹 **P1** (importante, fase seguinte)
- 💠 **P2** (nice-to-have)

---

## ✅ JÁ PRONTO NO MORDOMO (o que você já tem)

### Bloco 1 — Núcleo
- ✅ Chat Inteligente (streaming Ollama Qwen local)
- ✅ Rules Engine (agency/rules_engine.py)
- 🟡 Intent Router (via skills auto-detect)
- 🟡 Agent-to-Agent (Agent Manager já existe)

### Bloco 7 — Voz
- ✅ Voice Recognition (Whisper large-v3-turbo local)
- ✅ Text-to-Speech (Piper pt_BR-faber-medium)
- ✅ Hands-Free Controller (funcional)
- 🟡 Voice Profile Manager (1 voz hoje, precisa UI de seleção)

### Bloco 10 — Monitoramento
- ✅ System Monitor (MonitorPanel)
- ✅ Task Monitor (background_tasks)
- ✅ Error Logger (logs supervisor+docker)

### Bloco 12 — Agência
- ✅ Campaign Automation
- ✅ Task Automation
- ✅ Approval System

### Bloco 13 — Mentorias
- ✅ Mentorship Creator
- ✅ Mentorship Editor
- ✅ Mentorship Exporter (PDF/DOCX)

### Bloco 15 — Background Tasks
- ✅ Background Task Engine

### Bloco 16 — Segurança
- ✅ Authentication JWT
- ✅ Permission Validator (role admin/user)

### Bloco 17 — Multiagentes
- ✅ Agent Manager
- 🟡 Agent Communication (parcial)

### Bloco 18 — Integrações (parcial)
- ✅ Telegram API
- 🟡 Ollama dual LLM

### Skills existentes (hoje)
- ✅ Code Executor
- ✅ Web Scraper  
- ✅ URL Summarizer
- ✅ File Manager (local)
- ✅ Calculator
- ✅ API Caller
- ✅ System Info
- ✅ DateTime Info
- ✅ **Web Search (recém-adicionado — DuckDuckGo + Brave fallback)**

---

## 🔴 A CONSTRUIR — FASES PROPOSTAS

### 🚀 FASE 1 — Google Ecosystem ✅ CONCLUÍDO (Feb 18, 2026)
**Uma autorização cobre tudo (OAuth2 + refresh_token + auto-refresh):**
- ✅ Google OAuth2 base (login + refresh token + token encryption Fernet)
- ✅ Admin configura Client ID/Secret via Painel Admin → aba Integrações (não precisa de .env)
- ✅ Usuário conecta conta Google via botão "Minhas Integrações"
- ✅ Gmail (list, read, send via API REST + chat skill)
- ✅ Google Drive (list, create_folder, upload, rename, trash)
- ✅ Google Sheets (create com dados iniciais, read range, write/append)
- ✅ Google Calendar (list próximos eventos, create evento com attendees)
- ✅ YouTube (my_videos + channel stats, search, comments, upload)
- ✅ Integração no chat: `[SKILL:gmail]` `[SKILL:drive]` `[SKILL:sheets]` `[SKILL:calendar]` `[SKILL:youtube]`
- ✅ Backend: 19 skills registradas (14 antigas + 5 Google)
- 🔴 File Organizer inteligente (bloco 8) — próxima iteração
- 🔴 Email Auto-Responder com regras — próxima iteração

**Pós-deploy VPS**: usuário cola Client ID/Secret no Painel Admin → conecta sua conta → todas 5 APIs operacionais.

---

### 🚀 FASE 2 — Meta Ecosystem ⭐ P0 (1 sessão)
- 🔴 Meta OAuth base
- 🔴 Instagram Publisher (posts, reels, stories, carrossel)
- 🔴 Instagram DM Auto-Responder
- 🔴 Instagram Comment Responder
- 🔴 WhatsApp Business API (responder com IA)
- 🔴 Facebook (opcional, baixa prioridade)

---

### ✅ FASE 3 — TikTok + Social Unified (PARCIAL — Feb 18, 2026)
- 🟡 TikTok API — **pulado** por escolha do usuário (requer aprovação TikTok for Developers)
- ✅ Social Media Publisher unificado (`/api/social/publish` + skill `[SKILL:social_publish]`)
- ✅ YouTube conector completo via Google OAuth
- ✅ Frontend: modal "Publicar em Redes" (grid 5 redes, upload, campos, resultados por rede)
- 🔴 Social Media Manager dashboard (deferido)

---

### 🚀 FASE 4 — Admin Pro + Controle ✅ CONCLUÍDO (Feb 18, 2026)
#### Dashboard Admin
- ✅ Admin Dashboard (usuários online, CPU/RAM, alertas)
- ✅ User Manager (CRUD + bloquear/desbloquear + promover admin)
- ✅ Module Access Control (14 módulos granulares por usuário)
- ✅ Usage Metering (msgs, tasks, uploads por dia)
- ✅ Quota Controller (limites diários)
- ✅ Audit Log (login, CRUD users, quota, password resets)
- ✅ Session Monitor (online em tempo real — IP + UA + last_seen)
- ✅ Password Recovery (admin-driven + self-service com token)
- ✅ Frontend: 7 abas (Dashboard, Usuários, Módulos, Uso, Logs, Sessões, Sistema)
- ✅ Testing agent: 30/30 backend PASS + frontend 100%

---

### ✅ FASE 5 — Workflow & Automação Avançada (Feb 18, 2026)
- ✅ Workflow Engine (CRUD, execução, variáveis via `{{var}}`, on_error=stop/continue, histórico)
- ✅ Intent Router/Chat Command Executor (21 skills registradas, LLM aciona automaticamente)
- ✅ Web Automation Engine (Playwright + Chromium — goto/fill/click/extract/screenshot/scroll)
- ✅ Dockerfile backend com Playwright + deps do Chromium
- ✅ Frontend: painel "Fluxos de Trabalho" com editor visual + histórico
- ✅ Testing agent: 29/29 backend PASS + frontend 100%
- 🔴 System Watchdog (reiniciar containers com falha) — deferido

---

### 🚀 FASE 6 — Polimento & Segurança 💠 P2 (1 sessão)
- 🔴 Safe Self-Modification (UI pra ajustar voz/configs sem mexer no core)
- 🔴 Voice Profile Manager (seletor de voz M/F, velocidade, tom na UI)
- 🔴 Messaging Hub unificado (Telegram + WhatsApp + Instagram DM numa só inbox)

---

## 📊 ESTIMATIVA DE ESFORÇO

| Fase | Skills | Sessões |
|---|---|---|
| 1 (Google) | 10 | 1-2 |
| 2 (Meta) | 6 | 1 |
| 3 (TikTok+Social) | 3 | 1 |
| 4 (Admin) | 8 | 1-2 |
| 5 (Workflow) | 5 | 1 |
| 6 (Polimento) | 4 | 1 |
| **Total** | **36 skills** | **6-8 sessões** |

---

## 🔑 CREDENCIAIS NECESSÁRIAS (usuário provê)

### Fase 1 (Google)
- Google Cloud Console → novo projeto
- Ativar APIs: Drive, Gmail, Sheets, Calendar, YouTube Data v3
- OAuth 2.0 Client ID (Web Application)
- Redirect URI: `https://mordomo.virtual.grupomafort.com/api/oauth/google/callback`

### Fase 2 (Meta)
- Meta for Developers → criar app
- Permissões: `instagram_basic`, `instagram_content_publish`, `pages_messaging`, `whatsapp_business_messaging`
- App ID + Secret
- Redirect URI: `https://mordomo.virtual.grupomafort.com/api/oauth/meta/callback`
- Contas IG devem ser **Business** ou **Creator**

### Fase 3 (TikTok)
- TikTok for Developers → Content Posting API
- Business Account necessária

---

## 🎯 PRÓXIMO PASSO IMEDIATO

**FASE 1 (Google OAuth)** — ✅ FASE 4 concluída. Agora partir para Google Ecosystem:
1. Cobre 10 skills de uma vez com uma autorização
2. Infra-estrutura OAuth base serve pra Fase 2 também
3. Desbloqueia Gmail/Drive/Sheets que são uso diário alto
4. Controle por usuário já disponível via Admin → Módulos
