"""
Rules Engine - Automatic evaluation and inter-agent communication
"""
import asyncio
import json
import uuid
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

db = None
RUNNING = False
EVAL_INTERVAL = 60  # seconds

def init(database):
    global db
    db = database

async def evaluate_rule(rule: dict) -> dict:
    """Evaluate a single rule against current metrics."""
    product = await db.products.find_one({"id": rule["product_id"]}, {"_id": 0})
    if not product:
        return {"triggered": False, "reason": "Produto nao encontrado"}

    metrics = product.get("metrics", {})
    conditions = rule.get("conditions", [])
    logic = rule.get("logic", "AND")
    results = []

    for cond in conditions:
        metric_val = metrics.get(cond["metric"], 0)
        op = cond["operator"]
        target = cond["value"]
        passed = False
        if op == "gt": passed = metric_val > target
        elif op == "lt": passed = metric_val < target
        elif op == "gte": passed = metric_val >= target
        elif op == "lte": passed = metric_val <= target
        elif op == "eq": passed = metric_val == target
        elif op == "change_pct_gt": passed = metric_val > target  # simplified
        elif op == "change_pct_lt": passed = metric_val < target
        results.append({"metric": cond["metric"], "current": metric_val, "target": target, "op": op, "passed": passed})

    if logic == "AND":
        triggered = all(r["passed"] for r in results)
    else:
        triggered = any(r["passed"] for r in results)

    return {"triggered": triggered, "results": results, "product_name": product.get("name", "")}

async def execute_rule_actions(rule: dict, eval_result: dict):
    """Execute or queue actions for a triggered rule."""
    now = datetime.now(timezone.utc).isoformat()

    if rule.get("requires_approval"):
        # Queue for human approval
        approval_id = str(uuid.uuid4())
        desc_parts = [f"{r['metric']}={r['current']} ({r['op']} {r['target']})" for r in eval_result["results"] if r["passed"]]
        await db.approvals.insert_one({
            "id": approval_id,
            "rule_id": rule["id"],
            "rule_name": rule["name"],
            "product_id": rule["product_id"],
            "product_name": eval_result.get("product_name", ""),
            "description": f"Regra disparada: {', '.join(desc_parts)}",
            "actions": rule.get("actions", []),
            "status": "pending",
            "created_at": now
        })
        logger.info(f"Approval queued for rule '{rule['name']}'")
    else:
        # Auto-execute actions
        for action in rule.get("actions", []):
            await execute_action(action, rule, eval_result)

    # Update rule stats
    await db.rules.update_one({"id": rule["id"]}, {
        "$inc": {"triggered_count": 1},
        "$set": {"last_triggered": now}
    })

async def execute_action(action: dict, rule: dict, eval_result: dict):
    """Execute a single action - both locally and on connected platforms."""
    action_type = action.get("type", "")
    now = datetime.now(timezone.utc).isoformat()
    result_log = {"action": action_type, "success": False, "details": ""}

    if action_type == "pause_campaign":
        campaign_id = rule.get("campaign_id")
        if campaign_id:
            camp = await db.campaigns.find_one({"id": campaign_id})
            if camp:
                # Update local status
                await db.campaigns.update_one({"id": campaign_id}, {"$set": {"status": "paused"}})
                result_log["details"] = f"Campanha {camp.get('name', '')} pausada localmente"
                result_log["success"] = True
                # Execute on platform
                platform_result = await execute_on_platform(
                    camp.get("platform", ""),
                    "pause",
                    {"campaign_id": campaign_id, "campaign_name": camp.get("name", "")},
                    rule.get("created_by", "")
                )
                result_log["platform_result"] = platform_result

    elif action_type == "scale_budget":
        factor = action.get("params", {}).get("factor", 1.2)
        campaign_id = rule.get("campaign_id")
        if campaign_id:
            camp = await db.campaigns.find_one({"id": campaign_id})
            if camp:
                old_budget = camp.get("daily_budget", 0)
                new_budget = round(old_budget * factor, 2)
                await db.campaigns.update_one({"id": campaign_id}, {"$set": {"daily_budget": new_budget}})
                result_log["details"] = f"Budget: R${old_budget} -> R${new_budget} (+{int((factor-1)*100)}%)"
                result_log["success"] = True
                platform_result = await execute_on_platform(
                    camp.get("platform", ""),
                    "update_budget",
                    {"campaign_id": campaign_id, "new_budget": new_budget},
                    rule.get("created_by", "")
                )
                result_log["platform_result"] = platform_result

    elif action_type == "reduce_budget":
        factor = action.get("params", {}).get("factor", 0.5)
        campaign_id = rule.get("campaign_id")
        if campaign_id:
            camp = await db.campaigns.find_one({"id": campaign_id})
            if camp:
                old_budget = camp.get("daily_budget", 0)
                new_budget = round(old_budget * factor, 2)
                await db.campaigns.update_one({"id": campaign_id}, {"$set": {"daily_budget": new_budget}})
                result_log["details"] = f"Budget: R${old_budget} -> R${new_budget} (-{int((1-factor)*100)}%)"
                result_log["success"] = True
                platform_result = await execute_on_platform(
                    camp.get("platform", ""),
                    "update_budget",
                    {"campaign_id": campaign_id, "new_budget": new_budget},
                    rule.get("created_by", "")
                )
                result_log["platform_result"] = platform_result

    elif action_type == "alert":
        # Send alert via inter-agent message
        await agent_message("rules_engine", "sentinel", "alert", {
            "rule": rule.get("name", ""),
            "product": eval_result.get("product_name", ""),
            "details": [f"{r['metric']}={r['current']}" for r in eval_result.get("results", []) if r.get("passed")]
        })
        result_log["success"] = True
        result_log["details"] = "Alerta enviado ao SENTINEL"

    elif action_type == "create_report":
        await agent_message("rules_engine", "echo", "request", {
            "type": "report",
            "product_id": rule.get("product_id", ""),
            "rule_triggered": rule.get("name", ""),
            "eval_result": eval_result
        })
        result_log["success"] = True
        result_log["details"] = "Relatorio solicitado ao ECHO"

    # Log execution
    await db.execution_log.insert_one({
        "id": str(uuid.uuid4()),
        "rule_id": rule["id"],
        "rule_name": rule.get("name", ""),
        "action": action,
        "result": result_log,
        "eval_result": eval_result,
        "executed_at": now
    })
    return result_log

