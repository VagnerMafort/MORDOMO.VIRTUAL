"""
Admin module — FASE 4 Roadmap.
Contém:
- User Manager (CRUD + block + reset password)
- Module Access Control (allowed_modules por usuário)
- Usage Metering (agregação de uso)
- Quota Controller
- Audit Log
- Session Monitor
- Password Recovery (self-service + admin)
"""
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from bson import ObjectId
import bcrypt
import uuid
import secrets
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin")
public_router = APIRouter(prefix="/api/auth")

# Injected at init
db = None
get_current_user = None

# Lista canônica de módulos controlados pelo admin
AVAILABLE_MODULES = [
    {"key": "chat", "name": "Chat", "description": "Conversação com o agente"},
    {"key": "handsfree", "name": "Modo Mãos Livres", "description": "Voz contínua com wake word"},
    {"key": "mentorship", "name": "Mentorias", "description": "Criação e exportação de mentorias"},
    {"key": "agency", "name": "Agência", "description": "Automação de marketing e campanhas"},
    {"key": "telegram", "name": "Telegram", "description": "Bot conectado ao Telegram"},
    {"key": "agents", "name": "Agentes Customizados", "description": "Gerenciar agentes próprios"},
    {"key": "skills", "name": "Habilidades (Skills)", "description": "Painel de skills ativas"},
    {"key": "monitor", "name": "Monitoramento", "description": "Painel do sistema"},
    {"key": "admin", "name": "Painel Admin", "description": "Administração geral (apenas admin)"},
    # Reservas para próximas fases:
    {"key": "drive", "name": "Google Drive", "description": "Organização de arquivos no Drive"},
    {"key": "email", "name": "Email / Gmail", "description": "Leitura e envio de emails"},
    {"key": "sheets", "name": "Planilhas / Sheets", "description": "Criação e análise de planilhas"},
    {"key": "social", "name": "Redes Sociais", "description": "Publicação em IG/YT/TikTok"},
    {"key": "automation", "name": "Automação Web", "description": "Playwright / scraping avançado"},
]

DEFAULT_USER_MODULES = ["chat", "handsfree", "mentorship", "telegram", "agents", "skills", "monitor"]
ADMIN_ONLY_MODULES = ["admin"]

# ─── Models ───────────────────────────────────────────────────────────────────
class CreateUserInput(BaseModel):
    email: str
    password: str
    name: str
    role: str = "user"
    allowed_modules: Optional[List[str]] = None

