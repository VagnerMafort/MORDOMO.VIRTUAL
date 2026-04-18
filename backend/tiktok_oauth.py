"""
TikTok OAuth 2.0 + Content Posting API — FASE 3 Roadmap.
Mesmo padrão do google_oauth / meta_oauth: admin configura Client Key/Secret no
painel (dynamic credentials), usuário conecta sua conta TikTok via botão e o app
recebe access_token (24h) + refresh_token (365d) armazenados criptografados.

Escopos:
- user.info.basic: perfil básico (avatar, display_name, open_id)
- video.upload: upload de vídeo como draft no inbox do usuário
- video.publish: publicar vídeos diretamente no feed

Endpoints cobertos:
- POST /api/admin/integrations/tiktok (admin: configura client_key/secret)
- GET  /api/integrations/tiktok/start   (user: inicia OAuth)
- GET  /api/oauth/tiktok/callback       (TikTok redirect -> troca code por token)
- GET  /api/integrations/tiktok/status  (frontend verifica conexão)
- POST /api/integrations/tiktok/disconnect

REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH.
"""
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional
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

# TikTok v2 API
AUTH_DIALOG = "https://www.tiktok.com/v2/auth/authorize/"
OAUTH_TOKEN = "https://open.tiktokapis.com/v2/oauth/token/"
OAUTH_REVOKE = "https://open.tiktokapis.com/v2/oauth/revoke/"
USER_INFO = "https://open.tiktokapis.com/v2/user/info/"