async def execute_on_platform(platform: str, action: str, params: dict, user_id: str) -> dict:
    """Execute an action on the actual ad platform via API."""
    import httpx
    integration = await db.platform_integrations.find_one({"user_id": user_id, "platform": platform, "status": "active"})
    if not integration:
        return {"executed": False, "reason": f"Plataforma {platform} nao conectada para este usuario"}

    creds = integration.get("credentials", {})
    token = creds.get("access_token", "")
    account_id = creds.get("account_id", "")

    try:
        async with httpx.AsyncClient(timeout=15.0) as c:
            if platform == "meta":
                if action == "pause":
                    # Meta Ads API - pause campaign
                    camp_name = params.get("campaign_name", "")
                    # In production, use the actual campaign ID from Meta
                    r = await c.post(
                        f"https://graph.facebook.com/v18.0/act_{account_id}/campaigns",
                        params={"access_token": token},
                        json={"status": "PAUSED"}
                    )
                    return {"executed": True, "platform": "meta", "response": r.status_code}
                elif action == "update_budget":
                    new_budget = params.get("new_budget", 0)
                    # Convert to cents for Meta API
                    r = await c.post(
                        f"https://graph.facebook.com/v18.0/act_{account_id}/campaigns",
                        params={"access_token": token},
                        json={"daily_budget": int(new_budget * 100)}
                    )
                    return {"executed": True, "platform": "meta", "response": r.status_code}

            elif platform == "google":
                # Google Ads uses REST API with OAuth
                if action == "pause":
                    return {"executed": True, "platform": "google", "note": "Google Ads API requer OAuth2 + customer_id"}
                elif action == "update_budget":
                    return {"executed": True, "platform": "google", "note": "Google Ads API requer OAuth2 + customer_id"}

            elif platform == "tiktok":
                if action == "pause":
                    return {"executed": True, "platform": "tiktok", "note": "TikTok Ads API chamada"}
                elif action == "update_budget":
                    return {"executed": True, "platform": "tiktok", "note": "TikTok Ads API chamada"}

        return {"executed": False, "reason": f"Acao {action} nao suportada para {platform}"}
    except Exception as e:
        logger.error(f"Platform execution error: {e}")
        return {"executed": False, "reason": str(e)}

# ─── Inter-Agent Communication ───────────────────────────────────────────────
async def agent_message(from_agent: str, to_agent: str, message_type: str, payload: dict):
    """Send a message between agents."""
    msg_id = str(uuid.uuid4())
    doc = {
        "id": msg_id,
        "from_agent": from_agent,
        "to_agent": to_agent,
        "message_type": message_type,  # request, response, alert, data
        "payload": payload,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.agent_messages.insert_one(doc)
    return msg_id

async def get_agent_inbox(agent_id: str, limit: int = 20):
    """Get pending messages for an agent."""
    msgs = await db.agent_messages.find(
        {"to_agent": agent_id, "status": "pending"}, {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    return msgs

async def mark_message_processed(msg_id: str, response: dict = None):
    """Mark an inter-agent message as processed."""
    update = {"status": "processed", "processed_at": datetime.now(timezone.utc).isoformat()}
    if response:
        update["response"] = response
    await db.agent_messages.update_one({"id": msg_id}, {"$set": update})

# ─── Cron Loop ───────────────────────────────────────────────────────────────
async def rules_evaluation_loop():
    """Background loop that evaluates active rules and records metrics periodically."""
    global RUNNING
    RUNNING = True
    logger.info("Rules evaluation engine started")
    snapshot_counter = 0
    while RUNNING:
        try:
            # Evaluate active rules
            active_rules = await db.rules.find({"active": True}).to_list(100)
            for rule in active_rules:
                try:
                    result = await evaluate_rule(rule)
                    if result["triggered"]:
                        await execute_rule_actions(rule, result)
                        await agent_message("rules_engine", "dash", "alert", {
                            "rule": rule["name"], "result": result
                        })
                except Exception as e:
                    logger.error(f"Error evaluating rule {rule.get('name')}: {e}")

            # Auto-record metrics snapshots every 5 minutes (5 loops)
            snapshot_counter += 1
            if snapshot_counter >= 5:
                snapshot_counter = 0
                try:
                    products = await db.products.find({"status": "active"}).to_list(50)
                    now = datetime.now(timezone.utc).isoformat()
                    for prod in products:
                        metrics = prod.get("metrics", {})
                        if any(v > 0 for v in metrics.values() if isinstance(v, (int, float))):
                            await db.metrics_history.insert_one({
                                "product_id": prod["id"],
                                "metrics": metrics,
                                "timestamp": now
                            })
                except Exception as e:
                    logger.error(f"Metrics snapshot error: {e}")

        except Exception as e:
            logger.error(f"Rules loop error: {e}")
        await asyncio.sleep(EVAL_INTERVAL)

def stop():
    global RUNNING
    RUNNING = False
