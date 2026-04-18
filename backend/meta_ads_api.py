"""
Meta Marketing API v21 wrapper — braço executivo real do JAMES.

Funções cobertas:
  • list_ad_accounts(user)                 → devolve Ad Accounts do BM
  • list_pixels(ad_account_id)             → pixels disponíveis
  • create_pixel(business_id, name)        → cria pixel novo no Business
  • create_campaign(...)                   → cria Campaign (CONVERSIONS/LEADS/TRAFFIC)
  • create_adset(...)                      → AdSet com targeting + budget + optimization
  • create_ad_creative(...)                → creative com copy + imagem/vídeo
  • create_ad(...)                         → amarra adset + creative
  • get_insights(level, object_id)         → impressions/clicks/ctr/cpm/spend/conversions
  • pause_object(object_id)                → pausar campaign/adset/ad
  • resume_object(object_id)
  • update_budget(object_id, new_daily_brl)→ altera daily_budget em centavos

Tokens: usa access_token salvo no meta_oauth (enc Fernet).
"""
from typing import Dict, Any, List, Optional
import httpx
import logging

logger = logging.getLogger(__name__)

API_BASE = "https://graph.facebook.com/v21.0"


async def _token(user_id: str) -> Optional[str]:
    """Busca access_token válido do usuário (refreshed se expirado pelo meta_oauth)."""
    try:
        import meta_oauth
        acc = await meta_oauth.get_meta_account(user_id)
        if not acc or not acc.get("access_token"):
            return None
        return acc["access_token"]
    except Exception as e:
        logger.warning(f"meta_ads._token: {e}")
        return None


