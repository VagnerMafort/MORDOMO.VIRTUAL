"""
Google Skills — FASE 1 Roadmap.
Wrappers para Gmail, Drive, Sheets, Calendar, YouTube usando credenciais OAuth por usuário.

Uso como skill no chat:
    [SKILL:gmail] {"action":"list","query":"is:unread","max":5}
    [SKILL:drive] {"action":"list","query":"'root' in parents"}
    [SKILL:sheets] {"action":"create","title":"Minha Planilha","values":[["A","B"],["1","2"]]}
    [SKILL:calendar] {"action":"list","days_ahead":7}
    [SKILL:youtube] {"action":"my_videos","max":10}

Endpoints REST equivalentes estão em /api/google/{service}/{action}.
"""
from fastapi import APIRouter, HTTPException, Request, Depends, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import base64
import io
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/google")

# Injected
db = None
get_current_user = None
get_google_credentials = None  # from google_oauth


# ─── Helper ──────────────────────────────────────────────────────────────────
async def _service(user_id: str, name: str, version: str):
    creds = await get_google_credentials(user_id)
    if not creds:
        raise HTTPException(status_code=400, detail="Conta Google não conectada. Acesse 'Minhas Integrações' para conectar.")
    return build(name, version, credentials=creds, cache_discovery=False)


def _friendly_error(e: Exception) -> str:
    msg = str(e)
    if "insufficient" in msg.lower() or "scope" in msg.lower():
        return "Permissão Google insuficiente. Reconecte sua conta aceitando todos os escopos."
    if "invalid_grant" in msg.lower() or "Token has been expired" in msg:
        return "Token Google inválido/revogado. Reconecte sua conta."
    return f"Erro Google: {msg[:300]}"


# ═══════════════════════════════════════════════════════════════════════════════
# GMAIL
# ═══════════════════════════════════════════════════════════════════════════════
class GmailSendInput(BaseModel):
    to: str
    subject: str
    body: str
    cc: Optional[str] = None
    bcc: Optional[str] = None


@router.get("/gmail/list")
async def gmail_list(request: Request, query: str = "", max: int = 10):
    user = await get_current_user(request)
    try:
        svc = await _service(user["_id"], "gmail", "v1")
        res = svc.users().messages().list(userId="me", q=query, maxResults=min(max, 50)).execute()
        ids = [m["id"] for m in res.get("messages", [])]
        msgs = []
        for mid in ids:
            m = svc.users().messages().get(userId="me", id=mid, format="metadata",
                                            metadataHeaders=["From", "Subject", "Date"]).execute()
            headers = {h["name"]: h["value"] for h in m.get("payload", {}).get("headers", [])}
            msgs.append({
                "id": mid,
                "from": headers.get("From", ""),
                "subject": headers.get("Subject", "(sem assunto)"),
                "date": headers.get("Date", ""),
                "snippet": m.get("snippet", ""),
                "unread": "UNREAD" in m.get("labelIds", []),
            })
        return {"messages": msgs, "total": res.get("resultSizeEstimate", len(msgs))}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_friendly_error(e))


@router.get("/gmail/read/{message_id}")
async def gmail_read(message_id: str, request: Request):
    user = await get_current_user(request)
    try:
        svc = await _service(user["_id"], "gmail", "v1")
        m = svc.users().messages().get(userId="me", id=message_id, format="full").execute()
        headers = {h["name"]: h["value"] for h in m.get("payload", {}).get("headers", [])}
        body = ""
        payload = m.get("payload", {})
        def _extract(part):
            nonlocal body
            if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                body += base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
            for p in part.get("parts", []):
                _extract(p)
        _extract(payload)
        return {
            "id": message_id,
            "from": headers.get("From", ""),
            "to": headers.get("To", ""),
            "subject": headers.get("Subject", ""),
            "date": headers.get("Date", ""),
            "body": body[:8000],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_friendly_error(e))


