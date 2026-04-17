"""
Workflow Engine — FASE 5 Roadmap.
Permite criar fluxos de múltiplos passos que encadeiam skills.

Modelo:
    Workflow = {
        id, name, description, trigger (manual|schedule|webhook|chat),
        steps: [
            {id, skill, args, output_var?, on_error (stop|continue)},
            ...
        ],
        created_by, created_at, active
    }

Args suportam templating com {{var}} onde var = output_var de um step anterior.
Exemplo:
    Passo 1: [SKILL:web_search] {"query": "notícias cripto"} → output_var: "noticias"
    Passo 2: [SKILL:gmail] {"action":"send","to":"eu@x.com","subject":"Resumo","body":"{{noticias}}"}
"""
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from bson import ObjectId
import uuid
import json
import re
import logging
import asyncio

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/workflows")

# Injected
db = None
get_current_user = None
execute_skill = None  # from server.py


# ─── Models ───────────────────────────────────────────────────────────────────
class WorkflowStep(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    skill: str
    args: Dict[str, Any] = Field(default_factory=dict)
    output_var: Optional[str] = None
    on_error: str = "stop"  # stop | continue
    label: Optional[str] = None


class WorkflowCreate(BaseModel):
    name: str
    description: str = ""
    steps: List[WorkflowStep]
    trigger: str = "manual"  # manual | chat | schedule | webhook
    schedule_cron: Optional[str] = None
    active: bool = True


class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    steps: Optional[List[WorkflowStep]] = None
    active: Optional[bool] = None
    trigger: Optional[str] = None
    schedule_cron: Optional[str] = None


class RunInput(BaseModel):
    initial_vars: Optional[Dict[str, Any]] = None


# ─── Templating: substitui {{var}} em strings recursivamente ─────────────────
_TEMPLATE_RE = re.compile(r"\{\{\s*([\w\.]+)\s*\}\}")


def _interp(value: Any, ctx: Dict[str, Any]) -> Any:
    if isinstance(value, str):
        def repl(m):
            key = m.group(1)
            v = ctx
            for part in key.split("."):
                if isinstance(v, dict):
                    v = v.get(part, "")
                else:
                    v = ""
            return str(v) if v is not None else ""
        return _TEMPLATE_RE.sub(repl, value)
    if isinstance(value, dict):
        return {k: _interp(v, ctx) for k, v in value.items()}
    if isinstance(value, list):
        return [_interp(v, ctx) for v in value]
    return value


# ─── Execução ─────────────────────────────────────────────────────────────────
async def _run_workflow(wf: dict, user_id: str, initial_vars: Dict[str, Any] = None) -> dict:
    """Executa um workflow e retorna resultado + log dos passos."""
    ctx = dict(initial_vars or {})
    step_logs = []
    started = datetime.now(timezone.utc)
    final_status = "success"
    for idx, step in enumerate(wf.get("steps", [])):
        step_id = step.get("id", f"step-{idx}")
        skill = step.get("skill", "")
        args = _interp(step.get("args", {}) or {}, ctx)
        label = step.get("label") or skill
        t0 = datetime.now(timezone.utc)
        try:
            # execute_skill expects (skill_id, args, user_id)
            output = await execute_skill(skill, args, user_id)
        except Exception as e:
            output = f"Erro: {e}"
            if step.get("on_error", "stop") == "stop":
                step_logs.append({
                    "step_id": step_id, "label": label, "skill": skill,
                    "status": "error", "output": output,
                    "duration_ms": int((datetime.now(timezone.utc) - t0).total_seconds() * 1000),
                })
                final_status = "error"
                break
        var = step.get("output_var")
        if var:
            ctx[var] = output
        step_logs.append({
            "step_id": step_id, "label": label, "skill": skill,
            "status": "ok" if not str(output).startswith("Erro") else "warning",
            "output": (str(output) or "")[:2000],
            "duration_ms": int((datetime.now(timezone.utc) - t0).total_seconds() * 1000),
        })
    finished = datetime.now(timezone.utc)
    exec_doc = {
        "id": str(uuid.uuid4()),
        "workflow_id": wf["id"],
        "workflow_name": wf.get("name", ""),
        "user_id": user_id,
        "status": final_status,
        "started_at": started.isoformat(),
        "finished_at": finished.isoformat(),
        "duration_ms": int((finished - started).total_seconds() * 1000),
        "steps": step_logs,
        "initial_vars": initial_vars or {},
        "final_context_keys": list(ctx.keys()),
    }
    await db.workflow_executions.insert_one(exec_doc)
    exec_doc.pop("_id", None)
    return exec_doc


# ─── CRUD endpoints ───────────────────────────────────────────────────────────
@router.get("")
async def list_workflows(request: Request):
    user = await get_current_user(request)
    wfs = await db.workflows.find({"user_id": user["_id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return wfs


@router.post("")
async def create_workflow(body: WorkflowCreate, request: Request):
    user = await get_current_user(request)
    wf_id = str(uuid.uuid4())
    doc = {
        "id": wf_id,
        "user_id": user["_id"],
        "name": body.name.strip(),
        "description": body.description,
        "steps": [s.model_dump() for s in body.steps],
        "trigger": body.trigger,
        "schedule_cron": body.schedule_cron,
        "active": body.active,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.workflows.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.get("/{wf_id}")
async def get_workflow(wf_id: str, request: Request):
    user = await get_current_user(request)
    wf = await db.workflows.find_one({"id": wf_id, "user_id": user["_id"]}, {"_id": 0})
    if not wf:
        raise HTTPException(status_code=404, detail="Fluxo não encontrado")
    return wf


@router.put("/{wf_id}")
async def update_workflow(wf_id: str, body: WorkflowUpdate, request: Request):
    user = await get_current_user(request)
    update = {}
    for k, v in body.model_dump().items():
        if v is None:
            continue
        if k == "steps":
            update[k] = [s for s in v]
        else:
            update[k] = v
    if update:
        await db.workflows.update_one({"id": wf_id, "user_id": user["_id"]}, {"$set": update})
    wf = await db.workflows.find_one({"id": wf_id, "user_id": user["_id"]}, {"_id": 0})
    return wf


@router.delete("/{wf_id}")
async def delete_workflow(wf_id: str, request: Request):
    user = await get_current_user(request)
    await db.workflows.delete_one({"id": wf_id, "user_id": user["_id"]})
    return {"message": "Fluxo deletado"}


@router.post("/{wf_id}/run")
async def run_workflow(wf_id: str, body: RunInput, request: Request):
    user = await get_current_user(request)
    wf = await db.workflows.find_one({"id": wf_id, "user_id": user["_id"]})
    if not wf:
        raise HTTPException(status_code=404, detail="Fluxo não encontrado")
    if not wf.get("active", True):
        raise HTTPException(status_code=400, detail="Fluxo está desativado")
    result = await _run_workflow(wf, user["_id"], body.initial_vars)
    return result


@router.post("/run-by-name")
async def run_by_name(request: Request):
    """Permite disparar um workflow por nome (usado pelo chat skill)."""
    user = await get_current_user(request)
    body = await request.json()
    name = (body.get("name") or "").strip()
    initial_vars = body.get("initial_vars") or {}
    wf = await db.workflows.find_one({"user_id": user["_id"], "name": name})
    if not wf:
        raise HTTPException(status_code=404, detail=f"Fluxo '{name}' não encontrado")
    result = await _run_workflow(wf, user["_id"], initial_vars)
    return result


@router.get("/executions/recent")
async def recent_executions(request: Request, limit: int = 50):
    user = await get_current_user(request)
    execs = await db.workflow_executions.find({"user_id": user["_id"]}, {"_id": 0}).sort("started_at", -1).limit(limit).to_list(limit)
    return execs


# ─── Skill handler para uso via chat ──────────────────────────────────────────
async def execute_workflow_skill(args: dict, user_id: str) -> str:
    name = (args.get("name") or "").strip()
    if not name:
        return "Erro: informe 'name' do fluxo a executar"
    wf = await db.workflows.find_one({"user_id": user_id, "name": name})
    if not wf:
        return f"Fluxo '{name}' não encontrado"
    if not wf.get("active", True):
        return f"Fluxo '{name}' está desativado"
    initial_vars = args.get("initial_vars") or {}
    result = await _run_workflow(wf, user_id, initial_vars)
    summary = [f"Fluxo '{name}' — status: {result['status']} ({result['duration_ms']}ms)"]
    for s in result.get("steps", []):
        summary.append(f"  • {s['label']} [{s['status']}]: {s['output'][:150]}")
    return "\n".join(summary)


def init(db_ref, get_user_ref, execute_skill_fn):
    global db, get_current_user, execute_skill
    db = db_ref
    get_current_user = get_user_ref
    execute_skill = execute_skill_fn
