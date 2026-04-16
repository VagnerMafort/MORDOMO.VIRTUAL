"""
Smart LLM Router - Dual model, cache, background queue, conversation memory
"""
import asyncio
import hashlib
import json
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

db = None
OLLAMA_URL = ""
MODEL_FAST = "qwen2.5:7b"
MODEL_SMART = "qwen2.5:32b"

def init(database, ollama_url, model_fast, model_smart):
    global db, OLLAMA_URL, MODEL_FAST, MODEL_SMART
    db = database
    OLLAMA_URL = ollama_url
    MODEL_FAST = model_fast
    MODEL_SMART = model_smart

# ─── Task Complexity Detection ───────────────────────────────────────────────
COMPLEX_KEYWORDS = [
    "mentoria", "relatorio", "analise completa", "crie um projeto", "landing page",
    "plano completo", "estrategia", "pesquise", "analise detalhada", "crie uma",
    "gere um", "monte um", "desenvolva", "elabore", "planeje", "modulos",
    "campanha completa", "funil", "copy de vendas", "precificacao",
    "codigo completo", "script completo", "automatize", "dashboard",
]

SIMPLE_PATTERNS = [
    r"^(oi|ola|hey|bom dia|boa tarde|boa noite)",
    r"^(sim|nao|ok|entendi|obrigado|valeu)",
    r"^(o que e|quem e|quando|onde|como se)",
    r"que horas",
    r"quanto e|calcul",
]

def detect_complexity(message: str) -> str:
    """Detect if a message needs the smart or fast model."""
    msg_lower = message.lower().strip()

    # Simple patterns → fast
    for pattern in SIMPLE_PATTERNS:
        if re.search(pattern, msg_lower):
            return "fast"

    # Complex keywords → smart
    for kw in COMPLEX_KEYWORDS:
        if kw in msg_lower:
            return "smart"

    # Length heuristic: long messages tend to be complex
    if len(message) > 300:
        return "smart"

    # Default: fast for efficiency
    return "fast"

def get_model_for_task(message: str, user_settings: dict = None) -> tuple:
    """Return (model_name, ollama_url) based on task complexity."""
    complexity = detect_complexity(message)

    if user_settings:
        ollama_url = user_settings.get("ollama_url", OLLAMA_URL)
        model_fast = user_settings.get("ollama_model_fast", MODEL_FAST)
        model_smart = user_settings.get("ollama_model_smart", MODEL_SMART)
    else:
        ollama_url = OLLAMA_URL
        model_fast = MODEL_FAST
        model_smart = MODEL_SMART

    model = model_smart if complexity == "smart" else model_fast
    return model, ollama_url, complexity

# ─── Response Cache ──────────────────────────────────────────────────────────
def cache_key(message: str, context_hash: str = "") -> str:
    """Generate cache key from message + context."""
    raw = f"{message.strip().lower()[:200]}|{context_hash}"
    return hashlib.sha256(raw.encode()).hexdigest()

async def get_cached_response(message: str, context_hash: str = "") -> Optional[str]:
    """Check cache for a similar response."""
    key = cache_key(message, context_hash)
    cached = await db.response_cache.find_one({"key": key})
    if cached:
        # Check TTL (1 hour for simple, 24h for complex)
        created = datetime.fromisoformat(cached["created_at"])
        ttl_hours = cached.get("ttl_hours", 1)
        if datetime.now(timezone.utc) - created < timedelta(hours=ttl_hours):
            logger.info(f"Cache HIT: {message[:50]}...")
            return cached["response"]
        else:
            await db.response_cache.delete_one({"key": key})
    return None

async def set_cached_response(message: str, response: str, context_hash: str = "", complexity: str = "fast"):
    """Store response in cache."""
    key = cache_key(message, context_hash)
    ttl = 24 if complexity == "smart" else 1
    await db.response_cache.update_one(
        {"key": key},
        {"$set": {
            "key": key, "message": message[:200], "response": response,
            "ttl_hours": ttl, "complexity": complexity,
            "created_at": datetime.now(timezone.utc).isoformat()
        }},
        upsert=True
    )

# ─── Conversation Memory System ─────────────────────────────────────────────
async def build_memory_context(conversation_id: str, user_message: str, user_id: str) -> list:
    """Build context with smart memory management.
    
    Rules:
    - Last 6 messages always included (recent context)
    - Every 5 messages, generate a summary and store it
    - For old topics, search history and inject relevant messages
    """
    messages_context = []

    # 1. Get conversation summary (if exists)
    summary = await db.conversation_summaries.find_one(
        {"conversation_id": conversation_id}, {"_id": 0}
    )
    if summary and summary.get("summary"):
        messages_context.append({
            "role": "system",
            "content": f"[Resumo da conversa ate agora]: {summary['summary']}"
        })

    # 2. Get last 6 messages (recent context)
    recent = await db.messages.find(
        {"conversation_id": conversation_id}, {"_id": 0}
    ).sort("created_at", -1).limit(6).to_list(6)
    recent.reverse()

    # 3. Search for relevant old messages if topic seems to reference past
    old_topic_triggers = ["lembra", "falamos", "antes", "anterior", "voltando", "sobre aquilo", "como eu disse"]
    needs_old_context = any(t in user_message.lower() for t in old_topic_triggers)

    if needs_old_context:
        # Extract keywords from user message
        keywords = extract_keywords(user_message)
        if keywords:
            # Search older messages matching keywords
            search_filter = {
                "conversation_id": conversation_id,
                "$or": [{"content": {"$regex": kw, "$options": "i"}} for kw in keywords[:5]]
            }
            old_msgs = await db.messages.find(
                search_filter, {"_id": 0}
            ).sort("created_at", -1).limit(5).to_list(5)
            old_msgs.reverse()

            if old_msgs:
                context_text = "\n".join([f"[{m['role']}]: {m['content'][:200]}" for m in old_msgs])
                messages_context.append({
                    "role": "system",
                    "content": f"[Contexto relevante de mensagens anteriores]:\n{context_text}"
                })

    # 4. Also search across ALL user conversations for relevant knowledge
    if needs_old_context:
        keywords = extract_keywords(user_message)
        if keywords:
            cross_filter = {
                "$or": [{"content": {"$regex": kw, "$options": "i"}} for kw in keywords[:3]],
                "conversation_id": {"$ne": conversation_id},
                "role": "assistant"
            }
            # Find conversations belonging to this user
            user_convs = await db.conversations.find({"user_id": user_id}, {"id": 1, "_id": 0}).to_list(50)
            conv_ids = [c["id"] for c in user_convs]
            if conv_ids:
                cross_filter["conversation_id"] = {"$in": conv_ids}
                cross_msgs = await db.messages.find(cross_filter, {"_id": 0}).limit(3).to_list(3)
                if cross_msgs:
                    cross_text = "\n".join([f"{m['content'][:200]}" for m in cross_msgs])
                    messages_context.append({
                        "role": "system",
                        "content": f"[Conhecimento de conversas anteriores do usuario]:\n{cross_text}"
                    })

    # 5. Add recent messages
    for m in recent:
        messages_context.append({"role": m["role"], "content": m["content"]})

    return messages_context