@router.post("/gmail/send")
async def gmail_send(body: GmailSendInput, request: Request):
    user = await get_current_user(request)
    try:
        svc = await _service(user["_id"], "gmail", "v1")
        msg = MIMEMultipart("alternative")
        msg["To"] = body.to
        msg["Subject"] = body.subject
        if body.cc:
            msg["Cc"] = body.cc
        if body.bcc:
            msg["Bcc"] = body.bcc
        msg.attach(MIMEText(body.body, "plain", "utf-8"))
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
        sent = svc.users().messages().send(userId="me", body={"raw": raw}).execute()
        return {"message": "E-mail enviado", "id": sent.get("id", "")}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_friendly_error(e))


# ═══════════════════════════════════════════════════════════════════════════════
# DRIVE
# ═══════════════════════════════════════════════════════════════════════════════
class DriveFolderInput(BaseModel):
    name: str
    parent_id: Optional[str] = None


class DriveRenameInput(BaseModel):
    name: str


@router.get("/drive/list")
async def drive_list(request: Request, query: str = "", folder: Optional[str] = None, max: int = 30):
    user = await get_current_user(request)
    try:
        svc = await _service(user["_id"], "drive", "v3")
        q_parts = []
        if query:
            q_parts.append(f"name contains '{query}'")
        if folder:
            q_parts.append(f"'{folder}' in parents")
        q_parts.append("trashed=false")
        q = " and ".join(q_parts)
        res = svc.files().list(q=q, pageSize=min(max, 100),
                               fields="files(id,name,mimeType,size,modifiedTime,webViewLink,parents)").execute()
        return {"files": res.get("files", [])}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_friendly_error(e))


@router.post("/drive/folder")
async def drive_create_folder(body: DriveFolderInput, request: Request):
    user = await get_current_user(request)
    try:
        svc = await _service(user["_id"], "drive", "v3")
        meta = {"name": body.name, "mimeType": "application/vnd.google-apps.folder"}
        if body.parent_id:
            meta["parents"] = [body.parent_id]
        f = svc.files().create(body=meta, fields="id,name,webViewLink").execute()
        return {"message": "Pasta criada", "folder": f}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_friendly_error(e))


@router.post("/drive/upload")
async def drive_upload(request: Request, file: UploadFile = File(...), parent_id: Optional[str] = Form(None)):
    user = await get_current_user(request)
    try:
        svc = await _service(user["_id"], "drive", "v3")
        content = await file.read()
        meta = {"name": file.filename}
        if parent_id:
            meta["parents"] = [parent_id]
        media = MediaIoBaseUpload(io.BytesIO(content), mimetype=file.content_type or "application/octet-stream", resumable=False)
        f = svc.files().create(body=meta, media_body=media, fields="id,name,webViewLink,size").execute()
        return {"message": "Upload ok", "file": f}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_friendly_error(e))


@router.put("/drive/file/{file_id}/rename")
async def drive_rename(file_id: str, body: DriveRenameInput, request: Request):
    user = await get_current_user(request)
    try:
        svc = await _service(user["_id"], "drive", "v3")
        f = svc.files().update(fileId=file_id, body={"name": body.name}, fields="id,name").execute()
        return {"message": "Renomeado", "file": f}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_friendly_error(e))


@router.delete("/drive/file/{file_id}")
async def drive_delete(file_id: str, request: Request):
    user = await get_current_user(request)
    try:
        svc = await _service(user["_id"], "drive", "v3")
        # Move to trash (mais seguro que delete permanente)
        svc.files().update(fileId=file_id, body={"trashed": True}).execute()
        return {"message": "Enviado para a lixeira"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_friendly_error(e))


# ═══════════════════════════════════════════════════════════════════════════════
# SHEETS
# ═══════════════════════════════════════════════════════════════════════════════
class SheetsCreateInput(BaseModel):
    title: str
    values: Optional[List[List[Any]]] = None  # linhas


class SheetsWriteInput(BaseModel):
    spreadsheet_id: str
    range: str = "A1"
    values: List[List[Any]]
    mode: str = "update"  # update | append


