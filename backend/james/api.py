"""
FastAPI routes para o JAMES AGENCY.
Rotas públicas (autenticadas):
  GET    /api/james/agents                   — lista 24 agentes
  GET    /api/james/products                 — lista produtos do usuário
  POST   /api/james/products                 — cria produto
  DELETE /api/james/products/{id}
  POST   /api/james/products/{id}/ingest     — ingest manual de métricas (sensor layer)
  POST   /api/james/products/{id}/seed       — gera métricas sintéticas para demo
  POST   /api/james/products/{id}/tick       — roda 1 ciclo completo (com opção ?evaluate=true)
  GET    /api/james/products/{id}/anomalies
  GET    /api/james/products/{id}/plans
  POST   /api/james/plans/{plan_id}/approve  — marca plano como approved
  POST   /api/james/plans/{plan_id}/run      — executa plano
  GET    /api/james/reports                  — lista relatórios
  POST   /api/james/reports/generate         — gera novo relatório via ECHO
  GET    /api/james/learnings                — lista aprendizados
"""
from fastapi import APIRouter, HTTPException, Request, Query, Body
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
import random
import logging

from .models import Product, MetricSnapshot, _now
from . import orchestrator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/james")

# Injected
db = None
get_current_user = None


def init(db_ref, user_fn):
    global db, get_current_user
    db = db_ref
    get_current_user = user_fn


# ─── Produtos ─────────────────────────────────────────────────────────────────
class ProductIn(BaseModel):
    name: str
    niche: str = ""
    target_audience: str = ""
    offer: str = ""
    budget_daily: float = 0.0


class AutopilotConfigIn(BaseModel):
    autopilot_enabled: bool
    autopilot_interval_min: int = 30
    auto_approve_risk: str = "low"        # none | low | medium | all
    daily_report_enabled: bool = False
    daily_report_channel: str = "telegram"
    daily_report_hour: int = 9


@router.get("/agents")
async def list_agents(request: Request):
    await get_current_user(request)
    return {"agents": orchestrator.list_agents(), "total": len(orchestrator.list_agents())}


@router.get("/products")
async def list_products(request: Request):
    user = await get_current_user(request)
    items = await db.james_products.find({"user_id": user["_id"]}, {"_id": 0}).to_list(100)
    return items


@router.post("/products")
async def create_product(request: Request, body: ProductIn):
    user = await get_current_user(request)
    p = Product(user_id=user["_id"], **body.model_dump())
    await db.james_products.insert_one(p.model_dump())
    return p.model_dump()


@router.delete("/products/{product_id}")
async def delete_product(request: Request, product_id: str):
    user = await get_current_user(request)
    r = await db.james_products.delete_one({"id": product_id, "user_id": user["_id"]})
    if r.deleted_count == 0:
        raise HTTPException(404, "Produto não encontrado")
    # opcional: limpar métricas
    await db.james_metrics.delete_many({"product_id": product_id})
    await db.james_baselines.delete_many({"product_id": product_id})
    await db.james_anomalies.delete_many({"product_id": product_id})
    await db.james_plans.delete_many({"product_id": product_id})
    return {"message": "Produto removido"}


@router.put("/products/{product_id}/autopilot")
async def set_autopilot(request: Request, product_id: str, body: AutopilotConfigIn):
    """Liga/desliga o Autopilot 24/7 e configura parâmetros."""
    user = await get_current_user(request)
    p = await db.james_products.find_one({"id": product_id, "user_id": user["_id"]})
    if not p:
        raise HTTPException(404, "Produto não encontrado")
    valid_risks = {"none", "low", "medium", "all"}
    if body.auto_approve_risk not in valid_risks:
        raise HTTPException(400, f"auto_approve_risk deve ser um de: {valid_risks}")
    update = body.model_dump()
    update["updated_at"] = _now()
    await db.james_products.update_one({"id": product_id}, {"$set": update})
    return {"message": "Autopilot configurado", "config": update}


