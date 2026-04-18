"""
Data models for JAMES AGENCY. Pydantic + MongoDB-friendly dicts.
Coleções MongoDB:
  - james_metrics          Camada 1/2 — snapshots normalizados
  - james_baselines        Camada 3 — referências por métrica
  - james_anomalies        Camada 4 — desvios detectados
  - james_plans            Camada 6 — planos criados pelos agentes
  - james_executions       Camada 9 — execução real
  - james_evaluations      Camada 11 — antes/depois
  - james_learnings        Camada 12 — skills/padrões aprendidos
  - james_reports          Camada 14 — relatórios ECHO
  - james_products         produto = container (campanhas, criativos, lps, funil)
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime, timezone
import uuid


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id() -> str:
    return str(uuid.uuid4())


# ─── Produto ──────────────────────────────────────────────────────────────────
class Product(BaseModel):
    id: str = Field(default_factory=_id)
    user_id: str
    name: str
    niche: str = ""
    target_audience: str = ""
    offer: str = ""
    budget_daily: float = 0.0
    status: Literal["active", "paused", "archived"] = "active"
    created_at: str = Field(default_factory=_now)
    updated_at: str = Field(default_factory=_now)


# ─── Camada 1/2 — Métricas normalizadas ───────────────────────────────────────
class MetricSnapshot(BaseModel):
    id: str = Field(default_factory=_id)
    product_id: str
    source: Literal["meta_ads", "google_ads", "ga4", "stripe", "manual", "tiktok_ads", "telegram", "whatsapp"]
    metric: str                  # impressions, clicks, ctr, cpa, cpc, conversions, revenue, roas, leads
    value: float
    dimension: Dict[str, str] = Field(default_factory=dict)  # campaign, creative, audience, day
    captured_at: str = Field(default_factory=_now)


# ─── Camada 3 — Baseline ──────────────────────────────────────────────────────
class Baseline(BaseModel):
    id: str = Field(default_factory=_id)
    product_id: str
    metric: str
    dimension_key: str = ""       # ex: "campaign:abc123" ou "" para agregado
    mean: float
    std: float
    p25: float
    p50: float
    p75: float
    window_days: int = 7
    samples: int = 0
    updated_at: str = Field(default_factory=_now)


# ─── Camada 4 — Anomalias ─────────────────────────────────────────────────────
class Anomaly(BaseModel):
    id: str = Field(default_factory=_id)
    product_id: str
    metric: str
    dimension_key: str = ""
    kind: Literal["drop", "spike", "fatigue", "tracking_error", "low_conversion", "budget_exhaust"]
    severity: Literal["low", "medium", "high", "critical"]
    current_value: float
    expected_value: float
    delta_pct: float
    description: str
    detected_at: str = Field(default_factory=_now)
    status: Literal["new", "prioritized", "assigned", "resolved", "ignored"] = "new"
    priority_score: float = 0.0   # Camada 5
    assigned_agent: Optional[str] = None


# ─── Camada 6 — Plan (criado por agente) ──────────────────────────────────────
class PlanStep(BaseModel):
    order: int
    action: str                   # "pause_campaign", "rewrite_copy", "shift_budget", ...
    params: Dict[str, Any] = Field(default_factory=dict)
    rationale: str = ""


class Plan(BaseModel):
    id: str = Field(default_factory=_id)
    product_id: str
    anomaly_id: Optional[str] = None
    agent: str                    # ORION, DASH, MIDAS, ...
    skill: str                    # categoria de skill usada
    objective: str
    steps: List[PlanStep]
    estimated_impact: str = ""
    risk_level: Literal["low", "medium", "high"] = "low"
    status: Literal["draft", "validated", "blocked", "approved", "executing", "done", "failed"] = "draft"
    created_at: str = Field(default_factory=_now)
    validation: Dict[str, Any] = Field(default_factory=dict)  # camada 7/8
    guardrails_passed: bool = False
    objective_passed: bool = False


# ─── Camada 9 — Execução ──────────────────────────────────────────────────────
class Execution(BaseModel):
    id: str = Field(default_factory=_id)
    plan_id: str
    agent: str
    started_at: str = Field(default_factory=_now)
    completed_at: Optional[str] = None
    status: Literal["running", "success", "failure", "rolled_back"] = "running"
    output: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


# ─── Camada 11 — Avaliação ────────────────────────────────────────────────────
class Evaluation(BaseModel):
    id: str = Field(default_factory=_id)
    plan_id: str
    execution_id: str
    before: Dict[str, float] = Field(default_factory=dict)
    after: Dict[str, float] = Field(default_factory=dict)
    window_hours: int = 24
    result: Literal["PASS", "FAIL", "INCONCLUSIVE"]
    confidence: float = 0.0
    notes: str = ""
    created_at: str = Field(default_factory=_now)


# ─── Camada 12 — Aprendizado ──────────────────────────────────────────────────
class Learning(BaseModel):
    id: str = Field(default_factory=_id)
    level: Literal["skill", "agent", "campaign", "product"]
    key: str                      # ex: "skill:pause_on_ctr_drop"
    context: Dict[str, Any] = Field(default_factory=dict)
    pattern: str                  # texto livre gerado pelo LEARNER
    success_rate: float = 0.0
    samples: int = 0
    updated_at: str = Field(default_factory=_now)


# ─── Camada 14 — Relatório ECHO ───────────────────────────────────────────────
class Report(BaseModel):
    id: str = Field(default_factory=_id)
    product_id: Optional[str] = None
    level: Literal["agency", "product", "campaign", "sector"]
    sector: Optional[str] = None  # tracking, landing, funil, criativos, financeiro
    period_start: str
    period_end: str
    kpis: Dict[str, float] = Field(default_factory=dict)
    deltas: Dict[str, float] = Field(default_factory=dict)
    highlights: List[str] = Field(default_factory=list)
    actions_taken: List[Dict[str, Any]] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    narrative: str = ""           # ECHO gera texto executivo
    generated_at: str = Field(default_factory=_now)


# ─── Agent registry schema ────────────────────────────────────────────────────
class AgentInfo(BaseModel):
    code: str                     # ORION, DASH, ...
    name: str
    squad: str                    # SQUAD 1 ... 8
    phase: str                    # FASE 1 ... 6
    role: str
    skills: List[str] = Field(default_factory=list)
    enabled: bool = True
