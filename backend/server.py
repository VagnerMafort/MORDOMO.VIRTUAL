from dotenv import load_dotenv
from pathlib import Path
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from fastapi import FastAPI, APIRouter, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import os, logging, json, asyncio, secrets, uuid, bcrypt, jwt, httpx, re, math
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field
from typing import List, Optional

# ─── Config ───────────────────────────────────────────────────────────────────
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

JWT_ALGORITHM = "HS256"
OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'qwen2.5:32b')
EMERGENT_KEY = os.environ.get('EMERGENT_LLM_KEY', '')

app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ─── Auth Helpers ─────────────────────────────────────────────────────────────
def get_jwt_secret():
    return os.environ["JWT_SECRET"]

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))

def create_access_token(user_id: str, email: str) -> str:
    payload = {"sub": user_id, "email": email, "exp": datetime.now(timezone.utc) + timedelta(minutes=120), "type": "access"}
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)

def create_refresh_token(user_id: str) -> str:
    payload = {"sub": user_id, "exp": datetime.now(timezone.utc) + timedelta(days=7), "type": "refresh"}
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)

async def get_current_user(request: Request) -> dict:
    auth_header = request.headers.get("Authorization", "")
    token = auth_header[7:] if auth_header.startswith("Bearer ") else None
    if not token:
        raise HTTPException(status_code=401, detail="Nao autenticado")
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Token invalido")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="Usuario nao encontrado")
        user["_id"] = str(user["_id"])
        user.pop("password_hash", None)
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token invalido")

# ─── Pydantic Models ─────────────────────────────────────────────────────────
class RegisterInput(BaseModel):
    email: str
    password: str
    name: str

class LoginInput(BaseModel):
    email: str
    password: str

class ConversationCreate(BaseModel):
    title: Optional[str] = "Nova Conversa"
    agent_id: Optional[str] = None

class ConversationUpdate(BaseModel):
    title: str

class MessageCreate(BaseModel):
    content: str

class SettingsUpdate(BaseModel):
    ollama_url: Optional[str] = None
    ollama_model: Optional[str] = None
    tts_enabled: Optional[bool] = None
    tts_language: Optional[str] = None
    skills_enabled: Optional[List[str]] = None

class CredentialCreate(BaseModel):
    name: str
    service: str
    key_value: str

class CredentialUpdate(BaseModel):
    key_value: str

class AgentCreate(BaseModel):
    name: str
    description: str = ""
    icon: str = "Bot"
    system_prompt: str = ""
    skills_enabled: List[str] = []

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    system_prompt: Optional[str] = None
    skills_enabled: Optional[List[str]] = None

class NoteCreate(BaseModel):
    title: str
    content: str = ""
    tags: List[str] = []

class TaskCreate(BaseModel):
    title: str
    description: str = ""
    priority: str = "medium"

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    done: Optional[bool] = None
    priority: Optional[str] = None

# ─── Auth Routes ──────────────────────────────────────────────────────────────
from fastapi.responses import JSONResponse

