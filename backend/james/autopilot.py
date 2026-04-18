"""
JAMES Autopilot — loop 24/7 que roda ticks automáticos por produto.

Estratégia:
  - A cada 60s varremos produtos com autopilot_enabled=True
  - Se `last_autopilot_tick` for mais velho que `autopilot_interval_min`, roda tick
  - Planos com risk_level <= auto_approve_risk são aprovados e executados automaticamente
  - Planos mais arriscados ficam na inbox (status=validated) aguardando aprovação manual
  - Uma vez por dia (daily_report_hour UTC), ECHO gera relatório e envia via Telegram

Design: worker leve (asyncio.create_task) iniciado no server startup.
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from . import orchestrator

logger = logging.getLogger(__name__)

_db = None
_loop_task: Optional[asyncio.Task] = None
_running = False
RISK_RANK = {"none": 0, "low": 1, "medium": 2, "high": 3, "all": 4}


def init(db_ref):
    global _db
    _db = db_ref


async def _send_telegram_message(user_id: str, text: str):
    """Usa a integração Telegram existente do usuário pra enviar mensagem."""
    try:
        conn = await _db.telegram_connections.find_one({"user_id": user_id})
        if not conn or not conn.get("bot_token") or not conn.get("chat_id"):
            return False
        import httpx
        async with httpx.AsyncClient(timeout=10) as c:
            await c.post(
                f"https://api.telegram.org/bot{conn['bot_token']}/sendMessage",
                json={"chat_id": conn["chat_id"], "text": text[:4000],
                      "parse_mode": "Markdown"}
            )
        return True
    except Exception as e:
        logger.warning(f"Telegram send failed: {e}")
        return False


async def _run_product_tick(product: dict):
    """Roda 1 tick no produto e opcionalmente auto-aprova planos."""
    pid = product["id"]
    user_id = product["user_id"]
    auto_thresh = RISK_RANK.get(product.get("auto_approve_risk", "low"), 1)

    try:
        r = await orchestrator.tick(pid, evaluate=False)
    except Exception as e:
        logger.error(f"Autopilot tick failed for {pid}: {e}")
        return

    # Auto-aprovar planos dentro do risco tolerado
    auto_executed = []
    blocked_for_review = []
    for p in r.get("plans_created", []):
        if p.get("status") != "validated":
            continue
        plan_doc = await _db.james_plans.find_one({"id": p["plan_id"]}, {"_id": 0})
        if not plan_doc:
            continue
        risk = plan_doc.get("risk_level", "low")
        if RISK_RANK.get(risk, 3) <= auto_thresh:
            try:
                result = await orchestrator.run_plan(p["plan_id"])
                auto_executed.append({
                    "agent": p["agent"],
                    "objective": p["objective"],
                    "status": result.get("execution", {}).get("status"),
                    "evaluation": result.get("evaluation", {}).get("result"),
                })
            except Exception as e:
                logger.warning(f"Auto-run failed {p['plan_id']}: {e}")
        else:
            blocked_for_review.append(p)

    # Mongo: atualizar last_autopilot_tick
    await _db.james_products.update_one(
        {"id": pid},
        {"$set": {"last_autopilot_tick": datetime.now(timezone.utc).isoformat()}},
    )

    # Notificar usuário via Telegram se houver planos para revisar OU ações autoexecutadas
    if auto_executed or blocked_for_review:
        lines = [f"🤖 *JAMES Autopilot — {product['name']}*"]
        if auto_executed:
            lines.append(f"\n✅ *{len(auto_executed)} ações executadas automaticamente:*")
            for a in auto_executed[:5]:
                icon = "✅" if a["status"] == "success" else "⚠️"
                lines.append(f"  {icon} [{a['agent']}] {a['objective']}")
        if blocked_for_review:
            lines.append(f"\n⏸ *{len(blocked_for_review)} planos aguardando sua aprovação:*")
            for p in blocked_for_review[:5]:
                lines.append(f"  • [{p['agent']}] {p['objective']}")
            lines.append("\n_Abra o painel JAMES → Planos para revisar._")
        await _send_telegram_message(user_id, "\n".join(lines))


async def _maybe_send_daily_report(product: dict):
    """Envia relatório ECHO 1x/dia no horário configurado."""
    if not product.get("daily_report_enabled"):
        return
    hour = int(product.get("daily_report_hour", 9))
    now = datetime.now(timezone.utc)
    if now.hour != hour:
        return
    # dedupe: se já enviou hoje, skip
    last = product.get("last_autopilot_report")
    if last:
        try:
            last_dt = datetime.fromisoformat(last)
            if last_dt.date() == now.date():
                return
        except Exception:
            pass
    try:
        report = await orchestrator.generate_report(
            product["id"], level="product", period_hours=24,
        )
        await _send_telegram_message(
            product["user_id"],
            f"📊 *Relatório diário JAMES — {product['name']}*\n\n{report.narrative}",
        )
        await _db.james_products.update_one(
            {"id": product["id"]},
            {"$set": {"last_autopilot_report": now.isoformat()}},
        )
    except Exception as e:
        logger.warning(f"Daily report failed for {product['id']}: {e}")


async def _loop():
    global _running
    _running = True
    logger.info("JAMES Autopilot loop iniciado (check a cada 60s)")
    while _running:
        try:
            cursor = _db.james_products.find(
                {"autopilot_enabled": True, "status": "active"},
                {"_id": 0},
            )
            products = await cursor.to_list(500)
            now = datetime.now(timezone.utc)
            for p in products:
                # Tick na frequência configurada
                interval = timedelta(minutes=int(p.get("autopilot_interval_min", 30)))
                last_tick = p.get("last_autopilot_tick")
                should_tick = True
                if last_tick:
                    try:
                        last_dt = datetime.fromisoformat(last_tick)
                        if now - last_dt < interval:
                            should_tick = False
                    except Exception:
                        pass
                if should_tick:
                    await _run_product_tick(p)
                # Relatório diário
                await _maybe_send_daily_report(p)
        except Exception as e:
            logger.error(f"Autopilot loop error: {e}")
        await asyncio.sleep(60)


def start(db_ref):
    """Inicia loop em background. Chame no startup do server."""
    global _loop_task
    init(db_ref)
    if _loop_task and not _loop_task.done():
        return
    _loop_task = asyncio.create_task(_loop())


def stop():
    global _running
    _running = False