async def maybe_create_summary(conversation_id: str, user_id: str):
    """Every 5 messages, create/update a conversation summary."""
    msg_count = await db.messages.count_documents({"conversation_id": conversation_id})

    if msg_count > 0 and msg_count % 5 == 0:
        # Get all messages for summary
        all_msgs = await db.messages.find(
            {"conversation_id": conversation_id}, {"_id": 0}
        ).sort("created_at", 1).limit(30).to_list(30)

        # Build summary text from messages
        summary_parts = []
        for m in all_msgs:
            prefix = "Usuario" if m["role"] == "user" else "Assistente"
            summary_parts.append(f"{prefix}: {m['content'][:150]}")

        summary_text = "\n".join(summary_parts[-15:])  # Last 15 messages

        # Store summary
        await db.conversation_summaries.update_one(
            {"conversation_id": conversation_id},
            {"$set": {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "summary": f"Resumo da conversa ({msg_count} mensagens): " + summary_text[:2000],
                "message_count": msg_count,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }},
            upsert=True
        )
        logger.info(f"Summary updated for conversation {conversation_id} ({msg_count} msgs)")

def extract_keywords(text: str) -> list:
    """Extract meaningful keywords from text for search."""
    stop_words = {"o", "a", "os", "as", "um", "uma", "de", "da", "do", "das", "dos",
                  "em", "no", "na", "nos", "nas", "por", "para", "com", "sem", "que",
                  "e", "ou", "mas", "se", "como", "eu", "voce", "ele", "ela", "nos",
                  "eles", "isso", "isto", "aquilo", "me", "te", "se", "lhe", "nos",
                  "sobre", "ate", "mais", "muito", "bem", "mal", "ja", "ainda", "so",
                  "nao", "sim", "pode", "tem", "ter", "ser", "estar", "fazer", "ir"}
    words = re.findall(r'\b[a-zA-Zà-ú]{3,}\b', text.lower())
    keywords = [w for w in words if w not in stop_words]
    # Return unique keywords, most important first
    seen = set()
    result = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            result.append(kw)
    return result[:10]

# ─── Background Task Queue ──────────────────────────────────────────────────
task_queue = asyncio.Queue()
task_results = {}  # task_id -> {status, result}

async def add_task(task_id: str, task_type: str, payload: dict):
    """Add a heavy task to the background queue."""
    task_results[task_id] = {"status": "queued", "type": task_type, "created_at": datetime.now(timezone.utc).isoformat()}
    await task_queue.put({"id": task_id, "type": task_type, "payload": payload})
    # Also store in DB for persistence
    await db.background_tasks.insert_one({
        "id": task_id, "type": task_type, "status": "queued",
        "payload": {k: str(v)[:500] for k, v in payload.items()},
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    return task_id

def get_task_status(task_id: str) -> dict:
    return task_results.get(task_id, {"status": "not_found"})

async def background_worker():
    """Process heavy tasks in background."""
    logger.info("Background task worker started")
    while True:
        try:
            task = await task_queue.get()
            task_id = task["id"]
            task_results[task_id] = {"status": "processing", "type": task["type"]}

            try:
                # Process based on type
                if task["type"] == "generate_mentorship":
                    # Heavy LLM task - runs in background
                    result = await task["payload"]["callback"]()
                    task_results[task_id] = {"status": "completed", "result": result}
                elif task["type"] == "generate_report":
                    result = await task["payload"]["callback"]()
                    task_results[task_id] = {"status": "completed", "result": result}
                else:
                    task_results[task_id] = {"status": "completed", "result": "Unknown task type"}

                await db.background_tasks.update_one(
                    {"id": task_id},
                    {"$set": {"status": "completed", "completed_at": datetime.now(timezone.utc).isoformat()}}
                )
            except Exception as e:
                logger.error(f"Task {task_id} failed: {e}")
                task_results[task_id] = {"status": "failed", "error": str(e)}
                await db.background_tasks.update_one(
                    {"id": task_id},
                    {"$set": {"status": "failed", "error": str(e)}}
                )

            task_queue.task_done()
        except Exception as e:
            logger.error(f"Worker error: {e}")
            await asyncio.sleep(1)