@api_router.post("/auth/register")
async def register(body: RegisterInput):
    email = body.email.strip().lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="E-mail ja cadastrado")
    user_doc = {
        "email": email,
        "password_hash": hash_password(body.password),
        "name": body.name.strip(),
        "role": "user",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    result = await db.users.insert_one(user_doc)
    user_id = str(result.inserted_id)
    access = create_access_token(user_id, email)
    refresh = create_refresh_token(user_id)
    await db.settings.insert_one({
        "user_id": user_id, "ollama_url": OLLAMA_URL, "ollama_model": OLLAMA_MODEL,
        "tts_enabled": True, "tts_language": "pt-BR",
        "skills_enabled": ["web_scraper", "calculator", "code_runner", "system_info", "datetime_info"]
    })
    return {"user": {"id": user_id, "email": email, "name": body.name.strip(), "role": "user"}, "access_token": access, "refresh_token": refresh}

@api_router.post("/auth/login")
async def login(body: LoginInput):
    email = body.email.strip().lower()
    # Brute force check
    identifier = email
    attempt = await db.login_attempts.find_one({"identifier": identifier})
    if attempt and attempt.get("count", 0) >= 5:
        locked_until = attempt.get("locked_until")
        if locked_until and datetime.now(timezone.utc) < datetime.fromisoformat(locked_until):
            raise HTTPException(status_code=429, detail="Muitas tentativas. Tente novamente em 15 minutos.")
        else:
            await db.login_attempts.delete_one({"identifier": identifier})
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(body.password, user["password_hash"]):
        await db.login_attempts.update_one(
            {"identifier": identifier},
            {"$inc": {"count": 1}, "$set": {"locked_until": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()}},
            upsert=True
        )
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos")
    await db.login_attempts.delete_one({"identifier": identifier})
    user_id = str(user["_id"])
    access = create_access_token(user_id, email)
    refresh = create_refresh_token(user_id)
    return {"user": {"id": user_id, "email": email, "name": user.get("name", ""), "role": user.get("role", "user")}, "access_token": access, "refresh_token": refresh}

@api_router.post("/auth/logout")
async def logout():
    return {"message": "Desconectado"}

@api_router.get("/auth/me")
async def me(request: Request):
    user = await get_current_user(request)
    return user

class RefreshInput(BaseModel):
    refresh_token: str

@api_router.post("/auth/refresh")
async def refresh_token(body: RefreshInput):
    token = body.refresh_token
    if not token:
        raise HTTPException(status_code=401, detail="Sem refresh token")
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Token invalido")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="Usuario nao encontrado")
        user_id = str(user["_id"])
        new_access = create_access_token(user_id, user["email"])
        return {"access_token": new_access}
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token invalido")

# ─── Conversation Routes ─────────────────────────────────────────────────────
@api_router.get("/conversations")
async def list_conversations(request: Request):
    user = await get_current_user(request)
    convos = await db.conversations.find(
        {"user_id": user["_id"]}, {"_id": 0}
    ).sort("updated_at", -1).to_list(100)
    return convos

@api_router.post("/conversations")
async def create_conversation(body: ConversationCreate, request: Request):
    user = await get_current_user(request)
    now = datetime.now(timezone.utc).isoformat()
    conv_id = str(uuid.uuid4())
    doc = {
        "id": conv_id,
        "user_id": user["_id"],
        "title": body.title or "Nova Conversa",
        "agent_id": body.agent_id,
        "created_at": now,
        "updated_at": now
    }
    await db.conversations.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api_router.put("/conversations/{conv_id}")
async def update_conversation(conv_id: str, body: ConversationUpdate, request: Request):
    user = await get_current_user(request)
    result = await db.conversations.update_one(
        {"id": conv_id, "user_id": user["_id"]},
        {"$set": {"title": body.title, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Conversa nao encontrada")
    return {"message": "Atualizado"}

@api_router.delete("/conversations/{conv_id}")
async def delete_conversation(conv_id: str, request: Request):
    user = await get_current_user(request)
    await db.conversations.delete_one({"id": conv_id, "user_id": user["_id"]})
    await db.messages.delete_many({"conversation_id": conv_id})
    return {"message": "Deletado"}

# ─── Message Routes ──────────────────────────────────────────────────────────
@api_router.get("/conversations/{conv_id}/messages")
async def list_messages(conv_id: str, request: Request):
    user = await get_current_user(request)
    conv = await db.conversations.find_one({"id": conv_id, "user_id": user["_id"]})
    if not conv:
        raise HTTPException(status_code=404, detail="Conversa nao encontrada")
    msgs = await db.messages.find({"conversation_id": conv_id}, {"_id": 0}).sort("created_at", 1).to_list(500)
    return msgs

# ─── Skills System ───────────────────────────────────────────────────────────
AVAILABLE_SKILLS = [
    {"id": "code_executor", "name": "Executor de Codigo", "description": "Rodar Python, JS ou Bash com output real", "icon": "Terminal"},
    {"id": "code_generator", "name": "Gerador de Codigo", "description": "Criar scripts e projetos completos", "icon": "Code"},
    {"id": "web_scraper", "name": "Web Scraper", "description": "Extrair e analisar conteudo de paginas web", "icon": "Globe"},
    {"id": "url_summarizer", "name": "Resumidor de URLs", "description": "Resumir artigos e paginas automaticamente", "icon": "FileText"},
    {"id": "file_manager", "name": "Gerenciador de Arquivos", "description": "Criar, ler, editar e deletar arquivos", "icon": "FolderOpen"},
    {"id": "notes_tasks", "name": "Notas e Tarefas", "description": "Gerenciar notas e lista de tarefas", "icon": "ClipboardList"},
    {"id": "api_caller", "name": "Chamadas de API", "description": "Chamar qualquer API REST com GET/POST", "icon": "Zap"},
    {"id": "calculator", "name": "Calculadora", "description": "Calculos matematicos e financeiros avancados", "icon": "Calculator"},
    {"id": "system_info", "name": "Info do Sistema", "description": "Informacoes do sistema operacional", "icon": "Cpu"},
    {"id": "datetime_info", "name": "Data e Hora", "description": "Data, hora e fusos horarios", "icon": "Clock"},
    {"id": "browser_automation", "name": "Automacao Web", "description": "Automatizar acoes no navegador (VPS)", "icon": "Monitor"},
    {"id": "cron_jobs", "name": "Tarefas Agendadas", "description": "Agendar tarefas recorrentes (VPS)", "icon": "Timer"},
    {"id": "email_manager", "name": "Gerenciador de E-mail", "description": "Enviar e ler e-mails (VPS)", "icon": "Mail"},
]

import subprocess, shutil

def get_user_workspace(user_id: str) -> str:
    ws = f"/tmp/novaclaw_ws/{user_id}"
    os.makedirs(ws, exist_ok=True)
    return ws

async def execute_skill(skill_id: str, args: dict, user_id: str = None) -> str:
    try:
        if skill_id == "code_executor":
            code = args.get("code", "")
            lang = args.get("language", "python").lower()
            if lang in ("python", "py"):
                proc = subprocess.run(["python3", "-c", code], capture_output=True, text=True, timeout=15, cwd=get_user_workspace(user_id) if user_id else "/tmp")
            elif lang in ("javascript", "js", "node"):
                proc = subprocess.run(["node", "-e", code], capture_output=True, text=True, timeout=15)
            elif lang in ("bash", "sh"):
                proc = subprocess.run(["bash", "-c", code], capture_output=True, text=True, timeout=15, cwd=get_user_workspace(user_id) if user_id else "/tmp")
            else:
                return f"Linguagem '{lang}' nao suportada. Use: python, javascript, bash"
            output = proc.stdout
            if proc.stderr:
                output += f"\n[STDERR]: {proc.stderr}"
            if proc.returncode != 0:
                output += f"\n[Exit code: {proc.returncode}]"
            return output[:3000] if output.strip() else "Codigo executado sem saida."

        elif skill_id == "code_generator":
            return "SKILL_PASSTHROUGH"

        elif skill_id == "web_scraper":
            url = args.get("url", "")
            selector = args.get("selector", "")
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as c:
                r = await c.get(url, headers={"User-Agent": "Mozilla/5.0 (compatible; NovaClaw/1.0)"})
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(r.text, "html.parser")
                for tag in soup(["script", "style", "nav", "footer", "iframe", "noscript"]):
                    tag.decompose()
                if selector:
                    elements = soup.select(selector)
                    text = "\n".join(el.get_text(strip=True) for el in elements)
                else:
                    text = soup.get_text(separator="\n", strip=True)
                # Also extract links and images
                links = [a.get("href", "") for a in soup.find_all("a", href=True)[:10]]
                result = text[:2500]
                if links:
                    result += "\n\n[Links encontrados]:\n" + "\n".join(links[:10])
                return result

        elif skill_id == "url_summarizer":
            url = args.get("url", "")
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as c:
                r = await c.get(url, headers={"User-Agent": "Mozilla/5.0 (compatible; NovaClaw/1.0)"})
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(r.text, "html.parser")
                title = soup.title.string if soup.title else "Sem titulo"
                for tag in soup(["script", "style", "nav", "footer", "iframe", "noscript", "header"]):
                    tag.decompose()
                paragraphs = soup.find_all(["p", "article", "section"])
                text = "\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
                return f"Titulo: {title}\n\nConteudo extraido ({len(text)} chars):\n{text[:3000]}"

        elif skill_id == "file_manager":
            action = args.get("action", "list")
            ws = get_user_workspace(user_id) if user_id else "/tmp/novaclaw_ws/default"
            filename = args.get("filename", "")
            filepath = os.path.join(ws, filename) if filename else ws

            if action == "list":
                files = []
                for f in os.listdir(ws):
                    full = os.path.join(ws, f)
                    size = os.path.getsize(full) if os.path.isfile(full) else 0
                    ftype = "dir" if os.path.isdir(full) else "file"
                    files.append(f"{ftype}: {f} ({size} bytes)")
                return "\n".join(files) if files else "Workspace vazio."
            elif action == "read":
                if not os.path.exists(filepath):
                    return f"Arquivo '{filename}' nao encontrado."
                with open(filepath, "r") as f:
                    return f.read()[:5000]
            elif action == "write":
                content = args.get("content", "")
                os.makedirs(os.path.dirname(filepath), exist_ok=True) if "/" in filename else None
                with open(filepath, "w") as f:
                    f.write(content)
                return f"Arquivo '{filename}' criado/atualizado ({len(content)} chars)."
            elif action == "delete":
                if os.path.exists(filepath):
                    os.remove(filepath) if os.path.isfile(filepath) else shutil.rmtree(filepath)
                    return f"'{filename}' deletado."
                return f"'{filename}' nao encontrado."
            return "Acao invalida. Use: list, read, write, delete"

        elif skill_id == "notes_tasks":
            return "SKILL_PASSTHROUGH"

        elif skill_id == "calculator":
            expr = args.get("expression", "")
            safe_expr = re.sub(r'[^0-9+\-*/().%\s,]', '', expr)
            allowed = {"abs": abs, "round": round, "min": min, "max": max, "pow": pow,
                       "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan,
                       "pi": math.pi, "e": math.e, "log": math.log, "log10": math.log10}
            result = eval(safe_expr, {"__builtins__": {}}, allowed)
            return f"Resultado: {result}"

        elif skill_id == "api_caller":
            url = args.get("url", "")
            method = args.get("method", "GET").upper()
            headers = args.get("headers", {})
            body = args.get("body", None)
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as c:
                if method == "POST":
                    r = await c.post(url, json=body, headers=headers)
                elif method == "PUT":
                    r = await c.put(url, json=body, headers=headers)
                elif method == "DELETE":
                    r = await c.delete(url, headers=headers)
                else:
                    r = await c.get(url, headers=headers)
                try:
                    data = r.json()
                    return json.dumps(data, indent=2, ensure_ascii=False)[:3000]
                except Exception:
                    return r.text[:3000]

        elif skill_id == "system_info":
            import platform
            info = {"sistema": platform.system(), "versao": platform.version(),
                    "maquina": platform.machine(), "python": platform.python_version(),
                    "hostname": platform.node()}
            # Add disk and memory if available
            try:
                disk = shutil.disk_usage("/")
                info["disco_total"] = f"{disk.total // (1024**3)} GB"
                info["disco_livre"] = f"{disk.free // (1024**3)} GB"
            except Exception:
                pass
            return json.dumps(info, indent=2, ensure_ascii=False)

        elif skill_id == "datetime_info":
            now = datetime.now(timezone.utc)
            return f"Data/Hora UTC: {now.strftime('%d/%m/%Y %H:%M:%S')}\nTimestamp: {now.timestamp()}\nDia da semana: {now.strftime('%A')}"

        else:
            return f"Skill '{skill_id}' disponivel na VPS com acesso completo ao sistema."
    except Exception as e:
        return f"Erro ao executar skill: {str(e)}"

@api_router.get("/skills")
async def list_skills(request: Request):
    user = await get_current_user(request)
    settings = await db.settings.find_one({"user_id": user["_id"]}, {"_id": 0})
    enabled = settings.get("skills_enabled", []) if settings else []
    skills = []
    for s in AVAILABLE_SKILLS:
        skills.append({**s, "enabled": s["id"] in enabled})
    return skills

@api_router.post("/skills/{skill_id}/toggle")
async def toggle_skill(skill_id: str, request: Request):
    user = await get_current_user(request)
    settings = await db.settings.find_one({"user_id": user["_id"]})
    if not settings:
        raise HTTPException(status_code=404, detail="Configuracoes nao encontradas")
    enabled = settings.get("skills_enabled", [])
    if skill_id in enabled:
        enabled.remove(skill_id)
    else:
        enabled.append(skill_id)
    await db.settings.update_one({"user_id": user["_id"]}, {"$set": {"skills_enabled": enabled}})
    return {"enabled": enabled}

# ─── Settings Routes ─────────────────────────────────────────────────────────
@api_router.get("/settings")
async def get_settings(request: Request):
    user = await get_current_user(request)
    settings = await db.settings.find_one({"user_id": user["_id"]}, {"_id": 0})
    if not settings:
        default = {
            "user_id": user["_id"],
            "ollama_url": OLLAMA_URL,
            "ollama_model": OLLAMA_MODEL,
            "tts_enabled": True,
            "tts_language": "pt-BR",
            "skills_enabled": ["web_scraper", "calculator", "code_runner", "system_info", "datetime_info"]
        }
        await db.settings.insert_one(default)
        default.pop("_id", None)
        return default
    return settings

@api_router.put("/settings")
async def update_settings(body: SettingsUpdate, request: Request):
    user = await get_current_user(request)
    update_data = {k: v for k, v in body.model_dump().items() if v is not None}
    if update_data:
        await db.settings.update_one({"user_id": user["_id"]}, {"$set": update_data}, upsert=True)
    settings = await db.settings.find_one({"user_id": user["_id"]}, {"_id": 0})
    return settings

# ─── Credentials Routes ──────────────────────────────────────────────────────
@api_router.get("/credentials")
async def list_credentials(request: Request):
    user = await get_current_user(request)
    creds = await db.credentials.find({"user_id": user["_id"]}, {"_id": 0}).to_list(50)
    # Mask values for security
    for c in creds:
        val = c.get("key_value", "")
        c["key_masked"] = val[:4] + "****" + val[-4:] if len(val) > 8 else "****"
        c.pop("key_value", None)
    return creds

@api_router.post("/credentials")
async def create_credential(body: CredentialCreate, request: Request):
    user = await get_current_user(request)
    cred_id = str(uuid.uuid4())
    doc = {
        "id": cred_id,
        "user_id": user["_id"],
        "name": body.name,
        "service": body.service,
        "key_value": body.key_value,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.credentials.insert_one(doc)
    doc.pop("_id", None)
    doc["key_masked"] = body.key_value[:4] + "****" + body.key_value[-4:] if len(body.key_value) > 8 else "****"
    doc.pop("key_value", None)
    return doc

@api_router.put("/credentials/{cred_id}")
async def update_credential(cred_id: str, body: CredentialUpdate, request: Request):
    user = await get_current_user(request)
    result = await db.credentials.update_one(
        {"id": cred_id, "user_id": user["_id"]},
        {"$set": {"key_value": body.key_value}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Credencial nao encontrada")
    return {"message": "Atualizado"}

@api_router.delete("/credentials/{cred_id}")
async def delete_credential(cred_id: str, request: Request):
    user = await get_current_user(request)
    await db.credentials.delete_one({"id": cred_id, "user_id": user["_id"]})
    return {"message": "Deletado"}

# ─── Telegram Integration ────────────────────────────────────────────────────
class TelegramConnectInput(BaseModel):
    bot_token: str

async def telegram_api(token: str, method: str, data: dict = None):
    """Call Telegram Bot API."""
    url = f"https://api.telegram.org/bot{token}/{method}"
    async with httpx.AsyncClient(timeout=15.0) as c:
        if data:
            r = await c.post(url, json=data)
        else:
            r = await c.get(url)
        return r.json()

async def get_telegram_llm_response(user_id: str, user_text: str) -> str:
    """Process a Telegram message through the LLM pipeline."""
    settings = await db.settings.find_one({"user_id": user_id})
    ollama_url = settings.get("ollama_url", OLLAMA_URL) if settings else OLLAMA_URL
    ollama_model = settings.get("ollama_model", OLLAMA_MODEL) if settings else OLLAMA_MODEL
    # Get recent telegram conversation history for context
    recent = await db.telegram_messages.find(
        {"user_id": user_id}
    ).sort("created_at", -1).limit(10).to_list(10)
    recent.reverse()
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in recent:
        messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": user_text})
    # Try Ollama first, fallback to Emergent
    try:
        full = ""
        async for token in stream_ollama(messages, ollama_url, ollama_model):
            full += token
        return full
    except Exception:
        return await chat_emergent_fallback(messages)

@api_router.post("/telegram/connect")
async def telegram_connect(body: TelegramConnectInput, request: Request):
    """Connect a user's Telegram bot."""
    user = await get_current_user(request)
    token = body.bot_token.strip()
    # Validate token
    result = await telegram_api(token, "getMe")
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail="Token do bot invalido. Verifique com o @BotFather.")
    bot_info = result["result"]
    # Set webhook
    backend_url = os.environ.get("BACKEND_URL", "")
    if not backend_url:
        # Try to construct from request
        backend_url = str(request.base_url).rstrip("/")
    webhook_url = f"{backend_url}/api/telegram/webhook/{user['_id']}"
    wh_result = await telegram_api(token, "setWebhook", {"url": webhook_url})
    if not wh_result.get("ok"):
        logger.warning(f"Webhook set failed: {wh_result}")
    # Store connection
    conn = {
        "user_id": user["_id"],
        "bot_token": token,
        "bot_username": bot_info.get("username", ""),
        "bot_name": bot_info.get("first_name", ""),
        "webhook_url": webhook_url,
        "connected_at": datetime.now(timezone.utc).isoformat(),
        "active": True
    }
    await db.telegram_connections.update_one(
        {"user_id": user["_id"]},
        {"$set": conn},
        upsert=True
    )
    conn.pop("bot_token", None)
    return {"message": "Bot conectado com sucesso!", "bot": conn}

@api_router.get("/telegram/status")
async def telegram_status(request: Request):
    """Get user's Telegram connection status."""
    user = await get_current_user(request)
    conn = await db.telegram_connections.find_one({"user_id": user["_id"]}, {"_id": 0, "bot_token": 0})
    return {"connected": conn is not None and conn.get("active", False), "connection": conn}

@api_router.post("/telegram/disconnect")
async def telegram_disconnect(request: Request):
    """Disconnect user's Telegram bot."""
    user = await get_current_user(request)
    conn = await db.telegram_connections.find_one({"user_id": user["_id"]})
    if conn and conn.get("bot_token"):
        await telegram_api(conn["bot_token"], "deleteWebhook")
    await db.telegram_connections.update_one(
        {"user_id": user["_id"]},
        {"$set": {"active": False}}
    )
    return {"message": "Bot desconectado"}

@api_router.post("/telegram/webhook/{user_id}")
async def telegram_webhook(user_id: str, request: Request):
    """Receive messages from Telegram for a specific user's bot."""
    try:
        update = await request.json()
        message = update.get("message", {})
        text = message.get("text", "")
        chat_id = message.get("chat", {}).get("id")
        if not text or not chat_id:
            return {"ok": True}
        # Get user's bot connection
        conn = await db.telegram_connections.find_one({"user_id": user_id, "active": True})
        if not conn:
            return {"ok": True}
        token = conn["bot_token"]
        # Store user message
        await db.telegram_messages.insert_one({
            "user_id": user_id, "chat_id": chat_id,
            "role": "user", "content": text,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        # Handle /start command
        if text == "/start":
            await telegram_api(token, "sendMessage", {
                "chat_id": chat_id,
                "text": "Ola! Eu sou o NovaClaw, seu mordomo virtual AI. Me pergunte qualquer coisa!"
            })
            return {"ok": True}
        # Send "typing" action
        await telegram_api(token, "sendChatAction", {"chat_id": chat_id, "action": "typing"})
        # Get LLM response
        response = await get_telegram_llm_response(user_id, text)
        # Store AI message
        await db.telegram_messages.insert_one({
            "user_id": user_id, "chat_id": chat_id,
            "role": "assistant", "content": response,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        # Send response (split if too long)
        MAX_LEN = 4000
        if len(response) <= MAX_LEN:
            await telegram_api(token, "sendMessage", {"chat_id": chat_id, "text": response})
        else:
            for i in range(0, len(response), MAX_LEN):
                await telegram_api(token, "sendMessage", {"chat_id": chat_id, "text": response[i:i+MAX_LEN]})
        return {"ok": True}
    except Exception as e:
        logger.error(f"Telegram webhook error: {e}")
        return {"ok": True}

# ─── LLM & Streaming ────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Voce e o NovaClaw, um mordomo virtual AI avancado. Voce executa tarefas reais para o usuario.

## SUAS HABILIDADES (use o formato exato abaixo quando precisar executar):

[SKILL:code_executor] {"code": "print('hello')", "language": "python"}
- Executa Python, JavaScript ou Bash. Parametro "language": "python"|"javascript"|"bash"

[SKILL:web_scraper] {"url": "https://example.com", "selector": ""}
- Extrai conteudo de uma pagina. "selector" CSS opcional (ex: ".article-body", "h1")

[SKILL:url_summarizer] {"url": "https://example.com"}
- Extrai e retorna o conteudo principal de um artigo/pagina para voce resumir

[SKILL:file_manager] {"action": "write", "filename": "script.py", "content": "print('hi')"}
- Acoes: "list" (listar workspace), "read" (ler arquivo), "write" (criar/editar), "delete"

[SKILL:calculator] {"expression": "sqrt(144) + pow(2,10)"}
- Calculos com: sqrt, sin, cos, tan, log, log10, pi, e, pow, abs, round, min, max

[SKILL:api_caller] {"url": "https://api.example.com/data", "method": "GET", "headers": {}, "body": null}
- Metodos: GET, POST, PUT, DELETE

[SKILL:system_info] {}
- Retorna info do sistema (OS, RAM, disco, Python version)

[SKILL:datetime_info] {}
- Data e hora atual

## REGRAS:
- Quando o usuario pedir para executar, rodar, ou criar algo, USE A SKILL APROPRIADA
- Quando pedir para analisar codigo, analise diretamente sem executar
- Para criar arquivos ou projetos, use file_manager com action "write"
- Responda SEMPRE em portugues brasileiro
- Use markdown para formatacao
- Seja proativo: se pode resolver com uma skill, use-a"""

def build_messages(history: list, user_msg: str) -> list:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in history[-20:]:
        messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": user_msg})
    return messages

async def stream_ollama(messages: list, ollama_url: str, model: str):
    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0)) as c:
        async with c.stream("POST", f"{ollama_url}/api/chat", json={"model": model, "messages": messages, "stream": True}) as r:
            async for line in r.aiter_lines():
                if line:
                    data = json.loads(line)
                    content = data.get("message", {}).get("content", "")
                    if content:
                        yield content
                    if data.get("done"):
                        break

async def chat_emergent_fallback(messages: list) -> str:
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        # Build system message and history
        system_msg = ""
        history = []
        user_text = ""
        for m in messages:
            if m["role"] == "system":
                system_msg = m["content"]
            elif m["role"] == "user":
                user_text = m["content"]
                history.append({"role": "user", "content": m["content"]})
            elif m["role"] == "assistant":
                history.append({"role": "assistant", "content": m["content"]})
        chat = LlmChat(
            api_key=EMERGENT_KEY,
            session_id=str(uuid.uuid4()),
            system_message=system_msg or "Voce e o NovaClaw, um assistente AI pessoal.",
            initial_messages=history[:-1] if len(history) > 1 else []
        )
        chat = chat.with_model("openai", "gpt-4o-mini")
        response = await chat.send_message(UserMessage(text=user_text))
        return response
    except Exception as e:
        logger.error(f"Emergent fallback error: {e}")
        return f"Desculpe, ocorreu um erro ao processar sua mensagem. Erro: {str(e)}"

async def process_skill_calls(text: str, user_id: str = None) -> tuple:
    """Check for skill calls in LLM response and execute them."""
    skill_pattern = r'\[SKILL:(\w+)\]\s*(\{[^}]*\})'
    matches = re.findall(skill_pattern, text)
    if not matches:
        return text, []
    skill_results = []
    for skill_id, args_str in matches:
        try:
            args = json.loads(args_str)
        except json.JSONDecodeError:
            args = {}
        result = await execute_skill(skill_id, args, user_id)
        if result == "SKILL_PASSTHROUGH":
            continue
        skill_results.append({"skill": skill_id, "args": args, "result": result})
        text = text.replace(f"[SKILL:{skill_id}] {args_str}", f"\n**[Executando: {skill_id}]**\n```\n{result}\n```\n")
    return text, skill_results

@api_router.post("/conversations/{conv_id}/messages")
async def send_message(conv_id: str, body: MessageCreate, request: Request):
    user = await get_current_user(request)
    conv = await db.conversations.find_one({"id": conv_id, "user_id": user["_id"]})
    if not conv:
        raise HTTPException(status_code=404, detail="Conversa nao encontrada")
    now = datetime.now(timezone.utc).isoformat()
    user_msg_id = str(uuid.uuid4())
    await db.messages.insert_one({
        "id": user_msg_id, "conversation_id": conv_id,
        "role": "user", "content": body.content, "created_at": now
    })
    # Update conversation title if first message
    msg_count = await db.messages.count_documents({"conversation_id": conv_id})
    if msg_count <= 1:
        title = body.content[:50] + ("..." if len(body.content) > 50 else "")
        await db.conversations.update_one({"id": conv_id}, {"$set": {"title": title, "updated_at": now}})
    # Get history
    history = await db.messages.find({"conversation_id": conv_id}, {"_id": 0}).sort("created_at", 1).to_list(100)
    # Get user settings
    settings = await db.settings.find_one({"user_id": user["_id"]})
    ollama_url = settings.get("ollama_url", OLLAMA_URL) if settings else OLLAMA_URL
    ollama_model = settings.get("ollama_model", OLLAMA_MODEL) if settings else OLLAMA_MODEL
    messages = build_messages(history[:-1], body.content)

    # If conversation has an agent, use agent's system prompt
    agent_prompt = None
    if conv.get("agent_id"):
        agent = await db.agents.find_one({"id": conv["agent_id"]})
        if agent and agent.get("system_prompt"):
            agent_prompt = agent["system_prompt"]
    if agent_prompt:
        messages[0] = {"role": "system", "content": agent_prompt}

    ai_msg_id = str(uuid.uuid4())

    async def event_stream():
        full_response = ""
        try:
            async for token in stream_ollama(messages, ollama_url, ollama_model):
                full_response += token
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
        except Exception as e:
            logger.info(f"Ollama unavailable ({e}), using fallback...")
            yield f"data: {json.dumps({'type': 'status', 'content': 'Usando modelo de fallback...'})}\n\n"
            response_text = await chat_emergent_fallback(messages)
            # Check for skill calls
            response_text, skill_results = await process_skill_calls(response_text, user["_id"])
            for sr in skill_results:
                yield f"data: {json.dumps({'type': 'skill', 'skill': sr['skill'], 'result': sr['result']})}\n\n"
            # Stream the response in chunks to simulate streaming
            for i in range(0, len(response_text), 4):
                chunk = response_text[i:i+4]
                full_response += chunk
                yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
                await asyncio.sleep(0.015)

        # Check for skill calls in streamed response
        if full_response and not full_response.startswith(""):
            processed, skill_results = await process_skill_calls(full_response, user["_id"])
            if skill_results:
                full_response = processed
                for sr in skill_results:
                    yield f"data: {json.dumps({'type': 'skill', 'skill': sr['skill'], 'result': sr['result']})}\n\n"

        # Store AI message
        await db.messages.insert_one({
            "id": ai_msg_id, "conversation_id": conv_id,
            "role": "assistant", "content": full_response, "created_at": datetime.now(timezone.utc).isoformat()
        })
        await db.conversations.update_one({"id": conv_id}, {"$set": {"updated_at": datetime.now(timezone.utc).isoformat()}})
        yield f"data: {json.dumps({'type': 'done', 'message_id': ai_msg_id})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

# ─── Agents System ───────────────────────────────────────────────────────────
AGENT_TEMPLATES = [
    {"id": "coder", "name": "Dev Expert", "icon": "Code", "description": "Especialista em programacao - cria, analisa e roda codigo",
     "system_prompt": "Voce e um especialista em programacao. Crie, analise, debug e execute codigo. Use [SKILL:code_executor] para rodar e [SKILL:file_manager] para criar arquivos. Sempre mostre o codigo e o output real. Responda em PT-BR."},
    {"id": "researcher", "name": "Pesquisador Web", "icon": "Search", "description": "Pesquisa e extrai informacoes da web",
     "system_prompt": "Voce e um pesquisador expert. Use [SKILL:web_scraper] e [SKILL:url_summarizer] para extrair dados da web. Use [SKILL:api_caller] para APIs publicas. Sempre cite as fontes. Responda em PT-BR."},
    {"id": "analyst", "name": "Analista de Dados", "icon": "BarChart3", "description": "Analisa dados, metricas e faz calculos complexos",
     "system_prompt": "Voce e um analista de dados. Use [SKILL:calculator] para calculos, [SKILL:code_executor] com pandas/matplotlib para analises, [SKILL:api_caller] para buscar dados. Crie visualizacoes e relatorios. Responda em PT-BR."},
    {"id": "automator", "name": "Automatizador", "icon": "Workflow", "description": "Cria automacoes e scripts para tarefas repetitivas",
     "system_prompt": "Voce e um especialista em automacao. Crie scripts que automatizem tarefas. Use [SKILL:code_executor] para testar, [SKILL:file_manager] para salvar scripts, [SKILL:api_caller] para integracoes. Responda em PT-BR."},
]

@api_router.get("/agents")
async def list_agents(request: Request):
    user = await get_current_user(request)
    agents = await db.agents.find({"user_id": user["_id"]}, {"_id": 0}).to_list(50)
    return {"custom": agents, "templates": AGENT_TEMPLATES}

@api_router.post("/agents")
async def create_agent(body: AgentCreate, request: Request):
    user = await get_current_user(request)
    agent_id = str(uuid.uuid4())
    doc = {
        "id": agent_id, "user_id": user["_id"],
        "name": body.name, "description": body.description,
        "icon": body.icon, "system_prompt": body.system_prompt,
        "skills_enabled": body.skills_enabled,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.agents.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api_router.post("/agents/from-template/{template_id}")
async def create_agent_from_template(template_id: str, request: Request):
    user = await get_current_user(request)
    tmpl = next((t for t in AGENT_TEMPLATES if t["id"] == template_id), None)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template nao encontrado")
    agent_id = str(uuid.uuid4())
    doc = {
        "id": agent_id, "user_id": user["_id"],
        "name": tmpl["name"], "description": tmpl["description"],
        "icon": tmpl["icon"], "system_prompt": tmpl["system_prompt"],
        "skills_enabled": [],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.agents.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api_router.put("/agents/{agent_id}")
async def update_agent(agent_id: str, body: AgentUpdate, request: Request):
    user = await get_current_user(request)
    update_data = {k: v for k, v in body.model_dump().items() if v is not None}
    if update_data:
        await db.agents.update_one({"id": agent_id, "user_id": user["_id"]}, {"$set": update_data})
    agent = await db.agents.find_one({"id": agent_id, "user_id": user["_id"]}, {"_id": 0})
    return agent

@api_router.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str, request: Request):
    user = await get_current_user(request)
    await db.agents.delete_one({"id": agent_id, "user_id": user["_id"]})
    return {"message": "Agente deletado"}

# ─── Notes & Tasks ───────────────────────────────────────────────────────────
@api_router.get("/notes")
async def list_notes(request: Request):
    user = await get_current_user(request)
    notes = await db.notes.find({"user_id": user["_id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return notes

@api_router.post("/notes")
async def create_note(body: NoteCreate, request: Request):
    user = await get_current_user(request)
    note_id = str(uuid.uuid4())
    doc = {"id": note_id, "user_id": user["_id"], "title": body.title,
           "content": body.content, "tags": body.tags, "created_at": datetime.now(timezone.utc).isoformat()}
    await db.notes.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api_router.delete("/notes/{note_id}")
async def delete_note(note_id: str, request: Request):
    user = await get_current_user(request)
    await db.notes.delete_one({"id": note_id, "user_id": user["_id"]})
    return {"message": "Nota deletada"}

@api_router.get("/tasks")
async def list_tasks(request: Request):
    user = await get_current_user(request)
    tasks = await db.tasks.find({"user_id": user["_id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return tasks

@api_router.post("/tasks")
async def create_task(body: TaskCreate, request: Request):
    user = await get_current_user(request)
    task_id = str(uuid.uuid4())
    doc = {"id": task_id, "user_id": user["_id"], "title": body.title,
           "description": body.description, "priority": body.priority, "done": False,
           "created_at": datetime.now(timezone.utc).isoformat()}
    await db.tasks.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api_router.put("/tasks/{task_id}")
async def update_task(task_id: str, body: TaskUpdate, request: Request):
    user = await get_current_user(request)
    update_data = {k: v for k, v in body.model_dump().items() if v is not None}
    await db.tasks.update_one({"id": task_id, "user_id": user["_id"]}, {"$set": update_data})
    task = await db.tasks.find_one({"id": task_id, "user_id": user["_id"]}, {"_id": 0})
    return task

@api_router.delete("/tasks/{task_id}")
async def delete_task(task_id: str, request: Request):
    user = await get_current_user(request)
    await db.tasks.delete_one({"id": task_id, "user_id": user["_id"]})
    return {"message": "Tarefa deletada"}

# ─── Health & Root ───────────────────────────────────────────────────────────
@api_router.get("/")
async def root():
    return {"message": "NovaClaw API", "version": "1.0.0"}

@api_router.get("/health")
async def health():
    ollama_ok = False
    try:
        async with httpx.AsyncClient(timeout=3.0) as c:
            r = await c.get(f"{OLLAMA_URL}/api/tags")
            ollama_ok = r.status_code == 200
    except Exception:
        pass
    return {"status": "online", "ollama": ollama_ok, "fallback": bool(EMERGENT_KEY)}

# ─── Include Router & Middleware ─────────────────────────────────────────────
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Startup ─────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    # Indexes
    await db.users.create_index("email", unique=True)
    await db.conversations.create_index([("user_id", 1), ("updated_at", -1)])
    await db.messages.create_index([("conversation_id", 1), ("created_at", 1)])
    await db.settings.create_index("user_id", unique=True)
    await db.login_attempts.create_index("identifier")
    await db.credentials.create_index([("user_id", 1), ("service", 1)])
    await db.telegram_connections.create_index("user_id", unique=True)
    await db.telegram_messages.create_index([("user_id", 1), ("created_at", -1)])
    await db.agents.create_index([("user_id", 1)])
    await db.notes.create_index([("user_id", 1), ("created_at", -1)])
    await db.tasks.create_index([("user_id", 1), ("created_at", -1)])
    # Seed admin
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@novaclaw.com")
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
    existing = await db.users.find_one({"email": admin_email})
    if not existing:
        hashed = hash_password(admin_password)
        result = await db.users.insert_one({
            "email": admin_email, "password_hash": hashed,
            "name": "Admin", "role": "admin",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        user_id = str(result.inserted_id)
        await db.settings.insert_one({
            "user_id": user_id, "ollama_url": OLLAMA_URL, "ollama_model": OLLAMA_MODEL,
            "tts_enabled": True, "tts_language": "pt-BR",
            "skills_enabled": ["web_scraper", "calculator", "code_runner", "system_info", "datetime_info"]
        })
        logger.info(f"Admin criado: {admin_email}")
    elif not verify_password(admin_password, existing["password_hash"]):
        await db.users.update_one({"email": admin_email}, {"$set": {"password_hash": hash_password(admin_password)}})
        logger.info("Senha do admin atualizada")
    # Write test credentials
    try:
        os.makedirs("/app/memory", exist_ok=True)
        with open("/app/memory/test_credentials.md", "w") as f:
            f.write(f"# Test Credentials\n\n## Admin\n- Email: {admin_email}\n- Password: {admin_password}\n- Role: admin\n\n## Auth Endpoints\n- POST /api/auth/register\n- POST /api/auth/login\n- POST /api/auth/logout\n- GET /api/auth/me\n- POST /api/auth/refresh\n")
    except Exception:
        pass

@app.on_event("shutdown")
async def shutdown():
    client.close()
