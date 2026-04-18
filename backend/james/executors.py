"""
Executores — tradução dos plan steps em ações reais (DB/APIs).
Versão MVP: a maioria das ações fica em "dry-run" gravando no DB,
mas os pontos de plugin para Meta Ads / Google Ads / etc. estão claros.
"""
from typing import Dict, Any
from datetime import datetime, timezone
from .models import PlanStep


_db = None


def init(db_ref):
    global _db
    _db = db_ref


async def execute_step(step: PlanStep) -> Dict[str, Any]:
    """Roteia cada action para handler. Retorna {status, message, data}."""
    action = step.action
    params = step.params or {}
    handler = EXECUTORS.get(action, _unknown_action)
    try:
        result = await handler(params)
        await _db.james_execution_audit.insert_one({
            "action": action, "params": params, "result": result,
            "ts": datetime.now(timezone.utc).isoformat(),
        })
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)[:200]}


# ─── Ações mapeadas ───────────────────────────────────────────────────────────
async def _investigate_metric(params):
    return {"status": "ok", "message": f"Investigação enfileirada para {params.get('metric')}",
            "dry_run": True}


async def _drill_down_campaign(params):
    return {"status": "ok", "message": f"Top {params.get('top_n', 5)} campanhas",
            "dry_run": True}


async def _flag_tracking_issue(params):
    await _db.james_tracking_flags.insert_one({
        "scope": params.get("scope", "generic"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"status": "ok", "message": "Tracking issue registrada"}


async def _utm_check(params):
    return {"status": "ok", "message": "UTM check concluído", "dry_run": True}


async def _pause_campaign(params):
    """TODO: integrar com Meta Marketing API / Google Ads API.
    MVP: grava ação pendente pra execução manual ou EXEC real."""
    await _db.james_pending_actions.insert_one({
        "action": "pause_campaign",
        "campaign_key": params.get("campaign_key"),
        "status": "pending_external_sync",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"status": "ok", "message": f"Campanha {params.get('campaign_key')} marcada pra pausar",
            "requires_external": True}


async def _shift_budget(params):
    await _db.james_pending_actions.insert_one({
        "action": "shift_budget",
        "campaign_key": params.get("campaign_key"),
        "delta_pct": params.get("delta_pct"),
        "status": "pending_external_sync",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"status": "ok", "message": f"Budget shift {params.get('delta_pct')}% enfileirado",
            "requires_external": True}


async def _scale_campaign(params):
    return {"status": "ok", "message": f"Escala +{params.get('delta_pct', 20)}% enfileirada",
            "requires_external": True, "dry_run": True}


async def _pause_fatigued_creative(params):
    return {"status": "ok", "message": f"Criativo {params.get('creative_key')} pausado (simulado)",
            "dry_run": True}


async def _generate_creative_variations(params):
    count = int(params.get("count", 3))
    # Em produção: chamar NOVA.think para gerar; MVP: placeholder
    return {"status": "ok", "message": f"{count} variações de criativo geradas (placeholder)",
            "variations": [f"variation_{i+1}" for i in range(count)]}


async def _rewrite_copy(params):
    return {"status": "ok", "message": "Copy reescrito (placeholder)", "dry_run": True}


async def _unknown_action(params):
    return {"status": "error", "message": "action desconhecida"}


EXECUTORS = {
    "investigate_metric": _investigate_metric,
    "drill_down_campaign": _drill_down_campaign,
    "flag_tracking_issue": _flag_tracking_issue,
    "utm_check": _utm_check,
    "pause_campaign": _pause_campaign,
    "shift_budget": _shift_budget,
    "scale_campaign": _scale_campaign,
    "pause_fatigued_creative": _pause_fatigued_creative,
    "generate_creative_variations": _generate_creative_variations,
    "rewrite_copy": _rewrite_copy,
    "request_creative_review": _generate_creative_variations,
}
