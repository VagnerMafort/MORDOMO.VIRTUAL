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
EMERGENT_KEY = ""  # Removido - deploy 100% independente (somente Ollama local)

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
        if user.get("blocked"):
            raise HTTPException(status_code=403, detail="Conta bloqueada. Contate o administrador.")
        user["_id"] = str(user["_id"])
        user.pop("password_hash", None)
        # Track session (fire-and-forget)
        try:
            import admin as admin_mod
            await admin_mod.track_session(user["_id"], user.get("email", ""), request)
        except Exception:
            pass
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
    ollama_model_fast: Optional[str] = None
    ollama_model_smart: Optional[str] = None
    tts_enabled: Optional[bool] = None
    tts_language: Optional[str] = None
    voice_profile: Optional[str] = None
    voice_speed: Optional[float] = None
    skills_enabled: Optional[List[str]] = None
    agent_name: Optional[str] = None
    agent_personality: Optional[str] = None
    wake_word_enabled: Optional[bool] = None

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
        "allowed_modules": ["chat", "handsfree", "mentorship", "telegram", "agents", "skills", "monitor", "workflows", "social"],
        "blocked": False,
        "quota": {},
        "login_count": 0,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    result = await db.users.insert_one(user_doc)
    user_id = str(result.inserted_id)
    access = create_access_token(user_id, email)
    refresh = create_refresh_token(user_id)
    await db.settings.insert_one({
        "user_id": user_id, "ollama_url": OLLAMA_URL, "ollama_model": OLLAMA_MODEL,
        "tts_enabled": True, "tts_language": "pt-BR",
        "skills_enabled": ["code_executor", "web_scraper", "web_search", "url_summarizer", "file_manager", "calculator", "api_caller", "system_info", "datetime_info"],
        "agent_name": "Kaelum.AI",
        "agent_personality": ""
    })
    return {"user": {"id": user_id, "email": email, "name": body.name.strip(), "role": "user"}, "access_token": access, "refresh_token": refresh}

@api_router.post("/auth/login")
async def login(body: LoginInput, request: Request):
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
    if user.get("blocked"):
        raise HTTPException(status_code=403, detail="Conta bloqueada. Contate o administrador.")
    await db.login_attempts.delete_one({"identifier": identifier})
    user_id = str(user["_id"])
    # Update last_login + login_count
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"last_login": datetime.now(timezone.utc).isoformat()}, "$inc": {"login_count": 1}}
    )
    # Audit
    try:
        import admin as admin_mod
        await admin_mod.log_audit(user_id, "auth.login", user_id, {}, ip=(request.client.host if request.client else ""), user_email=email)
    except Exception:
        pass
    access = create_access_token(user_id, email)
    refresh = create_refresh_token(user_id)
    return {"user": {"id": user_id, "email": email, "name": user.get("name", ""), "role": user.get("role", "user"), "allowed_modules": user.get("allowed_modules", [])}, "access_token": access, "refresh_token": refresh}

@api_router.post("/auth/logout")
async def logout():
    return {"message": "Desconectado"}

