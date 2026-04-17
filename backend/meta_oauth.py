"""
Meta (Facebook/Instagram/WhatsApp) OAuth — FASE 2 Roadmap.
Mesmo padrão do google_oauth: admin configura App ID/Secret no painel,
usuário conecta sua conta Facebook via botão e o app recebe long-lived token.

Escopos:
- instagram_basic, instagram_content_publish (publicar no IG Business)
- pages_show_list, pages_read_engagement, pages_manage_posts (Facebook Pages)
- pages_messaging (DMs)
- whatsapp_business_messaging, whatsapp_business_management (WhatsApp Cloud API)
- business_management

REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH.
"""
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from cryptography.fernet import Fernet
import hashlib
import base64
import os
import jwt
import httpx
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

# Injected
db = None
get_current_user = None
JWT_SECRET = None

GRAPH_API = "https://graph.facebook.com/v21.0"
OAUTH_DIALOG = "https://www.facebook.com/v21.0/dialog/oauth"

SCOPES = [
    "email",
    "public_profile",
    "instagram_basic",
    "instagram_content_publish",
    "pages_show_list",
    "pages_read_engagement",
    "pages_manage_posts",
    "pages_messaging",
    "business_management",
    "whatsapp_business_messaging",
    "whatsapp_business_management",
]