@router.get("/products/{product_id}/autopilot")
async def get_autopilot(request: Request, product_id: str):
    user = await get_current_user(request)
    p = await db.james_products.find_one({"id": product_id, "user_id": user["_id"]}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Produto não encontrado")
    return {
        "autopilot_enabled": p.get("autopilot_enabled", False),
        "autopilot_interval_min": p.get("autopilot_interval_min", 30),
        "auto_approve_risk": p.get("auto_approve_risk", "low"),
        "daily_report_enabled": p.get("daily_report_enabled", False),
        "daily_report_channel": p.get("daily_report_channel", "telegram"),
        "daily_report_hour": p.get("daily_report_hour", 9),
        "last_autopilot_tick": p.get("last_autopilot_tick"),
        "last_autopilot_report": p.get("last_autopilot_report"),
    }


# ─── Ingest de métricas (Camada 1) ────────────────────────────────────────────
class MetricIngestPoint(BaseModel):
    metric: str
    value: float
    dimension: Dict[str, str] = {}
    captured_at: Optional[str] = None


class MetricIngestPayload(BaseModel):
    source: str = "manual"
    points: List[MetricIngestPoint]


@router.post("/products/{product_id}/ingest")
async def ingest_metrics(request: Request, product_id: str, body: MetricIngestPayload):
    user = await get_current_user(request)
    p = await db.james_products.find_one({"id": product_id, "user_id": user["_id"]})
    if not p:
        raise HTTPException(404, "Produto não encontrado")
    from . import layers
    n = await layers.layer1_sensors_ingest(product_id, body.source,
                                             [pt.model_dump() for pt in body.points])
    return {"inserted": n}


# ─── Demo seed (gera 7 dias de métricas sintéticas + 1 anomalia recente) ─────
@router.post("/products/{product_id}/seed")
async def seed_product(request: Request, product_id: str,
                       days: int = Query(7, ge=1, le=30),
                       anomaly: bool = Query(True)):
    """Popula métricas sintéticas pra demonstrar o sistema."""
    user = await get_current_user(request)
    p = await db.james_products.find_one({"id": product_id, "user_id": user["_id"]})
    if not p:
        raise HTTPException(404, "Produto não encontrado")
    now = datetime.now(timezone.utc)
    points = []
    baselines = {
        "impressions": 10000, "clicks": 350, "ctr": 3.5, "cpa": 12.0,
        "cpc": 0.35, "conversions": 25, "revenue": 850.0, "roas": 3.2, "leads": 40,
    }
    for d in range(days):
        ts = (now - timedelta(days=days - d)).isoformat()
        for metric, base in baselines.items():
            noise = base * random.uniform(-0.12, 0.12)
            val = round(base + noise, 3)
            points.append({"metric": metric, "value": val,
                            "dimension": {"campaign": "camp_main"},
                            "captured_at": ts})
    # anomalia recente (último tick): CTR cai 45%, CPA sobe 50%, ROAS cai 40%
    if anomaly:
        recent = now.isoformat()
        points.append({"metric": "ctr", "value": 3.5 * 0.55,
                        "dimension": {"campaign": "camp_main"}, "captured_at": recent})
        points.append({"metric": "cpa", "value": 12.0 * 1.50,
                        "dimension": {"campaign": "camp_main"}, "captured_at": recent})
        points.append({"metric": "roas", "value": 3.2 * 0.60,
                        "dimension": {"campaign": "camp_main"}, "captured_at": recent})
    from . import layers
    n = await layers.layer1_sensors_ingest(product_id, "manual", points)
    return {"inserted": n, "days": days, "anomaly_injected": anomaly}


# ─── Tick + planos ────────────────────────────────────────────────────────────
@router.post("/products/{product_id}/tick")
async def tick_product(request: Request, product_id: str,
                        evaluate: bool = Query(False)):
    user = await get_current_user(request)
    p = await db.james_products.find_one({"id": product_id, "user_id": user["_id"]})
    if not p:
        raise HTTPException(404, "Produto não encontrado")
    r = await orchestrator.tick(product_id, evaluate=evaluate)
    return r


@router.get("/products/{product_id}/anomalies")
async def list_anomalies(request: Request, product_id: str,
                          status: Optional[str] = None):
    await get_current_user(request)
    q = {"product_id": product_id}
    if status:
        q["status"] = status
    items = await db.james_anomalies.find(q, {"_id": 0}).sort("detected_at", -1).limit(100).to_list(100)
    return items


@router.get("/products/{product_id}/plans")
async def list_plans(request: Request, product_id: str):
    await get_current_user(request)
    items = await db.james_plans.find({"product_id": product_id}, {"_id": 0}).sort("created_at", -1).limit(50).to_list(50)
    return items


@router.post("/plans/{plan_id}/approve")
async def approve_plan(request: Request, plan_id: str):
    await get_current_user(request)
    r = await db.james_plans.update_one({"id": plan_id, "status": "validated"},
                                          {"$set": {"status": "approved"}})
    if r.matched_count == 0:
        raise HTTPException(400, "Plano não está validado ou não existe")
    return {"message": "Aprovado"}


@router.post("/plans/{plan_id}/run")
async def run_plan(request: Request, plan_id: str):
    await get_current_user(request)
    return await orchestrator.run_plan(plan_id)


# ─── Reports (ECHO) ───────────────────────────────────────────────────────────
@router.get("/reports")
async def list_reports(request: Request, level: Optional[str] = None,
                        product_id: Optional[str] = None):
    await get_current_user(request)
    q = {}
    if level:
        q["level"] = level
    if product_id:
        q["product_id"] = product_id
    items = await db.james_reports.find(q, {"_id": 0}).sort("generated_at", -1).limit(30).to_list(30)
    return items


class ReportGenIn(BaseModel):
    product_id: Optional[str] = None
    level: str = "agency"
    period_hours: int = 24


@router.post("/reports/generate")
async def generate_report(request: Request, body: ReportGenIn):
    await get_current_user(request)
    r = await orchestrator.generate_report(body.product_id, body.level, body.period_hours)
    return r.model_dump()


# ─── Learnings ────────────────────────────────────────────────────────────────
@router.get("/learnings")
async def list_learnings(request: Request, level: Optional[str] = None):
    await get_current_user(request)
    q = {}
    if level:
        q["level"] = level
    items = await db.james_learnings.find(q, {"_id": 0}).sort("updated_at", -1).limit(100).to_list(100)
    return items


# ─── Evaluations ──────────────────────────────────────────────────────────────
@router.get("/evaluations")
async def list_evaluations(request: Request):
    await get_current_user(request)
    items = await db.james_evaluations.find({}, {"_id": 0}).sort("created_at", -1).limit(50).to_list(50)
    return items


# ─── Skill handler (chat) ────────────────────────────────────────────────────
async def execute_james_skill(args: dict, user_id: str) -> str:
    """Skill [SKILL:james] no chat.
    args: {"action": "tick"|"report"|"anomalies", "product_id": "...", ...}"""
    action = (args.get("action") or "report").lower()
    product_id = args.get("product_id")
    if action == "tick":
        if not product_id:
            return "Erro: product_id obrigatório"
        r = await orchestrator.tick(product_id, evaluate=bool(args.get("execute")))
        return (f"JAMES tick concluído: {r.get('anomalies_detected')} anomalias detectadas, "
                f"{len(r.get('plans_created', []))} planos criados, "
                f"{len(r.get('executed', []))} executados.")
    if action == "report":
        r = await orchestrator.generate_report(product_id,
                                                 args.get("level", "agency"),
                                                 int(args.get("period_hours", 24)))
        return f"Relatório {r.level}:\n\n{r.narrative}"
    if action == "anomalies":
        if not product_id:
            return "Erro: product_id obrigatório"
        items = await db.james_anomalies.find({"product_id": product_id}, {"_id": 0}).sort("detected_at", -1).limit(5).to_list(5)
        if not items:
            return "Nenhuma anomalia registrada."
        lines = ["Anomalias recentes:"]
        for a in items:
            lines.append(f"  • {a['metric']} {a['kind']} {a['delta_pct']:+.1f}% [{a['severity']}] status={a['status']}")
        return "\n".join(lines)
    return f"Ação '{action}' desconhecida. Use: tick | report | anomalies"
