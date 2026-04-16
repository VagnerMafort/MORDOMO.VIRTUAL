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

### 2026-04-16 - Iteration 7 (Mordomo Virtual + Agência de Marketing + Visual Futurista)
- Renomeado para "Mordomo Virtual"
- 24 agentes de marketing da arquitetura JAMES AGENCY implementados (ORION, DASH, MIDAS, NOVA, HUNTER, etc.)
- 8 squads: Core & Governance, Data & Diagnostics, Traffic, Funnel & Sales, Creative, Pages & Conversion, Research & Product, Reporting & Finance
- Hands-free redesenhado: fundo azul escuro (#020810), espectro de luz circular com 3 anéis que giram e pulsam com a voz via Web Audio API
- AgentManager com busca e organização por squads

### 2026-04-16 - Iteration 8 (Marketing Agency Panel)
- Painel da Agência ({nome} Agency) com controle de acesso (admin-only + concessão manual)
- Sistema de Produtos (unidade central): CRUD com métricas (CTR, CPC, CPA, ROAS, conversões, gasto, receita)
- Campanhas vinculadas a produtos com métricas por plataforma
- Motor de Regras: condições (métrica + operador + valor) → ações (pausar, escalar, alertar, relatório) + aprovação humana opcional
- Fila de Aprovação: pendente/aprovado/rejeitado com log de auditoria
- Relatórios: nível agência e nível produto
- Controle de Acesso: admin concede/revoga acesso por e-mail
- Módulo separado (agency.py) para manutenibilidade

### 2026-04-16 - Iteration 9 (Cron + Dashboard + Integrations + Inter-Agent)
- Renomeado NovaClaw → "Mordomo Virtual" em todo o sistema (nome dinâmico do usuário substitui)
- Cron job: Rules Engine roda a cada 60s avaliando regras ativas automaticamente
- Dashboard com Recharts: gráficos de barras (gasto/receita por produto), pizza (distribuição), cards de métricas
- Integração de plataformas pelo painel: Meta Ads, Google Ads, TikTok (cada usuário conecta suas próprias contas)
- Comunicação entre agentes: sistema de mensagens inter-agent (from_agent → to_agent, payload, status)
- Histórico de métricas para gráficos temporais
- Sincronização de métricas das plataformas conectadas

### 2026-04-16 - Iteration 10 (Dashboard Temporal + Execução Real)
- Dashboard temporal: gráficos AreaChart (Gasto vs Receita com gradientes) e LineChart (ROAS, CPA, CTR) ao longo do tempo
- Seletor de produto no timeline para alternar entre produtos
- Execução real de ações aprovadas: quando aprovação é aceita, executa na plataforma conectada (Meta Ads API, Google Ads, TikTok)
- Log de execuções com status (sucesso/falha), detalhes, resultado da plataforma
- Auto-record de métricas: cron grava snapshots a cada 5 minutos para alimentar os gráficos
- PUT /products/{id}/metrics auto-cria snapshot no histórico
- 5 abas no Dashboard: Visão Geral, Timeline, Execuções, Integrações, Agentes

### 2026-04-16 - Iteration 11 (Criador de Mentorias)
- Sistema completo de criação de mentorias via IA
- Upload de conhecimento (txt, md, csv) + campo de texto livre
- Geração automática: nome, promessa, módulos (6+), aulas (4+/módulo), exercícios, bônus, metodologia, FAQ, copy de vendas, precificação
- CRUD de mentorias e base de conhecimento
- Agentes MOIRA e NOVA atualizados com capabilities de mentoria
- Painel dedicado com abas "Criar Mentoria" e "Mentorias"
- Botão "Criar Mentoria" no sidebar

### 2026-04-16 - Iteration 12 (Editor Visual + Export PDF/DOCX)
- Editor visual de módulos: cards expansíveis com módulos e aulas, edição inline, adicionar/remover módulos e aulas
- Parse automático: conteúdo gerado pela IA convertido em módulos estruturados (6+ módulos, 4-6 aulas cada)
- Export PDF: WeasyPrint gera PDF profissional A4 com design, borda amarela em módulos, capa
- Export DOCX: python-docx gera Word com headings, bullets, quebra de página por módulo
- Botões PDF/DOCX no editor para download direto

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