def _fernet() -> Fernet:
    key = hashlib.sha256(JWT_SECRET.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def enc(p: str) -> str:
    return _fernet().encrypt(p.encode()).decode()


def dec(c: str) -> str:
    return _fernet().decrypt(c.encode()).decode()


async def require_admin(request: Request) -> dict:
    user = await get_current_user(request)
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Apenas administradores")
    return user


def _build_redirect_uri(request: Request) -> str:
    """REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH."""
    forced = os.environ.get("META_REDIRECT_URI")
    if forced:
        return forced
    scheme = request.headers.get("x-forwarded-proto") or request.url.scheme
    host = request.headers.get("x-forwarded-host") or request.headers.get("host", request.url.hostname)
    return f"{scheme}://{host}/api/oauth/meta/callback"


# ─── Admin config ─────────────────────────────────────────────────────────────
class MetaConfig(BaseModel):
    app_id: str
    app_secret: str
    enabled: bool = True


@router.get("/admin/integrations/meta")
async def get_meta_config(admin: dict = Depends(require_admin)):
    cfg = await db.oauth_config.find_one({"provider": "meta"})
    redirect_uri = os.environ.get("META_REDIRECT_URI", "<derivado do host HTTPS>")
    if not cfg:
        return {"configured": False, "enabled": False, "app_id": "",
                "app_secret_set": False, "redirect_uri_hint": redirect_uri, "scopes": SCOPES}
    return {
        "configured": True, "enabled": cfg.get("enabled", True),
        "app_id": cfg.get("app_id", ""),
        "app_secret_set": bool(cfg.get("app_secret_enc")),
        "updated_at": cfg.get("updated_at", ""),
        "redirect_uri_hint": redirect_uri, "scopes": SCOPES,
    }


@router.put("/admin/integrations/meta")
async def set_meta_config(body: MetaConfig, admin: dict = Depends(require_admin)):
    if not body.app_id.strip() or not body.app_secret.strip():
        raise HTTPException(status_code=400, detail="App ID e Secret obrigatórios")
    await db.oauth_config.update_one(
        {"provider": "meta"},
        {"$set": {
            "provider": "meta",
            "app_id": body.app_id.strip(),
            "app_secret_enc": enc(body.app_secret.strip()),
            "enabled": body.enabled,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": admin["_id"],
        }},
        upsert=True
    )
    try:
        import admin as admin_mod
        await admin_mod.log_audit(admin["_id"], "integrations.meta.config", "meta", {"enabled": body.enabled}, user_email=admin.get("email", ""))
    except Exception:
        pass
    return {"message": "Configuração Meta salva"}


@router.delete("/admin/integrations/meta")
async def delete_meta_config(admin: dict = Depends(require_admin)):
    await db.oauth_config.delete_one({"provider": "meta"})
    return {"message": "Removido"}


# ─── User OAuth ───────────────────────────────────────────────────────────────
async def _load_cfg() -> dict:
    cfg = await db.oauth_config.find_one({"provider": "meta"})
    if not cfg or not cfg.get("enabled"):
        raise HTTPException(status_code=503, detail="Integração Meta ainda não configurada pelo administrador")
    return {"app_id": cfg["app_id"], "app_secret": dec(cfg["app_secret_enc"])}


@router.get("/integrations/meta/start")
async def start_meta_oauth(request: Request):
    user = await get_current_user(request)
    cfg = await _load_cfg()
    redirect_uri = _build_redirect_uri(request)
    state_payload = {
        "user_id": user["_id"],
        "email": user.get("email", ""),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
    }
    state_token = jwt.encode(state_payload, JWT_SECRET, algorithm="HS256")
    params = {
        "client_id": cfg["app_id"],
        "redirect_uri": redirect_uri,
        "state": state_token,
        "scope": ",".join(SCOPES),
        "response_type": "code",
    }
    from urllib.parse import urlencode
    auth_url = f"{OAUTH_DIALOG}?{urlencode(params)}"
    return {"auth_url": auth_url, "redirect_uri": redirect_uri}


@router.get("/oauth/meta/callback")
async def meta_callback(request: Request, code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = None, error_description: Optional[str] = None):
    """REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH."""
    scheme = request.headers.get("x-forwarded-proto") or request.url.scheme
    host = request.headers.get("x-forwarded-host") or request.headers.get("host", request.url.hostname)
    front_base = f"{scheme}://{host}"
    if error:
        return RedirectResponse(url=f"{front_base}/?meta=error&reason={error_description or error}")
    if not code or not state:
        return RedirectResponse(url=f"{front_base}/?meta=error&reason=missing_params")
    try:
        state_payload = jwt.decode(state, JWT_SECRET, algorithms=["HS256"])
        user_id = state_payload["user_id"]
    except Exception:
        return RedirectResponse(url=f"{front_base}/?meta=error&reason=invalid_state")
    try:
        cfg = await _load_cfg()
    except HTTPException as e:
        return RedirectResponse(url=f"{front_base}/?meta=error&reason={e.detail}")
    redirect_uri = _build_redirect_uri(request)
    # 1. Trocar code por short-lived token
    async with httpx.AsyncClient(timeout=20) as c:
        try:
            r = await c.get(f"{GRAPH_API}/oauth/access_token", params={
                "client_id": cfg["app_id"],
                "client_secret": cfg["app_secret"],
                "redirect_uri": redirect_uri,
                "code": code,
            })
            tok = r.json()
            if r.status_code != 200 or "access_token" not in tok:
                return RedirectResponse(url=f"{front_base}/?meta=error&reason={tok.get('error',{}).get('message','token_failed')}")
            short_token = tok["access_token"]
            # 2. Converter para long-lived (60 dias)
            r2 = await c.get(f"{GRAPH_API}/oauth/access_token", params={
                "grant_type": "fb_exchange_token",
                "client_id": cfg["app_id"],
                "client_secret": cfg["app_secret"],
                "fb_exchange_token": short_token,
            })
            long_data = r2.json()
            long_token = long_data.get("access_token", short_token)
            expires_in = long_data.get("expires_in", 5184000)  # 60d
            # 3. Perfil
            p = await c.get(f"{GRAPH_API}/me", params={"fields": "id,name,email", "access_token": long_token})
            profile = p.json() if p.status_code == 200 else {}
            # 4. Pages + IG Business accounts linkadas
            pg = await c.get(f"{GRAPH_API}/me/accounts",
                              params={"fields": "id,name,access_token,instagram_business_account{id,username},category", "access_token": long_token})
            pages = pg.json().get("data", []) if pg.status_code == 200 else []
        except Exception as e:
            logger.error(f"Meta callback: {e}")
            return RedirectResponse(url=f"{front_base}/?meta=error&reason=network")

    doc = {
        "user_id": user_id,
        "fb_user_id": profile.get("id", ""),
        "fb_name": profile.get("name", ""),
        "fb_email": profile.get("email", ""),
        "access_token_enc": enc(long_token),
        "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat(),
        "pages": [{
            "id": p.get("id"), "name": p.get("name"), "category": p.get("category"),
            "page_token_enc": enc(p.get("access_token", "")) if p.get("access_token") else None,
            "ig_account": p.get("instagram_business_account"),
        } for p in pages],
        "connected_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.meta_accounts.update_one({"user_id": user_id}, {"$set": doc}, upsert=True)
    try:
        import admin as admin_mod
        await admin_mod.log_audit(user_id, "integrations.meta.connect", user_id, {"email": profile.get("email", "")}, user_email=state_payload.get("email", ""))
    except Exception:
        pass
    return RedirectResponse(url=f"{front_base}/?meta=connected")


@router.get("/integrations/meta/status")
async def meta_status(request: Request):
    user = await get_current_user(request)
    cfg = await db.oauth_config.find_one({"provider": "meta"})
    available = bool(cfg and cfg.get("enabled"))
    acc = await db.meta_accounts.find_one(
        {"user_id": user["_id"]},
        {"_id": 0, "access_token_enc": 0, "pages.page_token_enc": 0}
    )
    return {"integration_available": available, "connected": acc is not None,
            "account": acc, "scopes": SCOPES}


@router.post("/integrations/meta/disconnect")
async def disconnect_meta(request: Request):
    user = await get_current_user(request)
    await db.meta_accounts.delete_one({"user_id": user["_id"]})
    return {"message": "Conta Meta desconectada"}


# ─── Helper para skills ───────────────────────────────────────────────────────
async def get_meta_account(user_id: str) -> Optional[dict]:
    """Retorna account com tokens decriptados, ou None."""
    acc = await db.meta_accounts.find_one({"user_id": user_id})
    if not acc:
        return None
    acc["access_token"] = dec(acc["access_token_enc"]) if acc.get("access_token_enc") else None
    for p in acc.get("pages", []):
        if p.get("page_token_enc"):
            p["page_token"] = dec(p["page_token_enc"])
    return acc


def init(db_ref, get_user_ref, jwt_secret: str):
    global db, get_current_user, JWT_SECRET
    db = db_ref
    get_current_user = get_user_ref
    JWT_SECRET = jwt_secret