@api_router.get("/auth/me")
async def me(request: Request):
    user = await get_current_user(request)
    # Garantir allowed_modules no retorno
    full = await db.users.find_one({"_id": ObjectId(user["_id"])})
    if full:
        user["allowed_modules"] = full.get("allowed_modules", [])
        user["blocked"] = full.get("blocked", False)
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
    {"id": "web_search", "name": "Pesquisa na Internet", "description": "Buscar informacoes atuais na web em tempo real", "icon": "Search"},
    {"id": "browser_automation", "name": "Automacao Web", "description": "Automatizar acoes no navegador (VPS)", "icon": "Monitor"},
    {"id": "cron_jobs", "name": "Tarefas Agendadas", "description": "Agendar tarefas recorrentes (VPS)", "icon": "Timer"},
    {"id": "email_manager", "name": "Gerenciador de E-mail", "description": "Enviar e ler e-mails (VPS)", "icon": "Mail"},
    {"id": "gmail", "name": "Gmail", "description": "Ler e enviar emails pela sua conta Google", "icon": "Mail"},
    {"id": "drive", "name": "Google Drive", "description": "Listar, criar pastas e fazer upload no Drive", "icon": "HardDrive"},
    {"id": "sheets", "name": "Google Sheets", "description": "Criar e ler planilhas", "icon": "FileSpreadsheet"},
    {"id": "calendar", "name": "Google Calendar", "description": "Listar e criar eventos na agenda", "icon": "Calendar"},
    {"id": "youtube", "name": "YouTube", "description": "Buscar videos, listar seu canal e ler comentarios", "icon": "Youtube"},
    {"id": "workflow", "name": "Fluxos de Trabalho", "description": "Executar fluxos salvos (encadeia varias skills)", "icon": "Workflow"},
    {"id": "social_publish", "name": "Publicar em Redes Sociais", "description": "Publica video/midia em multiplas redes de uma vez", "icon": "Share2"},
    {"id": "instagram", "name": "Instagram", "description": "Publica no IG Business (foto/Reels)", "icon": "Instagram"},
    {"id": "facebook", "name": "Facebook Pages", "description": "Publica post em Facebook Page", "icon": "Facebook"},
    {"id": "whatsapp", "name": "WhatsApp Business", "description": "Envia mensagens via WhatsApp Cloud API", "icon": "MessageCircle"},
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

        elif skill_id == "web_search":
            import web_search as ws_mod
            query = args.get("query", "").strip()
            if not query:
                return "Erro: informe 'query' para buscar"
            results = await ws_mod.web_search(query, max_results=5)
            return ws_mod.format_results_for_llm(results, query)

        elif skill_id in ("gmail", "drive", "sheets", "calendar", "youtube"):
            import google_skills as gs
            handler = {"gmail": gs.execute_gmail, "drive": gs.execute_drive,
                       "sheets": gs.execute_sheets, "calendar": gs.execute_calendar,
                       "youtube": gs.execute_youtube}[skill_id]
            return await handler(args, user_id)

        elif skill_id == "browser_automation":
            import web_automation as wa
            return await wa.execute_browser_automation(args, user_id)

        elif skill_id == "workflow":
            import workflows as wf_mod
            return await wf_mod.execute_workflow_skill(args, user_id)

        elif skill_id == "social_publish":
            import social_publisher as sp
            return await sp.execute_social_publish(args, user_id)

        elif skill_id == "instagram":
            import meta_skills as ms
            return await ms.execute_instagram(args, user_id)

        elif skill_id == "facebook":
            import meta_skills as ms
            return await ms.execute_facebook(args, user_id)

        elif skill_id == "whatsapp":
            import meta_skills as ms
            return await ms.execute_whatsapp(args, user_id)

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
            "agent_name": "Kaelum.AI",
            "agent_personality": "",
            "skills_enabled": ["code_executor", "web_scraper", "web_search", "url_summarizer", "file_manager", "calculator", "api_caller", "system_info", "datetime_info"],
        }
        await db.settings.insert_one(default)
        default.pop("_id", None)
        return default
    # Ensure new fields have defaults for existing users
    if "agent_name" not in settings:
        settings["agent_name"] = "NovaClaw"
    if "agent_personality" not in settings:
        settings["agent_personality"] = ""
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
    """Process a Telegram message through the LLM pipeline with smart memory."""
    import smart_llm
    settings = await db.settings.find_one({"user_id": user_id})
    model, ollama_url, complexity = smart_llm.get_model_for_task(user_text, settings)

    # Check cache
    cached = await smart_llm.get_cached_response(user_text, f"tg_{user_id}")
    if cached:
        return cached

    # Build context with memory from telegram messages
    recent = await db.telegram_messages.find({"user_id": user_id}).sort("created_at", -1).limit(10).to_list(10)
    recent.reverse()

    # Also search for relevant old messages if referencing past
    old_triggers = ["lembra", "falamos", "antes", "anterior", "voltando"]
    extra_context = ""
    if any(t in user_text.lower() for t in old_triggers):
        keywords = smart_llm.extract_keywords(user_text)
        if keywords:
            old_filter = {"user_id": user_id, "$or": [{"content": {"$regex": kw, "$options": "i"}} for kw in keywords[:3]]}
            old_msgs = await db.telegram_messages.find(old_filter).sort("created_at", -1).limit(5).to_list(5)
            if old_msgs:
                extra_context = "\n[Contexto anterior]: " + " | ".join([m["content"][:100] for m in old_msgs])

    # Also pull from web conversations for cross-system memory
    user_convs = await db.conversations.find({"user_id": user_id}, {"id": 1, "_id": 0}).to_list(20)
    conv_ids = [c["id"] for c in user_convs]
    if conv_ids:
        keywords = smart_llm.extract_keywords(user_text)
        if keywords:
            cross = await db.messages.find({
                "conversation_id": {"$in": conv_ids}, "role": "assistant",
                "$or": [{"content": {"$regex": kw, "$options": "i"}} for kw in keywords[:2]]
            }).limit(2).to_list(2)
            if cross:
                extra_context += "\n[Conhecimento de conversas web]: " + " | ".join([m["content"][:150] for m in cross])

    system = SYSTEM_PROMPT
    if extra_context:
        system += extra_context

    messages = [{"role": "system", "content": system}]
    for m in recent:
        messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": user_text})

    try:
        full = ""
        async for token in stream_ollama(messages, ollama_url, model):
            full += token
        if full:
            await smart_llm.set_cached_response(user_text, full, f"tg_{user_id}", complexity)
        return full
    except Exception:
        result = await chat_emergent_fallback(messages)
        if result:
            await smart_llm.set_cached_response(user_text, result, f"tg_{user_id}", complexity)
        return result

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

[SKILL:gmail] {"action":"list","query":"is:unread","max":5}
- Acoes: "list" (query gmail opcional), "send" (to, subject, body)

[SKILL:drive] {"action":"list","query":"nome parcial"}
- Acoes: "list" (query opcional), "create_folder" (name)

[SKILL:sheets] {"action":"create","title":"Minha Planilha","values":[["Col A","Col B"],["1","2"]]}
- Acoes: "create" (title + values opcionais), "read" (spreadsheet_id, range)

