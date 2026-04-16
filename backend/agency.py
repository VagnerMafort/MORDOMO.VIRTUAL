"""
Agency Module - Marketing Agency System
Products, Rules Engine, Approval Queue, Access Control
"""
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uuid
from datetime import datetime, timezone

router = APIRouter(prefix="/api/agency")

# Will be set from server.py
db = None
get_current_user = None

def init(database, auth_fn):
    global db, get_current_user
    db = database
    get_current_user = auth_fn

# ─── Access Control ──────────────────────────────────────────────────────────
async def check_agency_access(user: dict):
    """Only admin or users with explicit agency access can use agency features."""
    if user.get("role") == "admin":
        return True
    access = await db.agency_access.find_one({"user_id": user["_id"], "granted": True})
    if not access:
        raise HTTPException(status_code=403, detail="Sem acesso a agencia. Solicite ao administrador.")
    return True

class GrantAccessInput(BaseModel):
    user_email: str
    granted: bool = True

@router.post("/access/grant")
async def grant_agency_access(body: GrantAccessInput, request: Request):
    user = await get_current_user(request)
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Apenas o administrador pode conceder acesso")
    target = await db.users.find_one({"email": body.user_email.strip().lower()})
    if not target:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")
    target_id = str(target["_id"])
    await db.agency_access.update_one(
        {"user_id": target_id},
        {"$set": {"user_id": target_id, "email": body.user_email.strip().lower(), "granted": body.granted, "granted_by": user["_id"], "granted_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True
    )
    return {"message": f"Acesso {'concedido' if body.granted else 'revogado'} para {body.user_email}"}

@router.get("/access/list")
async def list_agency_access(request: Request):
    user = await get_current_user(request)
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Apenas o administrador")
    accesses = await db.agency_access.find({}, {"_id": 0}).to_list(100)
    return accesses

@router.get("/access/check")
async def check_access(request: Request):
    user = await get_current_user(request)
    if user.get("role") == "admin":
        return {"has_access": True, "role": "admin"}
    access = await db.agency_access.find_one({"user_id": user["_id"], "granted": True})
    return {"has_access": access is not None, "role": "member"}

# ─── Products (Central Unit) ────────────────────────────────────────────────
class ProductCreate(BaseModel):
    name: str
    description: str = ""
    niche: str = ""
    target_audience: str = ""
    monthly_budget: float = 0

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    niche: Optional[str] = None
    target_audience: Optional[str] = None
    monthly_budget: Optional[float] = None
    status: Optional[str] = None

@router.get("/products")
async def list_products(request: Request):
    user = await get_current_user(request)
    await check_agency_access(user)
    products = await db.products.find({}, {"_id": 0}).sort("created_at", -1).to_list(50)
    return products

@router.post("/products")
async def create_product(body: ProductCreate, request: Request):
    user = await get_current_user(request)
    await check_agency_access(user)
    prod_id = str(uuid.uuid4())
    doc = {
        "id": prod_id, "name": body.name, "description": body.description,
        "niche": body.niche, "target_audience": body.target_audience,
        "monthly_budget": body.monthly_budget, "status": "active",
        "metrics": {"ctr": 0, "cpc": 0, "cpa": 0, "roas": 0, "conversions": 0, "spend": 0, "revenue": 0},
        "created_by": user["_id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.products.insert_one(doc)
    doc.pop("_id", None)
    return doc

@router.put("/products/{prod_id}")
async def update_product(prod_id: str, body: ProductUpdate, request: Request):
    user = await get_current_user(request)
    await check_agency_access(user)
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    if data:
        await db.products.update_one({"id": prod_id}, {"$set": data})
    prod = await db.products.find_one({"id": prod_id}, {"_id": 0})
    return prod

@router.delete("/products/{prod_id}")
async def delete_product(prod_id: str, request: Request):
    user = await get_current_user(request)
    await check_agency_access(user)
    await db.products.delete_one({"id": prod_id})
    await db.campaigns.delete_many({"product_id": prod_id})
    await db.rules.delete_many({"product_id": prod_id})
    return {"message": "Produto deletado"}

# ─── Campaigns ───────────────────────────────────────────────────────────────
class CampaignCreate(BaseModel):
    product_id: str
    name: str
    platform: str = "meta"
    objective: str = ""
    daily_budget: float = 0

@router.get("/products/{prod_id}/campaigns")
async def list_campaigns(prod_id: str, request: Request):
    user = await get_current_user(request)
    await check_agency_access(user)
    campaigns = await db.campaigns.find({"product_id": prod_id}, {"_id": 0}).to_list(50)
    return campaigns

@router.post("/campaigns")
async def create_campaign(body: CampaignCreate, request: Request):
    user = await get_current_user(request)
    await check_agency_access(user)
    camp_id = str(uuid.uuid4())
    doc = {
        "id": camp_id, "product_id": body.product_id, "name": body.name,
        "platform": body.platform, "objective": body.objective,
        "daily_budget": body.daily_budget, "status": "active",
        "metrics": {"impressions": 0, "clicks": 0, "ctr": 0, "cpc": 0, "cpa": 0, "conversions": 0, "spend": 0, "roas": 0},
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.campaigns.insert_one(doc)
    doc.pop("_id", None)
    return doc

@router.delete("/campaigns/{camp_id}")
async def delete_campaign(camp_id: str, request: Request):
    user = await get_current_user(request)
    await check_agency_access(user)
    await db.campaigns.delete_one({"id": camp_id})
    return {"message": "Campanha deletada"}

# ─── Rules Engine ────────────────────────────────────────────────────────────
class RuleCondition(BaseModel):
    metric: str
    operator: str  # gt, lt, gte, lte, eq, change_pct_gt, change_pct_lt
    value: float
    period: str = "24h"  # 1h, 4h, 24h, 7d

class RuleAction(BaseModel):
    type: str  # pause_campaign, scale_budget, alert, change_bid, create_report
    params: dict = {}

class RuleCreate(BaseModel):
    name: str
    product_id: str
    campaign_id: Optional[str] = None
    conditions: List[RuleCondition]
    actions: List[RuleAction]
    requires_approval: bool = True
    logic: str = "AND"  # AND = all conditions, OR = any condition

@router.get("/rules")
async def list_rules(request: Request):
    user = await get_current_user(request)
    await check_agency_access(user)
    rules = await db.rules.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return rules

@router.post("/rules")
async def create_rule(body: RuleCreate, request: Request):
    user = await get_current_user(request)
    await check_agency_access(user)
    rule_id = str(uuid.uuid4())
    doc = {
        "id": rule_id, "name": body.name,
        "product_id": body.product_id, "campaign_id": body.campaign_id,
        "conditions": [c.model_dump() for c in body.conditions],
        "actions": [a.model_dump() for a in body.actions],
        "requires_approval": body.requires_approval,
        "logic": body.logic, "active": True,
        "triggered_count": 0, "last_triggered": None,
        "created_by": user["_id"],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.rules.insert_one(doc)
    doc.pop("_id", None)
    return doc

@router.put("/rules/{rule_id}/toggle")
async def toggle_rule(rule_id: str, request: Request):
    user = await get_current_user(request)
    await check_agency_access(user)
    rule = await db.rules.find_one({"id": rule_id})
    if not rule:
        raise HTTPException(status_code=404, detail="Regra nao encontrada")
    new_state = not rule.get("active", True)
    await db.rules.update_one({"id": rule_id}, {"$set": {"active": new_state}})
    return {"active": new_state}

@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str, request: Request):
    user = await get_current_user(request)
    await check_agency_access(user)
    await db.rules.delete_one({"id": rule_id})
    return {"message": "Regra deletada"}

# ─── Approval Queue ──────────────────────────────────────────────────────────
@router.get("/approvals")
async def list_approvals(request: Request):
    user = await get_current_user(request)
    await check_agency_access(user)
    approvals = await db.approvals.find({}, {"_id": 0}).sort("created_at", -1).to_list(50)
    return approvals

@router.post("/approvals/{approval_id}/approve")
async def approve_action(approval_id: str, request: Request):
    user = await get_current_user(request)
    await check_agency_access(user)
    approval = await db.approvals.find_one({"id": approval_id})
    if not approval:
        raise HTTPException(status_code=404, detail="Aprovacao nao encontrada")
    await db.approvals.update_one({"id": approval_id}, {"$set": {
        "status": "approved", "approved_by": user["_id"],
        "approved_at": datetime.now(timezone.utc).isoformat()
    }})
    # TODO: Execute the approved action
    await db.approval_log.insert_one({
        "approval_id": approval_id, "action": "approved",
        "user_id": user["_id"], "timestamp": datetime.now(timezone.utc).isoformat()
    })
    return {"message": "Acao aprovada e executada"}

@router.post("/approvals/{approval_id}/reject")
async def reject_action(approval_id: str, request: Request):
    user = await get_current_user(request)
    await check_agency_access(user)
    await db.approvals.update_one({"id": approval_id}, {"$set": {
        "status": "rejected", "rejected_by": user["_id"],
        "rejected_at": datetime.now(timezone.utc).isoformat()
    }})
    return {"message": "Acao rejeitada"}

# ─── Reports ─────────────────────────────────────────────────────────────────
@router.get("/reports/agency")
async def agency_report(request: Request):
    user = await get_current_user(request)
    await check_agency_access(user)
    products = await db.products.find({"status": "active"}, {"_id": 0}).to_list(50)
    total_spend = sum(p.get("metrics", {}).get("spend", 0) for p in products)
    total_revenue = sum(p.get("metrics", {}).get("revenue", 0) for p in products)
    total_conversions = sum(p.get("metrics", {}).get("conversions", 0) for p in products)
    rules_count = await db.rules.count_documents({"active": True})
    pending_approvals = await db.approvals.count_documents({"status": "pending"})
    return {
        "products_count": len(products),
        "total_spend": total_spend, "total_revenue": total_revenue,
        "total_conversions": total_conversions,
        "overall_roas": round(total_revenue / total_spend, 2) if total_spend > 0 else 0,
        "active_rules": rules_count, "pending_approvals": pending_approvals,
        "products": products
    }

@router.get("/reports/product/{prod_id}")
async def product_report(prod_id: str, request: Request):
    user = await get_current_user(request)
    await check_agency_access(user)
    product = await db.products.find_one({"id": prod_id}, {"_id": 0})
    if not product:
        raise HTTPException(status_code=404, detail="Produto nao encontrado")
    campaigns = await db.campaigns.find({"product_id": prod_id}, {"_id": 0}).to_list(50)
    rules = await db.rules.find({"product_id": prod_id}, {"_id": 0}).to_list(50)
    return {"product": product, "campaigns": campaigns, "rules": rules}
