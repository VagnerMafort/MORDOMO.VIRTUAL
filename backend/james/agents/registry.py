"""
Registry dos 24 agentes do JAMES AGENCY.
Cada agente é uma subclasse compacta de BaseAgent, com system_prompt e lógica de plan().
Agrupados por squad e fase conforme o PDF consolidado.
"""
from typing import Dict, Any, Optional, List
from .base import BaseAgent
from ..models import Plan, PlanStep, Anomaly


# ═══ SQUAD 1 — Core & Governance (FASE 1/5) ═══════════════════════════════════

class ORION(BaseAgent):
    code = "ORION"; name = "Orion"; squad = "SQUAD 1"; phase = "FASE 1"
    role = "Supervisor geral do sistema — decide qual agente acionar para cada anomalia"
    skills = ["route_anomaly", "oversee_agents", "escalate"]
    SYSTEM_PROMPT = """Você é ORION, supervisor geral do sistema JAMES AGENCY.
Função: ao receber uma anomalia, decide qual agente especializado deve resolvê-la.
Responda SEMPRE em JSON:
{"agent": "CÓDIGO_DO_AGENTE", "rationale": "motivo curto"}
Agentes disponíveis:
- DASH (diagnóstico de performance) — queda de CTR/conversão
- MIDAS (performance e orçamento) — problemas de CPA/ROAS/orçamento
- TRACK (tracking) — erros de rastreamento/pixel
- ATTRIB (atribuição) — anomalias de atribuição
- HUNTER (funil) — funil quebrado
- LNS (nutrição) — leads frios
- CLOSER (fechamento) — baixa conversão de lead→venda
- NOVA (criativos) — fadiga criativa, baixo CTR de criativo
- LPX (landing page) — baixa conversão de LP
- SENTINEL (segurança) — ações arriscadas
"""

    async def route(self, anomaly: Anomaly) -> str:
        prompt = f"Anomalia: {anomaly.metric} {anomaly.kind} {anomaly.delta_pct:+.1f}% ({anomaly.severity}). Descrição: {anomaly.description}"
        txt = await self.think(prompt, temperature=0.1)
        parsed = self.parse_json_from_llm(txt)
        if parsed and parsed.get("agent"):
            return parsed["agent"].upper()
        # Fallback heurístico
        m = anomaly.metric
        if m in ("cpa", "cpc", "roas"):
            return "MIDAS"
        if m == "ctr":
            return "NOVA"
        if m in ("conversions", "leads"):
            return "HUNTER"
        if m == "revenue":
            return "CLOSER"
        return "DASH"


class SENTINEL(BaseAgent):
    code = "SENTINEL"; name = "Sentinel"; squad = "SQUAD 1"; phase = "FASE 3"
    role = "Segurança e risco — valida planos antes de execução"
    skills = ["risk_assessment", "rollback_design"]
    SYSTEM_PROMPT = "Você é SENTINEL. Avalia risco de planos de marketing. Retorne JSON {risk_level, issues[]}."

    async def assess(self, plan: Plan) -> Dict[str, Any]:
        actions = [s.action for s in plan.steps]
        risk_actions = {"delete_campaign", "reset_pixel", "disable_tracking"}
        high = any(a in risk_actions for a in actions) or len(actions) > 10
        return {"risk_level": "high" if high else "low",
                "issues": [a for a in actions if a in risk_actions]}


class NERO(BaseAgent):
    code = "NERO"; name = "Nero"; squad = "SQUAD 1"; phase = "FASE 5"
    role = "Gestão de skills — cadastra, versiona e retira skills do catálogo"
    skills = ["skill_registry", "skill_versioning"]
    SYSTEM_PROMPT = "NERO gerencia o catálogo de skills de todos os agentes."


class ARCHIVIST(BaseAgent):
    code = "ARCHIVIST"; name = "Archivist"; squad = "SQUAD 1"; phase = "FASE 5"
    role = "Memória e auditoria — armazena histórico completo"
    skills = ["archive", "audit"]
    SYSTEM_PROMPT = "ARCHIVIST registra planos, resultados, decisões e artefatos."