SCOPES = [
    "user.info.basic",
    "video.upload",
    "video.publish",
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
    forced = os.environ.get("TIKTOK_REDIRECT_URI")
    if forced:
        return forced
    scheme = request.headers.get("x-forwarded-proto") or request.url.scheme
    host = request.headers.get("x-forwarded-host") or request.headers.get("host", request.url.hostname)
    return f"{scheme}://{host}/api/oauth/tiktok/callback"


# ─── Admin config ─────────────────────────────────────────────────────────────
class TikTokConfig(BaseModel):
    client_key: str
    client_secret: str
    enabled: bool = True


@router.get("/admin/integrations/tiktok")
async def get_tiktok_config(admin: dict = Depends(require_admin)):
    cfg = await db.oauth_config.find_one({"provider": "tiktok"})
    redirect_uri = os.environ.get("TIKTOK_REDIRECT_URI", "<derivado do host HTTPS>")
    if not cfg:
        return {"configured": False, "enabled": False, "client_key": "",
                "client_secret_set": False, "redirect_uri_hint": redirect_uri, "scopes": SCOPES}
    return {
        "configured": True, "enabled": cfg.get("enabled", True),
        "client_key": cfg.get("client_key", ""),
        "client_secret_set": bool(cfg.get("client_secret_enc")),
        "updated_at": cfg.get("updated_at", ""),
        "redirect_uri_hint": redirect_uri, "scopes": SCOPES,
    }


@router.put("/admin/integrations/tiktok")
async def set_tiktok_config(body: TikTokConfig, admin: dict = Depends(require_admin)):
    if not body.client_key.strip() or not body.client_secret.strip():
        raise HTTPException(status_code=400, detail="Client Key e Secret obrigatórios")
    await db.oauth_config.update_one(
        {"provider": "tiktok"},
        {"$set": {
            "provider": "tiktok",
            "client_key": body.client_key.strip(),
            "client_secret_enc": enc(body.client_secret.strip()),
            "enabled": body.enabled,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": admin["_id"],
        }},
        upsert=True
    )
    try:
        import admin as admin_mod
        await admin_mod.log_audit(admin["_id"], "integrations.tiktok.config", "tiktok",
                                   {"enabled": body.enabled}, user_email=admin.get("email", ""))
    except Exception:
        pass
    return {"message": "Configuração TikTok salva"}


@router.delete("/admin/integrations/tiktok")
async def delete_tiktok_config(admin: dict = Depends(require_admin)):
    await db.oauth_config.delete_one({"provider": "tiktok"})
    return {"message": "Removido"}


# ─── User OAuth ───────────────────────────────────────────────────────────────
async def _load_cfg() -> dict:
    cfg = await db.oauth_config.find_one({"provider": "tiktok"})
    if not cfg or not cfg.get("enabled"):
        raise HTTPException(status_code=503, detail="Integração TikTok ainda não configurada pelo administrador")
    return {"client_key": cfg["client_key"], "client_secret": dec(cfg["client_secret_enc"])}


@router.get("/integrations/tiktok/start")
async def start_tiktok_oauth(request: Request):
    user = await get_current_user(request)
    cfg = await _load_cfg()
    redirect_uri = _build_redirect_uri(request)
    state_payload = {
        "user_id": user["_id"],
        "email": user.get("email", ""),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
    }
    state_token = jwt.encode(state_payload, JWT_SECRET, algorithm="HS256")
    from urllib.parse import urlencode
    params = {
        "client_key": cfg["client_key"],
        "response_type": "code",
        "scope": ",".join(SCOPES),
        "redirect_uri": redirect_uri,
        "state": state_token,
    }
    auth_url = f"{AUTH_DIALOG}?{urlencode(params)}"
    return {"auth_url": auth_url, "redirect_uri": redirect_uri}


@router.get("/oauth/tiktok/callback")
async def tiktok_callback(request: Request, code: Optional[str] = None, state: Optional[str] = None,
                           error: Optional[str] = None, error_description: Optional[str] = None):
    """REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH."""
    scheme = request.headers.get("x-forwarded-proto") or request.url.scheme
    host = request.headers.get("x-forwarded-host") or request.headers.get("host", request.url.hostname)
    front_base = f"{scheme}://{host}"
    if error:
        return RedirectResponse(url=f"{front_base}/?tiktok=error&reason={error_description or error}")
    if not code or not state:
        return RedirectResponse(url=f"{front_base}/?tiktok=error&reason=missing_params")
    try:
        state_payload = jwt.decode(state, JWT_SECRET, algorithms=["HS256"])
        user_id = state_payload["user_id"]
    except Exception:
        return RedirectResponse(url=f"{front_base}/?tiktok=error&reason=invalid_state")
    try:
        cfg = await _load_cfg()
    except HTTPException as e:
        return RedirectResponse(url=f"{front_base}/?tiktok=error&reason={e.detail}")
    redirect_uri = _build_redirect_uri(request)
    # 1. Trocar code por access_token (24h) + refresh_token (365d)
    async with httpx.AsyncClient(timeout=20) as c:
        try:
            r = await c.post(OAUTH_TOKEN, headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Cache-Control": "no-cache",
            }, data={
                "client_key": cfg["client_key"],
                "client_secret": cfg["client_secret"],
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            })
            tok = r.json()
            if r.status_code != 200 or "access_token" not in tok:
                msg = tok.get("error_description") or tok.get("message") or "token_failed"
                return RedirectResponse(url=f"{front_base}/?tiktok=error&reason={msg}")
            access_token = tok["access_token"]
            refresh_token = tok.get("refresh_token", "")
            open_id = tok.get("open_id", "")
            expires_in = int(tok.get("expires_in", 86400))
            refresh_expires_in = int(tok.get("refresh_expires_in", 31536000))
            scope_granted = tok.get("scope", ",".join(SCOPES))
            # 2. Buscar perfil
            p = await c.get(USER_INFO, headers={"Authorization": f"Bearer {access_token}"},
                             params={"fields": "open_id,union_id,avatar_url,display_name,username"})
            profile = p.json().get("data", {}).get("user", {}) if p.status_code == 200 else {}
        except Exception as e:
            logger.error(f"TikTok callback: {e}")
            return RedirectResponse(url=f"{front_base}/?tiktok=error&reason=network")

    doc = {
        "user_id": user_id,
        "open_id": open_id or profile.get("open_id", ""),
        "union_id": profile.get("union_id", ""),
        "display_name": profile.get("display_name", ""),
        "username": profile.get("username", ""),
        "avatar_url": profile.get("avatar_url", ""),
        "access_token_enc": enc(access_token),
        "refresh_token_enc": enc(refresh_token) if refresh_token else None,
        "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat(),
        "refresh_expires_at": (datetime.now(timezone.utc) + timedelta(seconds=refresh_expires_in)).isoformat(),
        "scope": scope_granted,
        "connected_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.tiktok_accounts.update_one({"user_id": user_id}, {"$set": doc}, upsert=True)
    try:
        import admin as admin_mod
        await admin_mod.log_audit(user_id, "integrations.tiktok.connect", user_id,
                                   {"open_id": doc["open_id"]}, user_email=state_payload.get("email", ""))
    except Exception:
        pass
    return RedirectResponse(url=f"{front_base}/?tiktok=connected")


@router.get("/integrations/tiktok/status")
async def tiktok_status(request: Request):
    user = await get_current_user(request)
    cfg = await db.oauth_config.find_one({"provider": "tiktok"})
    available = bool(cfg and cfg.get("enabled"))
    acc = await db.tiktok_accounts.find_one(
        {"user_id": user["_id"]},
        {"_id": 0, "access_token_enc": 0, "refresh_token_enc": 0}
    )
    return {"integration_available": available, "connected": acc is not None,
            "account": acc, "scopes": SCOPES}


@router.post("/integrations/tiktok/disconnect")
async def disconnect_tiktok(request: Request):
    user = await get_current_user(request)
    acc = await db.tiktok_accounts.find_one({"user_id": user["_id"]})
    # Best-effort revoke com TikTok
    if acc and acc.get("access_token_enc"):
        try:
            cfg = await db.oauth_config.find_one({"provider": "tiktok"})
            if cfg:
                async with httpx.AsyncClient(timeout=10) as c:
                    await c.post(OAUTH_REVOKE, headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                    }, data={
                        "client_key": cfg["client_key"],
                        "client_secret": dec(cfg["client_secret_enc"]),
                        "token": dec(acc["access_token_enc"]),
                    })
        except Exception as e:
            logger.warning(f"TikTok revoke falhou (ignorando): {e}")
    await db.tiktok_accounts.delete_one({"user_id": user["_id"]})
    return {"message": "Conta TikTok desconectada"}


