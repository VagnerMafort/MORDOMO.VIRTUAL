# 📘 MANUAL COMPLETO — JAMES AGENCY (Kaelum.AI)
### Do primeiro login até a venda autônoma do produto

> Sistema: **Kaelum.AI** rodando na sua VPS · **JAMES AGENCY**: 24 agentes · 14 camadas · 8 squads · Modo Autopilot 24/7
> Documento gerado automaticamente · versão 1.0 · Abril/2026

---

## ÍNDICE

1. [Visão geral do fluxo](#1-visão-geral-do-fluxo)
2. [Pré-requisitos na VPS](#2-pré-requisitos-na-vps)
3. [Primeiro acesso e criação do admin](#3-primeiro-acesso-e-criação-do-admin)
4. [Conectar integrações (credenciais)](#4-conectar-integrações-credenciais)
5. [Criar o Produto](#5-criar-o-produto)
6. [Alimentar o JAMES com métricas (Sensores)](#6-alimentar-o-james-com-métricas-sensores)
7. [Primeiro Tick manual — validar o sistema](#7-primeiro-tick-manual--validar-o-sistema)
8. [Ativar Autopilot 24/7](#8-ativar-autopilot-247)
9. [Inbox de planos e aprovação](#9-inbox-de-planos-e-aprovação)
10. [Relatório executivo ECHO](#10-relatório-executivo-echo)
11. [Fluxo completo end-to-end (exemplo real)](#11-fluxo-completo-end-to-end-exemplo-real)
12. [Os 24 agentes e quando cada um atua](#12-os-24-agentes-e-quando-cada-um-atua)
13. [As 14 camadas operacionais](#13-as-14-camadas-operacionais)
14. [Publicação em redes sociais (YouTube/IG/FB/TikTok)](#14-publicação-em-redes-sociais)
15. [Troubleshooting](#15-troubleshooting)
16. [FAQ](#16-faq)

---

## 1. Visão geral do fluxo

```
┌───────────────────────────────────────────────────────────────────────────┐
│  1. Admin cadastra OAuth apps (Google, Meta, TikTok, Telegram)            │
│  2. Usuário conecta suas contas (1 clique por integração)                 │
│  3. Cadastra Produto (nicho, oferta, público, budget)                     │
│  4. Alimenta métricas (manual ou conectores automáticos)                  │
│  5. Ativa AUTOPILOT 24/7                                                  │
│  6. JAMES roda 24h/dia:                                                   │
│        detecta anomalias → ORION roteia → agente propõe plano             │
│        → guardrails → auto-aprova (risco baixo) ou inbox (risco alto)     │
│        → executa → avalia → aprende → arquiva                             │
│  7. Recebe relatório diário via Telegram                                  │
│  8. Ajusta estratégia com base nos learnings → vendas sobem               │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Pré-requisitos na VPS

### 2.1. Infraestrutura
| Item | Requisito mínimo | Recomendado |
|---|---|---|
| OS | Ubuntu 22.04 | Ubuntu 24.04 |
| RAM | 8 GB | 32 GB (para Ollama 32b) |
| CPU | 4 vCPU | 8 vCPU |
| Disco | 60 GB SSD | 200 GB NVMe |
| GPU | opcional | NVIDIA com CUDA (acelera Ollama 10x+) |
| Docker | 24.x | 27.x |

### 2.2. Software já instalado pelo setup
- Docker + Docker Compose
- MongoDB (via docker-compose)
- Ollama com `qwen2.5:7b` + `qwen2.5:32b` (LLM local, zero custo de API)
- Piper TTS + Whisper STT (voz local)
- Playwright (automação web)
- Chromium headless

### 2.3. Domínio
`https://mordomo.virtual.grupomafort.com` apontando pra IP da VPS com HTTPS (Caddy/Nginx + Let's Encrypt já configurado).

### 2.4. Atualizar o sistema quando há nova versão
```bash
cd /opt/mordomo
git pull
docker compose down
docker compose up -d --build
docker compose logs -f backend | head -n 30   # confirma startup limpo
```

---

## 3. Primeiro acesso e criação do admin

### 3.1. Login inicial
1. Abra `https://mordomo.virtual.grupomafort.com`
2. Registre o primeiro usuário — **ele vira admin automaticamente**
3. Salve email + senha

### 3.2. Painel Admin
- Clique no ícone do escudo (🛡️) no sidebar → **Admin Panel**
- Abas disponíveis:
  - **Dashboard** — visão de saúde do sistema
  - **Usuários** — criar/editar/desativar usuários + definir roles
  - **Módulos** — liga/desliga features por usuário (chat, agency, workflows, social, james, etc.)
  - **Quotas** — limite de uso por usuário (requests/dia, tokens LLM)
  - **Audit Log** — histórico de ações
  - **Monitor de Sessão** — quem está logado agora
  - **Integrações** — cadastra OAuth apps (próximo passo)

---

## 4. Conectar integrações (credenciais)

Todas as credenciais são guardadas **criptografadas no MongoDB** (Fernet AES-128). Nada fica em .env.

### 4.1. Google Ecosystem (Gmail + Drive + Calendar + Sheets + YouTube)

**Admin cria o App no Google Cloud Console:**
1. https://console.cloud.google.com/ → Criar projeto
2. APIs & Services → Enable APIs → ative:
   - Gmail API, Google Drive API, Google Calendar API, Google Sheets API, YouTube Data API v3
3. Credentials → Create Credentials → OAuth client ID → Web Application
4. **Redirect URI**: `https://mordomo.virtual.grupomafort.com/api/oauth/google/callback`
5. Copie **Client ID** e **Client Secret**

**No Kaelum.AI (Admin Panel → Integrações → Google):**
- Cole Client ID + Client Secret
- Marque "Habilitado"
- Salvar

**Usuário conecta a conta dele:**
- Menu → **Minhas Integrações** → Card Google → **Conectar com Google**
- Autoriza os escopos no popup Google
- Volta conectado ✅

### 4.2. Meta Ecosystem (Instagram + Facebook + WhatsApp Business)

**Admin cria o App no Meta for Developers:**
1. https://developers.facebook.com/ → Criar App → Tipo "Business"
2. Adicionar produtos: Instagram Basic Display, Facebook Login for Business, WhatsApp Business
3. Em Settings → Basic: copie **App ID** e **App Secret**
4. Em Facebook Login → Settings → **Valid OAuth Redirect URI**: `https://mordomo.virtual.grupomafort.com/api/oauth/meta/callback`

**No Kaelum.AI (Admin Panel → Integrações → Meta):**
- Cole App ID + App Secret + marque Habilitado → Salvar

**Usuário:**
- Minhas Integrações → Card Meta → **Conectar com Meta**
- Autoriza páginas Facebook + contas Instagram Business + WhatsApp phone_number_id

### 4.3. TikTok for Developers

**Admin cria no TikTok:**
1. https://developers.tiktok.com/ → Create App
2. Adicionar produtos: **Login Kit** + **Content Posting API**
3. Redirect URI: `https://mordomo.virtual.grupomafort.com/api/oauth/tiktok/callback`
4. Copie **Client Key** e **Client Secret**

**No Kaelum.AI (Admin Panel → Integrações → TikTok):**
- Cole Client Key + Client Secret → Salvar

**Usuário:**
- Minhas Integrações → Card TikTok → **Conectar com TikTok**

### 4.4. Telegram (notificações e relatórios diários)

**Criar o bot:**
1. Abra @BotFather no Telegram
2. `/newbot` → escolha nome → receba **HTTP API Token**
3. Fale "oi" para o bot recém-criado pelo menos uma vez
4. Acesse `https://api.telegram.org/bot<TOKEN>/getUpdates` e anote **chat.id**

**No Kaelum.AI (Configurações → Integrações → Telegram):**
- Cole Bot Token + Chat ID → Conectar
- Teste clicando em "Enviar mensagem de teste"

### 4.5. WhatsApp Business (via Meta)
Já vem quando você conecta Meta (seção 4.2). Use a skill `[SKILL:whatsapp]` no chat.

---

## 5. Criar o Produto

Um "Produto" é a unidade central — representa um funil de vendas com suas campanhas, criativos e métricas.

### 5.1. Via UI
1. Sidebar → **JAMES Agency** 🧠
2. Aba **Produtos** → **+ Novo Produto**
3. Preencha:
   - **Nome**: ex. "Curso Marketing Digital"
   - **Nicho**: ex. "empreendedorismo digital"
   - **Público-alvo**: ex. "homens 25-45, RJ/SP, renda R$ 5-15k"
   - **Oferta**: ex. "Curso + mentoria 12 meses por R$ 1.997 em 12x"
   - **Budget diário**: ex. 200 (em R$/dia)
4. **Criar**

### 5.2. Via API (programático)
```bash
curl -X POST "https://mordomo.virtual.grupomafort.com/api/james/products" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Curso Marketing Digital",
    "niche": "empreendedorismo digital",
    "target_audience": "homens 25-45 RJ/SP renda 5-15k",
    "offer": "Curso + mentoria 12 meses R$1997 12x",
    "budget_daily": 200
  }'
```

---

## 6. Alimentar o JAMES com métricas (Sensores)

### 6.1. Opção A — Seed DEMO (pra testar)
Gera 7 dias de dados sintéticos + 1 anomalia:
- No card do produto → botão **Seed Demo**
- 66 pontos de métrica inseridos automaticamente

### 6.2. Opção B — Ingest manual (suas métricas reais do dia)
```bash
curl -X POST "https://mordomo.virtual.grupomafort.com/api/james/products/{PRODUCT_ID}/ingest" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "meta_ads",
    "points": [
      {"metric": "impressions", "value": 12500, "dimension": {"campaign": "camp_awareness_01"}},
      {"metric": "clicks", "value": 430, "dimension": {"campaign": "camp_awareness_01"}},
      {"metric": "ctr", "value": 3.44, "dimension": {"campaign": "camp_awareness_01"}},
      {"metric": "cpa", "value": 14.20, "dimension": {"campaign": "camp_awareness_01"}},
      {"metric": "conversions", "value": 28, "dimension": {"campaign": "camp_awareness_01"}},
      {"metric": "revenue", "value": 892.40, "dimension": {"campaign": "camp_awareness_01"}},
      {"metric": "roas", "value": 3.15, "dimension": {"campaign": "camp_awareness_01"}},
      {"metric": "leads", "value": 45, "dimension": {"campaign": "camp_awareness_01"}}
    ]
  }'
```

**Métricas suportadas**:
`impressions, clicks, ctr, cpa, cpc, conversions, revenue, roas, leads`

**Fontes suportadas** (campo `source`):
`meta_ads, google_ads, ga4, stripe, tiktok_ads, telegram, whatsapp, manual`

### 6.3. Opção C — Conectores automáticos (roadmap)
Na próxima versão: conectores automáticos Meta Ads / Google Ads / GA4 que puxam métricas via OAuth a cada 15-30min. Por enquanto, faça ingest manual ou integre via cron próprio (exemplo abaixo).

**Exemplo de cron bash na VPS puxando Meta Ads Insights:**
```bash
# /etc/cron.d/kaelum-meta-sync (a cada 30min)
*/30 * * * * /usr/local/bin/sync-meta-to-kaelum.sh
```

---

## 7. Primeiro Tick manual — validar o sistema

O "Tick" é 1 ciclo completo das 14 camadas.

### 7.1. Rodar via UI
No card do produto → **Tick** (detecta + planeja, não executa)
Ou **Tick + Run** (detecta + planeja + executa planos validados)

### 7.2. Rodar via API
```bash
curl -X POST "https://mordomo.virtual.grupomafort.com/api/james/products/$PID/tick?evaluate=false" \
  -H "Authorization: Bearer $TOKEN"
```

### 7.3. O que acontece no tick
1. **Camada 3** recomputa baseline (média/mediana/p25/p75 dos últimos 7 dias)
2. **Camada 4** compara métrica atual × baseline → detecta anomalias (drop/spike/fatigue)
3. **Camada 5** prioriza (severidade × peso da métrica × log do delta %)
4. **Camada 6** ORION roteia as top 3 anomalias → agente especialista
5. Agente gera **Plan** com steps executáveis (pause_campaign, shift_budget, rewrite_copy, etc.)
6. **Camada 7** valida objetivo (padrões banidos, blast radius)
7. **Camada 8** aplica guardrails (max 40% budget change, high-risk flag)
8. Plano fica com status `validated` (passou) ou `blocked` (falhou)

### 7.4. Ver os resultados
- **Aba Anomalias**: todas anomalias detectadas com severidade + agente atribuído
- **Aba Planos**: planos gerados com steps + status validated/blocked

---

## 8. Ativar Autopilot 24/7

### 8.1. Configurar
No card do produto → botão **Ativar Autopilot 24/7** 🚀

Modal abre com:
| Campo | O que faz | Recomendado |
|---|---|---|
| **Ativar 24/7** | Liga o loop de ticks automáticos | ✅ |
| **Intervalo (min)** | De quanto em quanto tempo roda tick | 30 |
| **Auto-aprovar até risco** | Planos ≤ esse risco são auto-executados | `low` |
| **Relatório diário Telegram** | Envia resumo ECHO 1x/dia | ✅ |
| **Hora do envio (UTC)** | 0-23 (Brasília = UTC - 3h) | 12 (= 9h BR) |

**Salvar** → mensagem "Autopilot ATIVADO — rodando 24/7" ✅

### 8.2. Estratégias recomendadas por maturidade

#### 🟢 Iniciante (primeiros 30 dias)
- Intervalo: **60min**
- Auto-aprovar: **none** (só avisar, você aprova tudo)
- Relatório diário: **ativo**

→ Sistema fica "olhando" e propondo, mas nada roda sem seu OK. Você confere, aprende, vai liberando aos poucos.

#### 🟡 Experiente (após 30 dias validando planos)
- Intervalo: **30min**
- Auto-aprovar: **low** (só ações de baixo risco rodam sozinhas, ex. pausar criativo com fadiga)
- Relatório diário: **ativo**

→ Rotina diária reduz 80%. Você só intervém em decisões de médio/alto risco.

#### 🔴 Avançado (após 60+ dias, LEARNER amadurecido)
- Intervalo: **15min**
- Auto-aprovar: **medium** (budget shifts até 40% rodam sozinhos)
- Relatório diário: **ativo**

→ Agência quase 100% autônoma. Você só define estratégia e lê relatório.

### 8.3. O que acontece em background
A cada **60 segundos**, o loop:
- Busca produtos com `autopilot_enabled=true`
- Verifica se `now - last_tick >= interval_min` → se sim, roda tick
- Para cada plano validado:
  - Se `risk_level ≤ auto_approve_risk` → **APROVA + EXECUTA + AVALIA + APRENDE** automaticamente
  - Caso contrário → **DEIXA NA INBOX** (aba Planos, status=validated)
- Envia resumo via Telegram com ✅ ações executadas e ⏸ planos aguardando aprovação

### 8.4. Desativar
Modal Autopilot → desmarcar "Ativar 24/7" → Salvar.

---

## 9. Inbox de planos e aprovação

### 9.1. Onde ver os planos pendentes
JAMES Panel → aba **Planos**

Cada card mostra:
- **Agente** que propôs (ORION, MIDAS, NOVA, etc.)
- **Objetivo** (ex. "Reagir a CPA +50%")
- **Status** (draft / validated / approved / executing / done / failed / blocked)
- **Steps** (ex. "pause_campaign: camp_awareness_01")
- Escudo verde 🛡️ se passou pelos guardrails

### 9.2. Aprovar manualmente
No plano com status `validated` → botão **Aprovar + Executar**

Isso executa as 6 camadas finais de uma vez:
1. Execução real (chama executores)
2. Verificação pós-execução
3. Avaliação antes/depois (1h depois)
4. Aprendizado (LEARNER atualiza success_rate do agente/skill)
5. Arquivamento
6. Resultado volta em toast + aba Anomalias atualizada

### 9.3. Rejeitar plano
Por enquanto: delete a anomalia manualmente ou deixe `blocked`. Em futura versão: botão "Rejeitar" explícito.

---

## 10. Relatório executivo ECHO

### 10.1. Gerar via UI
JAMES Panel → aba **Relatórios** → **Gerar (ECHO)**

ECHO (agente da SQUAD 8) usa Ollama pra gerar narrativa executiva em português baseada em:
- KPIs agregados do período (24h ou 168h = 7 dias)
- Planos recentes e resultados (PASS/FAIL)
- Anomalias abertas
- Recomendações de próximos passos

### 10.2. Níveis de relatório
| Level | Quando usar |
|---|---|
| `agency` | Visão geral de todos os produtos |
| `product` | Foco em 1 produto específico |
| `campaign` | (futuro) Foco em 1 campanha |
| `sector` | (futuro) Por setor: tracking / landing / funil / criativos / financeiro |

### 10.3. Automático via Telegram
Se você ativou **Relatório diário** no Autopilot, o ECHO envia automaticamente no horário configurado para seu chat.

**Exemplo de mensagem recebida:**
```
📊 Relatório diário JAMES — Curso Marketing Digital

Nas últimas 24h o produto gerou R$ 3.247 em receita (+18% vs média 7d)
e 42 leads qualificados. O CTR médio subiu para 3.8% após NOVA
substituir 3 criativos em fadiga. MIDAS realocou R$ 80 do grupo de
anúncios "test_v2" para "winner_v1" (ROAS 4.1 vs 2.3).

Atenção: ATTRIB detectou queda de 12% na atribuição do pixel da LP
"/curso-full". Plano sugerido: TRACK audit. Aprove no painel.
```

---

## 11. Fluxo completo end-to-end (exemplo real)

### Cenário: lançamento do "Curso Marketing Digital"

**Dia 1 — Setup (1h)**
1. Admin cadastra OAuth: Google ✅ Meta ✅ Telegram ✅
2. Você conecta suas contas Google + Meta + Telegram
3. Cria produto "Curso Marketing Digital" (budget R$ 200/dia)
4. Cria campanhas na Meta Ads manualmente (3 grupos de anúncios, 5 criativos cada)

**Dia 2 — Primeiros dados (10min)**
5. Configura cron na VPS puxando Meta Insights a cada 30min → envia pro `/ingest`
6. Roda tick manual → ainda sem anomalias (baseline precisa de 3+ pontos)

**Dia 3 — Baseline pronto**
7. Backend já tem 48h de dados → baseline calculada
8. Ativa **Autopilot 30min + auto_approve=none + relatório diário 12h UTC**

**Dia 4-7 — Observação**
9. JAMES detecta:
   - Criativo "ad_v3" com CTR caindo (fadiga) → NOVA sugere pausar
   - Campanha "cold_01" com CPA subindo → MIDAS sugere shift 20% budget
10. Você aprova manualmente os planos no painel
11. Relatórios diários chegam no Telegram às 9h BR

**Dia 8 — Aprendizado**
12. LEARNER acumulou: NOVA tem 80% success em "pause_fatigued_creative"
13. Muda Autopilot para `auto_approve=low` → NOVA age sozinho
14. Rotina manual cai de 2h/dia para 20min

**Semana 3 — Otimização contínua**
15. MIDAS detecta ROAS subindo em "winner_v1" → sugere scale +25%
16. Você aprova → receita sobe 40%
17. HUNTER detecta baixa conversão no estágio "checkout" → sugere A/B em LPX
18. DEX constrói variação da LP automaticamente
19. LPX otimiza copy e CTA
20. Conversão checkout: 2.1% → 3.4%

**Mês 2 — Autonomia total**
- Autopilot `auto_approve=medium`
- Você só lê relatório diário + aprova decisões estratégicas
- Sistema aprendeu padrões do seu nicho
- Receita estabiliza 3x maior que início

---

## 12. Os 24 agentes e quando cada um atua

### SQUAD 1 — Core & Governance
| Agente | Quando atua |
|---|---|
| **ORION** | Toda anomalia: decide qual agente chamar |
| **SENTINEL** | Antes de qualquer EXEC: avalia risco |
| **EXEC** | Executa planos aprovados |
| **NERO** | Gerencia catálogo de skills (versões, publicação) |
| **ARCHIVIST** | Arquiva tudo no Mongo (já faz automático) |

### SQUAD 2 — Data & Diagnostics
| Agente | Quando atua |
|---|---|
| **DASH** | Queda de performance genérica → drill-down |
| **TRACK** | Suspeita de problema de rastreamento (pixel/UTM/events) |
| **ATTRIB** | Divergência entre cliques e conversões atribuídas |

### SQUAD 3 — Traffic
| Agente | Quando atua |
|---|---|
| **MIDAS** | CPA sobe, ROAS cai, budget no limite → shift/pause/scale |

### SQUAD 4 — Funnel & Sales
| Agente | Quando atua |
|---|---|
| **HUNTER** | Conversão caindo em algum estágio do funil |
| **LNS** | Leads frios sem engajamento → email/WA nurturing |
| **CLOSER** | Lead qualificado sem fechamento → revisar script |

### SQUAD 5 — Creative & Messaging
| Agente | Quando atua |
|---|---|
| **NOVA** | Fadiga criativa (CTR caindo, frequency alta) → gerar novas variações |
| **MARA** | Mensagem confusa, brand voice inconsistente |

### SQUAD 6 — Pages & Conversion
| Agente | Quando atua |
|---|---|
| **LPX** | Tráfego alto na LP mas conversão baixa |
| **DEX** | Precisa construir LP nova do zero |
| **OUBAS** | Problema de UX/fluxo de checkout |
| **REX** | Teste de preço / análise CRO |

### SQUAD 7 — Research & Product
| Agente | Quando atua |
|---|---|
| **ATLAS** | Precisa entender o mercado/concorrentes |
| **MOIRA** | Refinar oferta / posicionamento estratégico |

### SQUAD 8 — Reporting & Finance
| Agente | Quando atua |
|---|---|
| **EVAL** | Após cada execução: PASS / FAIL / INCONCLUSIVO |
| **LEARNER** | Acumula padrões — atualiza success_rate do catálogo |
| **FINN** | KPIs financeiros (MRR, ticket médio, LTV) |
| **ECHO** | Gera relatórios executivos em linguagem natural |

---

## 13. As 14 camadas operacionais

1. **Sensors** — Recebe dados das fontes (`/api/james/products/{id}/ingest`)
2. **Normalization** — Padroniza formato (metric + value + dimension)
3. **Baseline** — Calcula mean/std/p25/p50/p75 dos últimos 7 dias
4. **Anomalies** — Detecta drop/spike/fatigue usando thresholds por métrica
5. **Prioritization** — Score = severity × metric_weight × log(|delta%|+1)
6. **Orchestration** — ORION roteia para agente especialista
7. **Objective Governance** — Valida objetivo (banned patterns, blast radius)
8. **Guardrails** — max_budget_change=40%, high_risk flags, empty_plan
9. **Execution** — Executa steps do plano (dry-run ou API real)
10. **Verification** — Confere se executou de fato
11. **Evaluation** — Compara métricas 1h antes × 1h depois → PASS/FAIL
12. **Learning** — LEARNER atualiza success_rate por skill/agente/produto
13. **Memory** — Arquiva tudo no MongoDB (james_plans/executions/evaluations/learnings)
14. **Reporting** — ECHO gera relatório executivo com Ollama

---

## 14. Publicação em redes sociais

Separado do JAMES: você pode publicar conteúdo diretamente.

### 14.1. Via UI
Sidebar → **Publicar em Redes** 📤

Preencha título, descrição, upload arquivo, selecione redes (YouTube, FB, IG, TikTok), **Publicar**.

### 14.2. Via chat
```
Publica esse vídeo no YouTube e TikTok: [url_do_arquivo]
Título: Como fazer marketing com IA
Descrição: Neste vídeo você vai aprender...
```
Kaelum detecta e chama skill `[SKILL:social_publish]` automaticamente.

### 14.3. Notas por rede
| Rede | Requer | Observação |
|---|---|---|
| YouTube | Google OAuth (escopo youtube.upload) | Funciona 100% com upload binário |
| Facebook | Meta OAuth (pages) | Posta texto na primeira Page |
| Instagram | Meta OAuth + IG Business | Requer URL pública via skill direta |
| TikTok | TikTok OAuth | PULL_FROM_URL — vídeo em URL HTTPS pública |
| WhatsApp | Meta OAuth + phone_number_id | Skill `[SKILL:whatsapp]` direta (não publicação) |

---

## 15. Troubleshooting

### Backend não inicia
```bash
cd /opt/mordomo
docker compose logs backend | tail -n 50
```
Procure por: `ModuleNotFoundError`, `MONGO_URL`, `JWT_SECRET missing`.

### Ollama não responde / agentes rodam sem LLM
```bash
docker compose logs ollama | tail -n 20
curl http://localhost:11434/api/tags    # lista modelos instalados
ollama pull qwen2.5:7b                   # baixa modelo se faltar
```
Agentes têm fallback heurístico, mas qualidade dos planos cai muito sem LLM.

### Tick não detecta anomalias
- Conferir se tem ≥ 3 pontos no baseline: `mongosh --eval "db.james_metrics.count()"`
- Baseline só é recomputada dentro do tick → rode o tick uma vez para popular

### Telegram não manda notificação
- Cheque `db.telegram_connections.findOne({user_id:"seu_id"})` tem `bot_token` e `chat_id`
- Envie mensagem manual para o bot antes do primeiro uso
- Teste: Configurações → Telegram → "Enviar mensagem de teste"

### Autopilot não está rodando
```bash
docker compose logs backend | grep -i autopilot
# deve mostrar: "JAMES Autopilot loop iniciado (check a cada 60s)"
```
Se não aparecer, restart: `docker compose restart backend`.

### OAuth callback retorna erro
- Confira redirect URI: deve ser **exatamente** `https://seu-dominio/api/oauth/<provider>/callback`
- Sem barra final, com HTTPS, host bate com a config do app
- TikTok exige que o domínio seja cadastrado em "URL Prefixes" também

### PWA mobile com input cortado
- Reinstale: apague ícone da tela → Safari/Chrome → **Adicionar à Tela de Início**
- Ou force SW update: Chrome → Configurações → Privacidade → Limpar dados de navegação → Cookies + Cache

### Resetar tudo (cuidado: apaga DB)
```bash
docker compose down -v
docker compose up -d --build
```

---

## 16. FAQ

### Posso ter múltiplos produtos no mesmo Autopilot?
Sim. Cada produto tem sua própria configuração independente.

### O sistema consegue rodar sem GPU?
Sim, com modelo `qwen2.5:7b` em CPU. Fica 3-5x mais lento por tick mas funciona. Para produção real recomenda GPU (NVIDIA 12GB+).

### Como escalar pra muitos clientes (SaaS)?
- Cada cliente = 1 usuário no sistema
- Admin cria contas via painel
- `allowed_modules` controla quais features cada cliente vê
- Quota de requests/tokens por usuário
- MongoDB escala horizontalmente com replica set

### Perco dados ao dar `docker compose up -d --build`?
Não. Os volumes Mongo (`mongo_data`) e Ollama (`ollama_data`) são persistentes. Só `down -v` apaga.

### Como fazer backup?
```bash
docker exec $(docker ps -qf name=mongo) mongodump --archive > backup_$(date +%F).archive
```

### Posso usar Claude/GPT em vez de Ollama?
Sim, mas perde a gratuidade. Trocar `OLLAMA_URL` pro endpoint OpenAI-compatible de LiteLLM/OpenRouter nos .env e ajustar `OLLAMA_MODEL`. Todos os agentes passam a consumir seu crédito OpenAI/Anthropic.

### O sistema é open-source?
O código está no seu GitHub privado. Você é dono de 100%. Rode na sua VPS pra sempre sem mensalidade.

### Qual é o próximo passo do roadmap?
- Conectores automáticos Meta Ads / Google Ads / GA4 (sensor real em vez de manual)
- Executores reais via Marketing API (sair do dry-run)
- Messaging Hub Unificado (inbox centralizada de DMs)
- Kill switch global pra pausar todos os autopilots em eventos especiais

---

## 📬 Contato / Suporte

- Documentação técnica completa: `/app/docs/MANUAL_KAELUM_AI.md` (funcionalidades gerais)
- Código-fonte: seu repositório privado no GitHub (sincronizado via `git pull`)
- Logs em tempo real: `docker compose logs -f backend frontend`
- Monitor de saúde: aba Admin → Dashboard

---

**© 2026 Kaelum.AI · JAMES AGENCY · Open for your VPS forever. Zero lock-in.**