@router.post("/sheets/create")
async def sheets_create(body: SheetsCreateInput, request: Request):
    user = await get_current_user(request)
    try:
        svc = await _service(user["_id"], "sheets", "v4")
        ss = svc.spreadsheets().create(body={"properties": {"title": body.title}},
                                        fields="spreadsheetId,spreadsheetUrl,properties.title").execute()
        if body.values:
            svc.spreadsheets().values().update(
                spreadsheetId=ss["spreadsheetId"], range="A1",
                valueInputOption="USER_ENTERED", body={"values": body.values}
            ).execute()
        return {"message": "Planilha criada", "spreadsheet": ss}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_friendly_error(e))


@router.get("/sheets/{spreadsheet_id}/read")
async def sheets_read(spreadsheet_id: str, request: Request, range: str = "A1:Z1000"):
    user = await get_current_user(request)
    try:
        svc = await _service(user["_id"], "sheets", "v4")
        r = svc.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=range).execute()
        return {"range": r.get("range", ""), "values": r.get("values", [])}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_friendly_error(e))


@router.post("/sheets/write")
async def sheets_write(body: SheetsWriteInput, request: Request):
    user = await get_current_user(request)
    try:
        svc = await _service(user["_id"], "sheets", "v4")
        req = {"valueInputOption": "USER_ENTERED", "body": {"values": body.values},
               "spreadsheetId": body.spreadsheet_id, "range": body.range}
        if body.mode == "append":
            r = svc.spreadsheets().values().append(**req, insertDataOption="INSERT_ROWS").execute()
        else:
            r = svc.spreadsheets().values().update(**req).execute()
        return {"message": "Dados gravados", "updated": r.get("updates", r)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_friendly_error(e))


# ═══════════════════════════════════════════════════════════════════════════════
# CALENDAR
# ═══════════════════════════════════════════════════════════════════════════════
class CalendarEventInput(BaseModel):
    summary: str
    start_iso: str  # "2026-04-20T10:00:00-03:00"
    end_iso: str
    description: Optional[str] = ""
    attendees: Optional[List[str]] = None


@router.get("/calendar/events")
async def calendar_list(request: Request, days_ahead: int = 7, calendar_id: str = "primary"):
    user = await get_current_user(request)
    try:
        svc = await _service(user["_id"], "calendar", "v3")
        now = datetime.now(timezone.utc)
        tmax = now + timedelta(days=days_ahead)
        r = svc.events().list(calendarId=calendar_id, timeMin=now.isoformat(),
                              timeMax=tmax.isoformat(), singleEvents=True,
                              orderBy="startTime", maxResults=50).execute()
        events = []
        for e in r.get("items", []):
            events.append({
                "id": e.get("id"),
                "summary": e.get("summary", "(sem título)"),
                "start": e.get("start", {}).get("dateTime") or e.get("start", {}).get("date"),
                "end": e.get("end", {}).get("dateTime") or e.get("end", {}).get("date"),
                "location": e.get("location", ""),
                "description": (e.get("description", "") or "")[:300],
                "link": e.get("htmlLink", ""),
            })
        return {"events": events}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_friendly_error(e))


@router.post("/calendar/events")
async def calendar_create(body: CalendarEventInput, request: Request, calendar_id: str = "primary"):
    user = await get_current_user(request)
    try:
        svc = await _service(user["_id"], "calendar", "v3")
        event = {
            "summary": body.summary,
            "description": body.description,
            "start": {"dateTime": body.start_iso},
            "end": {"dateTime": body.end_iso},
        }
        if body.attendees:
            event["attendees"] = [{"email": em} for em in body.attendees]
        r = svc.events().insert(calendarId=calendar_id, body=event).execute()
        return {"message": "Evento criado", "event": {"id": r.get("id"), "link": r.get("htmlLink")}}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_friendly_error(e))