async def _get(user_id: str, path: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
    tok = await _token(user_id)
    if not tok:
        return {"error": "meta_not_connected"}
    params = dict(params or {})
    params["access_token"] = tok
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.get(f"{API_BASE}/{path}", params=params)
            d = r.json()
            if r.status_code >= 400:
                return {"error": d.get("error", {}).get("message", "api_error"), "raw": d}
            return d
    except Exception as e:
        return {"error": str(e)[:200]}


async def _post(user_id: str, path: str, payload: Dict[str, Any] = None,
                 use_form: bool = True) -> Dict[str, Any]:
    tok = await _token(user_id)
    if not tok:
        return {"error": "meta_not_connected"}
    payload = dict(payload or {})
    payload["access_token"] = tok
    try:
        async with httpx.AsyncClient(timeout=45) as c:
            if use_form:
                r = await c.post(f"{API_BASE}/{path}", data=payload)
            else:
                r = await c.post(f"{API_BASE}/{path}", json=payload)
            d = r.json()
            if r.status_code >= 400:
                return {"error": d.get("error", {}).get("message", "api_error"), "raw": d}
            return d
    except Exception as e:
        return {"error": str(e)[:200]}


# ─── Discovery (Ad Accounts, Pixels, Pages) ──────────────────────────────────
async def list_ad_accounts(user_id: str) -> List[Dict[str, Any]]:
    """Retorna Ad Accounts que o usuário pode gerenciar."""
    d = await _get(user_id, "me/adaccounts", {
        "fields": "id,account_id,name,account_status,currency,timezone_name,balance,business,disable_reason",
        "limit": 50,
    })
    return d.get("data", []) if "error" not in d else []


async def list_businesses(user_id: str) -> List[Dict[str, Any]]:
    d = await _get(user_id, "me/businesses", {"fields": "id,name,verification_status", "limit": 50})
    return d.get("data", []) if "error" not in d else []


async def list_pixels(user_id: str, ad_account_id: str) -> List[Dict[str, Any]]:
    """AdAccount format: act_XXXXX"""
    d = await _get(user_id, f"{ad_account_id}/adspixels", {
        "fields": "id,name,code,last_fired_time,is_created_by_business,automatic_matching_fields",
        "limit": 50,
    })
    return d.get("data", []) if "error" not in d else []


async def create_pixel(user_id: str, business_id: str, name: str) -> Dict[str, Any]:
    """Cria um Pixel novo no Business."""
    return await _post(user_id, f"{business_id}/adspixels", {"name": name})


async def list_pages(user_id: str) -> List[Dict[str, Any]]:
    d = await _get(user_id, "me/accounts", {"fields": "id,name,access_token,category", "limit": 50})
    return d.get("data", []) if "error" not in d else []


# ─── Campaign / AdSet / Ad Creation ──────────────────────────────────────────
# Objetivos Meta (v21): OUTCOME_SALES, OUTCOME_LEADS, OUTCOME_ENGAGEMENT,
# OUTCOME_TRAFFIC, OUTCOME_AWARENESS, OUTCOME_APP_PROMOTION
OBJECTIVE_MAP = {
    "sales": "OUTCOME_SALES",
    "conversions": "OUTCOME_SALES",
    "leads": "OUTCOME_LEADS",
    "traffic": "OUTCOME_TRAFFIC",
    "awareness": "OUTCOME_AWARENESS",
    "engagement": "OUTCOME_ENGAGEMENT",
}


async def create_campaign(user_id: str, ad_account_id: str, name: str,
                           objective: str = "sales",
                           status: str = "PAUSED",
                           special_ad_categories: List[str] = None) -> Dict[str, Any]:
    """Cria campanha. ad_account_id no formato act_XXXXX.
    status=PAUSED por padrão (boa prática — só ativa após criar adset+ad)."""
    payload = {
        "name": name,
        "objective": OBJECTIVE_MAP.get(objective.lower(), "OUTCOME_SALES"),
        "status": status,
        "special_ad_categories": special_ad_categories or [],
        "buying_type": "AUCTION",
    }
    return await _post(user_id, f"{ad_account_id}/campaigns", payload)


async def create_adset(user_id: str, ad_account_id: str, campaign_id: str,
                        name: str, daily_budget_brl: float,
                        pixel_id: str,
                        optimization_goal: str = "OFFSITE_CONVERSIONS",
                        billing_event: str = "IMPRESSIONS",
                        targeting: Dict[str, Any] = None,
                        custom_event_type: str = "PURCHASE",
                        status: str = "PAUSED") -> Dict[str, Any]:
    """Cria AdSet. daily_budget em BRL (convertido pra centavos)."""
    import time
    from datetime import datetime, timezone, timedelta
    now_utc = datetime.now(timezone.utc)
    start_time = (now_utc + timedelta(minutes=5)).isoformat()
    payload = {
        "name": name,
        "campaign_id": campaign_id,
        "daily_budget": int(round(daily_budget_brl * 100)),   # centavos
        "billing_event": billing_event,
        "optimization_goal": optimization_goal,
        "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
        "promoted_object": {
            "pixel_id": pixel_id,
            "custom_event_type": custom_event_type,
        },
        "targeting": targeting or {
            "geo_locations": {"countries": ["BR"]},
            "age_min": 22,
            "age_max": 55,
            "publisher_platforms": ["facebook", "instagram"],
            "facebook_positions": ["feed", "story"],
            "instagram_positions": ["stream", "story", "explore", "reels"],
        },
        "start_time": start_time,
        "status": status,
    }
    return await _post(user_id, f"{ad_account_id}/adsets", payload)


async def create_ad_creative(user_id: str, ad_account_id: str, name: str,
                              page_id: str, message: str, link_url: str,
                              image_hash: Optional[str] = None,
                              video_id: Optional[str] = None,
                              headline: str = "", description: str = "",
                              call_to_action_type: str = "LEARN_MORE") -> Dict[str, Any]:
    """Cria AdCreative. Precisa de image_hash (upload prévio) ou video_id."""
    link_data: Dict[str, Any] = {
        "link": link_url,
        "message": message[:500],
        "name": headline[:40] if headline else message[:40],
        "description": description[:30] if description else "",
        "call_to_action": {"type": call_to_action_type,
                             "value": {"link": link_url}},
    }
    if image_hash:
        link_data["image_hash"] = image_hash
    creative_story: Dict[str, Any] = {
        "page_id": page_id,
        "link_data": link_data,
    }
    if video_id:
        creative_story["video_data"] = {"video_id": video_id, "message": message[:500]}
        creative_story.pop("link_data", None)
    # payload aceita dict no Graph — usamos JSON
    import json as _j
    form_payload = {"name": name, "object_story_spec": _j.dumps(creative_story)}
    return await _post(user_id, f"{ad_account_id}/adcreatives", form_payload)


async def create_ad(user_id: str, ad_account_id: str, adset_id: str,
                     name: str, creative_id: str, status: str = "PAUSED") -> Dict[str, Any]:
    import json as _j
    payload = {
        "name": name,
        "adset_id": adset_id,
        "creative": _j.dumps({"creative_id": creative_id}),
        "status": status,
    }
    return await _post(user_id, f"{ad_account_id}/ads", payload)


async def upload_image(user_id: str, ad_account_id: str, image_url: str) -> Dict[str, Any]:
    """Upload imagem pro Ad Account via URL. Retorna {hash: ...}."""
    # Graph API aceita {url: "..."} no endpoint /adimages
    return await _post(user_id, f"{ad_account_id}/adimages", {"url": image_url})


# ─── Insights / Reading ──────────────────────────────────────────────────────
async def get_insights(user_id: str, object_id: str,
                        level: str = "campaign",
                        date_preset: str = "last_7d",
                        breakdowns: List[str] = None) -> List[Dict[str, Any]]:
    """object_id pode ser act_XXX, campaign_id, adset_id ou ad_id.
    level: account | campaign | adset | ad
    Métricas cobertas: impressions, clicks, ctr, cpm, spend, reach, frequency,
       actions (inclui conversions, purchases, leads)"""
    fields = ("impressions,clicks,ctr,cpm,cpc,spend,reach,frequency,"
              "actions,action_values,cost_per_action_type,purchase_roas")
    params: Dict[str, Any] = {
        "fields": fields,
        "level": level,
        "date_preset": date_preset,
        "limit": 500,
    }
    if breakdowns:
        params["breakdowns"] = ",".join(breakdowns)
    d = await _get(user_id, f"{object_id}/insights", params)
    return d.get("data", []) if "error" not in d else []


async def list_campaigns(user_id: str, ad_account_id: str) -> List[Dict[str, Any]]:
    d = await _get(user_id, f"{ad_account_id}/campaigns", {
        "fields": "id,name,objective,status,effective_status,daily_budget,lifetime_budget,created_time",
        "limit": 100,
    })
    return d.get("data", []) if "error" not in d else []


# ─── Pause / Resume / Budget ─────────────────────────────────────────────────
async def pause_object(user_id: str, object_id: str) -> Dict[str, Any]:
    """Funciona pra campaign, adset e ad (mesmo endpoint POST)."""
    return await _post(user_id, object_id, {"status": "PAUSED"})


async def resume_object(user_id: str, object_id: str) -> Dict[str, Any]:
    return await _post(user_id, object_id, {"status": "ACTIVE"})


async def update_campaign_budget(user_id: str, campaign_id: str,
                                   daily_budget_brl: float) -> Dict[str, Any]:
    """Usado quando campaign tem CBO ativo."""
    return await _post(user_id, campaign_id, {
        "daily_budget": int(round(daily_budget_brl * 100))
    })


async def update_adset_budget(user_id: str, adset_id: str,
                                daily_budget_brl: float) -> Dict[str, Any]:
    return await _post(user_id, adset_id, {
        "daily_budget": int(round(daily_budget_brl * 100))
    })


async def shift_budget_pct(user_id: str, object_id: str, delta_pct: float,
                             level: str = "adset") -> Dict[str, Any]:
    """Aumenta/diminui budget atual em delta_pct (-100..+1000)."""
    # Busca budget atual
    d = await _get(user_id, object_id, {"fields": "daily_budget,lifetime_budget,name"})
    if "error" in d:
        return d
    current_cents = int(d.get("daily_budget") or 0)
    if current_cents <= 0:
        return {"error": "no_daily_budget_set"}
    new_cents = max(100, int(round(current_cents * (1 + delta_pct / 100.0))))
    return await _post(user_id, object_id, {"daily_budget": new_cents})


# ─── Pixel Events Test ───────────────────────────────────────────────────────
async def test_pixel_event(user_id: str, pixel_id: str, test_event_code: str,
                            event_name: str = "Purchase") -> Dict[str, Any]:
    """Envia evento de teste pro Meta Events Manager (valida tracking)."""
    import time as _t
    payload = {
        "data": [{"event_name": event_name,
                   "event_time": int(_t.time()),
                   "action_source": "website",
                   "event_source_url": "https://example.com"}],
        "test_event_code": test_event_code,
    }
    return await _post(user_id, f"{pixel_id}/events", payload, use_form=False)
