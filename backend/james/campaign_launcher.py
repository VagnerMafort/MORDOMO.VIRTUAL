"""
Campaign Launcher — transforma um Product do JAMES em campanha real no Meta Ads.

Orquestra a criação em cascata:
  1. Campaign (objective = CONVERSIONS)
  2. AdSet (pixel + targeting + daily_budget baseado no preset)
  3. Ad Creative (copy gerado pelo NOVA + imagem fornecida)
  4. Ad (amarra adset + creative)

Endpoints REST:
  GET  /api/james/meta/ad-accounts        → lista Ad Accounts do usuário
  GET  /api/james/meta/pixels             → pixels disponíveis
  POST /api/james/products/{id}/launch    → dispara fluxo completo de criação
  GET  /api/james/products/{id}/campaigns → lista campanhas criadas pelo JAMES
  POST /api/james/products/{id}/sync-insights → puxa insights reais do Meta (ingest)
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import logging

import sys
sys.path.insert(0, "/app/backend")
import meta_ads_api as ma

logger = logging.getLogger(__name__)

_db = None
_get_user = None


def init(db_ref, user_fn):
    global _db, _get_user
    _db = db_ref
    _get_user = user_fn


router = APIRouter(prefix="/api/james/meta", tags=["james-meta"])


# ─── Discovery endpoints ─────────────────────────────────────────────────────
@router.get("/ad-accounts")
async def get_ad_accounts(request: Request):
    user = await _get_user(request)
    accounts = await ma.list_ad_accounts(user["_id"])
    return {"accounts": accounts, "count": len(accounts)}


@router.get("/businesses")
async def get_businesses(request: Request):
    user = await _get_user(request)
    return {"businesses": await ma.list_businesses(user["_id"])}


@router.get("/pixels")
async def get_pixels(request: Request, ad_account_id: str):
    user = await _get_user(request)
    pixels = await ma.list_pixels(user["_id"], ad_account_id)
    return {"pixels": pixels}


@router.get("/pages")
async def get_pages(request: Request):
    user = await _get_user(request)
    return {"pages": await ma.list_pages(user["_id"])}


class CreatePixelIn(BaseModel):
    business_id: str
    name: str


@router.post("/pixels")
async def create_pixel(request: Request, body: CreatePixelIn):
    user = await _get_user(request)
    r = await ma.create_pixel(user["_id"], body.business_id, body.name)
    if "error" in r:
        raise HTTPException(400, r["error"])
    return r


# ─── Budget Presets ──────────────────────────────────────────────────────────
PRESETS = {
    "conservative": {
        "daily_initial_brl": 20.0,
        "scale_up_pct_max": 20.0,       # MIDAS pode escalar até +20% por tick
        "scale_down_pct_max": 30.0,
        "auto_approve_risk": "low",
        "auto_scale_cap_multiplier": 1.5,  # teto: 1.5x budget inicial
        "description": "Testa devagar, escala pouco, minimiza risco.",
    },
    "moderate": {
        "daily_initial_brl": 50.0,
        "scale_up_pct_max": 40.0,
        "scale_down_pct_max": 50.0,
        "auto_approve_risk": "medium",
        "auto_scale_cap_multiplier": 3.0,
        "description": "Balanceado entre aprendizado e velocidade.",
    },
    "aggressive": {
        "daily_initial_brl": 100.0,
        "scale_up_pct_max": 100.0,     # pode dobrar budget
        "scale_down_pct_max": 80.0,
        "auto_approve_risk": "medium",
        "auto_scale_cap_multiplier": 10.0,
        "description": "Acelera depressa. Queima orçamento se copy estiver ruim.",
    },
}


@router.get("/presets")
async def get_presets(request: Request):
    await _get_user(request)
    return {"presets": PRESETS}


# ─── Launch Campaign (o coração) ─────────────────────────────────────────────
class LaunchCampaignIn(BaseModel):
    ad_account_id: str                     # formato act_XXXXXXX
    pixel_id: str                          # obrigatório (CONVERSIONS)
    page_id: str                           # Facebook Page (pra creative)
    landing_url: str                       # URL final (LP com pixel)
    budget_preset: str = "conservative"    # conservative | moderate | aggressive
    objective: str = "sales"               # sales | leads | traffic
    custom_event_type: str = "PURCHASE"    # PURCHASE | LEAD | VIEW_CONTENT
    copy_text: Optional[str] = None        # opcional (senão NOVA gera)
    image_url: Optional[str] = None        # URL pública da imagem do ad
    headline: Optional[str] = None
    description: Optional[str] = None
    call_to_action_type: str = "LEARN_MORE"  # LEARN_MORE | SHOP_NOW | SIGN_UP


@router.post("/products/{product_id}/launch")
async def launch_campaign(request: Request, product_id: str, body: LaunchCampaignIn):
    """Orquestra criação completa Campaign→AdSet→Creative→Ad no Meta.
    Tudo em PAUSED (não gasta dinheiro ainda). Activação é manual ou via autopilot."""
    user = await _get_user(request)
    product = await _db.james_products.find_one({"id": product_id, "user_id": user["_id"]})
    if not product:
        raise HTTPException(404, "Produto não encontrado")
    preset = PRESETS.get(body.budget_preset)
    if not preset:
        raise HTTPException(400, f"Preset inválido. Use: {list(PRESETS)}")

    daily_budget = preset["daily_initial_brl"]
    out: Dict[str, Any] = {"steps": [], "errors": []}

    # ─── 1. Copy generation (NOVA) ───
    copy_text = body.copy_text
    if not copy_text:
        from .agents.registry import agent_registry
        import os
        agents = agent_registry(
            os.environ.get("OLLAMA_URL", "http://localhost:11434"),
            os.environ.get("OLLAMA_MODEL", "qwen2.5:7b"),
        )
        nova = agents["NOVA"]
        prompt = (f"Gere UM anúncio Facebook/Instagram em português (máx 4 linhas) "
                  f"pra produto: {product['name']}. Nicho: {product.get('niche')}. "
                  f"Oferta: {product.get('offer')}. Público: {product.get('target_audience')}. "
                  f"Foco em: dor do cliente + solução + CTA pro link. "
                  f"Responda APENAS o texto do anúncio, sem explicações.")
        try:
            copy_text = (await nova.think(prompt, temperature=0.7)).strip() or product.get("offer", product["name"])
        except Exception:
            copy_text = product.get("offer", product["name"])
    out["copy_generated"] = copy_text

    # ─── 2. Criar Campaign ───
    camp = await ma.create_campaign(
        user_id=user["_id"], ad_account_id=body.ad_account_id,
        name=f"JAMES · {product['name']} · {body.budget_preset}",
        objective=body.objective, status="PAUSED",
    )
    if "error" in camp:
        out["errors"].append({"step": "campaign", "error": camp["error"]})
        return out
    campaign_id = camp["id"]
    out["campaign_id"] = campaign_id
    out["steps"].append({"step": "campaign", "id": campaign_id})

    # ─── 3. Criar AdSet ───
    adset = await ma.create_adset(
        user_id=user["_id"], ad_account_id=body.ad_account_id,
        campaign_id=campaign_id,
        name=f"AdSet · {product['name']}",
        daily_budget_brl=daily_budget,
        pixel_id=body.pixel_id,
        optimization_goal="OFFSITE_CONVERSIONS",
        billing_event="IMPRESSIONS",
        custom_event_type=body.custom_event_type,
        status="PAUSED",
    )
    if "error" in adset:
        out["errors"].append({"step": "adset", "error": adset["error"]})
        return out
    adset_id = adset["id"]
    out["adset_id"] = adset_id
    out["steps"].append({"step": "adset", "id": adset_id, "daily_budget_brl": daily_budget})

    # ─── 4. Upload imagem (se informada) ───
    image_hash = None
    if body.image_url:
        up = await ma.upload_image(user["_id"], body.ad_account_id, body.image_url)
        if "error" not in up and up.get("images"):
            # response format: {images: {bytes_hex: {hash, url}}}
            first = list(up["images"].values())[0]
            image_hash = first.get("hash")
            out["steps"].append({"step": "image_upload", "hash": image_hash})
        else:
            out["errors"].append({"step": "image_upload", "error": up.get("error", "no_hash")})

    # ─── 5. Criar AdCreative ───
    creative = await ma.create_ad_creative(
        user_id=user["_id"], ad_account_id=body.ad_account_id,
        name=f"Creative · {product['name']}",
        page_id=body.page_id, message=copy_text,
        link_url=body.landing_url, image_hash=image_hash,
        headline=body.headline or product.get("name", "")[:40],
        description=body.description or product.get("offer", "")[:30],
        call_to_action_type=body.call_to_action_type,
    )
    if "error" in creative:
        out["errors"].append({"step": "creative", "error": creative["error"]})
        return out
    creative_id = creative["id"]
    out["creative_id"] = creative_id
    out["steps"].append({"step": "creative", "id": creative_id})

    # ─── 6. Criar Ad ───
    ad = await ma.create_ad(
        user_id=user["_id"], ad_account_id=body.ad_account_id,
        adset_id=adset_id, name=f"Ad · {product['name']}",
        creative_id=creative_id, status="PAUSED",
    )
    if "error" in ad:
        out["errors"].append({"step": "ad", "error": ad["error"]})
        return out
    out["ad_id"] = ad["id"]
    out["steps"].append({"step": "ad", "id": ad["id"]})

    # ─── 7. Registrar no Mongo ───
    record = {
        "id": f"meta_{campaign_id}",
        "product_id": product_id,
        "user_id": user["_id"],
        "ad_account_id": body.ad_account_id,
        "pixel_id": body.pixel_id,
        "page_id": body.page_id,
        "campaign_id": campaign_id,
        "adset_id": adset_id,
        "creative_id": creative_id,
        "ad_id": ad["id"],
        "budget_preset": body.budget_preset,
        "daily_budget_brl": daily_budget,
        "landing_url": body.landing_url,
        "status": "PAUSED",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await _db.james_meta_campaigns.insert_one(record)
    # Atualizar produto com refs
    await _db.james_products.update_one(
        {"id": product_id},
        {"$set": {
            "meta_ad_account_id": body.ad_account_id,
            "meta_pixel_id": body.pixel_id,
            "meta_page_id": body.page_id,
            "budget_preset": body.budget_preset,
            "landing_url": body.landing_url,
            "last_campaign_created": campaign_id,
        }},
    )
    out["status"] = "ready"
    out["activation_hint"] = (
        f"Campanha criada em PAUSED. Para ativar rode: POST "
        f"/api/james/meta/objects/{campaign_id}/resume ou ative via autopilot."
    )
    return out


# ─── Listar campanhas criadas ────────────────────────────────────────────────
@router.get("/products/{product_id}/campaigns")
async def list_product_campaigns(request: Request, product_id: str):
    user = await _get_user(request)
    items = await _db.james_meta_campaigns.find(
        {"product_id": product_id, "user_id": user["_id"]},
        {"_id": 0},
    ).to_list(50)
    return items


# ─── Pause / Resume ──────────────────────────────────────────────────────────
@router.post("/objects/{object_id}/pause")
async def pause(request: Request, object_id: str):
    user = await _get_user(request)
    r = await ma.pause_object(user["_id"], object_id)
    if "error" in r:
        raise HTTPException(400, r["error"])
    return r


@router.post("/objects/{object_id}/resume")
async def resume(request: Request, object_id: str):
    user = await _get_user(request)
    r = await ma.resume_object(user["_id"], object_id)
    if "error" in r:
        raise HTTPException(400, r["error"])
    return r


# ─── Sync Insights (puxa métricas reais do Meta pro JAMES) ──────────────────
METRIC_MAP = {
    "impressions": "impressions",
    "clicks": "clicks",
    "ctr": "ctr",
    "cpm": "cpm",
    "cpc": "cpc",
    "spend": "spend",
    "reach": "reach",
    "frequency": "frequency",
}


async def _ingest_insights(product_id: str, user_id: str, rows: List[Dict[str, Any]],
                            dimension_key: str = "campaign"):
    """Converte resposta do Meta em pontos james_metrics."""
    from .layers import layer1_sensors_ingest
    points = []
    for row in rows:
        dim = {dimension_key: row.get(f"{dimension_key}_id") or row.get("id", "unknown")}
        ts = row.get("date_start") or datetime.now(timezone.utc).isoformat()
        for meta_k, james_k in METRIC_MAP.items():
            v = row.get(meta_k)
            if v is None:
                continue
            try:
                points.append({"metric": james_k, "value": float(v), "dimension": dim, "captured_at": ts})
            except Exception:
                pass
        # Actions: conversions / purchases / leads
        actions = row.get("actions", [])
        purchase_count = 0
        lead_count = 0
        for a in actions:
            at = a.get("action_type", "")
            if at in ("purchase", "offsite_conversion.fb_pixel_purchase"):
                purchase_count += float(a.get("value", 0))
            if at in ("lead", "offsite_conversion.fb_pixel_lead"):
                lead_count += float(a.get("value", 0))
        if purchase_count:
            points.append({"metric": "conversions", "value": purchase_count,
                            "dimension": dim, "captured_at": ts})
        if lead_count:
            points.append({"metric": "leads", "value": lead_count,
                            "dimension": dim, "captured_at": ts})
        # Revenue via action_values
        vals = row.get("action_values", [])
        for v in vals:
            if v.get("action_type") in ("purchase", "offsite_conversion.fb_pixel_purchase"):
                points.append({"metric": "revenue", "value": float(v.get("value", 0)),
                                "dimension": dim, "captured_at": ts})
        # ROAS
        roas = row.get("purchase_roas", [])
        for r in roas:
            points.append({"metric": "roas", "value": float(r.get("value", 0)),
                            "dimension": dim, "captured_at": ts})
    if points:
        await layer1_sensors_ingest(product_id, "meta_ads", points)
    return len(points)


@router.post("/products/{product_id}/sync-insights")
async def sync_insights(request: Request, product_id: str, date_preset: str = "today"):
    """Puxa insights reais do Meta pra todas as campanhas do produto."""
    user = await _get_user(request)
    camps = await _db.james_meta_campaigns.find(
        {"product_id": product_id, "user_id": user["_id"]},
        {"_id": 0, "campaign_id": 1},
    ).to_list(100)
    if not camps:
        return {"ingested": 0, "reason": "no_campaigns_found"}
    total = 0
    for c in camps:
        rows = await ma.get_insights(user["_id"], c["campaign_id"],
                                       level="campaign", date_preset=date_preset)
        total += await _ingest_insights(product_id, user["_id"], rows, "campaign")
    return {"ingested": total, "campaigns": len(camps), "date_preset": date_preset}
