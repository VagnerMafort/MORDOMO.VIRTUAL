# 🚀 GUIA DE DEPLOY — Mordomo Virtual na sua VPS

**Domínio:** `mordomo.virtual.grupomafort.com`
**Para:** VPS Ubuntu (48GB RAM, sem GPU)
**Tempo estimado:** 30 a 60 minutos

---

## ✅ HEALTH CHECK FEITO (antes de começar)

- Backend: **ONLINE** (`/api/health` → 200 OK)
- Login admin: **FUNCIONA** (JWT gerado com sucesso)
- Docker Compose: **OK** (6 serviços: mongo, ollama, backend, frontend, nginx, certbot)
- Nginx + SSL auto-renovável: **CONFIGURADO**
- Script `deploy.sh`: **PRONTO** (135 linhas)

**Código 100% pronto pra produção.** ✅

---

## 📋 O QUE VOCÊ VAI PRECISAR

1. **Acesso à sua VPS** (via SSH) — você já tem
2. **Domínio `mordomo.virtual.grupomafort.com` apontando pra sua VPS** (registro DNS tipo A)
3. **Seu código no GitHub** (você já salvou pelo botão "Save to GitHub")
4. **Um email válido** (pra o certificado SSL gratuito — Let's Encrypt)

---

## 🎯 PASSO A PASSO (faça NA ORDEM)

### **PASSO 1 — Descobrir o IP da sua VPS**

Abra o painel do seu provedor de VPS (Hostinger, DigitalOcean, Contabo, etc.) e copie o **IP público** (algo tipo `123.45.67.89`).

---

### **PASSO 2 — Apontar o domínio pra VPS (DNS)**

1. Entre no painel onde você gerencia o domínio `grupomafort.com`
2. Vá em **DNS / Zona DNS / Registros**
3. Crie um registro tipo **A** assim:
   - **Nome / Host:** `mordomo.virtual`
   - **Tipo:** `A`
   - **Valor / Aponta para:** (o IP que você copiou no passo 1)
   - **TTL:** `3600` (ou padrão)
4. Salve e **espere 5 a 15 minutos** pra propagar

**Como testar se propagou:**
No seu computador, abra o navegador e acesse: https://dnschecker.org
Digite `mordomo.virtual.grupomafort.com` e veja se aparece seu IP.

---

### **PASSO 3 — Conectar na VPS via SSH**

No seu computador (Windows: use **PowerShell**; Mac/Linux: use **Terminal**):

```bash
ssh root@SEU_IP_AQUI
```

Substitua `SEU_IP_AQUI` pelo IP da VPS. Digite a senha quando pedir.

---

### **PASSO 4 — Instalar Git e baixar o código do GitHub**

Copie e cole esses comandos (um de cada vez):

```bash
apt update && apt install -y git
cd /opt
git clone https://github.com/SEU_USUARIO/SEU_REPO.git mordomo
cd mordomo
```

⚠️ **Substitua** `SEU_USUARIO/SEU_REPO` pelo nome do seu repositório no GitHub (ex: `joaosilva/mordomo-virtual`).

---

### **PASSO 5 — Rodar o script de deploy automático**

```bash
chmod +x deploy.sh
./deploy.sh
```

**O que esse script faz automaticamente pra você:**

1. ✅ Instala o Docker (se ainda não tiver)
2. ✅ Cria um arquivo `.env` com senhas seguras (JWT + senha admin aleatória)
3. ✅ Verifica se o DNS tá apontando corretamente
4. ✅ Gera o certificado SSL grátis (Let's Encrypt)
5. ✅ Sobe os 6 containers: MongoDB, Ollama, Backend, Frontend, Nginx, Certbot
6. ✅ Mostra a senha do admin no final — **ANOTE ESSA SENHA!**

⚠️ **IMPORTANTE — guarde a senha admin que aparece na tela!**
Vai ser algo assim:
```
Senha admin gerada: kj3F2xM9P0qL
SALVE ESSA SENHA!
```

---

### **PASSO 6 — Baixar o modelo de IA (Ollama)**

O Ollama vai rodar sua IA local (sem depender de OpenAI/Anthropic). Baixe o modelo:

```bash
docker exec -it mordomo-ollama ollama pull qwen2.5:32b
```

⏱️ **Demora 10 a 20 minutos** (é um download de ~20GB).
Pode ir tomar um café. ☕

**Enquanto isso**, você pode baixar também o modelo rápido (menor):
```bash
docker exec -it mordomo-ollama ollama pull qwen2.5:7b
```

---

### **PASSO 7 — Testar se tudo tá no ar**

No seu navegador, abra:

👉 **https://mordomo.virtual.grupomafort.com**

Você vai ver a tela de login. Use:
- **Email:** `admin@mordomo.virtual.grupomafort.com`
- **Senha:** (a que o script mostrou no passo 5)

---

## 🔧 COMANDOS ÚTEIS (pra o dia a dia)

**Ver se os containers estão rodando:**
```bash
cd /opt/mordomo
docker compose ps
```

**Ver os logs (se algo der errado):**
```bash
docker compose logs backend   # logs do backend
docker compose logs nginx     # logs do nginx
docker compose logs -f        # ver TUDO ao vivo
```

**Reiniciar tudo:**
```bash
docker compose restart
```

**Parar tudo:**
```bash
docker compose down
```

**Atualizar o código (quando salvar nova versão no GitHub):**
```bash
cd /opt/mordomo
git pull
docker compose up -d --build
```

---

## ❓ SE DER ALGUM PROBLEMA

### "DNS não aponta pro IP"
- Aguarde mais tempo (pode levar até 24h em casos raros)
- Confira no https://dnschecker.org

### "Erro de SSL / certificado"
- Certifique-se que o DNS tá 100% apontando (passo 2)
- Rode: `docker compose logs certbot` pra ver o erro
- O Let's Encrypt tem limite de 5 tentativas por hora

### "Não consigo acessar o site"
- Libere as portas 80 e 443 no firewall da VPS:
  ```bash
  ufw allow 80
  ufw allow 443
  ufw reload
  ```

### "Esqueci a senha do admin"
Veja no arquivo `.env`:
```bash
cat /opt/mordomo/.env
```

---

## 🎉 PRONTO!

Depois que tudo subir, você vai ter:
- ✅ Seu Mordomo Virtual rodando 100% na SUA VPS
- ✅ IA local (Ollama) sem custo de API
- ✅ HTTPS com certificado grátis auto-renovável
- ✅ Todos os módulos: Chat, Telegram, Agência de Marketing, Mentorias, Painel de Monitoramento

---

## 📞 PRECISA DE AJUDA?

Se travar em algum passo:
1. Me diga **em qual passo** travou
2. Cole aqui **a mensagem de erro** exata
3. Se possível, mande o resultado de: `docker compose ps` e `docker compose logs --tail=50`

Eu te ajudo a destravar. 💪