class UpdateUserInput(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    blocked: Optional[bool] = None
    allowed_modules: Optional[List[str]] = None

class QuotaInput(BaseModel):
    messages_per_day: Optional[int] = None
    tasks_per_day: Optional[int] = None
    uploads_per_day: Optional[int] = None

class ResetPasswordInput(BaseModel):
    new_password: str

class ForgotPasswordInput(BaseModel):
    email: str

class ResetWithTokenInput(BaseModel):
    token: str
    new_password: str

# ─── Helpers ──────────────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

async def require_admin(request: Request) -> dict:
    user = await get_current_user(request)
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Acesso restrito: apenas administradores")
    return user

async def log_audit(user_id: str, action: str, target: str = "", details: dict = None, ip: str = "", user_email: str = ""):
    doc = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "user_email": user_email,
        "action": action,
        "target": target,
        "details": details or {},
        "ip": ip,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.audit_log.insert_one(doc)

async def track_session(user_id: str, email: str, request: Request):
    """Upsert uma sessão ativa (chamado pelo middleware em cada request autenticado)."""
    ip = request.client.host if request.client else ""
    ua = request.headers.get("user-agent", "")[:200]
    now = datetime.now(timezone.utc).isoformat()
    await db.sessions.update_one(
        {"user_id": user_id, "ip": ip},
        {"$set": {
            "user_id": user_id, "email": email,
            "ip": ip, "user_agent": ua, "last_seen": now
        }, "$setOnInsert": {"created_at": now}},
        upsert=True
    )

async def increment_usage(user_id: str, metric: str, amount: int = 1):
    """Incrementa contador diário de uso."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    await db.usage_metering.update_one(
        {"user_id": user_id, "date": today},
        {"$inc": {metric: amount}, "$setOnInsert": {"user_id": user_id, "date": today}},
        upsert=True
    )

async def check_quota(user_id: str, metric: str) -> bool:
    """Retorna True se ainda pode consumir. False se ultrapassou."""
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        return False
    quota = user.get("quota", {})
    limit = quota.get(metric)
    if not limit or limit <= 0:
        return True  # sem limite configurado
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    usage = await db.usage_metering.find_one({"user_id": user_id, "date": today})
    used = (usage or {}).get(metric, 0) if usage else 0
    return used < limit

def _serialize_user(u: dict) -> dict:
    return {
        "id": str(u["_id"]),
        "email": u.get("email", ""),
        "name": u.get("name", ""),
        "role": u.get("role", "user"),
        "blocked": u.get("blocked", False),
        "allowed_modules": u.get("allowed_modules", DEFAULT_USER_MODULES),
        "quota": u.get("quota", {}),
        "created_at": u.get("created_at", ""),
        "last_login": u.get("last_login", ""),
        "login_count": u.get("login_count", 0),
    }

# ─── ADMIN: User Management ───────────────────────────────────────────────────
@router.get("/users")
async def list_users(admin: dict = Depends(require_admin)):
    users = await db.users.find({}).to_list(500)
    return [_serialize_user(u) for u in users]

@router.post("/users")
async def create_user(body: CreateUserInput, request: Request, admin: dict = Depends(require_admin)):
    email = body.email.strip().lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")
    allowed = body.allowed_modules if body.allowed_modules is not None else DEFAULT_USER_MODULES
    if body.role == "admin":
        allowed = list(set(allowed + ADMIN_ONLY_MODULES))
    doc = {
        "email": email,
        "password_hash": hash_password(body.password),
        "name": body.name.strip(),
        "role": body.role if body.role in ("user", "admin") else "user",
        "allowed_modules": allowed,
        "blocked": False,
        "quota": {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    result = await db.users.insert_one(doc)
    user_id = str(result.inserted_id)
    await db.settings.update_one(
        {"user_id": user_id},
        {"$setOnInsert": {
            "user_id": user_id,
            "tts_enabled": True, "tts_language": "pt-BR",
            "skills_enabled": ["code_executor", "web_scraper", "web_search", "calculator", "datetime_info"],
            "agent_name": "Mordomo Virtual",
            "agent_personality": ""
        }},
        upsert=True
    )
    await log_audit(admin["_id"], "user.create", user_id, {"email": email, "role": body.role}, user_email=admin.get("email", ""))
    return _serialize_user({**doc, "_id": result.inserted_id})

@router.put("/users/{user_id}")
async def update_user(user_id: str, body: UpdateUserInput, admin: dict = Depends(require_admin)):
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID inválido")
    existing = await db.users.find_one({"_id": oid})
    if not existing:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    # Prevent admin from demoting/blocking themselves accidentally
    if str(existing["_id"]) == admin["_id"]:
        if body.role and body.role != "admin":
            raise HTTPException(status_code=400, detail="Você não pode remover seu próprio privilégio admin")
        if body.blocked:
            raise HTTPException(status_code=400, detail="Você não pode bloquear sua própria conta")
    update = {k: v for k, v in body.model_dump().items() if v is not None}
    if update:
        await db.users.update_one({"_id": oid}, {"$set": update})
    await log_audit(admin["_id"], "user.update", user_id, update, user_email=admin.get("email", ""))
    refreshed = await db.users.find_one({"_id": oid})
    return _serialize_user(refreshed)

@router.delete("/users/{user_id}")
async def delete_user(user_id: str, admin: dict = Depends(require_admin)):
    if user_id == admin["_id"]:
        raise HTTPException(status_code=400, detail="Você não pode deletar sua própria conta")
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID inválido")
    result = await db.users.delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    # Cleanup
    await db.settings.delete_many({"user_id": user_id})
    await db.conversations.delete_many({"user_id": user_id})
    await db.sessions.delete_many({"user_id": user_id})
    await log_audit(admin["_id"], "user.delete", user_id, user_email=admin.get("email", ""))
    return {"message": "Usuário excluído"}

@router.post("/users/{user_id}/reset-password")
async def admin_reset_password(user_id: str, body: ResetPasswordInput, admin: dict = Depends(require_admin)):
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID inválido")
    result = await db.users.update_one({"_id": oid}, {"$set": {"password_hash": hash_password(body.new_password)}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    await log_audit(admin["_id"], "user.password_reset", user_id, user_email=admin.get("email", ""))
    return {"message": "Senha redefinida"}

@router.put("/users/{user_id}/quota")
async def set_quota(user_id: str, body: QuotaInput, admin: dict = Depends(require_admin)):
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID inválido")
    quota = {k: v for k, v in body.model_dump().items() if v is not None}
    await db.users.update_one({"_id": oid}, {"$set": {"quota": quota}})
    await log_audit(admin["_id"], "user.quota_update", user_id, quota, user_email=admin.get("email", ""))
    return {"quota": quota}

# ─── ADMIN: Modules ───────────────────────────────────────────────────────────
@router.get("/modules")
async def list_modules(admin: dict = Depends(require_admin)):
    return AVAILABLE_MODULES

# ─── ADMIN: Usage ─────────────────────────────────────────────────────────────
@router.get("/usage")
async def get_usage(admin: dict = Depends(require_admin), days: int = 7):
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    records = await db.usage_metering.find({"date": {"$gte": since}}, {"_id": 0}).to_list(5000)
    # Aggregate per user
    per_user = {}
    for r in records:
        uid = r["user_id"]
        if uid not in per_user:
            per_user[uid] = {"user_id": uid, "messages": 0, "tasks": 0, "uploads": 0, "downloads": 0, "model_seconds": 0}
        for k in ("messages", "tasks", "uploads", "downloads", "model_seconds"):
            per_user[uid][k] += r.get(k, 0)
    # Attach user name/email
    user_ids = [ObjectId(uid) for uid in per_user.keys() if ObjectId.is_valid(uid)]
    users = await db.users.find({"_id": {"$in": user_ids}}).to_list(500)
    user_map = {str(u["_id"]): {"email": u.get("email", ""), "name": u.get("name", "")} for u in users}
    result = []
    for uid, stats in per_user.items():
        info = user_map.get(uid, {"email": "?", "name": "?"})
        result.append({**stats, "email": info["email"], "name": info["name"]})
    result.sort(key=lambda x: x["messages"], reverse=True)
    return {"days": days, "users": result, "daily": records}

# ─── ADMIN: Audit Log ─────────────────────────────────────────────────────────
@router.get("/audit")
async def get_audit(admin: dict = Depends(require_admin), limit: int = 200):
    logs = await db.audit_log.find({}, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    return logs

# ─── ADMIN: Sessions ──────────────────────────────────────────────────────────
@router.get("/sessions")
async def get_sessions(admin: dict = Depends(require_admin)):
    # Consider "online" anyone seen in last 10 minutes
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    online = await db.sessions.find({"last_seen": {"$gte": cutoff}}, {"_id": 0}).sort("last_seen", -1).to_list(200)
    recent = await db.sessions.find({"last_seen": {"$lt": cutoff}}, {"_id": 0}).sort("last_seen", -1).limit(50).to_list(50)
    return {"online": online, "recent": recent, "online_count": len(online)}

@router.delete("/sessions/{session_id}")
async def kill_session(session_id: str, admin: dict = Depends(require_admin)):
    # Sessions are tracked by composite key; here we just delete by user_id + ip
    await db.sessions.delete_one({"user_id": session_id})
    await log_audit(admin["_id"], "session.kill", session_id, user_email=admin.get("email", ""))
    return {"message": "Sessão encerrada"}

# ─── ADMIN: Dashboard Summary ─────────────────────────────────────────────────
@router.get("/dashboard")
async def admin_dashboard(admin: dict = Depends(require_admin)):
    total_users = await db.users.count_documents({})
    blocked_users = await db.users.count_documents({"blocked": True})
    admins = await db.users.count_documents({"role": "admin"})
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    online_count = await db.sessions.count_documents({"last_seen": {"$gte": cutoff}})
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_usage = await db.usage_metering.find({"date": today}, {"_id": 0}).to_list(500)
    total_msgs_today = sum(r.get("messages", 0) for r in today_usage)
    total_tasks_today = sum(r.get("tasks", 0) for r in today_usage)
    # System stats
    import platform
    import shutil
    disk = shutil.disk_usage("/")
    try:
        with open("/proc/meminfo") as f:
            meminfo = f.read()
        mem_total = int([ln for ln in meminfo.split("\n") if "MemTotal" in ln][0].split()[1]) // 1024
        mem_avail = int([ln for ln in meminfo.split("\n") if "MemAvailable" in ln][0].split()[1]) // 1024
        mem_used = mem_total - mem_avail
    except Exception:
        mem_total = mem_used = mem_avail = 0
    return {
        "users": {"total": total_users, "blocked": blocked_users, "admins": admins, "online": online_count},
        "today": {"messages": total_msgs_today, "tasks": total_tasks_today},
        "system": {
            "os": platform.system(),
            "ram_total_mb": mem_total, "ram_used_mb": mem_used, "ram_available_mb": mem_avail,
            "ram_percent": round((mem_used / mem_total * 100), 1) if mem_total else 0,
            "disk_total_gb": round(disk.total / (1024**3), 1),
            "disk_used_gb": round(disk.used / (1024**3), 1),
            "disk_free_gb": round(disk.free / (1024**3), 1),
            "disk_percent": round(disk.used / disk.total * 100, 1),
        },
        "modules": AVAILABLE_MODULES,
    }

# ─── PUBLIC: Password Recovery (self-service) ─────────────────────────────────
@public_router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordInput):
    email = body.email.strip().lower()
    user = await db.users.find_one({"email": email})
    # Sempre retornar 200 para não vazar se o email existe
    if user:
        token = secrets.token_urlsafe(32)
        expires = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        await db.password_resets.insert_one({
            "token": token,
            "user_id": str(user["_id"]),
            "email": email,
            "expires_at": expires,
            "used": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        await log_audit(str(user["_id"]), "password.reset_requested", str(user["_id"]), {"email": email}, user_email=email)
        logger.info(f"[PASSWORD_RESET] Token gerado para {email}: {token} (expira em 1h)")
    return {"message": "Se o e-mail estiver cadastrado, um token de recuperação foi gerado. Solicite ao administrador ou verifique o painel admin."}

@public_router.post("/reset-password")
async def reset_password_with_token(body: ResetWithTokenInput):
    record = await db.password_resets.find_one({"token": body.token, "used": False})
    if not record:
        raise HTTPException(status_code=400, detail="Token inválido ou já utilizado")
    if datetime.now(timezone.utc) > datetime.fromisoformat(record["expires_at"]):
        raise HTTPException(status_code=400, detail="Token expirado")
    await db.users.update_one(
        {"_id": ObjectId(record["user_id"])},
        {"$set": {"password_hash": hash_password(body.new_password)}}
    )
    await db.password_resets.update_one({"token": body.token}, {"$set": {"used": True, "used_at": datetime.now(timezone.utc).isoformat()}})
    await log_audit(record["user_id"], "password.reset_completed", record["user_id"], user_email=record.get("email", ""))
    return {"message": "Senha redefinida com sucesso"}

@router.get("/password-resets")
async def list_password_resets(admin: dict = Depends(require_admin)):
    """Admin vê tokens de reset ativos (facilita repasse manual enquanto SMTP não está configurado)."""
    now = datetime.now(timezone.utc).isoformat()
    active = await db.password_resets.find(
        {"used": False, "expires_at": {"$gt": now}},
        {"_id": 0}
    ).sort("created_at", -1).limit(50).to_list(50)
    return active


def init(db_ref, get_user_ref):
    global db, get_current_user
    db = db_ref
    get_current_user = get_user_ref
