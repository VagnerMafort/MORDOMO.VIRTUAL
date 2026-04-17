"""
Google OAuth2 multi-service integration — FASE 1 Roadmap.
Suporta: Gmail, Drive, Sheets, Calendar, YouTube.

REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH.
Redirect URI sempre derivado do host da requisição ou de um env opcional.

Fluxo:
1. Admin configura Client ID/Secret via /api/admin/integrations/google (criptografado com Fernet)
2. Usuário clica "Conectar Google" → GET /api/integrations/google/start
3. Backend gera state assinado (JWT) contendo user_id → redireciona para Google
4. Google retorna no /api/oauth/google/callback?code=...&state=...
5. Backend valida state, troca code por tokens, salva em google_accounts (1 por user — MVP)
6. Helper get_google_credentials(user_id) carrega credentials (com auto-refresh) para usar nas APIs
"""
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from cryptography.fernet import Fernet
import base64
import hashlib
import json
import os
import jwt
import httpx
import logging

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleAuthRequest
from google_auth_oauthlib.flow import Flow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# Injected
db = None
get_current_user = None
JWT_SECRET = None

# Escopos do MVP FASE 1 — uma autorização cobre tudo
SCOPES = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.upload",
]


# ─── Fernet util (criptografia dos secrets no banco) ─────────────────────────
def _fernet() -> Fernet:
    # Deriva chave 32 bytes do JWT_SECRET
    key = hashlib.sha256(JWT_SECRET.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def enc(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def dec(ciphertext: str) -> str:
    return _fernet().decrypt(ciphertext.encode()).decode()


# ─── Admin: configurar OAuth app ─────────────────────────────────────────────
class GoogleOAuthConfig(BaseModel):
    client_id: str
    client_secret: str
    enabled: bool = True


async def require_admin(request: Request) -> dict:
    user = await get_current_user(request)
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Apenas administradores")
    return user


def _build_redirect_uri(request: Request) -> str:
    """
    REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH.
    Usa env opcional GOOGLE_REDIRECT_URI (para produção VPS onde o host HTTPS pode diferir do request.base_url),
    ou deriva do request em modo fallback.
    """
    forced = os.environ.get("GOOGLE_REDIRECT_URI")
    if forced:
        return forced
    # Derivar do scheme/host respeitando proxy
    scheme = request.headers.get("x-forwarded-proto") or request.url.scheme
    host = request.headers.get("x-forwarded-host") or request.headers.get("host", request.url.hostname)
    return f"{scheme}://{host}/api/oauth/google/callback"


@router.get("/admin/integrations/google")
async def get_google_config(admin: dict = Depends(require_admin)):
    cfg = await db.oauth_config.find_one({"provider": "google"})
    redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI", "<derivado do host HTTPS>")
    if not cfg:
        return {
            "configured": False, "enabled": False,
            "client_id": "", "client_secret_set": False,
            "redirect_uri_hint": redirect_uri,
            "scopes": SCOPES,
        }
    secret_enc = cfg.get("client_secret_enc", "")
    return {
        "configured": True,
        "enabled": cfg.get("enabled", True),
        "client_id": cfg.get("client_id", ""),
        "client_secret_set": bool(secret_enc),
        "client_secret_masked": "****" if secret_enc else "",
        "updated_at": cfg.get("updated_at", ""),
        "redirect_uri_hint": redirect_uri,
        "scopes": SCOPES,
    }


@router.put("/admin/integrations/google")
async def set_google_config(body: GoogleOAuthConfig, admin: dict = Depends(require_admin)):
    if not body.client_id.strip() or not body.client_secret.strip():
        raise HTTPException(status_code=400, detail="Client ID e Secret são obrigatórios")
    doc = {
        "provider": "google",
        "client_id": body.client_id.strip(),
        "client_secret_enc": enc(body.client_secret.strip()),
        "enabled": body.enabled,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": admin["_id"],
    }
    await db.oauth_config.update_one({"provider": "google"}, {"$set": doc}, upsert=True)
    # Log via admin module
    try:
        import admin as admin_mod
        await admin_mod.log_audit(admin["_id"], "integrations.google.config", "google", {"enabled": body.enabled}, user_email=admin.get("email", ""))
    except Exception:
        pass
    return {"message": "Configuração salva", "enabled": body.enabled}


@router.delete("/admin/integrations/google")
async def delete_google_config(admin: dict = Depends(require_admin)):
    await db.oauth_config.delete_one({"provider": "google"})
    return {"message": "Configuração removida"}


# ─── Usuário: conectar/desconectar sua conta Google ──────────────────────────
async def _load_oauth_cfg() -> dict:
    cfg = await db.oauth_config.find_one({"provider": "google"})
    if not cfg or not cfg.get("enabled"):
        raise HTTPException(status_code=503, detail="Integração Google ainda não configurada pelo administrador")
    return {
        "client_id": cfg["client_id"],
        "client_secret": dec(cfg["client_secret_enc"]),
    }


def _build_flow(client_id: str, client_secret: str, redirect_uri: str) -> Flow:
    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect_uri],
        }
    }
    flow = Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=redirect_uri)
    return flow


