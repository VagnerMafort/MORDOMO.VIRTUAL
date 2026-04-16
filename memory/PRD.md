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
- [x] PWA manifest for mobile install
- [x] Portuguese BR interface
- [x] Dark theme (Swiss high-contrast)

## What's Been Implemented (2026-04-16)
### Backend
- JWT auth (register, login, logout, me, refresh, brute force protection)
- Conversations CRUD with per-user isolation
- Messages with SSE streaming
- 10 agent skills (web scraper, calculator, code runner, system info, datetime, file manager, browser automation, cron jobs, email manager, API caller)
- Settings per-user (Ollama URL, model, TTS config)
- Health endpoint

### Frontend
- Login/Register page with NovaClaw branding
- ChatGPT-like layout (sidebar + chat area)
- Conversation management (create, rename, delete)
- Message display with markdown formatting
- SSE streaming with typing indicator
- Voice mode (Web Speech API STT)
- Settings panel (Ollama config)
- Skills dashboard with toggle functionality
- Responsive mobile layout (hamburger menu)
- PWA manifest

## Prioritized Backlog

### P0 (Critical)
- None (core MVP complete)

### P1 (Important)
- Hands-free TTS auto-read responses (Web Speech Synthesis)
- Conversation search
- Message copy/delete
- Export conversations

### P2 (Nice to have)
- Telegram integration
- WhatsApp integration
- Multi-model support in settings
- Browser automation execution (Playwright)
- Cron job scheduler UI
- Email integration (IMAP/SMTP)
- File upload/attachment support
- User admin panel

## Next Tasks
1. Add TTS auto-read for voice mode responses
2. Add conversation search in sidebar
3. Implement VPS deployment guide with Docker
4. Add Telegram bot integration
5. Implement actual browser automation skill with Playwright
