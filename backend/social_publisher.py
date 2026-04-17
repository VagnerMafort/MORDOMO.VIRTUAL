"""
Social Unified Publisher — FASE 3 Roadmap.
Endpoint único que distribui conteúdo (vídeo/imagem/texto) para múltiplas redes sociais.

Uso REST (frontend):
    POST /api/social/publish (multipart/form-data)
      title, description, networks=["youtube","tiktok","instagram"], privacy, file

Uso como skill (chat):
    [SKILL:social_publish] {
      "title":"Meu video",
      "description":"Descricao...",
      "media_url":"https://...",   # alternativa ao upload direto
      "networks":["youtube"]
    }

Cada conector tenta publicar e retorna status individual — erros em uma rede não
impedem as outras. Extensível: basta registrar um novo publisher em PUBLISHERS.
"""
from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import httpx
import io
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/social")

# Injected
db = None
get_current_user = None
get_google_credentials = None


# ─── Conectores ───────────────────────────────────────────────────────────────
async def _publish_youtube(user_id: str, title: str, description: str,
                            media_bytes: bytes, mime: str, privacy: str = "private",
                            tags: List[str] = None) -> Dict[str, Any]:
    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseUpload
        creds = await get_google_credentials(user_id)
        if not creds:
            return {"network": "youtube", "status": "error", "message": "Google não conectado. Acesse Minhas Integrações."}
        svc = build("youtube", "v3", credentials=creds, cache_discovery=False)
        body = {
            "snippet": {"title": title, "description": description,
                        "tags": tags or [], "categoryId": "22"},
            "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
        }
        media = MediaIoBaseUpload(io.BytesIO(media_bytes), mimetype=mime or "video/*",
                                   chunksize=-1, resumable=True)
        req = svc.videos().insert(part="snippet,status", body=body, media_body=media)
        response = None
        while response is None:
            _, response = req.next_chunk()
        vid = response.get("id", "")
        return {"network": "youtube", "status": "ok", "id": vid, "url": f"https://youtu.be/{vid}"}
    except Exception as e:
        return {"network": "youtube", "status": "error", "message": str(e)[:300]}


async def _publish_placeholder(network_name: str) -> Dict[str, Any]:
    return {"network": network_name, "status": "not_implemented",
            "message": f"Publisher para '{network_name}' ainda não implementado — roadmap Fase 2/3."}


PUBLISHERS = {
    "youtube": _publish_youtube,
    # Placeholders para extensibilidade:
    "tiktok": None,      # TODO: OAuth TikTok Content Posting API
    "instagram": None,   # TODO: Meta Graph API (após FASE 2)
    "facebook": None,    # TODO: Meta Graph API
    "whatsapp": None,    # TODO: WhatsApp Cloud API
}


# ─── Endpoint REST ────────────────────────────────────────────────────────────
@router.post("/publish")
async def publish(request: Request, title: str = Form(...), description: str = Form(""),
                  networks: str = Form("youtube"), privacy: str = Form("private"),
                  tags: str = Form(""), file: UploadFile = File(...)):
    user = await get_current_user(request)
    targets = [n.strip().lower() for n in networks.split(",") if n.strip()]
    if not targets:
        raise HTTPException(status_code=400, detail="Informe pelo menos 1 network")
    media_bytes = await file.read()
    mime = file.content_type or "video/*"
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    results = []
    for net in targets:
        publisher = PUBLISHERS.get(net)
        if publisher is None:
            results.append(await _publish_placeholder(net))
            continue
        r = await publisher(user["_id"], title, description, media_bytes, mime, privacy, tag_list)
        results.append(r)
    ok_count = sum(1 for r in results if r["status"] == "ok")
    return {
        "summary": f"{ok_count}/{len(results)} redes publicadas",
        "results": results,
    }


@router.get("/networks")
async def list_networks(request: Request):
    """Retorna redes disponíveis e seus status de conexão para o usuário atual."""
    user = await get_current_user(request)
    # YouTube depende de Google conectado
    google = await db.google_accounts.find_one({"user_id": user["_id"]})
    return {
        "networks": [
            {"key": "youtube", "name": "YouTube", "connected": bool(google), "available": True},
            {"key": "tiktok", "name": "TikTok", "connected": False, "available": False, "message": "Em breve (Fase 3 oficial)"},
            {"key": "instagram", "name": "Instagram", "connected": False, "available": False, "message": "Em breve (Fase 2 - Meta)"},
            {"key": "facebook", "name": "Facebook", "connected": False, "available": False, "message": "Em breve (Fase 2 - Meta)"},
            {"key": "whatsapp", "name": "WhatsApp Business", "connected": False, "available": False, "message": "Em breve (Fase 2 - Meta)"},
        ]
    }


# ─── Skill handler (chat) ─────────────────────────────────────────────────────
async def execute_social_publish(args: dict, user_id: str) -> str:
    title = args.get("title", "").strip()
    description = args.get("description", "").strip()
    media_url = args.get("media_url", "").strip()
    networks = args.get("networks") or ["youtube"]
    privacy = args.get("privacy", "private")
    if not title:
        return "Erro: 'title' é obrigatório"
    if not media_url:
        return "Erro: 'media_url' é obrigatório para publicação via chat (upload de arquivo só via interface)"
    # Baixa mídia
    try:
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.get(media_url, follow_redirects=True)
            r.raise_for_status()
            media_bytes = r.content
            mime = r.headers.get("content-type", "video/mp4")
    except Exception as e:
        return f"Erro ao baixar mídia de {media_url}: {str(e)[:200]}"
    results = []
    for net in networks:
        pub = PUBLISHERS.get(net)
        if pub is None:
            results.append(await _publish_placeholder(net))
        else:
            results.append(await pub(user_id, title, description, media_bytes, mime, privacy, []))
    lines = ["Publicação multi-rede:"]
    for r in results:
        if r["status"] == "ok":
            lines.append(f"  ✓ {r['network']}: {r.get('url', r.get('id',''))}")
        elif r["status"] == "not_implemented":
            lines.append(f"  • {r['network']}: (ainda não implementado)")
        else:
            lines.append(f"  ✗ {r['network']}: {r.get('message','erro')}")
    return "\n".join(lines)


def init(db_ref, get_user_ref, get_creds_fn):
    global db, get_current_user, get_google_credentials
    db = db_ref
    get_current_user = get_user_ref
    get_google_credentials = get_creds_fn
