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

### 🚀 FASE 1 — Google Ecosystem ⭐ P0 (1-2 sessões)
**Uma autorização cobre tudo:**
- 🔴 Google OAuth base (login + refresh token + multi-conta)
- 🔴 Google Drive Manager (bloco 7)
- 🔴 File Organizer (bloco 8, baseado em Drive)
- 🔴 Gmail Manager (bloco 3)
- 🔴 Email Auto-Responder
- 🔴 Email Attachment Sender
- 🔴 Google Sheets Creator (bloco 4)
- 🔴 Spreadsheet Analyzer
- 🔴 Google Calendar (extensão)
- 🔴 **YouTube API** (upload, metrics, comments)

**UX:** Aba "Integrações" → conectar múltiplas contas Google → dar apelidos.

---

### 🚀 FASE 2 — Meta Ecosystem ⭐ P0 (1 sessão)
- 🔴 Meta OAuth base
- 🔴 Instagram Publisher (posts, reels, stories, carrossel)
- 🔴 Instagram DM Auto-Responder
- 🔴 Instagram Comment Responder
- 🔴 WhatsApp Business API (responder com IA)
- 🔴 Facebook (opcional, baixa prioridade)

---

### 🚀 FASE 3 — TikTok + Social Unified 🔹 P1 (1 sessão)
- 🔴 TikTok API
- 🔴 Social Media Publisher unificado (posta em múltiplas redes com 1 comando)
- 🔴 Social Media Manager dashboard

---

### 🚀 FASE 4 — Admin Pro + Controle 🔹 P1 (1-2 sessões)
#### Dashboard Admin
- 🔴 Admin Dashboard completo (usuários online, sessões, CPU/RAM, alertas)
- 🔴 User Manager (CRUD avançado, bloquear/desbloquear)
- 🔴 Module Access Control (liberar/ocultar módulo por usuário)
- 🔴 Usage Metering (msgs, uploads, tempo)
- 🔴 Quota Controller (limites por usuário)
- 🔴 Audit Log (login, mudanças de permissão)
- 🔴 Session Monitor (quem tá online agora)
- 🔴 Password Recovery (email de reset)

---

### 🚀 FASE 5 — Workflow & Automação Avançada 🔹 P1 (1 sessão)
- 🔴 Workflow Engine (encadear tarefas multi-passo)
- 🔴 Intent Router avançado (comando natural executa módulo)
- 🔴 Chat Command Executor ("Crie uma mentoria" → executa)
- 🔴 System Watchdog (reiniciar containers com falha)
- 🔴 Web Automation Engine (Playwright na VPS: preencher forms, baixar arquivos)

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

Começar **Fase 1 (Google OAuth)** por:
1. Cobre 10 skills de uma vez com uma autorização
2. Infra-estrutura OAuth base serve pra Fase 2 também
3. Desbloqueou Gmail/Drive/Sheets que são uso diário alto