class EXEC(BaseAgent):
    code = "EXEC"; name = "Exec"; squad = "SQUAD 1"; phase = "FASE 3"
    role = "Executor operacional unificado"
    skills = ["execute_plan", "rollback"]
    SYSTEM_PROMPT = "EXEC executa planos aprovados nos sistemas conectados (Meta/Google Ads, GA4, etc)."


# ═══ SQUAD 2 — Data & Diagnostics (FASE 1/5) ══════════════════════════════════

class DASH(BaseAgent):
    code = "DASH"; name = "Dash"; squad = "SQUAD 2"; phase = "FASE 1"
    role = "Diagnóstico de performance — analisa KPIs e identifica gargalos"
    skills = ["kpi_analysis", "diagnose", "drill_down"]
    SYSTEM_PROMPT = """Você é DASH, agente de diagnóstico de performance.
Ao receber uma anomalia, proponha plano em JSON:
{"objective": "...", "steps": [{"order": 1, "action": "...", "params": {}, "rationale": "..."}], "risk_level": "low|medium|high"}
Ações válidas: investigate_metric, drill_down_campaign, request_creative_review, flag_tracking_issue"""

    async def plan(self, anomaly: Optional[Anomaly], product_id: str,
                   context: Dict[str, Any]) -> Plan:
        if not anomaly:
            return await super().plan(anomaly, product_id, context)
        user_prompt = f"Anomalia: {anomaly.description}. Baseline {anomaly.expected_value:.2f} → atual {anomaly.current_value:.2f}. Proponha plano diagnóstico."
        txt = await self.think(user_prompt, temperature=0.3)
        parsed = self.parse_json_from_llm(txt)
        if parsed and parsed.get("steps"):
            steps = [PlanStep(**s) for s in parsed["steps"]]
            return Plan(
                product_id=product_id, anomaly_id=anomaly.id, agent=self.code,
                skill="kpi_analysis",
                objective=parsed.get("objective", f"Diagnosticar {anomaly.metric}"),
                steps=steps, risk_level=parsed.get("risk_level", "low"),
            )
        # Fallback heurístico
        return Plan(
            product_id=product_id, anomaly_id=anomaly.id, agent=self.code,
            skill="kpi_analysis",
            objective=f"Investigar {anomaly.metric} ({anomaly.delta_pct:+.0f}%)",
            steps=[
                PlanStep(order=1, action="investigate_metric",
                          params={"metric": anomaly.metric,
                                  "dimension_key": anomaly.dimension_key},
                          rationale="Drill-down por dimensão mais impactada"),
                PlanStep(order=2, action="drill_down_campaign",
                          params={"top_n": 5},
                          rationale="Top campanhas afetadas"),
            ],
            risk_level="low",
        )


class TRACK(BaseAgent):
    code = "TRACK"; name = "Track"; squad = "SQUAD 2"; phase = "FASE 1"
    role = "Auditoria de tracking — pixels, UTMs, eventos"
    skills = ["pixel_audit", "utm_check", "event_consistency"]
    SYSTEM_PROMPT = "TRACK audita tracking de pixels, UTMs e eventos. Detecta divergências entre fontes."

    async def plan(self, anomaly, product_id, context):
        return Plan(
            product_id=product_id, anomaly_id=anomaly.id if anomaly else None,
            agent=self.code, skill="pixel_audit",
            objective="Auditar tracking fim-a-fim",
            steps=[
                PlanStep(order=1, action="flag_tracking_issue",
                          params={"scope": "pixel"},
                          rationale="Verifica se pixel dispara eventos"),
                PlanStep(order=2, action="utm_check",
                          params={"campaign": (anomaly.dimension_key if anomaly else "")},
                          rationale="UTMs padronizados"),
            ], risk_level="low",
        )


class ATTRIB(BaseAgent):
    code = "ATTRIB"; name = "Attrib"; squad = "SQUAD 2"; phase = "FASE 1"
    role = "Auditoria de atribuição — modelo multi-touch"
    skills = ["attribution_model", "multi_touch"]
    SYSTEM_PROMPT = "ATTRIB audita o modelo de atribuição (last-click, linear, data-driven)."