# ═══════════════════════════════════════════════════════════════════════════════
# YOUTUBE
# ═══════════════════════════════════════════════════════════════════════════════
@router.get("/youtube/mine")
async def youtube_my_videos(request: Request, max: int = 25):
    user = await get_current_user(request)
    try:
        svc = await _service(user["_id"], "youtube", "v3")
        # Acha o uploads playlist do canal
        ch = svc.channels().list(part="contentDetails,snippet,statistics", mine=True).execute()
        if not ch.get("items"):
            return {"videos": [], "channel": None}
        channel = ch["items"][0]
        uploads = channel["contentDetails"]["relatedPlaylists"]["uploads"]
        pl = svc.playlistItems().list(part="snippet,contentDetails", playlistId=uploads, maxResults=min(max, 50)).execute()
        videos = [{
            "id": i["contentDetails"]["videoId"],
            "title": i["snippet"]["title"],
            "published": i["snippet"]["publishedAt"],
            "thumbnail": i["snippet"]["thumbnails"].get("default", {}).get("url", ""),
        } for i in pl.get("items", [])]
        return {
            "channel": {
                "id": channel["id"],
                "title": channel["snippet"]["title"],
                "subscribers": channel["statistics"].get("subscriberCount", "0"),
                "total_videos": channel["statistics"].get("videoCount", "0"),
            },
            "videos": videos,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_friendly_error(e))


@router.get("/youtube/search")
async def youtube_search(request: Request, q: str, max: int = 10):
    user = await get_current_user(request)
    try:
        svc = await _service(user["_id"], "youtube", "v3")
        r = svc.search().list(part="snippet", q=q, maxResults=min(max, 25), type="video").execute()
        return {"results": [{
            "id": i["id"]["videoId"],
            "title": i["snippet"]["title"],
            "channel": i["snippet"]["channelTitle"],
            "thumbnail": i["snippet"]["thumbnails"].get("default", {}).get("url", ""),
            "published": i["snippet"]["publishedAt"],
        } for i in r.get("items", [])]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_friendly_error(e))


@router.get("/youtube/comments")
async def youtube_comments(request: Request, video_id: str, max: int = 20):
    user = await get_current_user(request)
    try:
        svc = await _service(user["_id"], "youtube", "v3")
        r = svc.commentThreads().list(part="snippet", videoId=video_id, maxResults=min(max, 50),
                                       order="time", textFormat="plainText").execute()
        comments = []
        for thread in r.get("items", []):
            t = thread["snippet"]["topLevelComment"]["snippet"]
            comments.append({
                "id": thread["id"],
                "author": t["authorDisplayName"],
                "text": t["textDisplay"][:500],
                "likes": t.get("likeCount", 0),
                "published": t["publishedAt"],
            })
        return {"comments": comments}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_friendly_error(e))


class YoutubeUploadMetaInput(BaseModel):
    title: str
    description: str = ""
    privacy: str = "private"  # private | unlisted | public
    tags: Optional[List[str]] = None
    category_id: str = "22"  # People & Blogs (default)


