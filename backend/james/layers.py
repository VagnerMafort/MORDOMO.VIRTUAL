"""
Camadas operacionais (1..14) do JAMES AGENCY.

Cada camada tem entrada/saída bem definidas. O orquestrador passa o contexto
pelas camadas em ordem (ou pula para reagir a um evento externo).
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from statistics import mean, stdev
import logging

from .models import (
    MetricSnapshot, Baseline, Anomaly, Plan, Execution, Evaluation,
    Learning, Report, _now,
)

logger = logging.getLogger(__name__)

# injected
_db = None


def init(db_ref):
    global _db
    _db = db_ref


# ─── Camada 1 — Sensores ──────────────────────────────────────────────────────
async def layer1_sensors_ingest(product_id: str, source: str, points: List[Dict[str, Any]]) -> int:
    """Recebe métricas cruas de conectores (meta/google/ga4/stripe/manual).
    points = [{"metric": "ctr", "value": 0.034, "dimension": {"campaign": "c1"}, "captured_at": "..."}]
    """
    docs = []
    for p in points:
        snap = MetricSnapshot(
            product_id=product_id,
            source=source,
            metric=p["metric"],
            value=float(p["value"]),
            dimension=p.get("dimension", {}),
            captured_at=p.get("captured_at") or _now(),
        )
        docs.append(snap.model_dump())
    if docs:
        await _db.james_metrics.insert_many(docs)
    return len(docs)


# ─── Camada 2 — Normalização (já aplicada no ingest) ──────────────────────────
# As métricas são guardadas em formato canônico (metric + value + dimension).


# ─── Camada 3 — Baseline ──────────────────────────────────────────────────────
async def layer3_recompute_baseline(product_id: str, metric: str, window_days: int = 7,
                                      dimension_key: str = "") -> Optional[Baseline]:
    since = datetime.now(timezone.utc) - timedelta(days=window_days)
    query: Dict[str, Any] = {
        "product_id": product_id,
        "metric": metric,
        "captured_at": {"$gte": since.isoformat()},
    }
    if dimension_key:
        # dimension_key = "campaign:abc" => dimension.campaign = "abc"
        k, v = dimension_key.split(":", 1)
        query[f"dimension.{k}"] = v
    cursor = _db.james_metrics.find(query, {"_id": 0, "value": 1})
    values = [d["value"] async for d in cursor]
    if len(values) < 3:
        return None
    values.sort()
    n = len(values)
    p25 = values[int(n * 0.25)]
    p50 = values[int(n * 0.5)]
    p75 = values[int(n * 0.75)]
    m = mean(values)
    s = stdev(values) if n > 1 else 0.0
    base = Baseline(
        product_id=product_id, metric=metric, dimension_key=dimension_key,
        mean=m, std=s, p25=p25, p50=p50, p75=p75,
        window_days=window_days, samples=n,
    )
    await _db.james_baselines.update_one(
        {"product_id": product_id, "metric": metric, "dimension_key": dimension_key},
        {"$set": base.model_dump()},
        upsert=True,
    )
    return base


# ─── Camada 4 — Anomalias ─────────────────────────────────────────────────────
ANOMALY_RULES = {
    # métrica: (tipo_se_queda, limiar_queda%, tipo_se_spike, limiar_spike%)
    "ctr":          ("drop", -20.0, "spike", 80.0),
    "cpa":          ("spike", 30.0, None, None),
    "cpc":          ("spike", 30.0, None, None),
    "roas":         ("drop", -25.0, None, None),
    "conversions":  ("drop", -30.0, None, None),
    "revenue":      ("drop", -25.0, "spike", 100.0),
    "leads":        ("drop", -30.0, None, None),
    "impressions":  ("drop", -50.0, None, None),
}


async def layer4_detect_anomalies(product_id: str) -> List[Anomaly]:
    """Compara últimas medições x baseline por métrica. Gera registros de Anomaly."""
    found: List[Anomaly] = []
    baselines = await _db.james_baselines.find({"product_id": product_id}, {"_id": 0}).to_list(200)
    for b in baselines:
        metric = b["metric"]
        if metric not in ANOMALY_RULES:
            continue
        # pega último ponto
        q: Dict[str, Any] = {"product_id": product_id, "metric": metric}
        if b.get("dimension_key"):
            k, v = b["dimension_key"].split(":", 1)
            q[f"dimension.{k}"] = v
        last = await _db.james_metrics.find_one(q, {"_id": 0}, sort=[("captured_at", -1)])
        if not last:
            continue
        current = last["value"]
        expected = b["p50"] if b["p50"] else b["mean"]
        if expected == 0:
            continue
        delta_pct = ((current - expected) / abs(expected)) * 100.0
        drop_kind, drop_thr, spike_kind, spike_thr = ANOMALY_RULES[metric]
        anomaly_kind = None
        if drop_kind and delta_pct <= drop_thr:
            anomaly_kind = drop_kind
        elif spike_kind and delta_pct >= spike_thr:
            anomaly_kind = spike_kind
        if not anomaly_kind:
            continue
        sev = "low"
        abs_delta = abs(delta_pct)
        if abs_delta >= 60:
            sev = "critical"
        elif abs_delta >= 40:
            sev = "high"
        elif abs_delta >= 20:
            sev = "medium"
        a = Anomaly(
            product_id=product_id, metric=metric,
            dimension_key=b.get("dimension_key", ""),
            kind=anomaly_kind, severity=sev,
            current_value=current, expected_value=expected, delta_pct=delta_pct,
            description=f"{metric} {anomaly_kind} {delta_pct:+.1f}% vs baseline",
        )
        # dedupe: só cria se não há anomaly igual 'new' há menos de 2h
        existing = await _db.james_anomalies.find_one({
            "product_id": product_id, "metric": metric,
            "dimension_key": a.dimension_key, "kind": anomaly_kind,
            "status": {"$in": ["new", "prioritized", "assigned"]},
            "detected_at": {"$gte": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()},
        })
        if existing:
            continue
        await _db.james_anomalies.insert_one(a.model_dump())
        found.append(a)
    return found


# ─── Camada 5 — Priorização ───────────────────────────────────────────────────
SEVERITY_WEIGHT = {"low": 1, "medium": 3, "high": 7, "critical": 15}
METRIC_WEIGHT = {"revenue": 5, "roas": 4, "conversions": 4, "cpa": 3, "ctr": 2, "cpc": 2, "leads": 3, "impressions": 1}


async def layer5_prioritize(product_id: str) -> List[Anomaly]:
    """Calcula priority_score = sev_weight * metric_weight * log(|delta_pct|+1).
    Retorna anomalias ordenadas."""
    import math
    new = await _db.james_anomalies.find(
        {"product_id": product_id, "status": "new"},
        {"_id": 0}
    ).to_list(100)
    ranked = []
    for a in new:
        sw = SEVERITY_WEIGHT.get(a["severity"], 1)
        mw = METRIC_WEIGHT.get(a["metric"], 1)
        score = sw * mw * math.log(abs(a["delta_pct"]) + 1)
        await _db.james_anomalies.update_one(
            {"id": a["id"]},
            {"$set": {"priority_score": score, "status": "prioritized"}},
        )
        a["priority_score"] = score
        a["status"] = "prioritized"
        ranked.append(Anomaly(**a))
    ranked.sort(key=lambda x: x.priority_score, reverse=True)
    return ranked


# ─── Camada 7 — Objective Governance ──────────────────────────────────────────
BANNED_OBJECTIVE_PATTERNS = [
    "delete_all", "drop_database", "rm -rf", "revoke_all", "disable_all_security",
]


def layer7_validate_objective(plan: Plan) -> Dict[str, Any]:
    """Impede otimização errada. Regras:
      - objetivo não pode ser ambíguo / vazio
      - nenhum step pode usar padrões banidos
      - nenhuma ação deve conflitar com métrica de guarda (ex: pausar tudo)"""
    issues = []
    if not plan.objective or len(plan.objective.strip()) < 5:
        issues.append("objective_too_short")
    text = (plan.objective + " " + " ".join(s.action for s in plan.steps)).lower()
    for p in BANNED_OBJECTIVE_PATTERNS:
        if p in text:
            issues.append(f"banned_pattern:{p}")
    # guarda: se ação é 'pause_campaign', não pode afetar > N campanhas
    pauses = [s for s in plan.steps if s.action == "pause_campaign"]
    if len(pauses) > 5:
        issues.append("pause_blast_radius_too_large")
    return {"passed": len(issues) == 0, "issues": issues}


# ─── Camada 8 — Guardrails ────────────────────────────────────────────────────
HIGH_RISK_ACTIONS = {"delete_campaign", "delete_creative", "reset_pixel", "disable_tracking"}
MAX_BUDGET_CHANGE_PCT = 40.0


def layer8_guardrails(plan: Plan) -> Dict[str, Any]:
    """Bloqueia ações perigosas. Exige: limite de alteração, rollback plan, risk_level coerente."""
    issues = []
    for s in plan.steps:
        if s.action in HIGH_RISK_ACTIONS and plan.risk_level != "high":
            issues.append(f"high_risk_action_without_risk_flag:{s.action}")
        if s.action == "shift_budget":
            pct = abs(float(s.params.get("delta_pct", 0)))
            if pct > MAX_BUDGET_CHANGE_PCT:
                issues.append(f"budget_change_exceeds_limit:{pct:.0f}%")
    # plano deve ter pelo menos 1 step
    if not plan.steps:
        issues.append("empty_plan")
    return {"passed": len(issues) == 0, "issues": issues, "max_budget_change_pct": MAX_BUDGET_CHANGE_PCT}


# ─── Camada 9 — Execução ──────────────────────────────────────────────────────
async def layer9_execute(plan: Plan, executor_fn) -> Execution:
    """executor_fn(step: PlanStep, product_id) -> dict. Coleta outputs e status final."""
    ex = Execution(plan_id=plan.id, agent=plan.agent, status="running")
    await _db.james_executions.insert_one(ex.model_dump())
    outputs = []
    ok = True
    err = None
    try:
        for s in plan.steps:
            r = await executor_fn(s, plan.product_id)
            outputs.append({"action": s.action, "result": r})
            if isinstance(r, dict) and r.get("status") == "error":
                ok = False
                err = r.get("message", "unknown")
                break
    except Exception as e:
        ok = False
        err = str(e)[:500]
    ex.completed_at = _now()
    ex.status = "success" if ok else "failure"
    ex.output = {"steps": outputs}
    ex.error = err
    await _db.james_executions.update_one({"id": ex.id}, {"$set": ex.model_dump()})
    await _db.james_plans.update_one({"id": plan.id}, {"$set": {"status": "done" if ok else "failed"}})
    return ex


# ─── Camada 10 — Verificação ──────────────────────────────────────────────────
async def layer10_verify(execution: Execution) -> Dict[str, Any]:
    """Confere se execução realmente aconteceu."""
    return {"verified": execution.status == "success",
            "execution_id": execution.id, "status": execution.status}


# ─── Camada 11 — Avaliação antes/depois ───────────────────────────────────────
async def layer11_evaluate(plan: Plan, window_hours: int = 24) -> Evaluation:
    """Compara métricas 'window_hours' antes vs depois da execução."""
    ex = await _db.james_executions.find_one({"plan_id": plan.id}, sort=[("started_at", -1)])
    if not ex:
        return Evaluation(plan_id=plan.id, execution_id="", result="INCONCLUSIVE",
                           notes="no execution")
    started = datetime.fromisoformat(ex["started_at"])
    before_start = (started - timedelta(hours=window_hours)).isoformat()
    after_start = started.isoformat()
    after_end = (started + timedelta(hours=window_hours)).isoformat()
    before_agg: Dict[str, float] = {}
    after_agg: Dict[str, float] = {}
    # cursor sync manual (aiter)
    for metric in ["ctr", "cpa", "roas", "conversions", "revenue"]:
        b_cur = _db.james_metrics.find(
            {"product_id": plan.product_id, "metric": metric,
             "captured_at": {"$gte": before_start, "$lt": after_start}},
            {"_id": 0, "value": 1},
        )
        b_vals = [d["value"] async for d in b_cur]
        a_cur = _db.james_metrics.find(
            {"product_id": plan.product_id, "metric": metric,
             "captured_at": {"$gte": after_start, "$lte": after_end}},
            {"_id": 0, "value": 1},
        )
        a_vals = [d["value"] async for d in a_cur]
        if b_vals:
            before_agg[metric] = mean(b_vals)
        if a_vals:
            after_agg[metric] = mean(a_vals)
    # decisão: se a métrica-alvo do objetivo melhorou > 5% = PASS, piorou > 5% = FAIL
    result = "INCONCLUSIVE"
    confidence = 0.3
    # heurística por objetivo
    obj = plan.objective.lower()
    target_metric = None
    direction = None
    if "ctr" in obj:
        target_metric, direction = "ctr", +1
    elif "cpa" in obj:
        target_metric, direction = "cpa", -1
    elif "roas" in obj:
        target_metric, direction = "roas", +1
    elif "convers" in obj:
        target_metric, direction = "conversions", +1
    elif "revenue" in obj or "receita" in obj:
        target_metric, direction = "revenue", +1
    if target_metric and target_metric in before_agg and target_metric in after_agg:
        b = before_agg[target_metric]
        a = after_agg[target_metric]
        if b != 0:
            change = ((a - b) / abs(b)) * 100 * direction
            if change >= 5:
                result = "PASS"
                confidence = min(0.95, 0.5 + change / 100)
            elif change <= -5:
                result = "FAIL"
                confidence = min(0.95, 0.5 + abs(change) / 100)
    ev = Evaluation(
        plan_id=plan.id, execution_id=ex["id"],
        before=before_agg, after=after_agg,
        window_hours=window_hours, result=result, confidence=confidence,
        notes=f"target={target_metric} direction={'+' if direction == 1 else '-'}" if target_metric else "no target",
    )
    await _db.james_evaluations.insert_one(ev.model_dump())
    return ev


# ─── Camada 12 — Aprendizado ──────────────────────────────────────────────────
async def layer12_learn(plan: Plan, evaluation: Evaluation):
    """Atualiza Learning registry baseado no resultado."""
    keys = [
        ("skill", f"skill:{plan.skill}"),
        ("agent", f"agent:{plan.agent}"),
        ("product", f"product:{plan.product_id}"),
    ]
    for level, key in keys:
        cur = await _db.james_learnings.find_one({"level": level, "key": key})
        samples = (cur["samples"] if cur else 0) + 1
        prev_rate = cur["success_rate"] if cur else 0.0
        prev_samples = cur["samples"] if cur else 0
        hits = prev_rate * prev_samples + (1 if evaluation.result == "PASS" else 0)
        new_rate = hits / samples if samples else 0.0
        pattern = f"{plan.skill} em {plan.product_id} → {evaluation.result} ({evaluation.confidence:.0%})"
        doc = Learning(
            level=level, key=key,
            context={"skill": plan.skill, "agent": plan.agent, "product_id": plan.product_id},
            pattern=pattern, success_rate=new_rate, samples=samples,
        ).model_dump()
        await _db.james_learnings.update_one(
            {"level": level, "key": key}, {"$set": doc}, upsert=True
        )


# ─── Camada 13 — Memória (implícita: insert em todas coleções) ────────────────
async def layer13_archive(plan: Plan, execution: Execution, evaluation: Evaluation):
    """Tudo já é persistido nas coleções james_*. Esta função retorna o resumo."""
    return {
        "plan": plan.model_dump(),
        "execution": execution.model_dump(),
        "evaluation": evaluation.model_dump(),
    }


# ─── Camada 14 — Reporting (ECHO) ─────────────────────────────────────────────
async def layer14_generate_kpis(product_id: Optional[str], period_hours: int = 24) -> Dict[str, Any]:
    """Agrega KPIs para o período. Retorna dict pronto pra ECHO formatar."""
    start = (datetime.now(timezone.utc) - timedelta(hours=period_hours)).isoformat()
    q = {"captured_at": {"$gte": start}}
    if product_id:
        q["product_id"] = product_id
    agg = {}
    for metric in ["impressions", "clicks", "ctr", "cpa", "cpc", "conversions", "revenue", "roas", "leads"]:
        qq = {**q, "metric": metric}
        cur = _db.james_metrics.find(qq, {"_id": 0, "value": 1})
        vals = [d["value"] async for d in cur]
        if vals:
            if metric in ("ctr", "cpa", "cpc", "roas"):
                agg[metric] = round(mean(vals), 4)
            else:
                agg[metric] = round(sum(vals), 2)
    # ações tomadas
    plans = await _db.james_plans.find(
        {"product_id": product_id} if product_id else {},
        {"_id": 0}
    ).sort("created_at", -1).limit(20).to_list(20)
    evals = await _db.james_evaluations.find({}, {"_id": 0}).sort("created_at", -1).limit(20).to_list(20)
    anomalies_open = await _db.james_anomalies.count_documents({
        **({"product_id": product_id} if product_id else {}),
        "status": {"$in": ["new", "prioritized", "assigned"]},
    })
    return {
        "kpis": agg,
        "plans_recent": plans,
        "evaluations_recent": evals,
        "anomalies_open": anomalies_open,
    }
