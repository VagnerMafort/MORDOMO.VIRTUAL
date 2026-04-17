# 📘 MANUAL DO USUÁRIO — KAELUM.AI

**Versão:** 1.0 · Produção
**URL:** https://mordomo.virtual.grupomafort.com
**Data:** Fevereiro 2026

---

## 📑 ÍNDICE

1. [Visão Geral](#1-visão-geral)
2. [Primeiro Acesso & Login](#2-primeiro-acesso--login)
3. [Painel Principal](#3-painel-principal)
4. [💬 Chat com o Agente](#4-chat-com-o-agente)
5. [🎙️ Modo Hands-Free (Ativação por Voz)](#5-modo-hands-free-ativação-por-voz)
6. [⚙️ Configurações do Agente](#6-configurações-do-agente)
7. [🤖 Gerenciador de Agentes Múltiplos](#7-gerenciador-de-agentes-múltiplos)
8. [📲 Integração com Telegram](#8-integração-com-telegram)
9. [📢 Agência de Marketing](#9-agência-de-marketing)
10. [📚 Criador de Mentorias](#10-criador-de-mentorias)
11. [📊 Painel de Monitoramento do Sistema](#11-painel-de-monitoramento-do-sistema)
12. [🛠️ Skills (Habilidades do Agente)](#12-skills-habilidades-do-agente)
13. [👥 Gestão de Usuários (Admin)](#13-gestão-de-usuários-admin)
14. [🧰 Manutenção & Solução de Problemas](#14-manutenção--solução-de-problemas)
15. [📞 Suporte](#15-suporte)

---

## 1. VISÃO GERAL

O **Kaelum.AI** é um agente de inteligência artificial completo, multi-usuário, que roda **100% na sua VPS** sem depender de serviços externos pagos (OpenAI, Anthropic). Ele combina:

- 💬 Chat conversacional com IA local (Ollama Qwen 2.5)
- 📱 Funciona como aplicativo no celular (PWA)
- 🎙️ Controle por voz sem precisar tocar na tela
- 📢 Automação de marketing e campanhas
- 📚 Criação de cursos/mentorias com exportação PDF/DOCX
- 📲 Integração com Telegram (bot particular)
- 🧠 Dois modelos de IA (rápido 7B + avançado 32B)

**Sem custo de API.** Só o custo fixo da sua VPS que você já paga.

---

## 2. PRIMEIRO ACESSO & LOGIN

### 2.1 Acessando o sistema

Abra seu navegador e acesse: **https://mordomo.virtual.grupomafort.com**

### 2.2 Tela de Login

- **E-mail:** `ministerioprvagner@gmail.com`
- **Senha:** `DAx4OwaqmVubkHtn` (a senha que foi gerada no deploy)

> ⚠️ **Importante:** Troque essa senha no primeiro acesso indo em **Configurações → Conta**.

### 2.3 Instalando como App no Celular (PWA)

**No Android (Chrome):**
1. Acesse o site no navegador
2. Clique no menu (três pontos) → "**Instalar aplicativo**" ou "**Adicionar à tela inicial**"
3. O ícone aparecerá como um app normal

**No iPhone (Safari):**
1. Acesse o site no Safari
2. Toque no botão Compartilhar (quadrado com seta pra cima)
3. Role e toque em "**Adicionar à Tela de Início**"

Agora você tem o Mordomo como app no seu celular, funcionando offline parcialmente.

---

## 3. PAINEL PRINCIPAL

Ao fazer login, você verá:

- **Barra Lateral Esquerda (Sidebar):** Lista de conversas anteriores e menu de módulos
- **Área Central:** Chat atual ou módulo selecionado
- **Barra Superior:** Nome do agente, modo hands-free, configurações

### 3.1 Menu Principal (Sidebar)

| Ícone | Função |
|---|---|
| ➕ **Nova Conversa** | Inicia novo chat |
| 💬 **Conversas** | Histórico de chats |
| 🤖 **Agentes** | Gerenciar múltiplos agentes (admin) |
| 📲 **Telegram** | Conectar seu bot |
| 📢 **Agência** | Módulo de marketing automatizado |
| 📚 **Mentorias** | Criador de cursos |
| 📊 **Monitor** | Estado do sistema |
| 🛠️ **Skills** | Habilidades ativas |
| ⚙️ **Configurações** | Personalização |

---

## 4. 💬 CHAT COM O AGENTE

### 4.1 Como conversar

1. Clique em **➕ Nova Conversa**
2. Digite sua mensagem na caixa de texto na parte inferior
3. Pressione **Enter** ou clique em **Enviar** (→)
4. O agente responde em streaming (palavra por palavra, como o ChatGPT)

### 4.2 Recursos do chat

- **📎 Anexar arquivo:** Clique no clipe para enviar PDFs, imagens, docs (OCR automático)
- **🎤 Ditado por voz:** Clique no microfone para ditar em vez de digitar
- **🗣️ Text-to-Speech:** O agente pode ler as respostas em voz alta (configurável)
- **💾 Histórico:** Todas conversas ficam salvas na sidebar

### 4.3 Comandos rápidos

- `/skills` — Lista habilidades disponíveis
- `/limpar` — Limpa a conversa atual
- `/exportar` — Baixa o chat em TXT
- `/modelo rápido` — Usa Qwen 7B (respostas em segundos)
- `/modelo avançado` — Usa Qwen 32B (respostas mais inteligentes, ~20-60s)

### 4.4 Sistema Dual de IA

O Mordomo **escolhe automaticamente** entre dois modelos:
- **Qwen 2.5 7B** (rápido): Para perguntas simples e respostas imediatas
- **Qwen 2.5 32B** (avançado): Para análises complexas, código, estratégias

Você pode forçar um modelo específico em **Configurações → Modelo LLM**.

---

## 5. 🎙️ MODO HANDS-FREE (Ativação por Voz)

### 5.1 O que é?

O agente fica **ouvindo o tempo todo** e responde quando você fala a palavra de ativação (tipo "Alexa" ou "Hey Siri"). Perfeito para quem tá dirigindo, cozinhando ou fazendo outra coisa.

### 5.2 Como ativar

1. Clique no ícone **🎙️** no canto superior direito
2. Aceite a permissão de microfone do navegador
3. Pronto! O Mordomo tá ouvindo.

### 5.3 Palavra de ativação (Wake Word)

Por padrão: **"Hey Mordomo"**

**Exemplo:**
- Você: "Hey Mordomo, qual a previsão do tempo pra amanhã?"
- Mordomo: *(responde em voz alta)*

### 5.4 Personalizar palavra de ativação

Em **Configurações → Voz → Palavra de ativação**, troque por qualquer nome. Por exemplo:
- "Hey Jarvis"
- "Alô Pastor"
- "Querido assistente"

### 5.5 Desativar

Clique no ícone 🎙️ novamente. O microfone para.

> ⚠️ **Privacidade:** O reconhecimento de voz acontece **no seu navegador** (Web Speech API). Só a transcrição final é enviada pro servidor.

---

## 6. ⚙️ CONFIGURAÇÕES DO AGENTE

Acesse em **Sidebar → ⚙️ Configurações**.

### 6.1 Aba "Agente"

- **Nome do agente:** Ex: "Mordomo", "Jarvis", "Assistente"
- **Personalidade:** Texto que define como ele fala (ex: "Responda de forma formal e concisa. Use sempre emojis. Chame-me de Pastor.")

### 6.2 Aba "Voz"

- **TTS habilitado:** Ativa/desativa fala em voz alta
- **Idioma TTS:** pt-BR (padrão), en-US, es-ES, etc.
- **Velocidade da fala:** 0.5x a 2x
- **Palavra de ativação:** Customizar wake word

### 6.3 Aba "Modelo LLM"

- **URL do Ollama:** `http://ollama:11434` (não mexa, é o container)
- **Modelo rápido:** `qwen2.5:7b`
- **Modelo avançado:** `qwen2.5:32b`
- **Seleção automática:** Liga/desliga escolha inteligente

### 6.4 Aba "Skills"

Lista todas as habilidades e você **marca/desmarca** quais ficam ativas:

- ✅ Executor de código Python
- ✅ Web scraping
- ✅ Resumidor de URLs
- ✅ Gerenciador de arquivos
- ✅ Calculadora
- ✅ Chamadas de API
- ✅ Informações do sistema
- ✅ Data/hora

### 6.5 Aba "Conta"

- Trocar senha
- Trocar email
- Fazer logout
- Excluir conta (cuidado!)

---

## 7. 🤖 GERENCIADOR DE AGENTES MÚLTIPLOS

### 7.1 O que é?

Você pode criar **vários agentes** dentro do Mordomo, cada um com personalidade, skills e bot do Telegram diferente. Útil para separar contextos:
- Agente "Atendimento" — responde clientes
- Agente "Marketing" — só analisa dados e sugere campanhas
- Agente "Pastoral" — só responde perguntas bíblicas

### 7.2 Criar novo agente

1. Vá em **Sidebar → 🤖 Agentes**
2. Clique em **➕ Novo Agente**
3. Preencha:
   - Nome
   - Foto/avatar
   - Personalidade (prompt de sistema)
   - Skills permitidas
   - Telegram bot (opcional)
4. Salvar

### 7.3 Alternar entre agentes

No topo da tela, clique no nome do agente atual e escolha outro da lista.

---

## 8. 📲 INTEGRAÇÃO COM TELEGRAM

Permite que você converse com seu Mordomo **pelo Telegram no celular**, sem precisar abrir o navegador.

### 8.1 Criar um Bot no Telegram

1. No Telegram, procure `@BotFather`
2. Envie `/newbot`
3. Escolha um nome (ex: "Meu Kaelum.AI")
4. Escolha um username (precisa terminar em `bot`, ex: `meu_mordomo_bot`)
5. BotFather te envia um **TOKEN** (algo tipo `123456:ABCdef...`)

### 8.2 Conectar no Mordomo

1. Vá em **Sidebar → 📲 Telegram**
2. Cole o **Token do Bot**
3. Clique em **Conectar**
4. ✅ Aparece "Conectado como @seu_bot"

### 8.3 Usar pelo Telegram

1. No Telegram, abra seu bot (ex: `@meu_mordomo_bot`)
2. Envie `/start`
3. Mande qualquer mensagem — o Mordomo responde!

### 8.4 Recursos do Telegram

- Histórico sincronizado com o painel web
- Usa o mesmo modelo LLM configurado
- Responde áudios (transcreve automaticamente)
- Envia imagens (descreve o que vê)

### 8.5 Desconectar bot

Em **📲 Telegram**, clique em **Desconectar**. O bot para de responder mas não é deletado.

---

## 9. 📢 AGÊNCIA DE MARKETING

Módulo completo para **gerenciar produtos, campanhas e automações de marketing**. Pense nisso como um mini-CRM + mini-SEMrush.

### 9.1 Acessar

**Sidebar → 📢 Agência**

### 9.2 Abas do módulo

#### 9.2.1 **Dashboard**

Visão geral com gráficos (Recharts):
- Receita do mês
- Produtos ativos
- Campanhas rodando
- Regras disparadas hoje
- Aprovações pendentes

#### 9.2.2 **Produtos**

Cadastre seus produtos/serviços:
- Nome, descrição
- Preço
- Público-alvo
- Status: ativo, pausado, esgotado

**Como cadastrar:**
1. Aba **Produtos** → **➕ Novo Produto**
2. Preencher campos
3. Salvar

#### 9.2.3 **Campanhas**

Crie campanhas vinculadas a produtos:
- Nome da campanha
- Canal: Facebook, Instagram, Google Ads, Email, Orgânico
- Orçamento
- Métricas (cliques, conversões, custo)
- Data início/fim

#### 9.2.4 **Regras (Rules Engine)**

**O coração da automação.** Cria regras do tipo "SE X ACONTECER, ENTÃO FAZER Y".

**Exemplos:**
- **SE** vendas do produto "Curso XPTO" < 10/dia **ENTÃO** mandar alerta no Telegram
- **SE** campanha "Black Friday" tiver CPC > R$5 **ENTÃO** pausar e notificar
- **SE** estoque < 20% **ENTÃO** criar aprovação para reposição

**Como criar:**
1. Aba **Regras** → **➕ Nova Regra**
2. Escolher produto ou campanha
3. Definir condição (dropdown)
4. Definir ação (dropdown)
5. Frequência: diária, horária, tempo-real
6. Ativar

O motor de regras roda em **background (cron a cada 5 min)**.

#### 9.2.5 **Aprovações**

Lista de ações que **precisam da sua autorização** antes de executar (ex: reajustar preço, pausar campanha, gastar acima de R$X).

- Clique em ✅ **Aprovar** ou ❌ **Rejeitar**
- Aprovação gera log auditável

#### 9.2.6 **Log de Execução**

Histórico de **tudo que o sistema fez automaticamente**: regras disparadas, campanhas pausadas, alertas enviados. Bom pra auditar.

### 9.3 Controle de Acesso

Por padrão, **todos os usuários logados têm acesso** ao módulo Agência. Se quiser restringir, o admin pode ir em **Agência → Acessos** e liberar usuário por usuário.

---

## 10. 📚 CRIADOR DE MENTORIAS

Cria **cursos/mentorias completas com IA** e exporta em PDF/DOCX prontos pra vender.

### 10.1 Acessar

**Sidebar → 📚 Mentorias**

### 10.2 Criar nova mentoria

1. **➕ Nova Mentoria**
2. Preencher:
   - **Título:** Ex: "Mentoria em Marketing Digital"
   - **Nicho:** Ex: "Empreendedorismo", "Saúde", "Teologia"
   - **Público-alvo:** Ex: "Pequenos empresários iniciantes"
   - **Duração:** Ex: "6 semanas"
   - **Número de módulos:** 4 a 12
3. Clique em **🧠 Gerar com IA**
4. O Mordomo cria **estrutura completa** em ~30-60 segundos:
   - Nome de cada módulo
   - Tópicos de cada aula
   - Exercícios sugeridos
   - Bibliografia

### 10.3 Editor Visual

Depois de gerada, você pode **editar tudo visualmente**:
- Arrastar e soltar módulos (reordenar)
- Adicionar/remover aulas
- Editar conteúdo com editor rich text
- Inserir imagens

### 10.4 Exportar

Clique em **📥 Exportar** → escolha:
- **PDF** (WeasyPrint, visual bonito, pronto para distribuir)
- **DOCX** (Word, para você editar mais depois)

O arquivo é baixado direto no seu computador.

### 10.5 Biblioteca de mentorias

Todas suas mentorias ficam salvas. Você pode:
- Duplicar (criar outra baseada nela)
- Atualizar
- Excluir

---

## 11. 📊 PAINEL DE MONITORAMENTO DO SISTEMA

### 11.1 Acessar

**Sidebar → 📊 Monitor**

### 11.2 O que mostra

**Gráficos em tempo real:**
- 💾 Uso de RAM (total e por container)
- 💻 Uso de CPU
- 💿 Espaço em disco
- 🤖 Status do Ollama (modelos carregados, tokens/segundo)
- 🗄️ Status do MongoDB (conexões ativas, coleções)
- 📈 Requisições por minuto
- 🚦 Tarefas em background (fila)
- ⏱️ Latência média de respostas

### 11.3 Alertas automáticos

Se algo passar do limite (ex: RAM > 90%), aparece **alerta vermelho** no painel.

### 11.4 Logs recentes

Role até embaixo pra ver últimas 100 linhas de logs do sistema.

---

## 12. 🛠️ SKILLS (HABILIDADES DO AGENTE)

O Mordomo **não só conversa**. Ele **executa ações reais** quando você pede.

### 12.1 Skills disponíveis

| Skill | O que faz | Exemplo de uso |
|---|---|---|
| 🐍 **Code Executor** | Roda Python real | "Calcule a média destes números: 10, 20, 30" |
| 🌐 **Web Scraper** | Extrai dados de sites | "Pegue o título e preço do produto nessa URL: ..." |
| 📄 **URL Summarizer** | Resume páginas web | "Resume esse artigo pra mim: https://..." |
| 📁 **File Manager** | Lê/cria arquivos | "Liste os arquivos na minha pasta" |
| 🧮 **Calculator** | Contas complexas | "Se investir R$1000 a 12% ao ano por 5 anos, quanto tenho?" |
| 🔌 **API Caller** | Chama APIs externas | "Consulte o CEP 01310-100 na API dos Correios" |
| 💻 **System Info** | Estado do servidor | "Quanto de RAM estou usando?" |
| 📅 **DateTime** | Data/hora atual | "Que horas são em Tóquio agora?" |

### 12.2 Como ativar/desativar skills

**Configurações → Skills** — marque/desmarque cada uma.

### 12.3 Dashboard de Skills

**Sidebar → 🛠️ Skills** mostra:
- Quantas vezes cada skill foi usada
- Taxa de sucesso
- Erros recentes

---

## 13. 👥 GESTÃO DE USUÁRIOS (Admin)

*Disponível só para usuários com role `admin`.*

### 13.1 Criar novo usuário

Dois caminhos:

**A) Auto-cadastro:**
- Compartilhe a URL com a pessoa
- Ela clica em "Registrar" na tela de login
- Cria própria conta

**B) Cadastro manual (admin):**
- **Configurações → Usuários → ➕ Novo Usuário**
- Define email, senha, role

### 13.2 Roles (papéis)

- **admin:** Acesso total (incluindo Painel Monitor e gestão de usuários)
- **user:** Acesso ao chat, mentorias, telegram, agência

### 13.3 Desativar usuário

**Configurações → Usuários** → clique no usuário → **Desativar**.

---

## 14. 🧰 MANUTENÇÃO & SOLUÇÃO DE PROBLEMAS

Acesse sua VPS via SSH: `ssh root@IP_DA_SUA_VPS`

### 14.1 Comandos essenciais

```bash
# Ir pra pasta do projeto
cd /opt/mordomo

# Ver status dos containers
docker compose ps

# Ver logs em tempo real
docker compose logs -f

# Ver logs de um serviço específico
docker compose logs backend
docker compose logs ollama

# Reiniciar tudo
docker compose restart

# Reiniciar só um container
docker compose restart backend

# Parar tudo
docker compose down

# Subir tudo
docker compose up -d

# Atualizar código (depois de Save to GitHub)
git pull && docker compose up -d --build
```

### 14.2 Problemas comuns

**"Não consigo acessar o site"**
```bash
docker compose ps              # verificar se tudo tá "Up"
docker compose logs nginx      # ver erros do nginx
```

**"Chat não responde"**
```bash
docker compose logs backend    # ver erros da API
docker compose logs ollama     # ver se a IA tá rodando
docker exec mordomo-ollama ollama list   # listar modelos baixados
```

**"Modelo Ollama sumiu"**
```bash
docker exec mordomo-ollama ollama pull qwen2.5:7b
docker exec mordomo-ollama ollama pull qwen2.5:32b
```

**"Esqueci a senha admin"**
```bash
cat /opt/mordomo/.env | grep ADMIN
```

**"Certificado SSL expirou"**
O certbot renova sozinho a cada 12h. Se precisar forçar:
```bash
docker compose restart certbot
```

### 14.3 Backup do banco de dados

```bash
# Criar backup
docker exec mordomo-mongodb mongodump --out /tmp/backup
docker cp mordomo-mongodb:/tmp/backup ./mongo_backup_$(date +%Y%m%d)

# Restaurar
docker cp mongo_backup_YYYYMMDD mordomo-mongodb:/tmp/restore
docker exec mordomo-mongodb mongorestore /tmp/restore
```

**Recomendação:** Configure cron na VPS pra fazer backup diário automático.

### 14.4 Atualizar modelos Ollama

Se quiser trocar pra um modelo mais novo (ex: Qwen 3):
```bash
docker exec mordomo-ollama ollama pull qwen3:7b
```
Depois vá em **Configurações → Modelo LLM** e troque o nome.

---

## 15. 📞 SUPORTE

### 15.1 Autoatendimento

- Logs: `docker compose logs -f`
- Status: `docker compose ps`
- Documentação: este arquivo

### 15.2 Recursos do sistema

- **VPS:** Ubuntu 48GB RAM, sem GPU
- **Portas usadas:** 80, 443
- **Domínio:** mordomo.virtual.grupomafort.com
- **Código-fonte:** https://github.com/VagnerMafort/MORDOMO.VIRTUAL

### 15.3 Limites recomendados

| Recurso | Consumo esperado |
|---|---|
| RAM | 25-35 GB (com modelo 32B carregado) |
| Disco | ~30 GB (modelos) + dados |
| CPU | 2-4 cores ativos durante respostas |
| Usuários simultâneos | 10-20 sem degradação |
| Mensagens/dia | Ilimitado (custo zero de API) |

---

## 🎯 DICAS DE USO

### Para tirar o máximo do Mordomo:

1. **Use personalidades específicas:** Crie agentes separados pra cada contexto (cliente, equipe, pessoal)
2. **Automatize tudo:** Use o módulo Agência pra rodar regras 24/7
3. **Grave mentorias uma vez, venda sempre:** O gerador de PDF faz produtos digitais em minutos
4. **Use Telegram pra agilidade:** Responda clientes pelo celular usando IA local
5. **Monitore sempre:** Olhe o painel Monitor 1x/semana pra evitar gargalos
6. **Faça backup:** Configure backup diário do MongoDB pra não perder dados

---

## 📋 CHECKLIST DE ONBOARDING

Siga essa ordem na primeira semana:

- [ ] Login e troca de senha
- [ ] Personalizar nome e personalidade do agente
- [ ] Instalar como PWA no celular
- [ ] Testar modo hands-free
- [ ] Criar bot Telegram e conectar
- [ ] Testar o chat com pergunta complexa
- [ ] Cadastrar primeiro produto no módulo Agência
- [ ] Criar primeira regra automática
- [ ] Gerar primeira mentoria de teste
- [ ] Exportar mentoria em PDF
- [ ] Verificar painel Monitor
- [ ] Configurar backup diário do MongoDB
- [ ] Anotar senha admin em gerenciador seguro

---

## 🎓 CONCLUSÃO

O **Kaelum.AI** é seu **assistente 24/7**, **vendedor automático** e **criador de produtos digitais**, tudo rodando no seu próprio servidor, **sem custo de API**, com **privacidade total** (seus dados nunca saem da sua VPS).

**Use, explore, personalize.** Qualquer dúvida, consulte este manual ou os logs do sistema.

---

**Desenvolvido com ❤️ · Deploy em 17 de fevereiro de 2026**
**Versão do Manual:** 1.0

---