# ═══ SQUAD 3 — Traffic (FASE 2) ═══════════════════════════════════════════════

class MIDAS(BaseAgent):
    code = "MIDAS"; name = "Midas"; squad = "SQUAD 3"; phase = "FASE 2"
    role = "Performance e orçamento — gestão de ROAS, CPA e budget"
    skills = ["budget_shift", "pause_campaign", "scale_campaign"]
    SYSTEM_PROMPT = """MIDAS: otimiza orçamento de mídia paga. Ao ver anomalia de CPA/ROAS/budget,
propõe plano em JSON com ações: shift_budget, pause_campaign, scale_campaign.
Sempre respeite limite de ±40% de orçamento por ação.
Formato: {"objective":"...", "steps":[{"order":1,"action":"...","params":{},"rationale":"..."}], "risk_level":"low|medium|high"}"""

    async def plan(self, anomaly: Optional[Anomaly], product_id: str, context: Dict[str, Any]) -> Plan:
        if not anomaly:
            return await super().plan(anomaly, product_id, context)
        prompt = f"Métrica {anomaly.metric} {anomaly.delta_pct:+.1f}% na campanha {anomaly.dimension_key}. Baseline {anomaly.expected_value:.2f}. Proponha ação."
        txt = await self.think(prompt, 0.2)
        parsed = self.parse_json_from_llm(txt)
        if parsed and parsed.get("steps"):
            steps = [PlanStep(**s) for s in parsed["steps"]]
            return Plan(product_id=product_id, anomaly_id=anomaly.id, agent=self.code,
                        skill="budget_optimization",
                        objective=parsed.get("objective", f"Otimizar {anomaly.metric}"),
                        steps=steps, risk_level=parsed.get("risk_level", "medium"))
        # Fallback: se CPA subiu muito, pausa; se ROAS caiu, reduz budget 20%
        if anomaly.metric in ("cpa", "cpc") and anomaly.delta_pct > 40:
            steps = [PlanStep(order=1, action="pause_campaign",
                              params={"campaign_key": anomaly.dimension_key},
                              rationale=f"{anomaly.metric} subiu {anomaly.delta_pct:.0f}%")]
        elif anomaly.metric == "roas" and anomaly.delta_pct < -20:
            steps = [PlanStep(order=1, action="shift_budget",
                              params={"campaign_key": anomaly.dimension_key, "delta_pct": -20},
                              rationale="ROAS caiu — reduzir orçamento 20%")]
        else:
            steps = [PlanStep(order=1, action="investigate_metric",
                              params={"metric": anomaly.metric}, rationale="Investigar causa")]
        return Plan(product_id=product_id, anomaly_id=anomaly.id, agent=self.code,
                    skill="budget_optimization",
                    objective=f"Reagir a {anomaly.metric} {anomaly.delta_pct:+.0f}%",
                    steps=steps, risk_level="medium")


# ═══ SQUAD 4 — Funnel & Sales (FASE 2/4) ══════════════════════════════════════

class HUNTER(BaseAgent):
    code = "HUNTER"; name = "Hunter"; squad = "SQUAD 4"; phase = "FASE 2"
    role = "Estratégia de funil — desenha e otimiza fluxos"
    skills = ["funnel_design", "funnel_audit", "stage_optimization"]
    SYSTEM_PROMPT = "HUNTER otimiza funil de vendas por estágio. Propõe ajustes de copy, CTA, ofertas."


class LNS(BaseAgent):
    code = "LNS"; name = "Lens"; squad = "SQUAD 4"; phase = "FASE 4"
    role = "Nutrição de leads — emails, WA, sequências"
    skills = ["email_sequence", "whatsapp_flow", "score_leads"]
    SYSTEM_PROMPT = "LNS gerencia nutrição de leads — sequências automatizadas por email/WhatsApp."


