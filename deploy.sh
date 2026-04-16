#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# Mordomo Virtual - Script de Deploy para VPS
# ═══════════════════════════════════════════════════════════════

set -e

echo "=== Mordomo Virtual - Deploy ==="
echo ""

# 1. Check Docker
if ! command -v docker &> /dev/null; then
    echo "Instalando Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
fi

if ! command -v docker compose &> /dev/null; then
    echo "Instalando Docker Compose..."
    sudo apt-get install -y docker-compose-plugin
fi

# 2. Create .env if not exists
if [ ! -f .env ]; then
    echo "Criando .env..."
    cat > .env << 'EOF'
JWT_SECRET=TROQUE_POR_UMA_CHAVE_SEGURA_ALEATORIA
ADMIN_EMAIL=admin@mordomo.local
ADMIN_PASSWORD=TROQUE_POR_SENHA_SEGURA
OLLAMA_MODEL=qwen2.5:32b
BACKEND_URL=http://SEU_IP_OU_DOMINIO:8001
EOF
    echo "IMPORTANTE: Edite o arquivo .env com suas configuracoes!"
    echo ""
fi

# 3. Start services
echo "Iniciando servicos..."
docker compose up -d

# 4. Wait for Ollama and pull models
echo "Aguardando Ollama iniciar..."
sleep 10

echo "Baixando modelo rapido (7B)..."
docker exec mordomo-ollama ollama pull qwen2.5:7b

echo "Baixando modelo inteligente (32B)..."
echo "(Isso pode levar 15-30 minutos dependendo da conexao)"
docker exec mordomo-ollama ollama pull qwen2.5:32b

echo ""
echo "=== Deploy concluido! ==="
echo "Frontend: http://localhost"
echo "Backend:  http://localhost:8001"
echo "Ollama:   http://localhost:11434"
echo ""
echo "Credenciais padrao:"
echo "  Email: admin@mordomo.local"
echo "  Senha: admin123"
echo ""
echo "IMPORTANTE: Troque a senha e o JWT_SECRET no .env!"
