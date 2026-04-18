# 🚀 Deploy automático via GitHub Actions

Depois de configurado uma vez, todo `Save to Github` dispara deploy automático na sua VPS em ~2-3 minutos.

## 📋 Setup único (10 minutos, só pelo celular)

### 1. Abrir o GitHub do projeto no celular

Safari/Chrome → `github.com/<seu-user>/<seu-repo>`

### 2. Adicionar 4 secrets

No repositório → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Crie 4 secrets (exatamente esses nomes, maiúsculas):

| Nome | Valor |
|---|---|
| `VPS_HOST` | `144.91.105.101` |
| `VPS_USER` | `root` |
| `VPS_PASSWORD` | (sua senha root da VPS) |
| `VPS_PORT` | `22` (opcional — se SSH padrão) |

⚠️ **Importante**: Secrets ficam criptografados no GitHub, **ninguém consegue ler**, nem o próprio GitHub mostra depois de salvar. É seguro.

🛡️ **Recomendação futura (quando tiver tempo num computador)**: substituir senha por chave SSH. Mais seguro ainda. Mas com senha já funciona.

### 3. Testar

Agora é só fazer **"Save to Github"** aqui no Emergent.

Depois do push:
1. Abra `github.com/<seu-user>/<seu-repo>/actions` no celular
2. Vai aparecer o workflow **"Deploy Kaelum.AI to VPS"** rodando
3. Em ~2-3 min fica verde ✅
4. Pronto — sua VPS já está atualizada

### 4. Testar manualmente (quando quiser forçar um deploy sem fazer push)

GitHub → Actions → "Deploy Kaelum.AI to VPS" → **Run workflow** → Run

## 🔍 Se der erro

Clica no workflow vermelho → clica no step "Deploy via SSH" → vê o log detalhado.

Erros comuns:
- ❌ `ssh: handshake failed` → senha errada ou porta bloqueada
- ❌ `git pull conflict` → VPS tem arquivos modificados, rode `git stash` uma vez pelo SSH
- ❌ `docker compose not found` → atualize pra docker compose v2 na VPS

## 🎁 Bônus: trocar senha por chave SSH (mais seguro)

Quando estiver num computador:

```bash
# 1. No seu computador, gerar chave
ssh-keygen -t ed25519 -C "github-actions-kaelum" -f ~/.ssh/kaelum_deploy

# 2. Copiar chave pública pra VPS
ssh-copy-id -i ~/.ssh/kaelum_deploy.pub root@144.91.105.101

# 3. No GitHub Secrets, adicionar:
#    VPS_SSH_KEY = (conteúdo do arquivo ~/.ssh/kaelum_deploy — a chave PRIVADA)

# 4. Me avisa que eu ajusto o workflow pra usar SSH key em vez de senha
```