class CLOSER(BaseAgent):
    code = "CLOSER"; name = "Closer"; squad = "SQUAD 4"; phase = "FASE 4"
    role = "Análise de fechamento — converter leads qualificados em vendas"
    skills = ["close_audit", "script_optimization", "objection_handling"]
    SYSTEM_PROMPT = "CLOSER analisa taxa de fechamento, scripts e objeções."


# ═══ SQUAD 5 — Creative & Messaging (FASE 2) ══════════════════════════════════

class NOVA(BaseAgent):
    code = "NOVA"; name = "Nova"; squad = "SQUAD 5"; phase = "FASE 2"
    role = "Criativos e copy — gera novos ângulos, headlines, variações"
    skills = ["copy_generation", "creative_variation", "angle_testing"]
    SYSTEM_PROMPT = """NOVA cria copy e ideias de criativos. Quando fadiga criativa detectada,
propõe plano com ações: rewrite_copy, generate_creative_variations, pause_fatigued_creative.
Responda em JSON igual os outros agentes."""

    async def plan(self, anomaly, product_id, context):
        return Plan(
            product_id=product_id, anomaly_id=anomaly.id if anomaly else None,
            agent=self.code, skill="creative_refresh",
            objective="Renovar criativos (fadiga)",
            steps=[
                PlanStep(order=1, action="pause_fatigued_creative",
                          params={"creative_key": (anomaly.dimension_key if anomaly else "")},
                          rationale="CTR caiu — criativo saturado"),
                PlanStep(order=2, action="generate_creative_variations",
                          params={"count": 3},
                          rationale="3 variações novas"),
            ], risk_level="low",
        )


class MARA(BaseAgent):
    code = "MARA"; name = "Mara"; squad = "SQUAD 5"; phase = "FASE 2"
    role = "Posicionamento estratégico — brand messaging"
    skills = ["brand_positioning", "voice_tone"]
    SYSTEM_PROMPT = "MARA cuida de posicionamento, voz da marca e mensagens estratégicas."


# ═══ SQUAD 6 — Pages & Conversion (FASE 3) ════════════════════════════════════

class LPX(BaseAgent):
    code = "LPX"; name = "LPX"; squad = "SQUAD 6"; phase = "FASE 3"
    role = "Otimização de landing page"
    skills = ["lp_optimization", "ab_test_lp"]
    SYSTEM_PROMPT = "LPX otimiza landing pages — copy, hero, CTA, prova social."


class DEX(BaseAgent):
    code = "DEX"; name = "Dex"; squad = "SQUAD 6"; phase = "FASE 3"
    role = "Construção de páginas"
    skills = ["build_lp", "html_templates"]
    SYSTEM_PROMPT = "DEX constrói landing pages do zero com templates e blocos reusáveis."


class OUBAS(BaseAgent):
    code = "OUBAS"; name = "Oubas"; squad = "SQUAD 6"; phase = "FASE 3"
    role = "UX e experiência do usuário"
    skills = ["ux_audit", "user_testing"]
    SYSTEM_PROMPT = "OUBAS audita UX de páginas e checkout."


class REX(BaseAgent):
    code = "REX"; name = "Rex"; squad = "SQUAD 6"; phase = "FASE 3"
    role = "CRO e precificação"
    skills = ["cro", "pricing_test"]
    SYSTEM_PROMPT = "REX otimiza conversão (CRO) e preço."


# ═══ SQUAD 7 — Research & Product (FASE 2) ════════════════════════════════════

class ATLAS(BaseAgent):
    code = "ATLAS"; name = "Atlas"; squad = "SQUAD 7"; phase = "FASE 2"
    role = "Pesquisa de mercado"
    skills = ["market_research", "competitor_analysis"]
    SYSTEM_PROMPT = "ATLAS faz pesquisa de mercado e análise competitiva."


class MOIRA(BaseAgent):
    code = "MOIRA"; name = "Moira"; squad = "SQUAD 7"; phase = "FASE 2"
    role = "Gestão de produto"
    skills = ["product_strategy", "offer_refinement"]
    SYSTEM_PROMPT = "MOIRA cuida de estratégia de produto e refinamento de oferta."