[SKILL:calendar] {"action":"list","days_ahead":7}
- Acoes: "list" (days_ahead), "create" (summary, start_iso, end_iso, description)

[SKILL:youtube] {"action":"my_videos","max":10}
- Acoes: "my_videos", "search" (query), "comments" (video_id)

[SKILL:browser_automation] {"url":"https://...", "actions":[{"type":"fill","selector":"#q","value":"x"},{"type":"click","selector":"#go"},{"type":"extract","selector":".result","as":"text","var":"resultado"}]}
- Automacao web real via Playwright. Types: goto, fill, click, press, wait, wait_for, extract, screenshot, scroll

[SKILL:workflow] {"name":"rotina_matinal"}
- Executa um fluxo salvo pelo usuario (serie de passos pre-configurados)

[SKILL:social_publish] {"title":"Meu video","description":"...","media_url":"https://...","networks":["youtube"]}
- Publica um video/midia em varias redes de uma vez (YouTube ja funciona; Insta/TikTok/WhatsApp em breve)

[SKILL:instagram] {"action":"publish","page_id":"...","caption":"...","image_url":"https://..."}
- Acoes: "list" (contas IG disponiveis), "publish" (precisa page_id + image_url ou video_url)

[SKILL:facebook] {"action":"publish","page_id":"...","message":"..."}
- Acoes: "list_pages", "publish" (precisa page_id + message, link opcional)

[SKILL:whatsapp] {"action":"send","phone_number_id":"...","to":"5511...","text":"Ola!"}
- Envia mensagem WhatsApp Business (to sem '+', formato E.164)