@router.get("/integrations/google/start")
async def start_google_oauth(request: Request):
    """Gera URL de autorização e redireciona (ou retorna URL para frontend abrir em nova aba)."""
    user = await get_current_user(request)
    cfg = await _load_oauth_cfg()
    redirect_uri = _build_redirect_uri(request)
    flow = _build_flow(cfg["client_id"], cfg["client_secret"], redirect_uri)
    # State assinado: contém user_id e timestamp
    state_payload = {
        "user_id": user["_id"],
        "email": user.get("email", ""),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
    }
    state_token = jwt.encode(state_payload, JWT_SECRET, algorithm="HS256")
    auth_url, _ = flow.authorization_url(
        access_type="offline",           # necessário para receber refresh_token
        include_granted_scopes="true",
        prompt="consent",                # força tela de consent p/ sempre ter refresh_token
        state=state_token,
    )
    return {"auth_url": auth_url, "redirect_uri": redirect_uri}


@router.get("/oauth/google/callback")
async def google_callback(request: Request, code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = None):
    """
    REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH.
    Endpoint público onde o Google retorna após o consent.
    """
    # Fronteira onde redirecionar o usuário após o fluxo (página principal do app)
    scheme = request.headers.get("x-forwarded-proto") or request.url.scheme
    host = request.headers.get("x-forwarded-host") or request.headers.get("host", request.url.hostname)
    front_base = f"{scheme}://{host}"
    if error:
        return RedirectResponse(url=f"{front_base}/?google=error&reason={error}")
    if not code or not state:
        return RedirectResponse(url=f"{front_base}/?google=error&reason=missing_params")
    # Valida state
    try:
        state_payload = jwt.decode(state, JWT_SECRET, algorithms=["HS256"])
        user_id = state_payload["user_id"]
    except Exception as e:
        logger.warning(f"state inválido: {e}")
        return RedirectResponse(url=f"{front_base}/?google=error&reason=invalid_state")
    try:
        cfg = await _load_oauth_cfg()
    except HTTPException as e:
        return RedirectResponse(url=f"{front_base}/?google=error&reason={e.detail}")
    redirect_uri = _build_redirect_uri(request)
    flow = _build_flow(cfg["client_id"], cfg["client_secret"], redirect_uri)
    try:
        flow.fetch_token(code=code)
    except Exception as e:
        logger.error(f"Erro ao trocar code por token: {e}")
        return RedirectResponse(url=f"{front_base}/?google=error&reason=token_exchange_failed")
    creds: Credentials = flow.credentials
    # Obter email/profile do usuário Google
    profile = {}
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(
                "https://openidconnect.googleapis.com/v1/userinfo",
                headers={"Authorization": f"Bearer {creds.token}"},
            )
            profile = r.json() if r.status_code == 200 else {}
    except Exception as e:
        logger.warning(f"Falha userinfo: {e}")
    # Persistir tokens (1 por user — MVP). Upsert para permitir re-conectar/trocar conta.
    doc = {
        "user_id": user_id,
        "google_email": profile.get("email", ""),
        "google_name": profile.get("name", ""),
        "google_picture": profile.get("picture", ""),
        "access_token_enc": enc(creds.token or ""),
        "refresh_token_enc": enc(creds.refresh_token or "") if creds.refresh_token else None,
        "token_expiry": creds.expiry.replace(tzinfo=timezone.utc).isoformat() if creds.expiry else None,
        "scopes": list(creds.scopes or SCOPES),
        "connected_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.google_accounts.update_one({"user_id": user_id}, {"$set": doc}, upsert=True)
    try:
        import admin as admin_mod
        await admin_mod.log_audit(user_id, "integrations.google.connect", user_id, {"email": profile.get("email", "")}, user_email=state_payload.get("email", ""))
    except Exception:
        pass
    return RedirectResponse(url=f"{front_base}/?google=connected")


@router.get("/integrations/google/status")
async def google_status(request: Request):
    user = await get_current_user(request)
    cfg = await db.oauth_config.find_one({"provider": "google"})
    available = bool(cfg and cfg.get("enabled"))
    account = await db.google_accounts.find_one({"user_id": user["_id"]}, {"_id": 0, "access_token_enc": 0, "refresh_token_enc": 0})
    return {
        "integration_available": available,
        "connected": account is not None,
        "account": account,
        "scopes": SCOPES,
    }


@router.post("/integrations/google/disconnect")
async def disconnect_google(request: Request):
    user = await get_current_user(request)
    account = await db.google_accounts.find_one({"user_id": user["_id"]})
    if not account:
        return {"message": "Não havia conexão"}
    # Revoga no Google (best-effort)
    try:
        token = dec(account.get("access_token_enc", ""))
        if token:
            async with httpx.AsyncClient(timeout=10) as c:
                await c.post(f"https://oauth2.googleapis.com/revoke?token={token}")
    except Exception as e:
        logger.warning(f"Falha ao revogar token no Google: {e}")
    await db.google_accounts.delete_one({"user_id": user["_id"]})
    try:
        import admin as admin_mod
        await admin_mod.log_audit(user["_id"], "integrations.google.disconnect", user["_id"], user_email=user.get("email", ""))
    except Exception:
        pass
    return {"message": "Conta Google desconectada"}


# ─── Helper público: obter credentials prontos para chamar APIs Google ───────
async def get_google_credentials(user_id: str) -> Optional[Credentials]:
    """
    Retorna google.oauth2.credentials.Credentials válido para o user_id,
    renovando o access_token automaticamente se expirado.
    """
    account = await db.google_accounts.find_one({"user_id": user_id})
    if not account:
        return None
    cfg = await db.oauth_config.find_one({"provider": "google"})
    if not cfg:
        return None
    access_token = dec(account.get("access_token_enc", "")) if account.get("access_token_enc") else None
    refresh_token = dec(account.get("refresh_token_enc", "")) if account.get("refresh_token_enc") else None
    client_id = cfg["client_id"]
    client_secret = dec(cfg["client_secret_enc"])
    expiry = None
    if account.get("token_expiry"):
        try:
            expiry = datetime.fromisoformat(account["token_expiry"]).replace(tzinfo=None)
        except Exception:
            expiry = None
    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=account.get("scopes", SCOPES),
        expiry=expiry,
    )
    # Auto refresh se expirou
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(GoogleAuthRequest())
            # Persistir novo access_token
            await db.google_accounts.update_one(
                {"user_id": user_id},
                {"$set": {
                    "access_token_enc": enc(creds.token),
                    "token_expiry": creds.expiry.replace(tzinfo=timezone.utc).isoformat() if creds.expiry else None,
                }}
            )
        except Exception as e:
            logger.error(f"Falha ao refresh token Google user={user_id}: {e}")
            return None
    return creds


def init(db_ref, get_user_ref, jwt_secret: str):
    global db, get_current_user, JWT_SECRET
    db = db_ref
    get_current_user = get_user_ref
    JWT_SECRET = jwt_secret