# ═══ SQUAD 8 — Reporting & Finance (FASE 5/6) ═════════════════════════════════

class EVAL(BaseAgent):
    code = "EVAL"; name = "Eval"; squad = "SQUAD 8"; phase = "FASE 5"
    role = "Avaliação de impacto (PASS/FAIL/INCONCLUSIVO)"
    skills = ["before_after", "uplift_analysis"]
    SYSTEM_PROMPT = "EVAL compara métricas antes/depois e decide PASS/FAIL/INCONCLUSIVO."


class LEARNER(BaseAgent):
    code = "LEARNER"; name = "Learner"; squad = "SQUAD 8"; phase = "FASE 5"
    role = "Aprendizado estratégico — atualiza padrões/skills"
    skills = ["pattern_learning", "skill_update"]
    SYSTEM_PROMPT = "LEARNER extrai padrões vencedores e atualiza o catálogo de skills."


class FINN(BaseAgent):
    code = "FINN"; name = "Finn"; squad = "SQUAD 8"; phase = "FASE 4"
    role = "Financeiro — receita, MRR, ticket médio, LTV"
    skills = ["financial_kpis", "ticket_analysis"]
    SYSTEM_PROMPT = "FINN calcula KPIs financeiros e alerta sobre receita/margem."


class ECHO(BaseAgent):
    code = "ECHO"; name = "Echo"; squad = "SQUAD 8"; phase = "FASE 6"
    role = "Relatórios executivos — Agência/Produto/Campanha/Setor"
    skills = ["executive_report", "narrative_generation"]
    SYSTEM_PROMPT = """ECHO gera relatórios executivos em linguagem natural.
Dado um dict de KPIs, deltas, planos executados e recomendações,
produza um relatório em português, conciso, focado em AÇÃO e IMPACTO.
Formato: Resumo (3-5 linhas), Highlights, Ações tomadas, Recomendações.
Sem bullets markdown, apenas parágrafos fluentes."""

    async def narrate(self, payload: Dict[str, Any]) -> str:
        kpis = payload.get("kpis", {})
        plans = payload.get("plans_recent", [])
        evals = payload.get("evaluations_recent", [])
        anomalies_open = payload.get("anomalies_open", 0)
        prompt = f"""Gere relatório executivo:
KPIs: {kpis}
Planos recentes (últimos 20): {[p.get('objective', '') for p in plans[:5]]}
Avaliações recentes: {[{'r': e.get('result'), 'c': e.get('confidence')} for e in evals[:5]]}
Anomalias abertas: {anomalies_open}"""
        txt = await self.think(prompt, temperature=0.5)
        if txt:
            return txt
        # Fallback narrative
        pass_count = sum(1 for e in evals if e.get("result") == "PASS")
        fail_count = sum(1 for e in evals if e.get("result") == "FAIL")
        return (f"Período com {pass_count} vitórias, {fail_count} planos malsucedidos e "
                f"{anomalies_open} anomalias em aberto. KPIs: {kpis}. "
                f"Recomendação: revisar planos FAIL e priorizar anomalias críticas.")


# ═══ Registry global ══════════════════════════════════════════════════════════
ALL_AGENTS: List[type] = [
    ORION, DASH, MIDAS, TRACK, ATTRIB,        # SQUAD 1 + 2 + 3 (FASE 1/2)
    HUNTER, LNS, CLOSER,                       # SQUAD 4
    NOVA, MARA,                                # SQUAD 5
    ATLAS, MOIRA,                              # SQUAD 7
    LPX, DEX, OUBAS, REX,                      # SQUAD 6
    NERO, SENTINEL, EXEC,                      # SQUAD 1
    EVAL, ARCHIVIST, LEARNER, FINN, ECHO,      # SQUAD 8 + SQUAD 1
]


def agent_registry(ollama_url: str, model: str) -> Dict[str, BaseAgent]:
    return {cls.code: cls(ollama_url, model) for cls in ALL_AGENTS}
