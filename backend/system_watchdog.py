"""
System Watchdog — FASE 6 P2 Roadmap.
Monitora serviços críticos (MongoDB, Ollama, Disk, RAM) a cada N segundos.
Registra alertas em `system_alerts` collection e, se configurado, tenta reiniciar serviços.
"""
import asyncio
import logging
import os
import shutil
from datetime import datetime, timezone
import httpx

logger = logging.getLogger(__name__)

db = None
_task = None
_stop_event = None

CHECK_INTERVAL = int(os.environ.get("WATCHDOG_INTERVAL", "60"))  # segundos
DISK_THRESHOLD = int(os.environ.get("WATCHDOG_DISK_PCT", "90"))
RAM_THRESHOLD = int(os.environ.get("WATCHDOG_RAM_PCT", "92"))


async def _log_alert(kind: str, severity: str, message: str, details: dict = None):
    doc = {
        "kind": kind, "severity": severity, "message": message,
        "details": details or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.system_alerts.insert_one(doc)
    logger.warning(f"[WATCHDOG {severity}] {kind}: {message}")


async def _check_mongo():
    try:
        await db.command("ping")
        return True
    except Exception as e:
        await _log_alert("mongo", "critical", f"MongoDB não responde: {e}")
        return False


async def _check_ollama():
    url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get(f"{url}/api/tags")
            if r.status_code == 200:
                return True
            await _log_alert("ollama", "warning", f"Ollama status {r.status_code}")
            return False
    except Exception as e:
        await _log_alert("ollama", "warning", f"Ollama indisponível: {str(e)[:100]}")
        return False


async def _check_disk():
    try:
        d = shutil.disk_usage("/")
        pct = d.used / d.total * 100
        if pct >= DISK_THRESHOLD:
            await _log_alert("disk", "critical", f"Disco {pct:.1f}% cheio (limite {DISK_THRESHOLD}%)",
                             {"used_gb": round(d.used / 1e9, 1), "total_gb": round(d.total / 1e9, 1)})
            return False
        return True
    except Exception as e:
        logger.error(f"disk check: {e}")
        return True


async def _check_ram():
    try:
        with open("/proc/meminfo") as f:
            meminfo = f.read()
        total = int([ln for ln in meminfo.split("\n") if "MemTotal" in ln][0].split()[1])
        avail = int([ln for ln in meminfo.split("\n") if "MemAvailable" in ln][0].split()[1])
        used_pct = (total - avail) / total * 100
        if used_pct >= RAM_THRESHOLD:
            await _log_alert("ram", "warning", f"RAM {used_pct:.1f}% em uso (limite {RAM_THRESHOLD}%)",
                             {"used_mb": (total - avail) // 1024, "total_mb": total // 1024})
            return False
        return True
    except Exception:
        return True


async def _watchdog_loop():
    while not _stop_event.is_set():
        try:
            await _check_mongo()
            await _check_ollama()
            await _check_disk()
            await _check_ram()
        except Exception as e:
            logger.error(f"watchdog loop: {e}")
        try:
            await asyncio.wait_for(_stop_event.wait(), timeout=CHECK_INTERVAL)
        except asyncio.TimeoutError:
            pass


def start(db_ref):
    global db, _task, _stop_event
    db = db_ref
    _stop_event = asyncio.Event()
    _task = asyncio.create_task(_watchdog_loop())
    logger.info(f"System Watchdog iniciado (interval={CHECK_INTERVAL}s)")


async def stop():
    if _stop_event:
        _stop_event.set()
    if _task:
        try:
            await asyncio.wait_for(_task, timeout=3)
        except asyncio.TimeoutError:
            _task.cancel()


async def get_alerts(limit: int = 50):
    alerts = await db.system_alerts.find({}, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    return alerts