## REGRAS:
- Quando o usuario pedir para executar, rodar, ou criar algo, USE A SKILL APROPRIADA
- Quando pedir para analisar codigo, analise diretamente sem executar
- Para criar arquivos ou projetos, use file_manager com action "write"
- Responda SEMPRE em portugues brasileiro
- Use markdown para formatacao
- Seja proativo: se pode resolver com uma skill, use-a"""

def build_messages(history: list, user_msg: str, custom_prompt: str = None) -> list:
    prompt = custom_prompt if custom_prompt else SYSTEM_PROMPT
    messages = [{"role": "system", "content": prompt}]
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
    """Fallback desativado - deploy 100% Ollama local."""
    return "Erro: Ollama local indisponivel. Verifique se o servico Ollama esta rodando e o modelo foi baixado. Use: docker exec mordomo-ollama ollama list"

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
    # Quota check
    import admin as admin_mod
    if not await admin_mod.check_quota(user["_id"], "messages"):
        raise HTTPException(status_code=429, detail="Cota diária de mensagens atingida. Contate o administrador.")
    conv = await db.conversations.find_one({"id": conv_id, "user_id": user["_id"]})
    if not conv:
        raise HTTPException(status_code=404, detail="Conversa nao encontrada")
    # Incrementa contador de uso
    await admin_mod.increment_usage(user["_id"], "messages", 1)
    now = datetime.now(timezone.utc).isoformat()
    user_msg_id = str(uuid.uuid4())
    await db.messages.insert_one({
        "id": user_msg_id, "conversation_id": conv_id,
        "role": "user", "content": body.content, "created_at": now
    })
    msg_count = await db.messages.count_documents({"conversation_id": conv_id})
    if msg_count <= 1:
        title = body.content[:50] + ("..." if len(body.content) > 50 else "")
        await db.conversations.update_one({"id": conv_id}, {"$set": {"title": title, "updated_at": now}})

    settings = await db.settings.find_one({"user_id": user["_id"]})

    # Smart model selection
    import smart_llm
    model, ollama_url, complexity = smart_llm.get_model_for_task(body.content, settings)

    # Check cache first
    cached = await smart_llm.get_cached_response(body.content)

    # Determine system prompt
    custom_prompt = None
    if conv.get("agent_id"):
        agent = await db.agents.find_one({"id": conv["agent_id"]})
        if agent and agent.get("system_prompt"):
            custom_prompt = agent["system_prompt"]
    elif settings and settings.get("agent_personality"):
        agent_name = settings.get("agent_name", "Kaelum.AI")
        personality = settings["agent_personality"]
        custom_prompt = f"Voce e o {agent_name}. {personality}\n\n" + SYSTEM_PROMPT.split("## SUAS HABILIDADES", 1)[-1] if "## SUAS HABILIDADES" in SYSTEM_PROMPT else f"Voce e o {agent_name}. {personality}\n\nResponda sempre em portugues brasileiro."

    # Build context with smart memory
    memory_context = await smart_llm.build_memory_context(conv_id, body.content, user["_id"])

    # Build final messages
    messages = [{"role": "system", "content": custom_prompt or SYSTEM_PROMPT}]
    messages.extend(memory_context)
    messages.append({"role": "user", "content": body.content})

    ai_msg_id = str(uuid.uuid4())

    async def event_stream():
        full_response = ""
        # Send model info
        model_label = "rapido" if complexity == "fast" else "inteligente"
        model_short = model.split(":")[0]
        yield f"data: {json.dumps({'type': 'status', 'content': f'Modelo {model_label} ({model_short})'})}\n\n"

        # Use cache if available
        if cached:
            yield f"data: {json.dumps({'type': 'status', 'content': 'Resposta do cache'})}\n\n"
            for i in range(0, len(cached), 6):
                chunk = cached[i:i+6]
                full_response += chunk
                yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
                await asyncio.sleep(0.01)
        else:
            try:
                async for token in stream_ollama(messages, ollama_url, model):
                    full_response += token
                    yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
            except Exception as e:
                logger.info(f"Ollama unavailable ({e}), using fallback...")
                yield f"data: {json.dumps({'type': 'status', 'content': 'Usando fallback...'})}\n\n"
                response_text = await chat_emergent_fallback(messages)
                response_text, skill_results = await process_skill_calls(response_text, user["_id"])
                for sr in skill_results:
                    yield f"data: {json.dumps({'type': 'skill', 'skill': sr['skill'], 'result': sr['result']})}\n\n"
                for i in range(0, len(response_text), 4):
                    chunk = response_text[i:i+4]
                    full_response += chunk
                    yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
                    await asyncio.sleep(0.015)

        # Process skills
        if full_response:
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

        # Cache response
        if not cached and full_response:
            await smart_llm.set_cached_response(body.content, full_response, "", complexity)

        # Update conversation summary every 5 messages
        await smart_llm.maybe_create_summary(conv_id, user["_id"])

        yield f"data: {json.dumps({'type': 'done', 'message_id': ai_msg_id})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

# ─── Agents System ───────────────────────────────────────────────────────────
AGENT_TEMPLATES = [
    # --- SQUAD 1: CORE & GOVERNANCE ---
    {"id": "orion", "name": "ORION - Orquestrador", "icon": "Workflow", "description": "Supervisor geral do sistema. Recebe eventos, monta contexto, seleciona agentes e coordena toda a operacao.",
     "system_prompt": "Voce e ORION, o orquestrador central da agencia de marketing. Seu papel e receber relatorios, detectar anomalias, priorizar problemas e coordenar os outros agentes. Voce seleciona qual agente deve atuar, cria planos de acao e valida resultados. Responda em PT-BR."},
    {"id": "sentinel", "name": "SENTINEL - Seguranca", "icon": "Shield", "description": "Seguranca e controle de risco. Bloqueia acoes perigosas e garante rollback.",
     "system_prompt": "Voce e SENTINEL, responsavel por seguranca e guardrails. Valide limites de alteracao, bloqueie acoes perigosas, garanta rollback para toda acao. Nada executa sem validacao. Responda em PT-BR."},
    {"id": "exec_agent", "name": "EXEC - Executor", "icon": "Play", "description": "Executor operacional. Realiza as acoes decididas pelos outros agentes.",
     "system_prompt": "Voce e EXEC, o executor operacional. Receba planos de acao e execute-os. Use [SKILL:code_executor] para scripts, [SKILL:api_caller] para APIs, [SKILL:file_manager] para arquivos. Confirme execucao e reporte resultado. Responda em PT-BR."},
    # --- SQUAD 2: DATA & DIAGNOSTICS ---
    {"id": "dash", "name": "DASH - Diagnostico", "icon": "BarChart3", "description": "Diagnostico de performance. Detecta anomalias em CTR, CPA, conversao, fadiga criativa.",
     "system_prompt": "Voce e DASH, especialista em diagnostico de performance. Analise metricas (CTR, CPC, CPA, ROAS, CVR), detecte anomalias, queda de conversao, fadiga criativa, erros de tracking. Use [SKILL:calculator] para calculos e [SKILL:api_caller] para buscar dados. Responda em PT-BR."},
    {"id": "track", "name": "TRACK - Tracking", "icon": "Crosshair", "description": "Auditoria de tracking e pixels. Verifica se todos os eventos estao disparando corretamente.",
     "system_prompt": "Voce e TRACK, auditor de tracking. Verifique pixels (Meta, Google, TikTok), UTMs, eventos de conversao, postback. Use [SKILL:web_scraper] para verificar paginas e [SKILL:code_executor] para validar scripts. Responda em PT-BR."},
    {"id": "attrib", "name": "ATTRIB - Atribuicao", "icon": "GitBranch", "description": "Auditoria de atribuicao. Analisa modelos de atribuicao e identifica discrepancias.",
     "system_prompt": "Voce e ATTRIB, especialista em atribuicao. Compare dados entre plataformas de ads e analytics, identifique discrepancias, sugira modelos de atribuicao adequados. Use [SKILL:calculator] e [SKILL:api_caller]. Responda em PT-BR."},
    # --- SQUAD 3: TRAFFIC ---
    {"id": "midas", "name": "MIDAS - Performance", "icon": "DollarSign", "description": "Performance e orcamento. Otimiza gastos, redistribui budget e escala campanhas.",
     "system_prompt": "Voce e MIDAS, gestor de performance e orcamento. Analise ROAS, CPA, distribua budget entre campanhas, decida escalar ou pausar. Calcule break-even, LTV, CAC. Use [SKILL:calculator] para calculos financeiros. Responda em PT-BR."},
    # --- SQUAD 4: FUNNEL & SALES ---
    {"id": "hunter", "name": "HUNTER - Funil", "icon": "Target", "description": "Estrategista de funil. Mapeia jornada, identifica gargalos e otimiza conversao.",
     "system_prompt": "Voce e HUNTER, estrategista de funil. Mapeie TOFU/MOFU/BOFU, identifique gargalos de conversao, sugira otimizacoes em cada etapa. Analise taxas de passagem entre etapas. Responda em PT-BR."},
    {"id": "lns", "name": "LNS - Nutricao de Leads", "icon": "Mail", "description": "Nutricao de leads. Cria sequencias de email, segmenta audiencia, qualifica leads.",
     "system_prompt": "Voce e LNS, especialista em nutricao de leads. Crie sequencias de email, defina segmentacao, qualifique leads (MQL/SQL), sugira conteudo para cada etapa do funil. Responda em PT-BR."},
    {"id": "closer", "name": "CLOSER - Fechamento", "icon": "Handshake", "description": "Analise de fechamento. Otimiza taxas de conversao final e checkout.",
     "system_prompt": "Voce e CLOSER, analista de fechamento. Otimize paginas de checkout, reduza abandono de carrinho, analise objecoes, sugira urgencia e escassez. Use [SKILL:web_scraper] para analisar paginas. Responda em PT-BR."},
    # --- SQUAD 5: CREATIVE & MESSAGING ---
    {"id": "nova", "name": "NOVA - Criativos & Conteudo", "icon": "Sparkles", "description": "Criacao de criativos, copy, conteudo de mentorias e scripts de aulas.",
     "system_prompt": "Voce e NOVA, especialista em criativos, copy e conteudo educacional. Crie headlines, descricoes, CTAs, scripts de video/reels, roteiros de aulas para mentorias, materiais didaticos, exercicios praticos. Quando solicitado, crie conteudo detalhado para aulas e modulos de mentoria. Responda em PT-BR."},
    {"id": "mara", "name": "MARA - Posicionamento", "icon": "Compass", "description": "Posicionamento estrategico. Define tom de voz, proposta de valor, diferenciacao.",
     "system_prompt": "Voce e MARA, estrategista de posicionamento. Defina proposta de valor, tom de voz, diferenciais competitivos, messaging framework. Analise concorrentes e sugira posicionamento unico. Responda em PT-BR."},
    # --- SQUAD 6: PAGES & CONVERSION ---
    {"id": "lpx", "name": "LPX - Landing Pages", "icon": "Layout", "description": "Otimizacao de landing pages. Analisa estrutura, velocidade, copy e conversao.",
     "system_prompt": "Voce e LPX, otimizador de landing pages. Analise estrutura, hierarquia visual, velocidade, copy, CTAs. Use [SKILL:web_scraper] para analisar paginas e [SKILL:url_summarizer] para extrair conteudo. Responda em PT-BR."},
    {"id": "dex", "name": "DEX - Construcao de Paginas", "icon": "Code", "description": "Construcao de paginas web. Cria landing pages, formularios, componentes.",
     "system_prompt": "Voce e DEX, construtor de paginas. Crie landing pages completas em HTML/CSS/JS, formularios de captacao, componentes UI. Use [SKILL:code_executor] para testar e [SKILL:file_manager] para salvar arquivos. Responda em PT-BR."},
    {"id": "oubas", "name": "OUBAS - UX", "icon": "MousePointer", "description": "UX e experiencia do usuario. Analisa usabilidade e jornada do usuario.",
     "system_prompt": "Voce e OUBAS, especialista em UX. Analise usabilidade, fluxo do usuario, pontos de friccao, acessibilidade. Sugira melhorias de experiencia e navegacao. Responda em PT-BR."},
    {"id": "rex", "name": "REX - CRO", "icon": "TrendingUp", "description": "CRO e precificacao. Otimiza taxa de conversao, testa precos e ofertas.",
     "system_prompt": "Voce e REX, especialista em CRO e precificacao. Sugira testes A/B, otimize taxas de conversao, analise elasticidade de preco, crie ofertas e pronocoes. Use [SKILL:calculator] para projecoes. Responda em PT-BR."},
    # --- SQUAD 7: RESEARCH & PRODUCT ---
    {"id": "atlas", "name": "ATLAS - Pesquisa", "icon": "Search", "description": "Pesquisa de mercado. Analisa concorrencia, tendencias e oportunidades.",
     "system_prompt": "Voce e ATLAS, pesquisador de mercado. Analise concorrentes, tendencias, oportunidades de mercado. Use [SKILL:web_scraper] para pesquisar e [SKILL:url_summarizer] para resumir artigos. Responda em PT-BR."},
    {"id": "moira", "name": "MOIRA - Produto & Mentoria", "icon": "Package", "description": "Gestao de produto e criacao de mentorias completas a partir do conhecimento do usuario.",
     "system_prompt": "Voce e MOIRA, gestora de produto e especialista em criacao de mentorias. Analise product-market fit, crie mentorias completas com modulos, aulas, exercicios e materiais. Quando o usuario compartilhar seu conhecimento, estruture em uma mentoria profissional com: nome, promessa, modulos detalhados (min 6), aulas por modulo (min 4), exercicios, bonus, precificacao e copy de vendas. Responda em PT-BR."},
    # --- SQUAD 8: REPORTING & FINANCE ---
    {"id": "finn", "name": "FINN - Financeiro", "icon": "DollarSign", "description": "Gestao financeira. Projeta receita, controla custos e calcula ROI.",
     "system_prompt": "Voce e FINN, gestor financeiro. Calcule ROI, ROAS, LTV, CAC, break-even. Projete receita, controle custos, analise margem. Use [SKILL:calculator] para todos os calculos. Responda em PT-BR."},
    {"id": "echo", "name": "ECHO - Relatorios", "icon": "FileText", "description": "Geracao de relatorios executivos por produto, campanha e setor.",
     "system_prompt": "Voce e ECHO, gerador de relatorios. Crie relatorios executivos com metricas-chave, comparacoes antes/depois, recomendacoes. Formatos: agencia, produto, campanha, setor. Use markdown formatado. Responda em PT-BR."},
    # --- SUPPORT AGENTS ---
    {"id": "nero", "name": "NERO - Skills", "icon": "Cpu", "description": "Gestao de skills e capacidades do sistema.",
     "system_prompt": "Voce e NERO, gestor de skills. Avalie quais skills estao disponiveis, sugira novas capacidades, otimize uso de ferramentas. Responda em PT-BR."},
    {"id": "eval_agent", "name": "EVAL - Avaliacao", "icon": "CheckCircle", "description": "Avaliacao de impacto. Compara antes/depois e classifica resultado.",
     "system_prompt": "Voce e EVAL, avaliador de impacto. Compare metricas antes/depois de cada acao. Classifique como PASS, FAIL ou INCONCLUSIVO. Calcule impacto percentual. Use [SKILL:calculator]. Responda em PT-BR."},
    {"id": "archivist", "name": "ARCHIVIST - Memoria", "icon": "Database", "description": "Memoria e auditoria. Armazena historico de decisoes e resultados.",
     "system_prompt": "Voce e ARCHIVIST, responsavel pela memoria do sistema. Registre todas as decisoes, resultados, planos e artefatos. Mantenha historico organizado para consulta. Responda em PT-BR."},
    {"id": "learner", "name": "LEARNER - Aprendizado", "icon": "Brain", "description": "Aprendizado estrategico. Identifica padroes e evolui a inteligencia do sistema.",
     "system_prompt": "Voce e LEARNER, responsavel pelo aprendizado. Identifique padroes em resultados passados, sugira otimizacoes baseadas em dados historicos, evolua strategies. Responda em PT-BR."},
    # --- GENERAL PURPOSE ---
    {"id": "coder", "name": "Dev Expert", "icon": "Code", "description": "Especialista em programacao - cria, analisa e roda codigo",
     "system_prompt": "Voce e um especialista em programacao. Crie, analise, debug e execute codigo. Use [SKILL:code_executor] para rodar e [SKILL:file_manager] para criar arquivos. Responda em PT-BR."},
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


@api_router.get("/web/search")
async def web_search_endpoint(q: str, max_results: int = 5, user: dict = Depends(get_current_user)):
    """Busca web em tempo real. Retorna resultados estruturados."""
    import web_search as ws_mod
    results = await ws_mod.web_search(q, max_results=min(max_results, 10))
    return {"query": q, "results": results, "count": len(results)}

@api_router.get("/docs/manual")
async def download_manual(format: str = "pdf"):
    """Download the user manual in PDF or Markdown format."""
    from fastapi.responses import FileResponse
    base = os.path.join(os.path.dirname(__file__), "static_docs")
    if format.lower() == "md":
        path = os.path.join(base, "MANUAL_MORDOMO_VIRTUAL.md")
        filename = "Manual_Mordomo_Virtual.md"
        media = "text/markdown"
    else:
        path = os.path.join(base, "MANUAL_MORDOMO_VIRTUAL.pdf")
        filename = "Manual_Mordomo_Virtual.pdf"
        media = "application/pdf"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Manual nao encontrado")
    return FileResponse(path, media_type=media, filename=filename)


# ─── Include Router & Middleware ─────────────────────────────────────────────
# Agency module
import agency
agency.init(db, get_current_user)
app.include_router(agency.router)

# Rules engine
import rules_engine
rules_engine.init(db)

# Mentorship module
# Mentorship module
import mentorship

async def llm_generate_for_mentorship(prompt: str, user_id: str) -> str:
    """Generate content via LLM for mentorship creation."""
    settings = await db.settings.find_one({"user_id": user_id})
    ollama_url = settings.get("ollama_url", OLLAMA_URL) if settings else OLLAMA_URL
    ollama_model = settings.get("ollama_model", OLLAMA_MODEL) if settings else OLLAMA_MODEL
    messages = [{"role": "system", "content": "Voce e um especialista em criacao de mentorias e infoprodutos."}, {"role": "user", "content": prompt}]
    try:
        full = ""
        async for token in stream_ollama(messages, ollama_url, ollama_model):
            full += token
        return full
    except Exception:
        return await chat_emergent_fallback(messages)

mentorship.init(db, get_current_user, llm_generate_for_mentorship)
app.include_router(mentorship.router)

# Voice pipeline (STT Whisper + TTS Piper - 100% local)
import voice
app.include_router(voice.router)

# Admin module (FASE 4 — user mgmt, module access, quota, audit, sessions)
import admin as admin_mod
admin_mod.init(db, get_current_user)
app.include_router(admin_mod.router)
app.include_router(admin_mod.public_router)

# Google OAuth (FASE 1 — Gmail/Drive/Sheets/Calendar/YouTube)
import google_oauth
google_oauth.init(db, get_current_user, os.environ["JWT_SECRET"])
app.include_router(google_oauth.router)

# Google Skills (Gmail, Drive, Sheets, Calendar, YouTube)
import google_skills
google_skills.init(db, get_current_user, google_oauth.get_google_credentials)
app.include_router(google_skills.router)

# Workflow Engine (FASE 5)
import workflows as workflows_mod
workflows_mod.init(db, get_current_user, execute_skill)
app.include_router(workflows_mod.router)

# Social Unified Publisher (FASE 3)
import social_publisher
social_publisher.init(db, get_current_user, google_oauth.get_google_credentials)
app.include_router(social_publisher.router)

# Meta OAuth (FASE 2 — Instagram/Facebook/WhatsApp)
import meta_oauth
meta_oauth.init(db, get_current_user, os.environ["JWT_SECRET"])
app.include_router(meta_oauth.router)

# Meta Skills
import meta_skills
meta_skills.init(db, get_current_user, meta_oauth.get_meta_account)
app.include_router(meta_skills.router)

# Smart LLM
import smart_llm
smart_llm.init(db, OLLAMA_URL, "qwen2.5:7b", OLLAMA_MODEL)

# ─── Inter-Agent Communication Routes ────────────────────────────────────────
@api_router.get("/agent-comms")
async def get_agent_communications(request: Request):
    user = await get_current_user(request)
    msgs = await db.agent_messages.find({}, {"_id": 0}).sort("created_at", -1).limit(50).to_list(50)
    return msgs

@api_router.post("/agent-comms/send")
async def send_agent_message(request: Request):
    user = await get_current_user(request)
    body = await request.json()
    msg_id = await rules_engine.agent_message(
        body.get("from_agent", "user"),
        body.get("to_agent", "orion"),
        body.get("message_type", "request"),
        body.get("payload", {})
    )
    return {"id": msg_id, "message": "Mensagem enviada"}

@api_router.get("/agent-comms/{agent_id}/inbox")
async def get_agent_inbox(agent_id: str, request: Request):
    user = await get_current_user(request)
    msgs = await rules_engine.get_agent_inbox(agent_id)
    return msgs

@api_router.get("/system/memory-stats")
async def memory_stats(request: Request):
    user = await get_current_user(request)
    cache_count = await db.response_cache.count_documents({})
    summaries_count = await db.conversation_summaries.count_documents({})
    tasks_pending = await db.background_tasks.count_documents({"status": "queued"})
    tasks_done = await db.background_tasks.count_documents({"status": "completed"})
    total_messages = await db.messages.count_documents({})
    total_conversations = await db.conversations.count_documents({})
    total_users = await db.users.count_documents({})
    total_agents = await db.agents.count_documents({})
    total_products = await db.products.count_documents({})
    total_rules = await db.rules.count_documents({"active": True})
    total_mentorships = await db.mentorships.count_documents({})

    # System info
    import platform, shutil, os
    disk = shutil.disk_usage("/")
    try:
        with open("/proc/meminfo") as f:
            meminfo = f.read()
        mem_total = int([l for l in meminfo.split("\n") if "MemTotal" in l][0].split()[1]) // 1024
        mem_avail = int([l for l in meminfo.split("\n") if "MemAvailable" in l][0].split()[1]) // 1024
        mem_used = mem_total - mem_avail
    except Exception:
        mem_total = mem_used = mem_avail = 0

    # Response time tracking
    recent_logs = await db.execution_log.find({}).sort("executed_at", -1).limit(10).to_list(10)

    return {
        "cache_entries": cache_count,
        "conversation_summaries": summaries_count,
        "tasks_pending": tasks_pending,
        "tasks_completed": tasks_done,
        "total_messages": total_messages,
        "total_conversations": total_conversations,
        "total_users": total_users,
        "total_agents": total_agents,
        "total_products": total_products,
        "active_rules": total_rules,
        "total_mentorships": total_mentorships,
        "system": {
            "os": platform.system(),
            "python": platform.python_version(),
            "ram_total_mb": mem_total,
            "ram_used_mb": mem_used,
            "ram_available_mb": mem_avail,
            "ram_percent": round((mem_used / mem_total * 100), 1) if mem_total > 0 else 0,
            "disk_total_gb": round(disk.total / (1024**3), 1),
            "disk_used_gb": round(disk.used / (1024**3), 1),
            "disk_free_gb": round(disk.free / (1024**3), 1),
            "disk_percent": round(disk.used / disk.total * 100, 1),
        },
        "recent_executions": len(recent_logs),
    }

@api_router.get("/system/task/{task_id}")
async def get_task(task_id: str, request: Request):
    user = await get_current_user(request)
    return smart_llm.get_task_status(task_id)

# Include api_router AFTER all routes are defined
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
    await db.agency_access.create_index("user_id", unique=True)
    await db.products.create_index("status")
    await db.campaigns.create_index("product_id")
    await db.rules.create_index([("product_id", 1), ("active", 1)])
    await db.approvals.create_index([("status", 1), ("created_at", -1)])
    await db.agent_messages.create_index([("to_agent", 1), ("status", 1)])
    await db.execution_log.create_index("executed_at")
    await db.mentorships.create_index([("user_id", 1), ("created_at", -1)])
    await db.knowledge_base.create_index([("user_id", 1)])
    await db.response_cache.create_index("key", unique=True)
    await db.response_cache.create_index("created_at")
    await db.conversation_summaries.create_index("conversation_id", unique=True)
    await db.background_tasks.create_index("status")
    # Admin module indexes
    await db.audit_log.create_index([("created_at", -1)])
    await db.sessions.create_index([("user_id", 1), ("ip", 1)], unique=True)
    await db.sessions.create_index("last_seen")
    await db.usage_metering.create_index([("user_id", 1), ("date", 1)], unique=True)
    await db.usage_metering.create_index("date")
    await db.password_resets.create_index("token", unique=True)
    await db.password_resets.create_index("expires_at")
    # Google OAuth (FASE 1)
    await db.oauth_config.create_index("provider", unique=True)
    await db.google_accounts.create_index("user_id", unique=True)
    # Workflows (FASE 5)
    await db.workflows.create_index([("user_id", 1), ("name", 1)])
    await db.workflow_executions.create_index([("user_id", 1), ("started_at", -1)])
    # Meta (FASE 2)
    await db.meta_accounts.create_index("user_id", unique=True)
    await db.meta_dm_rules.create_index([("user_id", 1), ("page_id", 1)])
    # Start rules evaluation engine
    asyncio.create_task(rules_engine.rules_evaluation_loop())
    # Start background task worker
    asyncio.create_task(smart_llm.background_worker())
    # Seed admin
    admin_email = os.environ.get("ADMIN_EMAIL")
    admin_password = os.environ.get("ADMIN_PASSWORD")
    if not admin_email or not admin_password:
        logger.warning("ADMIN_EMAIL/ADMIN_PASSWORD nao definidos no .env - seed de admin pulado")
        return
    existing = await db.users.find_one({"email": admin_email})
    if not existing:
        hashed = hash_password(admin_password)
        result = await db.users.insert_one({
            "email": admin_email, "password_hash": hashed,
            "name": "Admin", "role": "admin",
            "allowed_modules": ["chat", "handsfree", "mentorship", "agency", "telegram", "agents", "skills", "monitor", "admin", "drive", "email", "sheets", "social", "automation"],
            "blocked": False, "quota": {}, "login_count": 0,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        user_id = str(result.inserted_id)
        await db.settings.insert_one({
            "user_id": user_id, "ollama_url": OLLAMA_URL, "ollama_model": OLLAMA_MODEL,
            "tts_enabled": True, "tts_language": "pt-BR",
            "skills_enabled": ["code_executor", "web_scraper", "web_search", "url_summarizer", "file_manager", "calculator", "api_caller", "system_info", "datetime_info"],
        "agent_name": "Kaelum.AI",
        "agent_personality": ""
        })
        logger.info(f"Admin criado: {admin_email}")
    elif not verify_password(admin_password, existing["password_hash"]):
        await db.users.update_one({"email": admin_email}, {"$set": {"password_hash": hash_password(admin_password)}})
        logger.info("Senha do admin atualizada")
    # Garantir que admin tem todos os módulos liberados e sem bloqueio
    await db.users.update_one(
        {"email": admin_email},
        {"$set": {
            "role": "admin", "blocked": False,
            "allowed_modules": ["chat", "handsfree", "mentorship", "agency", "telegram", "agents", "skills", "monitor", "workflows", "admin", "drive", "email", "sheets", "social", "automation"]
        }}
    )
    # Rebrand automático: Mordomo Virtual -> Kaelum.AI em todos os settings
    await db.settings.update_many(
        {"agent_name": {"$in": ["Mordomo Virtual", "NovaClaw", "Novaclaw"]}},
        {"$set": {"agent_name": "Kaelum.AI"}}
    )
    # Write test credentials
    try:
        os.makedirs("/app/memory", exist_ok=True)
        with open("/app/memory/test_credentials.md", "w") as f:
            f.write(f"# Test Credentials\n\n## Admin\n- Email: {admin_email}\n- Password: {admin_password}\n- Role: admin\n\n## Auth Endpoints\n- POST /api/auth/register\n- POST /api/auth/login\n- POST /api/auth/logout\n- GET /api/auth/me\n- POST /api/auth/refresh\n")
    except Exception:
        pass
    # System Watchdog (FASE 6)
    try:
        import system_watchdog
        system_watchdog.start(db)
    except Exception as e:
        logger.error(f"watchdog falha ao iniciar: {e}")

@app.on_event("shutdown")
async def shutdown():
    rules_engine.stop()
    try:
        import system_watchdog
        await system_watchdog.stop()
    except Exception:
        pass
    client.close()
