# NovaClaw - AI Agent PWA (OpenClaw-like)

## Original Problem Statement
Build an AI agent application similar to OpenClaw - a personal virtual butler/assistant that executes online tasks. Requirements: ChatGPT-like interface, PWA responsive for mobile, multi-user support, conversation management, hands-free voice mode (STT + TTS), agent skills system, Portuguese BR interface. Connect to local LLM via Ollama (for VPS with 48GB RAM, no GPU).

## Architecture
- **Backend**: FastAPI + MongoDB (Motor async driver)
- **Frontend**: React PWA with Tailwind CSS
- **Auth**: JWT Bearer token (localStorage)
- **LLM**: Ollama API (primary) + Emergent LLM key fallback (gpt-4o-mini)
- **Voice**: Web Speech API (browser native, free)
- **Database**: MongoDB (novaclaw_db)

## User Personas
- **Admin**: Full access to all features, manages system settings
- **User**: Chat with AI, manage own conversations, configure personal settings

## Core Requirements (Static)
- [x] Multi-user authentication (register/login/logout)
- [x] ChatGPT-like chat interface with sidebar
- [x] Conversation management (create/rename/delete)
- [x] Message streaming via SSE
- [x] LLM integration (Ollama + fallback)
- [x] Agent skills system (10 skills)
- [x] Settings panel (Ollama URL, model, TTS)
- [x] Voice input (Web Speech API STT)
- [x] TTS auto-read responses toggle
- [x] PWA manifest + service worker + icons
- [x] Portuguese BR interface
- [x] Dark theme (Swiss high-contrast)
- [x] Credentials/API keys management panel
- [x] PWA install instructions (Android/iOS/Desktop)

## What's Been Implemented

### 2026-04-16 - Iteration 1 (MVP)
- JWT auth (register, login, logout, me, refresh, brute force protection)
- Conversations CRUD with per-user isolation
- Messages with SSE streaming
- 10 agent skills
- Settings per-user (Ollama URL, model, TTS config)
- ChatGPT-like layout (sidebar + chat area)
- Voice input mode (Web Speech API STT)
- Responsive mobile layout (hamburger menu)

### 2026-04-16 - Iteration 2 (PWA + Credentials)
- Credentials management panel (CRUD) - store Telegram tokens, API keys, SMTP, etc.
- Full PWA support: manifest.json, service worker (sw.js), app icons (192/512), apple-touch-icon
- PWA install instructions (Android, iPhone, Desktop)
- TTS auto-read toggle on chat header
- Safe-area padding for PWA standalone mode
- Deploy guide for VPS with Docker/Ollama

### 2026-04-16 - Iteration 3 (Telegram + UX)
- Telegram bot integration per user (connect/disconnect/webhook)
- Each user can connect their own Telegram bot via @BotFather token
- Webhook receives Telegram messages and responds via same LLM pipeline
- Back buttons added to Settings and Skills modals
- Settings panel now has 4 tabs: Geral, Telegram, Credenciais, Instalar

### 2026-04-16 - Iteration 4 (Skills Avançados + Agentes)
- 7 skills avançados funcionais: code_executor (Python/JS/Bash), code_generator, web_scraper (CSS selectors), url_summarizer, file_manager (CRUD), notes_tasks, api_caller (GET/POST/PUT/DELETE)
- Sistema de Agentes: 4 templates prontos (Dev Expert, Pesquisador Web, Analista de Dados, Automatizador) + criação de agentes personalizados
- Conversas vinculadas a agentes usam system prompt específico do agente
- Notes e Tasks API (CRUD completo)
- 13 skills totais no dashboard (10 disponíveis + 3 requerem VPS)

### 2026-04-16 - Iteration 5 (Hands-Free + Personalidade)
- Modo Mãos Livres completo: tela fullscreen, reconhecimento de voz contínuo, envio automático, TTS auto-leitura, loop de conversa
- Personalização do agente principal: campos de nome e personalidade nas configurações
- Botão headphones no desktop (FAB) e mobile (header)
- Conversas de voz com prefixo [Voz] no título

### 2026-04-16 - Iteration 6 (Wake Word Activation)
- Ativação por voz "Hey {nome do agente}" - escuta passiva contínua
- Suporte a variações: "hey", "ei", "oi", "hei" + nome do agente
- Indicador visual no canto inferior esquerdo (bolinha verde pulsando)
- Terminal info box explicativo quando ativado
- Configuração wake_word_enabled persistida no backend

## Prioritized Backlog

### P0 (Critical)
- None (core features complete)

### P1 (Important)
- Telegram bot integration (use stored credentials)
- Conversation search in sidebar
- Message copy/delete
- Export conversations

### P2 (Nice to have)
- WhatsApp integration
- Multi-model support dropdown
- Browser automation execution (Playwright)
- Cron job scheduler UI
- Email integration (IMAP/SMTP)
- File upload/attachment support
- User admin panel

## Next Tasks
1. Integrate Telegram bot using stored credentials
2. Add conversation search in sidebar
3. Create Dockerfile for easy VPS deployment
4. Implement actual browser automation skill with Playwright
5. Add message actions (copy, delete, regenerate)
