"""
Meta Skills — Instagram Publisher, Facebook Pages, WhatsApp Send, DM Auto-Responder.
FASE 2 Roadmap.

Uso via chat:
    [SKILL:instagram] {"action":"publish","page_id":"...","caption":"...","image_url":"https://..."}
    [SKILL:facebook] {"action":"publish","page_id":"...","message":"...","link":"https://..."}
    [SKILL:whatsapp] {"action":"send","phone_number_id":"...","to":"5511...","text":"Olá!"}
    [SKILL:meta_dm] {"action":"list","page_id":"..."}

As credenciais WhatsApp (phone_number_id + access_token dedicado) podem vir do Meta account padrão
ou ser passadas explicitamente. O Facebook page token é carregado automaticamente do meta_accounts.
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List
import httpx
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/meta")

# Injected
db = None
get_current_user = None
get_meta_account = None

GRAPH = "https://graph.facebook.com/v21.0"


async def _account(user_id: str) -> dict:
    acc = await get_meta_account(user_id)
    if not acc:
        raise HTTPException(status_code=400, detail="Conta Meta não conectada. Acesse Minhas Integrações.")
    return acc


def _page_token(acc: dict, page_id: str) -> str:
    for p in acc.get("pages", []):
        if p.get("id") == page_id and p.get("page_token"):
            return p["page_token"]
    # fallback: usar user token (funciona pra algumas chamadas)
    return acc.get("access_token", "")


# ═══════════════════════════════════════════════════════════════════════════════
# INSTAGRAM
# ═══════════════════════════════════════════════════════════════════════════════
class InstagramPublishInput(BaseModel):
    page_id: str            # Facebook Page associada
    caption: str = ""
    image_url: Optional[str] = None   # para foto
    video_url: Optional[str] = None   # para Reels
    is_reel: bool = False


@router.get("/instagram/accounts")
async def ig_accounts(request: Request):
    user = await get_current_user(request)
    acc = await _account(user["_id"])
    out = []
    for p in acc.get("pages", []):
        ig = p.get("ig_account")
        if ig:
            out.append({"page_id": p["id"], "page_name": p["name"],
                         "ig_user_id": ig.get("id"), "ig_username": ig.get("username")})
    return {"accounts": out}


@router.post("/instagram/publish")
async def ig_publish(body: InstagramPublishInput, request: Request):
    user = await get_current_user(request)
    acc = await _account(user["_id"])
    token = _page_token(acc, body.page_id)
    ig_user_id = None
    for p in acc.get("pages", []):
        if p.get("id") == body.page_id and p.get("ig_account"):
            ig_user_id = p["ig_account"].get("id")
    if not ig_user_id:
        raise HTTPException(status_code=400, detail="Página não tem Instagram Business linkado")
    async with httpx.AsyncClient(timeout=60) as c:
        params = {"caption": body.caption, "access_token": token}
        if body.is_reel and body.video_url:
            params.update({"media_type": "REELS", "video_url": body.video_url})
        elif body.video_url:
            params.update({"media_type": "VIDEO", "video_url": body.video_url})
        elif body.image_url:
            params["image_url"] = body.image_url
        else:
            raise HTTPException(status_code=400, detail="informe image_url ou video_url")
        # 1. Criar container
        r = await c.post(f"{GRAPH}/{ig_user_id}/media", params=params)
        d = r.json()
        if r.status_code != 200 or "id" not in d:
            raise HTTPException(status_code=400, detail=f"Instagram: {d.get('error',{}).get('message',d)}")
        creation_id = d["id"]
        # 2. Publicar
        r2 = await c.post(f"{GRAPH}/{ig_user_id}/media_publish",
                           params={"creation_id": creation_id, "access_token": token})
        d2 = r2.json()
        if r2.status_code != 200 or "id" not in d2:
            raise HTTPException(status_code=400, detail=f"Publish falhou: {d2}")
        return {"message": "Publicado no Instagram", "media_id": d2["id"]}


# ═══════════════════════════════════════════════════════════════════════════════
# FACEBOOK PAGES
# ═══════════════════════════════════════════════════════════════════════════════
class FbPostInput(BaseModel):
    page_id: str
    message: str
    link: Optional[str] = None


@router.get("/facebook/pages")
async def fb_pages(request: Request):
    user = await get_current_user(request)
    acc = await _account(user["_id"])
    return {"pages": [{"id": p["id"], "name": p["name"], "category": p.get("category", "")}
                       for p in acc.get("pages", [])]}


@router.post("/facebook/post")
async def fb_post(body: FbPostInput, request: Request):
    user = await get_current_user(request)
    acc = await _account(user["_id"])
    token = _page_token(acc, body.page_id)
    async with httpx.AsyncClient(timeout=30) as c:
        params = {"message": body.message, "access_token": token}
        if body.link:
            params["link"] = body.link
        r = await c.post(f"{GRAPH}/{body.page_id}/feed", params=params)
        d = r.json()
        if r.status_code != 200:
            raise HTTPException(status_code=400, detail=f"FB post: {d}")
        return {"message": "Publicado no Facebook", "id": d.get("id", "")}


# ═══════════════════════════════════════════════════════════════════════════════
# WHATSAPP (Cloud API)
# ═══════════════════════════════════════════════════════════════════════════════
class WaSendInput(BaseModel):
    phone_number_id: str    # do WhatsApp Business (em business.facebook.com)
    to: str                 # numero E.164 sem '+'
    text: str


@router.post("/whatsapp/send")
async def wa_send(body: WaSendInput, request: Request):
    user = await get_current_user(request)
    acc = await _account(user["_id"])
    # WhatsApp usa o system-user access token (acc["access_token"]) com escopo whatsapp_business_messaging
    token = acc.get("access_token", "")
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(
            f"{GRAPH}/{body.phone_number_id}/messages",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": body.to,
                "type": "text",
                "text": {"body": body.text},
            },
        )
        d = r.json()
        if r.status_code != 200:
            raise HTTPException(status_code=400, detail=f"WhatsApp: {d.get('error',{}).get('message',d)}")
        msgs = d.get("messages", [])
        return {"message": "Mensagem WhatsApp enviada", "id": msgs[0].get("id", "") if msgs else ""}


# ═══════════════════════════════════════════════════════════════════════════════
# META DM AUTO-RESPONDER (placeholder básico)
# ═══════════════════════════════════════════════════════════════════════════════
class DmAutoRuleInput(BaseModel):
    page_id: str
    trigger_keyword: str    # se msg contém esse keyword, responde
    response_text: str
    enabled: bool = True


@router.get("/dm-rules")
async def list_dm_rules(request: Request):
    user = await get_current_user(request)
    rules = await db.meta_dm_rules.find({"user_id": user["_id"]}, {"_id": 0}).to_list(100)
    return rules


@router.post("/dm-rules")
async def create_dm_rule(body: DmAutoRuleInput, request: Request):
    user = await get_current_user(request)
    import uuid
    from datetime import datetime, timezone
    doc = {
        "id": str(uuid.uuid4()),
        "user_id": user["_id"],
        "page_id": body.page_id,
        "trigger_keyword": body.trigger_keyword.lower(),
        "response_text": body.response_text,
        "enabled": body.enabled,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.meta_dm_rules.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.delete("/dm-rules/{rule_id}")
async def delete_dm_rule(rule_id: str, request: Request):
    user = await get_current_user(request)
    await db.meta_dm_rules.delete_one({"id": rule_id, "user_id": user["_id"]})
    return {"message": "Regra removida"}


# ═══════════════════════════════════════════════════════════════════════════════
# Skill handlers (chat)
# ═══════════════════════════════════════════════════════════════════════════════
async def execute_instagram(args: dict, user_id: str) -> str:
    try:
        action = args.get("action", "publish")
        acc = await get_meta_account(user_id)
        if not acc:
            return "Conta Meta não conectada. Vá em 'Minhas Integrações'."
        if action == "list":
            accounts = []
            for p in acc.get("pages", []):
                if p.get("ig_account"):
                    accounts.append(f"• {p['name']}: @{p['ig_account'].get('username')} (page_id={p['id']})")
            return "Contas IG:\n" + ("\n".join(accounts) if accounts else "(nenhuma)")
        elif action == "publish":
            page_id = args.get("page_id", "")
            caption = args.get("caption", "")
            image_url = args.get("image_url")
            if not page_id or not image_url:
                return "Erro: page_id e image_url obrigatórios"
            ig_user_id = None
            for p in acc.get("pages", []):
                if p.get("id") == page_id and p.get("ig_account"):
                    ig_user_id = p["ig_account"].get("id")
            if not ig_user_id:
                return f"Página {page_id} não tem IG Business linkado"
            token = _page_token(acc, page_id)
            async with httpx.AsyncClient(timeout=60) as c:
                r = await c.post(f"{GRAPH}/{ig_user_id}/media",
                                  params={"caption": caption, "image_url": image_url, "access_token": token})
                d = r.json()
                if "id" not in d:
                    return f"Erro ao criar container: {d}"
                r2 = await c.post(f"{GRAPH}/{ig_user_id}/media_publish",
                                   params={"creation_id": d["id"], "access_token": token})
                d2 = r2.json()
                return f"Publicado no IG! media_id: {d2.get('id','?')}"
        return f"Ação '{action}' não suportada"
    except Exception as e:
        return f"Erro Instagram: {str(e)[:250]}"


async def execute_facebook(args: dict, user_id: str) -> str:
    try:
        acc = await get_meta_account(user_id)
        if not acc:
            return "Conta Meta não conectada."
        action = args.get("action", "publish")
        if action == "list_pages":
            return "Páginas:\n" + "\n".join([f"• {p['name']} (id: {p['id']})" for p in acc.get("pages", [])])
        elif action == "publish":
            page_id = args.get("page_id", "")
            message = args.get("message", "")
            if not page_id or not message:
                return "Erro: page_id e message obrigatórios"
            token = _page_token(acc, page_id)
            async with httpx.AsyncClient(timeout=30) as c:
                params = {"message": message, "access_token": token}
                if args.get("link"):
                    params["link"] = args["link"]
                r = await c.post(f"{GRAPH}/{page_id}/feed", params=params)
                d = r.json()
                if r.status_code != 200:
                    return f"Erro: {d}"
                return f"Publicado no Facebook! id: {d.get('id','?')}"
        return f"Ação '{action}' não suportada"
    except Exception as e:
        return f"Erro Facebook: {str(e)[:250]}"


async def execute_whatsapp(args: dict, user_id: str) -> str:
    try:
        acc = await get_meta_account(user_id)
        if not acc:
            return "Conta Meta não conectada."
        phone_id = args.get("phone_number_id", "")
        to = args.get("to", "")
        text = args.get("text", "")
        if not phone_id or not to or not text:
            return "Erro: phone_number_id, to e text obrigatórios"
        token = acc.get("access_token", "")
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.post(
                f"{GRAPH}/{phone_id}/messages",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text}},
            )
            d = r.json()
            if r.status_code != 200:
                return f"Erro WhatsApp: {d.get('error',{}).get('message',d)}"
            return f"WhatsApp enviado para {to}"
    except Exception as e:
        return f"Erro WhatsApp: {str(e)[:250]}"


def init(db_ref, get_user_ref, get_meta_fn):
    global db, get_current_user, get_meta_account
    db = db_ref
    get_current_user = get_user_ref
    get_meta_account = get_meta_fn
