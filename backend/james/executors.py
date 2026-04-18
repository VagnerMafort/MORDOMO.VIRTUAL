"""
Executores — tradução dos plan steps em ações reais (APIs reais + DB).

Ações reais (sair do dry-run):
  • pause_campaign         → Meta Marketing API pause_object
  • shift_budget           → Meta Marketing API shift_budget_pct
  • scale_campaign         → Meta Marketing API update_adset_budget (+delta_pct)
  • resume_campaign        → Meta Marketing API resume_object

Ações ainda em DRY-RUN (planejadas pra próximas sessões):
  • investigate_metric, drill_down_campaign, flag_tracking_issue, utm_check,
    pause_fatigued_creative, generate_creative_variations, rewrite_copy

O user_id é resolvido via mapeamento product_id → product.user_id.
O object_id do Meta é buscado na coleção james_meta_campaigns via campaign_key.
"""
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from .models import PlanStep


_db = None


def init(db_ref):
    global _db
    _db = db_ref


async def _resolve_meta_object(product_id: str, campaign_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retorna {user_id, campaign_id, adset_id, ad_id} do Meta pra um produto."""
    q: Dict[str, Any] = {"product_id": product_id}
    if campaign_key:
        # campaign_key pode vir como "camp_main" (interno) ou ID real
        if campaign_key.startswith("act_") or campaign_key.isdigit():
            q["campaign_id"] = campaign_key
    rec = await _db.james_meta_campaigns.find_one(q, sort=[("created_at", -1)])
    return rec


async def execute_step(step: PlanStep, product_id: Optional[str] = None) -> Dict[str, Any]:
    """Roteia cada action para handler. Retorna {status, message, data}."""
    action = step.action
    params = step.params or {}
    handler = EXECUTORS.get(action, _unknown_action)
    try:
        result = await handler(params, product_id)
        await _db.james_execution_audit.insert_one({
            "action": action, "params": params, "result": result,
            "product_id": product_id,
            "ts": datetime.now(timezone.utc).isoformat(),
        })
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)[:200]}


# ─── Ações REAIS (Meta Ads API) ──────────────────────────────────────────────
async def _pause_campaign_real(params, product_id):
    """Pausa campanha/adset real no Meta. campaign_key opcional."""
    if not product_id:
        return {"status": "error", "message": "product_id não informado"}
    rec = await _resolve_meta_object(product_id, params.get("campaign_key"))
    if not rec:
        # Fallback dry-run se não há campanha real
        await _db.james_pending_actions.insert_one({
            "action": "pause_campaign", "product_id": product_id,
            "campaign_key": params.get("campaign_key"),
            "status": "no_meta_campaign_found",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        return {"status": "ok", "message": "Nenhuma campanha Meta encontrada — ação registrada",
                "dry_run": True}
    import meta_ads_api as ma
    target = params.get("target", "adset")  # adset | campaign | ad
    obj_id = rec.get(f"{target}_id") or rec["adset_id"]
    r = await ma.pause_object(rec["user_id"], obj_id)
    if "error" in r:
        return {"status": "error", "message": r["error"]}
    await _db.james_meta_campaigns.update_one({"id": rec["id"]}, {"$set": {"status": "PAUSED"}})
    return {"status": "ok", "message": f"{target} {obj_id} pausado no Meta"}


async def _shift_budget_real(params, product_id):
    if not product_id:
        return {"status": "error", "message": "product_id faltando"}
    rec = await _resolve_meta_object(product_id, params.get("campaign_key"))
    if not rec:
        await _db.james_pending_actions.insert_one({
            "action": "shift_budget", "product_id": product_id,
            "campaign_key": params.get("campaign_key"),
            "delta_pct": params.get("delta_pct"),
            "status": "no_meta_campaign_found",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        return {"status": "ok", "message": "Nenhuma campanha Meta encontrada", "dry_run": True}
    import meta_ads_api as ma
    delta_pct = float(params.get("delta_pct", 0))
    adset_id = rec["adset_id"]
    r = await ma.shift_budget_pct(rec["user_id"], adset_id, delta_pct, level="adset")
    if "error" in r:
        return {"status": "error", "message": r["error"]}
    return {"status": "ok", "message": f"Budget {delta_pct:+.0f}% aplicado no adset {adset_id}"}


async def _scale_campaign_real(params, product_id):
    """scale = aumentar budget, respeitando cap do preset do produto."""
    if not product_id:
        return {"status": "error", "message": "product_id faltando"}
    # Respeita cap do preset (conservative=1.5x, moderate=3x, aggressive=10x)
    product = await _db.james_products.find_one({"id": product_id})
    from .campaign_launcher import PRESETS
    preset = PRESETS.get(product.get("budget_preset", "conservative"), PRESETS["conservative"])
    cap = preset["auto_scale_cap_multiplier"]
    rec = await _resolve_meta_object(product_id, params.get("campaign_key"))
    if not rec:
        return {"status": "ok", "message": "sem campanha Meta", "dry_run": True}
    import meta_ads_api as ma
    delta_pct = min(float(params.get("delta_pct", 20)), preset["scale_up_pct_max"])
    # Cap absoluto: não ultrapassa cap * budget inicial
    max_budget = rec["daily_budget_brl"] * cap
    d = await ma._get(rec["user_id"], rec["adset_id"], {"fields": "daily_budget"})
    current_cents = int(d.get("daily_budget") or 0) if "error" not in d else 0
    new_cents = int(current_cents * (1 + delta_pct / 100.0))
    if new_cents > int(max_budget * 100):
        new_cents = int(max_budget * 100)
    r = await ma._post(rec["user_id"], rec["adset_id"], {"daily_budget": new_cents})
    if "error" in r:
        return {"status": "error", "message": r["error"]}
    return {"status": "ok", "message": f"Budget escalado para R$ {new_cents/100:.2f}/dia",
             "cap_reached": new_cents >= int(max_budget * 100)}


async def _resume_campaign_real(params, product_id):
    rec = await _resolve_meta_object(product_id, params.get("campaign_key"))
    if not rec:
        return {"status": "ok", "message": "sem campanha Meta", "dry_run": True}
    import meta_ads_api as ma
    r = await ma.resume_object(rec["user_id"], rec["adset_id"])
    if "error" in r:
        return {"status": "error", "message": r["error"]}
    await _db.james_meta_campaigns.update_one({"id": rec["id"]}, {"$set": {"status": "ACTIVE"}})
    return {"status": "ok", "message": "Campanha ativada no Meta"}


# ─── Ações em DRY-RUN (pra próximas sessões) ─────────────────────────────────
async def _investigate_metric(params, product_id):
    return {"status": "ok", "message": f"Investigação enfileirada para {params.get('metric')}",
            "dry_run": True}


async def _drill_down_campaign(params, product_id):
    return {"status": "ok", "message": f"Top {params.get('top_n', 5)} campanhas",
            "dry_run": True}


async def _flag_tracking_issue(params, product_id):
    await _db.james_tracking_flags.insert_one({
        "scope": params.get("scope", "generic"),
        "product_id": product_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"status": "ok", "message": "Tracking issue registrada"}


async def _utm_check(params, product_id):
    return {"status": "ok", "message": "UTM check concluído", "dry_run": True}


async def _pause_fatigued_creative(params, product_id):
    # Criativo fatigado = pausar o Ad específico (não o adset inteiro)
    if not product_id:
        return {"status": "error", "message": "product_id faltando"}
    rec = await _resolve_meta_object(product_id)
    if not rec:
        return {"status": "ok", "message": "sem campanha Meta", "dry_run": True}
    import meta_ads_api as ma
    r = await ma.pause_object(rec["user_id"], rec["ad_id"])
    if "error" in r:
        return {"status": "error", "message": r["error"]}
    return {"status": "ok", "message": f"Ad {rec['ad_id']} pausado (fadiga criativa)"}


async def _generate_creative_variations(params, product_id):
    count = int(params.get("count", 3))
    return {"status": "ok", "message": f"{count} variações (CREATIVE_BUILDER — próxima sessão)",
            "variations": [f"variation_{i+1}" for i in range(count)], "dry_run": True}


async def _rewrite_copy(params, product_id):
    return {"status": "ok", "message": "Copy reescrito (placeholder)", "dry_run": True}


async def _unknown_action(params, product_id):
    return {"status": "error", "message": "action desconhecida"}


EXECUTORS = {
    # REAIS
    "pause_campaign": _pause_campaign_real,
    "shift_budget": _shift_budget_real,
    "scale_campaign": _scale_campaign_real,
    "resume_campaign": _resume_campaign_real,
    "pause_fatigued_creative": _pause_fatigued_creative,
    # DRY-RUN
    "investigate_metric": _investigate_metric,
    "drill_down_campaign": _drill_down_campaign,
    "flag_tracking_issue": _flag_tracking_issue,
    "utm_check": _utm_check,
    "generate_creative_variations": _generate_creative_variations,
    "rewrite_copy": _rewrite_copy,
    "request_creative_review": _generate_creative_variations,
}