@router.post("/youtube/upload")
async def youtube_upload(request: Request, file: UploadFile = File(...),
                          title: str = Form(...), description: str = Form(""),
                          privacy: str = Form("private"), tags: str = Form("")):
    user = await get_current_user(request)
    try:
        svc = await _service(user["_id"], "youtube", "v3")
        content = await file.read()
        body_meta = {
            "snippet": {"title": title, "description": description,
                        "tags": [t.strip() for t in tags.split(",") if t.strip()],
                        "categoryId": "22"},
            "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
        }
        media = MediaIoBaseUpload(io.BytesIO(content),
                                   mimetype=file.content_type or "video/*",
                                   chunksize=-1, resumable=True)
        req = svc.videos().insert(part="snippet,status", body=body_meta, media_body=media)
        response = None
        # upload em 1 shot (chunksize=-1). Pra vídeos grandes o frontend deveria usar upload resumable nativo.
        while response is None:
            status, response = req.next_chunk()
        return {"message": "Vídeo enviado", "video_id": response.get("id", ""), "url": f"https://youtu.be/{response.get('id','')}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=_friendly_error(e))


# ═══════════════════════════════════════════════════════════════════════════════
# CHAT SKILL INTEGRATION — handlers que server.py vai chamar
# ═══════════════════════════════════════════════════════════════════════════════
async def execute_gmail(args: dict, user_id: str) -> str:
    try:
        action = args.get("action", "list")
        svc = await _service(user_id, "gmail", "v1")
        if action == "list":
            q = args.get("query", "")
            n = min(int(args.get("max", 5)), 20)
            res = svc.users().messages().list(userId="me", q=q, maxResults=n).execute()
            ids = [m["id"] for m in res.get("messages", [])]
            out = []
            for mid in ids:
                m = svc.users().messages().get(userId="me", id=mid, format="metadata",
                                                metadataHeaders=["From", "Subject", "Date"]).execute()
                h = {x["name"]: x["value"] for x in m.get("payload", {}).get("headers", [])}
                out.append(f"• {h.get('Subject','(sem assunto)')} — {h.get('From','')} — {m.get('snippet','')[:120]}")
            return "Últimos emails:\n" + ("\n".join(out) if out else "(nenhum encontrado)")
        elif action == "send":
            to = args.get("to", ""); subject = args.get("subject", ""); body_text = args.get("body", "")
            if not to or not subject:
                return "Erro: 'to' e 'subject' são obrigatórios para enviar email"
            msg = MIMEText(body_text, "plain", "utf-8")
            msg["To"] = to; msg["Subject"] = subject
            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            r = svc.users().messages().send(userId="me", body={"raw": raw}).execute()
            return f"E-mail enviado para {to}. ID: {r.get('id','?')}"
        return f"Ação '{action}' não suportada em gmail. Use: list, send"
    except Exception as e:
        return _friendly_error(e)


async def execute_drive(args: dict, user_id: str) -> str:
    try:
        action = args.get("action", "list")
        svc = await _service(user_id, "drive", "v3")
        if action == "list":
            q = args.get("query", "")
            q_parts = [f"name contains '{q}'"] if q else []
            q_parts.append("trashed=false")
            r = svc.files().list(q=" and ".join(q_parts), pageSize=20,
                                  fields="files(id,name,mimeType,modifiedTime,webViewLink)").execute()
            files = r.get("files", [])
            lines = [f"• {f['name']} ({f['mimeType'].split('.')[-1]}) — {f.get('webViewLink','')}" for f in files]
            return f"Arquivos ({len(files)}):\n" + ("\n".join(lines) if lines else "(vazio)")
        elif action == "create_folder":
            name = args.get("name", "")
            if not name: return "Erro: 'name' é obrigatório"
            f = svc.files().create(body={"name": name, "mimeType": "application/vnd.google-apps.folder"},
                                    fields="id,name,webViewLink").execute()
            return f"Pasta '{f['name']}' criada: {f.get('webViewLink','')}"
        return f"Ação '{action}' não suportada em drive. Use: list, create_folder"
    except Exception as e:
        return _friendly_error(e)


async def execute_sheets(args: dict, user_id: str) -> str:
    try:
        action = args.get("action", "create")
        svc = await _service(user_id, "sheets", "v4")
        if action == "create":
            title = args.get("title", "Planilha sem título")
            values = args.get("values", [])
            ss = svc.spreadsheets().create(body={"properties": {"title": title}},
                                            fields="spreadsheetId,spreadsheetUrl").execute()
            if values:
                svc.spreadsheets().values().update(
                    spreadsheetId=ss["spreadsheetId"], range="A1",
                    valueInputOption="USER_ENTERED", body={"values": values}
                ).execute()
            return f"Planilha '{title}' criada: {ss.get('spreadsheetUrl','')}"
        elif action == "read":
            sid = args.get("spreadsheet_id", "")
            rng = args.get("range", "A1:Z100")
            if not sid: return "Erro: 'spreadsheet_id' é obrigatório"
            r = svc.spreadsheets().values().get(spreadsheetId=sid, range=rng).execute()
            vals = r.get("values", [])
            return f"Linhas ({len(vals)}):\n" + "\n".join([" | ".join(str(c) for c in row) for row in vals[:20]])
        return f"Ação '{action}' não suportada em sheets. Use: create, read"
    except Exception as e:
        return _friendly_error(e)


async def execute_calendar(args: dict, user_id: str) -> str:
    try:
        action = args.get("action", "list")
        svc = await _service(user_id, "calendar", "v3")
        if action == "list":
            days = int(args.get("days_ahead", 7))
            now = datetime.now(timezone.utc)
            tmax = now + timedelta(days=days)
            r = svc.events().list(calendarId="primary", timeMin=now.isoformat(),
                                   timeMax=tmax.isoformat(), singleEvents=True,
                                   orderBy="startTime", maxResults=20).execute()
            lines = []
            for e in r.get("items", []):
                start = e.get("start", {}).get("dateTime") or e.get("start", {}).get("date", "")
                lines.append(f"• {start[:16].replace('T',' ')} — {e.get('summary','(sem título)')}")
            return f"Próximos {days} dias ({len(lines)} eventos):\n" + ("\n".join(lines) if lines else "(nenhum)")
        elif action == "create":
            summary = args.get("summary", "")
            start = args.get("start_iso", "")
            end = args.get("end_iso", "")
            if not (summary and start and end):
                return "Erro: 'summary', 'start_iso' e 'end_iso' obrigatórios"
            r = svc.events().insert(calendarId="primary", body={
                "summary": summary, "description": args.get("description", ""),
                "start": {"dateTime": start}, "end": {"dateTime": end},
            }).execute()
            return f"Evento '{summary}' criado: {r.get('htmlLink','')}"
        return f"Ação '{action}' não suportada em calendar. Use: list, create"
    except Exception as e:
        return _friendly_error(e)


async def execute_youtube(args: dict, user_id: str) -> str:
    try:
        action = args.get("action", "my_videos")
        svc = await _service(user_id, "youtube", "v3")
        if action == "my_videos":
            ch = svc.channels().list(part="contentDetails,snippet,statistics", mine=True).execute()
            if not ch.get("items"): return "Nenhum canal encontrado."
            channel = ch["items"][0]
            uploads = channel["contentDetails"]["relatedPlaylists"]["uploads"]
            n = min(int(args.get("max", 10)), 25)
            pl = svc.playlistItems().list(part="snippet,contentDetails", playlistId=uploads, maxResults=n).execute()
            lines = [f"• {i['snippet']['title']} (id: {i['contentDetails']['videoId']})" for i in pl.get("items", [])]
            stats = channel["statistics"]
            return (f"Canal: {channel['snippet']['title']} — {stats.get('subscriberCount','0')} inscritos, "
                    f"{stats.get('videoCount','0')} vídeos\n\n" + "\n".join(lines))
        elif action == "search":
            q = args.get("query", "")
            if not q: return "Erro: 'query' é obrigatório"
            r = svc.search().list(part="snippet", q=q, maxResults=10, type="video").execute()
            lines = [f"• {i['snippet']['title']} — {i['snippet']['channelTitle']} (https://youtu.be/{i['id']['videoId']})"
                     for i in r.get("items", [])]
            return f"Resultados para '{q}':\n" + "\n".join(lines)
        elif action == "comments":
            vid = args.get("video_id", "")
            if not vid: return "Erro: 'video_id' é obrigatório"
            r = svc.commentThreads().list(part="snippet", videoId=vid, maxResults=10, textFormat="plainText").execute()
            lines = [f"• {t['snippet']['topLevelComment']['snippet']['authorDisplayName']}: "
                     f"{t['snippet']['topLevelComment']['snippet']['textDisplay'][:200]}"
                     for t in r.get("items", [])]
            return "Comentários:\n" + ("\n".join(lines) if lines else "(nenhum)")
        return f"Ação '{action}' não suportada em youtube. Use: my_videos, search, comments"
    except Exception as e:
        return _friendly_error(e)


def init(db_ref, get_user_ref, get_creds_fn):
    global db, get_current_user, get_google_credentials
    db = db_ref
    get_current_user = get_user_ref
    get_google_credentials = get_creds_fn
