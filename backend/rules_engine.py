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
    """Execute a single action."""
    action_type = action.get("type", "")
    now = datetime.now(timezone.utc).isoformat()

    if action_type == "pause_campaign":
        campaign_id = rule.get("campaign_id")
        if campaign_id:
            await db.campaigns.update_one({"id": campaign_id}, {"$set": {"status": "paused"}})
    elif action_type == "scale_budget":
        factor = action.get("params", {}).get("factor", 1.2)
        campaign_id = rule.get("campaign_id")
        if campaign_id:
            camp = await db.campaigns.find_one({"id": campaign_id})
            if camp:
                new_budget = camp.get("daily_budget", 0) * factor
                await db.campaigns.update_one({"id": campaign_id}, {"$set": {"daily_budget": new_budget}})
    elif action_type == "reduce_budget":
        factor = action.get("params", {}).get("factor", 0.5)
        campaign_id = rule.get("campaign_id")
        if campaign_id:
            camp = await db.campaigns.find_one({"id": campaign_id})
            if camp:
                new_budget = camp.get("daily_budget", 0) * factor
                await db.campaigns.update_one({"id": campaign_id}, {"$set": {"daily_budget": new_budget}})
    elif action_type == "alert":
        pass  # TODO: Send telegram notification
    elif action_type == "create_report":
        pass  # TODO: Generate report via ECHO agent

    # Log execution
    await db.execution_log.insert_one({
        "id": str(uuid.uuid4()),
        "rule_id": rule["id"],
        "action": action,
        "result": eval_result,
        "executed_at": now
    })

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
    """Background loop that evaluates active rules periodically."""
    global RUNNING
    RUNNING = True
    logger.info("Rules evaluation engine started")
    while RUNNING:
        try:
            active_rules = await db.rules.find({"active": True}).to_list(100)
            for rule in active_rules:
                try:
                    result = await evaluate_rule(rule)
                    if result["triggered"]:
                        await execute_rule_actions(rule, result)
                        # Inter-agent: notify DASH about triggered rule
                        await agent_message("rules_engine", "dash", "alert", {
                            "rule": rule["name"], "result": result
                        })
                except Exception as e:
                    logger.error(f"Error evaluating rule {rule.get('name')}: {e}")
        except Exception as e:
            logger.error(f"Rules loop error: {e}")
        await asyncio.sleep(EVAL_INTERVAL)

def stop():
    global RUNNING
    RUNNING = False
