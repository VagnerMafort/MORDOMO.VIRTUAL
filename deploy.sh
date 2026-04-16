#!/bin/bash
set -e

DOMAIN="mordomo.virtual.grupomafort.com"
ADMIN_USER_EMAIL="ministerioprvagner@gmail.com"
EMAIL="${CERTBOT_EMAIL:-$ADMIN_USER_EMAIL}"

echo "=========================================="
echo "  Mordomo Virtual - Deploy Completo"
echo "  Dominio: $DOMAIN"
echo "=========================================="
echo ""

# 1. Docker
if ! command -v docker &> /dev/null; then
    echo "[1/7] Instalando Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
else
    echo "[1/7] Docker OK"
fi

if ! docker compose version &> /dev/null; then
    echo "Instalando Docker Compose plugin..."
    sudo apt-get update && sudo apt-get install -y docker-compose-plugin
fi

# 2. .env
if [ ! -f .env ]; then
    echo "[2/7] Criando .env..."
    JWT=$(openssl rand -hex 32)
    ADMIN_PASS=$(openssl rand -base64 12)
    cat > .env << EOF
JWT_SECRET=$JWT
ADMIN_EMAIL=$ADMIN_USER_EMAIL
ADMIN_PASSWORD=$ADMIN_PASS
OLLAMA_MODEL=qwen2.5:32b
CERTBOT_EMAIL=$EMAIL
EOF
    echo "  Email admin: $ADMIN_USER_EMAIL"
    echo "  Senha admin gerada: $ADMIN_PASS"
    echo "  SALVE ESSA SENHA!"
else
    echo "[2/7] .env ja existe"
fi

# 3. DNS check
echo "[3/7] Verificando DNS..."
IP=$(dig +short $DOMAIN 2>/dev/null || echo "")
MY_IP=$(curl -s ifconfig.me 2>/dev/null || echo "unknown")
if [ "$IP" = "$MY_IP" ]; then
    echo "  DNS OK: $DOMAIN -> $MY_IP"
else
    echo "  AVISO: DNS aponta para '$IP', este servidor e '$MY_IP'"
    echo "  Configure o DNS antes de gerar o SSL!"
    echo "  Adicione um registro A: $DOMAIN -> $MY_IP"
    read -p "  Continuar mesmo assim? (s/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then exit 1; fi
fi

# 4. Gerar SSL (primeira vez)
echo "[4/7] Gerando certificado SSL..."
# Nginx temporario para validacao
mkdir -p /tmp/certbot-www
docker run -d --name tmp-nginx -p 80:80 \
    -v /tmp/certbot-www:/var/www/certbot:ro \
    -v $(pwd)/nginx-temp.conf:/etc/nginx/conf.d/default.conf:ro \
    nginx:alpine 2>/dev/null || true

# Criar nginx temp
cat > nginx-temp.conf << 'NGINX'
server {
    listen 80;
    server_name _;
    location /.well-known/acme-challenge/ { root /var/www/certbot; }
    location / { return 200 'ok'; }
}
NGINX

docker stop tmp-nginx 2>/dev/null; docker rm tmp-nginx 2>/dev/null
docker run -d --name tmp-nginx -p 80:80 \
    -v /tmp/certbot-www:/var/www/certbot:ro \
    -v $(pwd)/nginx-temp.conf:/etc/nginx/conf.d/default.conf:ro \
    nginx:alpine

# Certbot
docker run --rm \
    -v mordomo_certbot_conf:/etc/letsencrypt \
    -v /tmp/certbot-www:/var/www/certbot \
    certbot/certbot certonly --webroot \
    --webroot-path=/var/www/certbot \
    --email $EMAIL --agree-tos --no-eff-email \
    -d $DOMAIN || echo "  SSL falhou - verifique o DNS e tente novamente"

docker stop tmp-nginx 2>/dev/null; docker rm tmp-nginx 2>/dev/null
rm -f nginx-temp.conf

# 5. Build e start
echo "[5/7] Construindo e iniciando servicos..."
docker compose build
docker compose up -d

# 6. Baixar modelos Ollama
echo "[6/7] Baixando modelos LLM..."
sleep 10
echo "  Baixando qwen2.5:7b (modelo rapido)..."
docker exec mordomo-ollama ollama pull qwen2.5:7b
echo "  Baixando qwen2.5:32b (modelo inteligente)..."
echo "  (Pode levar 15-30 minutos na primeira vez)"
docker exec mordomo-ollama ollama pull qwen2.5:32b

# 7. Verificar
echo "[7/7] Verificando..."
sleep 5
docker compose ps

echo ""
echo "=========================================="
echo "  DEPLOY CONCLUIDO!"
echo "=========================================="
echo ""
echo "  URL:    https://$DOMAIN"
echo "  Admin:  $(grep ADMIN_EMAIL .env | cut -d= -f2)"
echo "  Senha:  $(grep ADMIN_PASSWORD .env | cut -d= -f2)"
echo ""
echo "  IMPORTANTE:"
echo "  1. Salve a senha acima em lugar seguro"
echo "  2. Mude a senha no primeiro login"
echo "  3. O SSL renova automaticamente"
echo ""
echo "  Comandos uteis:"
echo "    docker compose logs -f        # Ver logs"
echo "    docker compose restart        # Reiniciar"
echo "    docker compose down           # Parar"
echo "    docker compose up -d          # Iniciar"
echo "=========================================="
