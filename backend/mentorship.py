"""
Mentorship Module - Create complete mentorship programs from user knowledge
"""
from fastapi import APIRouter, Request, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import List, Optional
import uuid, os, json
from datetime import datetime, timezone

router = APIRouter(prefix="/api/mentorship")

db = None
get_current_user = None
llm_generate = None  # Will be set from server.py

def init(database, auth_fn, llm_fn):
    global db, get_current_user, llm_generate
    db = database
    get_current_user = auth_fn
    llm_generate = llm_fn

MENTORSHIP_PROMPT = """Voce e um especialista em criacao de mentorias e infoprodutos digitais. Com base no conhecimento fornecido pelo usuario, crie uma MENTORIA COMPLETA e detalhada.

## CONHECIMENTO DO USUARIO:
{knowledge}

## INSTRUCOES:
Crie uma mentoria completa com a seguinte estrutura:

1. **NOME DA MENTORIA** - Um nome atrativo e profissional
2. **PROMESSA PRINCIPAL** - O que o aluno vai conquistar (1 frase poderosa)
3. **PUBLICO-ALVO** - Para quem e essa mentoria (perfil detalhado)
4. **DURACAO E FORMATO** - Semanas, encontros, formato (ao vivo, gravado, misto)
5. **MODULOS DETALHADOS** - Cada modulo com:
   - Nome do modulo
   - Objetivo
   - Aulas (titulo + descricao de cada aula)
   - Materiais complementares
   - Exercicio pratico
6. **BONUS** - Materiais extras, templates, checklists
7. **METODOLOGIA** - Como o aluno vai aprender (passo a passo)
8. **RESULTADOS ESPERADOS** - O que o aluno alcanca ao final de cada modulo
9. **FAQ** - Perguntas frequentes e respostas
10. **COPY DE VENDAS** - Headline, subheadline, bullets de beneficio, CTA
11. **ESTRATEGIA DE PRECO** - Sugestao de precificacao com ancoragem

Seja extremamente detalhado e profissional. Cada modulo deve ter no minimo 4-5 aulas. A mentoria deve ter no minimo 6 modulos.
Responda em portugues brasileiro."""

class MentorshipCreate(BaseModel):
    title: Optional[str] = ""
    knowledge_text: str = ""
    niche: str = ""
    target_audience: str = ""
    duration_weeks: int = 8

class MentorshipUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    status: Optional[str] = None

# ─── Knowledge Upload ────────────────────────────────────────────────────────
@router.post("/upload-knowledge")
async def upload_knowledge(request: Request, file: UploadFile = File(...)):
    """Upload a file with user's knowledge (txt, pdf, md, doc)."""
    user = await get_current_user(request)
    content = await file.read()
    text = ""
    filename = file.filename or "upload"

    if filename.endswith(('.txt', '.md')):
        text = content.decode('utf-8', errors='ignore')
    elif filename.endswith('.csv'):
        text = content.decode('utf-8', errors='ignore')
    else:
        # Try to decode as text
        try:
            text = content.decode('utf-8', errors='ignore')
        except Exception:
            text = str(content[:5000])

    # Store knowledge
    knowledge_id = str(uuid.uuid4())
    doc = {
        "id": knowledge_id,
        "user_id": user["_id"],
        "filename": filename,
        "content": text[:50000],  # Limit to 50k chars
        "size": len(text),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.knowledge_base.insert_one(doc)
    doc.pop("_id", None)
    return {"id": knowledge_id, "filename": filename, "size": len(text), "preview": text[:300]}

@router.get("/knowledge")
async def list_knowledge(request: Request):
    user = await get_current_user(request)
    items = await db.knowledge_base.find(
        {"user_id": user["_id"]}, {"_id": 0, "content": 0}
    ).sort("created_at", -1).to_list(20)
    return items

@router.delete("/knowledge/{kid}")
async def delete_knowledge(kid: str, request: Request):
    user = await get_current_user(request)
    await db.knowledge_base.delete_one({"id": kid, "user_id": user["_id"]})
    return {"message": "Conhecimento removido"}

# ─── Mentorship CRUD ─────────────────────────────────────────────────────────
@router.get("/list")
async def list_mentorships(request: Request):
    user = await get_current_user(request)
    mentorships = await db.mentorships.find(
        {"user_id": user["_id"]}, {"_id": 0}
    ).sort("created_at", -1).to_list(20)
    return mentorships

@router.get("/{mentorship_id}")
async def get_mentorship(mentorship_id: str, request: Request):
    user = await get_current_user(request)
    m = await db.mentorships.find_one({"id": mentorship_id, "user_id": user["_id"]}, {"_id": 0})
    if not m:
        raise HTTPException(status_code=404, detail="Mentoria nao encontrada")
    return m

@router.post("/generate")
async def generate_mentorship(body: MentorshipCreate, request: Request):
    """Generate a complete mentorship using AI based on user's knowledge."""
    user = await get_current_user(request)

    # Gather knowledge from text + uploaded files
    knowledge_parts = []
    if body.knowledge_text:
        knowledge_parts.append(body.knowledge_text)

    # Also pull from knowledge base
    kb_items = await db.knowledge_base.find({"user_id": user["_id"]}).to_list(10)
    for item in kb_items:
        knowledge_parts.append(f"[Arquivo: {item.get('filename', '')}]\n{item.get('content', '')[:10000]}")

    if not knowledge_parts:
        raise HTTPException(status_code=400, detail="Forneca seu conhecimento no campo de texto ou faca upload de um arquivo")

    full_knowledge = "\n\n---\n\n".join(knowledge_parts)
    if body.niche:
        full_knowledge += f"\n\nNicho: {body.niche}"
    if body.target_audience:
        full_knowledge += f"\nPublico-alvo desejado: {body.target_audience}"
    if body.duration_weeks:
        full_knowledge += f"\nDuracao desejada: {body.duration_weeks} semanas"

    # Generate via LLM
    prompt = MENTORSHIP_PROMPT.format(knowledge=full_knowledge[:15000])
    content = await llm_generate(prompt, user["_id"])

    # Store mentorship
    mentorship_id = str(uuid.uuid4())
    title = body.title or "Nova Mentoria"
    # Try to extract title from generated content
    if "**NOME DA MENTORIA**" in content:
        try:
            title_line = content.split("**NOME DA MENTORIA**")[1].split("\n")[0].strip().strip(":-–— ")
            if title_line:
                title = title_line
        except Exception:
            pass

    doc = {
        "id": mentorship_id,
        "user_id": user["_id"],
        "title": title,
        "content": content,
        "knowledge_summary": full_knowledge[:1000],
        "niche": body.niche,
        "target_audience": body.target_audience,
        "duration_weeks": body.duration_weeks,
        "status": "draft",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.mentorships.insert_one(doc)
    doc.pop("_id", None)
    return doc

@router.put("/{mentorship_id}")
async def update_mentorship(mentorship_id: str, body: MentorshipUpdate, request: Request):
    user = await get_current_user(request)
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    if data:
        await db.mentorships.update_one({"id": mentorship_id, "user_id": user["_id"]}, {"$set": data})
    m = await db.mentorships.find_one({"id": mentorship_id, "user_id": user["_id"]}, {"_id": 0})
    return m

@router.delete("/{mentorship_id}")
async def delete_mentorship(mentorship_id: str, request: Request):
    user = await get_current_user(request)
    await db.mentorships.delete_one({"id": mentorship_id, "user_id": user["_id"]})
    return {"message": "Mentoria deletada"}
