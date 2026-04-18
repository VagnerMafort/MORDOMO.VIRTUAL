"""
Orquestrador Central do JAMES AGENCY.
Fluxo padrão (tick):
  sensors → baseline → anomalies → priorize → ORION route → agent.plan
         → objective validation → guardrails → execute → verify → evaluate
         → learn → archive → report

Pode ser chamado:
  - Automaticamente a cada N minutos (tick)
  - Manualmente via API (/api/james/tick ou /api/james/run_plan)
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import logging

from . import layers
from .models import Plan, Anomaly, Report, _now
from .agents.registry import agent_registry
from . import executors

logger = logging.getLogger(__name__)

_db = None
_agents: Dict[str, Any] = {}


def init(db_ref, ollama_url: str, model: str):
    global _db, _agents
    _db = db_ref
    _agents = agent_registry(ollama_url, model)
    layers.init(db_ref)
    executors.init(db_ref)
    logger.info(f"JAMES AGENCY: {len(_agents)} agentes registrados")


def list_agents() -> List[Dict[str, Any]]:
    return [a.as_info() for a in _agents.values()]


def get_agent(code: str):
    return _agents.get(code.upper())


async def tick(product_id: str, evaluate: bool = False) -> Dict[str, Any]:
    """Roda um ciclo completo pra 1 produto. Retorna resumo."""
    result = {"product_id": product_id, "started_at": _now()}
    # 1. Recompute baselines para métricas comuns
    baselines_updated = 0
    for metric in ["ctr", "cpa", "cpc", "roas", "conversions", "revenue", "leads", "impressions"]:
        b = await layers.layer3_recompute_baseline(product_id, metric)
        if b:
            baselines_updated += 1
    result["baselines_updated"] = baselines_updated

    # 2. Detect anomalies
    anomalies = await layers.layer4_detect_anomalies(product_id)
    result["anomalies_detected"] = len(anomalies)

    # 3. Prioritize
    ranked = await layers.layer5_prioritize(product_id)
    result["anomalies_prioritized"] = len(ranked)

    # 4. Route + plan pras top 3 anomalias
    orion = _agents["ORION"]
    plans_created = []
    for anomaly in ranked[:3]:
        target_code = await orion.route(anomaly)
        agent = _agents.get(target_code) or _agents["DASH"]
        plan = await agent.plan(anomaly, product_id, {})
        # marca anomaly como assigned
        await _db.james_anomalies.update_one(
            {"id": anomaly.id},
            {"$set": {"status": "assigned", "assigned_agent": target_code}},
        )
        # 5. validar objetivo
        obj_val = layers.layer7_validate_objective(plan)
        plan.objective_passed = obj_val["passed"]
        # 6. guardrails
        grd = layers.layer8_guardrails(plan)
        plan.guardrails_passed = grd["passed"]
        plan.validation = {"objective": obj_val, "guardrails": grd}
        plan.status = "validated" if (obj_val["passed"] and grd["passed"]) else "blocked"
        await _db.james_plans.insert_one(plan.model_dump())
        plans_created.append({"agent": target_code, "objective": plan.objective,
                               "status": plan.status, "plan_id": plan.id})
    result["plans_created"] = plans_created

    # 7. opcionalmente executar planos validados automaticamente
    executed = []
    if evaluate:
        plans_to_run = await _db.james_plans.find(
            {"product_id": product_id, "status": "validated"},
            {"_id": 0}
        ).to_list(5)
        for pd in plans_to_run:
            from .models import Plan as PlanCls
            plan = PlanCls(**pd)
            await _db.james_plans.update_one({"id": plan.id}, {"$set": {"status": "executing"}})
            ex = await layers.layer9_execute(plan, executors.execute_step)
            await layers.layer10_verify(ex)
            evalu = await layers.layer11_evaluate(plan, window_hours=1)
            await layers.layer12_learn(plan, evalu)
            executed.append({"plan_id": plan.id, "exec_status": ex.status,
                              "evaluation": evalu.result})
    result["executed"] = executed
    result["finished_at"] = _now()
    return result


async def run_plan(plan_id: str) -> Dict[str, Any]:
    """Roda execução + avaliação + aprendizado de um plano validado."""
    pd = await _db.james_plans.find_one({"id": plan_id}, {"_id": 0})
    if not pd:
        return {"error": "plan not found"}
    from .models import Plan as PlanCls
    plan = PlanCls(**pd)
    if plan.status not in ("validated", "approved"):
        return {"error": f"plan status {plan.status}, só roda validated/approved"}
    await _db.james_plans.update_one({"id": plan_id}, {"$set": {"status": "executing"}})
    ex = await layers.layer9_execute(plan, executors.execute_step)
    await layers.layer10_verify(ex)
    evalu = await layers.layer11_evaluate(plan, window_hours=1)
    await layers.layer12_learn(plan, evalu)
    return {"execution": ex.model_dump(), "evaluation": evalu.model_dump()}


async def generate_report(product_id: Optional[str], level: str = "agency",
                           period_hours: int = 24) -> Report:
    """Gera relatório via ECHO."""
    payload = await layers.layer14_generate_kpis(product_id, period_hours=period_hours)
    echo = _agents["ECHO"]
    narrative = await echo.narrate(payload)
    now = datetime.now(timezone.utc)
    from datetime import timedelta
    report = Report(
        product_id=product_id,
        level=level,                      # type: ignore
        period_start=(now - timedelta(hours=period_hours)).isoformat(),
        period_end=now.isoformat(),
        kpis=payload.get("kpis", {}),
        highlights=[
            f"{payload.get('anomalies_open', 0)} anomalias abertas",
            f"{len(payload.get('plans_recent', []))} planos recentes",
        ],
        actions_taken=[{"agent": p.get("agent"), "objective": p.get("objective"),
                         "status": p.get("status")} for p in payload.get("plans_recent", [])],
        recommendations=[
            "Revisar planos FAIL antes de re-executar",
            "Priorizar anomalias critical/high do dia",
        ],
        narrative=narrative,
    )
    await _db.james_reports.insert_one(report.model_dump())
    return report