# ─── Token refresh (lazy, chamado antes de API calls) ─────────────────────────
async def _refresh_access_token(user_id: str) -> Optional[str]:
    acc = await db.tiktok_accounts.find_one({"user_id": user_id})
    if not acc or not acc.get("refresh_token_enc"):
        return None
    cfg = await db.oauth_config.find_one({"provider": "tiktok"})
    if not cfg:
        return None
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(OAUTH_TOKEN, headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Cache-Control": "no-cache",
            }, data={
                "client_key": cfg["client_key"],
                "client_secret": dec(cfg["client_secret_enc"]),
                "grant_type": "refresh_token",
                "refresh_token": dec(acc["refresh_token_enc"]),
            })
            tok = r.json()
            if r.status_code != 200 or "access_token" not in tok:
                logger.error(f"TikTok refresh falhou: {tok}")
                return None
            access_token = tok["access_token"]
            expires_in = int(tok.get("expires_in", 86400))
            update = {
                "access_token_enc": enc(access_token),
                "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat(),
            }
            # TikTok pode rotacionar o refresh_token
            if tok.get("refresh_token"):
                update["refresh_token_enc"] = enc(tok["refresh_token"])
                rex = int(tok.get("refresh_expires_in", 31536000))
                update["refresh_expires_at"] = (datetime.now(timezone.utc) + timedelta(seconds=rex)).isoformat()
            await db.tiktok_accounts.update_one({"user_id": user_id}, {"$set": update})
            return access_token
    except Exception as e:
        logger.error(f"TikTok refresh exception: {e}")
        return None


async def get_tiktok_account(user_id: str) -> Optional[dict]:
    """Retorna account com access_token decriptado e válido (auto-refresh). None se não conectado."""
    acc = await db.tiktok_accounts.find_one({"user_id": user_id})
    if not acc:
        return None
    # Checa expiração
    try:
        exp = datetime.fromisoformat(acc["expires_at"])
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) >= exp - timedelta(minutes=5):
            new_token = await _refresh_access_token(user_id)
            if new_token:
                acc = await db.tiktok_accounts.find_one({"user_id": user_id})
            else:
                return None
    except Exception:
        pass
    if acc.get("access_token_enc"):
        acc["access_token"] = dec(acc["access_token_enc"])
    return acc


# ─── Content Posting API — Upload direto de vídeo via URL ─────────────────────
async def publish_video_from_url(user_id: str, video_url: str, title: str = "",
                                  privacy_level: str = "SELF_ONLY",
                                  disable_comment: bool = False,
                                  disable_duet: bool = False,
                                  disable_stitch: bool = False) -> dict:
    """
    Usa o endpoint Content Posting API "PULL_FROM_URL" - TikTok baixa o vídeo da URL
    pública. Privacy levels: PUBLIC_TO_EVERYONE, MUTUAL_FOLLOW_FRIENDS, SELF_ONLY.
    Retorna {publish_id} ou {error}.
    """
    acc = await get_tiktok_account(user_id)
    if not acc:
        return {"error": "TikTok não conectado"}
    if "video.publish" not in acc.get("scope", ""):
        return {"error": "Escopo video.publish não autorizado pelo usuário"}
    access_token = acc["access_token"]
    endpoint = "https://open.tiktokapis.com/v2/post/publish/video/init/"
    payload = {
        "post_info": {
            "title": title or "",
            "privacy_level": privacy_level,
            "disable_duet": disable_duet,
            "disable_comment": disable_comment,
            "disable_stitch": disable_stitch,
        },
        "source_info": {
            "source": "PULL_FROM_URL",
            "video_url": video_url,
        },
    }
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(endpoint, headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=UTF-8",
            }, json=payload)
            data = r.json()
            if r.status_code != 200:
                return {"error": data.get("error", {}).get("message", str(data))[:300]}
            publish_id = data.get("data", {}).get("publish_id", "")
            return {"publish_id": publish_id, "status": "processing"}
    except Exception as e:
        return {"error": str(e)[:200]}


async def get_publish_status(user_id: str, publish_id: str) -> dict:
    acc = await get_tiktok_account(user_id)
    if not acc:
        return {"error": "TikTok não conectado"}
    endpoint = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(endpoint, headers={
                "Authorization": f"Bearer {acc['access_token']}",
                "Content-Type": "application/json; charset=UTF-8",
            }, json={"publish_id": publish_id})
            data = r.json()
            if r.status_code != 200:
                return {"error": data.get("error", {}).get("message", "status_failed")[:300]}
            return data.get("data", {})
    except Exception as e:
        return {"error": str(e)[:200]}


def init(db_ref, get_user_ref, jwt_secret: str):
    global db, get_current_user, JWT_SECRET
    db = db_ref
    get_current_user = get_user_ref
    JWT_SECRET = jwt_secret
