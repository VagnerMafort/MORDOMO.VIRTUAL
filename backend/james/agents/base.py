"""
Classe base para os 24 agentes do JAMES AGENCY.
Cada agente tem: code, name, squad, phase, role, skills, system_prompt.
Pode pensar (via LLM) e propor Plans executáveis.
"""
from typing import List, Dict, Any, Optional
import logging
import httpx
import json
import os

from ..models import Plan, PlanStep, Anomaly, _id, _now

logger = logging.getLogger(__name__)


class BaseAgent:
    code: str = "BASE"
    name: str = "Base Agent"
    squad: str = "SQUAD 0"
    phase: str = "FASE 0"
    role: str = ""
    skills: List[str] = []

    def __init__(self, ollama_url: str, model: str):
        self.ollama_url = ollama_url
        self.model = model

    # ── Cada agente define seu SYSTEM_PROMPT ──
    SYSTEM_PROMPT = """Você é um agente genérico. Substitua esta classe."""

    def as_info(self) -> Dict[str, Any]:
        return {
            "code": self.code, "name": self.name, "squad": self.squad,
            "phase": self.phase, "role": self.role, "skills": self.skills,
        }

    async def think(self, user_prompt: str, temperature: float = 0.3) -> str:
        """Chama o Ollama local com system_prompt + user_prompt."""
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {"temperature": temperature, "num_ctx": 4096},
        }
        try:
            async with httpx.AsyncClient(timeout=120) as c:
                r = await c.post(f"{self.ollama_url}/api/chat", json=payload)
                d = r.json()
                return d.get("message", {}).get("content", "")
        except Exception as e:
            logger.warning(f"Ollama indisponível para {self.code}: {e}")
            return ""  # agentes devolvem plano heurístico sem LLM quando offline

    async def plan(self, anomaly: Optional[Anomaly], product_id: str,
                   context: Dict[str, Any]) -> Plan:
        """Cada agente implementa sua lógica de geração de plano.
        Default: plano vazio; subclasses sobrescrevem."""
        return Plan(
            product_id=product_id,
            anomaly_id=anomaly.id if anomaly else None,
            agent=self.code, skill="noop",
            objective=f"{self.code} no-op",
            steps=[],
        )

    @staticmethod
    def parse_json_from_llm(text: str) -> Optional[Dict[str, Any]]:
        """Extrai primeiro bloco JSON da resposta do LLM."""
        if not text:
            return None
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            return json.loads(text[start:end + 1])
        except Exception:
            return None
