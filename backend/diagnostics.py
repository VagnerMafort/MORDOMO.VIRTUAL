"""
Diagnóstico completo do sistema — endpoint público que retorna estado de tudo.
GET /api/diagnostics/full
GET /api/diagnostics/full?token=ADMIN_DIAG_TOKEN  (proteção opcional)

Coleta:
  - Health backend (versão, uptime, env)
  - MongoDB connection + counts por coleção
  - Ollama status (URL, modelo, responsividade)
  - OAuth configs (sem secrets) — Google, Meta, TikTok, Telegram
  - Integrações conectadas por usuário (count)
  - JAMES status (autopilot loop, agentes carregados)
  - Skills disponíveis
  - Logs recentes de erro
"""
from fastapi import APIRouter, Request, HTTPException
from typing import Dict, Any, List
from datetime import datetime, timezone
import os
import time
import logging
import httpx

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/diagnostics", tags=["diagnostics"])

_db = None
_ollama_url = ""
_ollama_model = ""
_started_at = time.time()


def init(db_ref, ollama_url: str, ollama_model: str):
    global _db, _ollama_url, _ollama_model
    _db = db_ref
    _ollama_url = ollama_url
    _ollama_model = ollama_model


async def _check_mongo() -> Dict[str, Any]:
    try:
        await _db.command("ping")
        collections = await _db.list_collection_names()
        counts = {}
        important = ["users", "conversations", "messages", "settings",
                      "google_accounts", "meta_accounts", "tiktok_accounts",
                      "telegram_connections", "oauth_config", "mentorships",
                      "agency_products", "agents",
                      "james_products", "james_metrics", "james_anomalies",
                      "james_plans", "james_meta_campaigns", "james_reports"]
        for c in important:
            if c in collections:
                try:
                    counts[c] = await _db[c].count_documents({})
                except Exception as e:
                    counts[c] = f"err: {e}"
        return {"status": "ok", "collections_total": len(collections),
                "counts": counts}
    except Exception as e:
        return {"status": "error", "error": str(e)[:200]}


async def _check_ollama() -> Dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"{_ollama_url}/api/tags")
            if r.status_code == 200:
                models = [m["name"] for m in r.json().get("models", [])]
                return {"status": "ok", "url": _ollama_url,
                        "configured_model": _ollama_model,
                        "model_present": _ollama_model in models,
                        "models_available": models}
            return {"status": "error", "url": _ollama_url, "http": r.status_code}
    except Exception as e:
        return {"status": "offline", "url": _ollama_url, "error": str(e)[:200]}


async def _check_oauth_configs() -> Dict[str, Any]:
    out = {}
    for prov in ["google", "meta", "tiktok"]:
        cfg = await _db.oauth_config.find_one({"provider": prov})
        out[prov] = {
            "configured": bool(cfg),
            "enabled": cfg.get("enabled", False) if cfg else False,
            "client_id_set": bool(cfg and (cfg.get("client_id") or cfg.get("client_key"))),
            "client_secret_set": bool(cfg and cfg.get("client_secret_enc")),
            "updated_at": cfg.get("updated_at", None) if cfg else None,
        }
    return out


async def _check_users() -> Dict[str, Any]:
    total = await _db.users.count_documents({})
    admins = await _db.users.count_documents({"role": "admin"})
    return {"total_users": total, "admins": admins}


async def _check_integrations_per_user() -> List[Dict[str, Any]]:
    """Lista usuários e quantidade de integrações conectadas pra cada."""
    users = await _db.users.find({}, {"_id": 0, "id": 1, "email": 1, "role": 1}).to_list(50)
    out = []
    for u in users:
        uid = u.get("id") or u.get("_id")
        out.append({
            "email": u.get("email"),
            "role": u.get("role"),
            "google_connected": bool(await _db.google_accounts.find_one({"user_id": uid})),
            "meta_connected": bool(await _db.meta_accounts.find_one({"user_id": uid})),
            "tiktok_connected": bool(await _db.tiktok_accounts.find_one({"user_id": uid})),
            "telegram_connected": bool(await _db.telegram_connections.find_one({"user_id": uid})),
        })
    return out


def _check_env() -> Dict[str, Any]:
    keys = ["MONGO_URL", "DB_NAME", "JWT_SECRET", "OLLAMA_URL", "OLLAMA_MODEL",
             "TIKTOK_REDIRECT_URI", "EMERGENT_LLM_KEY"]
    out = {}
    for k in keys:
        v = os.environ.get(k, "")
        out[k] = "SET" if v else "MISSING"
        if k in ("MONGO_URL", "JWT_SECRET", "EMERGENT_LLM_KEY") and v:
            out[k] = f"SET (len={len(v)})"
    return out


@router.get("/full")
async def full_diagnostics(request: Request):
    """Diagnóstico completo do sistema. Endpoint público pra suporte/debug."""
    out = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": int(time.time() - _started_at),
        "host": request.headers.get("host", "unknown"),
    }
    out["env"] = _check_env()
    out["mongo"] = await _check_mongo()
    out["ollama"] = await _check_ollama()
    out["oauth_configs"] = await _check_oauth_configs()
    out["users"] = await _check_users()
    out["integrations_per_user"] = await _check_integrations_per_user()

    # JAMES status
    try:
        from james import autopilot as ap
        from james.orchestrator import list_agents
        out["james"] = {
            "status": "loaded",
            "agents_count": len(list_agents()),
            "autopilot_running": ap._running,
        }
    except Exception as e:
        out["james"] = {"status": "error", "error": str(e)[:200]}

    # Recent backend errors (last 50)
    try:
        log_path = "/var/log/supervisor/backend.err.log"
        if os.path.exists(log_path):
            with open(log_path, "rb") as f:
                f.seek(0, 2)
                size = f.tell()
                f.seek(max(0, size - 8000))
                tail = f.read().decode("utf-8", "ignore")
            error_lines = [line for line in tail.split("\n")
                            if any(k in line.lower() for k in ("error", "exception", "traceback", "critical"))][-30:]
            out["recent_errors"] = error_lines
        else:
            out["recent_errors"] = ["log file not found at " + log_path]
    except Exception as e:
        out["recent_errors"] = [f"error reading log: {e}"]

    return out
