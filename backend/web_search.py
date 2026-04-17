"""
Web Search Skill - busca em tempo real na internet.
Usa DuckDuckGo HTML (sem API key, grátis) + Brave Search como fallback opcional.
"""
import os
import re
import asyncio
import logging
from typing import List, Dict
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BRAVE_API_KEY = os.environ.get("BRAVE_SEARCH_API_KEY", "")
MAX_RESULTS = 5
TIMEOUT = 10.0


async def search_duckduckgo(query: str, max_results: int = MAX_RESULTS) -> List[Dict]:
    """Busca usando DuckDuckGo HTML (sem API key)."""
    url = "https://html.duckduckgo.com/html/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as c:
            r = await c.post(url, headers=headers, data={"q": query, "kl": "br-pt"})
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            results = []
            for item in soup.select(".result")[:max_results]:
                title_el = item.select_one(".result__title a")
                snippet_el = item.select_one(".result__snippet")
                url_el = item.select_one(".result__url")
                if not title_el:
                    continue
                results.append({
                    "title": title_el.get_text(strip=True),
                    "url": title_el.get("href", ""),
                    "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
                    "source": url_el.get_text(strip=True) if url_el else "",
                })
            return results
    except Exception as e:
        logger.warning(f"DuckDuckGo search falhou: {e}")
        return []


async def search_brave(query: str, max_results: int = MAX_RESULTS) -> List[Dict]:
    """Busca usando Brave Search API (se BRAVE_SEARCH_API_KEY estiver definido)."""
    if not BRAVE_API_KEY:
        return []
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {"X-Subscription-Token": BRAVE_API_KEY, "Accept": "application/json"}
    params = {"q": query, "count": max_results, "country": "BR", "search_lang": "pt"}
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as c:
            r = await c.get(url, headers=headers, params=params)
            r.raise_for_status()
            data = r.json()
            results = []
            for item in data.get("web", {}).get("results", [])[:max_results]:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("description", ""),
                    "source": item.get("url", "").split("/")[2] if item.get("url") else "",
                })
            return results
    except Exception as e:
        logger.warning(f"Brave search falhou: {e}")
        return []


async def web_search(query: str, max_results: int = MAX_RESULTS) -> List[Dict]:
    """Busca unificada com fallback entre providers."""
    query = (query or "").strip()
    if not query:
        return []

    # Tenta Brave primeiro (mais confiavel) se tiver key
    if BRAVE_API_KEY:
        results = await search_brave(query, max_results)
        if results:
            return results

    # Fallback/default: DuckDuckGo
    return await search_duckduckgo(query, max_results)


async def fetch_page_summary(url: str, max_chars: int = 3000) -> str:
    """Busca conteúdo de uma URL e extrai texto limpo."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as c:
            r = await c.get(url, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            # Remove script/style/nav
            for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)
            # Normalize whitespace
            text = re.sub(r"\n{3,}", "\n\n", text)
            text = re.sub(r"[ \t]+", " ", text)
            return text[:max_chars]
    except Exception as e:
        logger.warning(f"fetch_page erro {url}: {e}")
        return ""


def format_results_for_llm(results: List[Dict], query: str) -> str:
    """Formata resultados pra o LLM usar como contexto."""
    if not results:
        return f"Busca por '{query}' nao retornou resultados."
    out = [f"Resultados da busca na web por '{query}':\n"]
    for i, r in enumerate(results, 1):
        out.append(f"[{i}] {r['title']}")
        out.append(f"    {r['snippet']}")
        out.append(f"    Fonte: {r.get('source', r.get('url', ''))}")
        out.append("")
    return "\n".join(out)


def needs_web_search(text: str) -> bool:
    """Heuristica simples: detecta se mensagem precisa de info atual."""
    text_lower = text.lower()
    triggers = [
        "hoje", "agora", "ultim", "atual", "recente", "noticia", "cotacao",
        "preco de", "quanto custa", "clima", "tempo em", "temperatura",
        "quem e ", "quem foi", "o que aconteceu", "quando foi", "quando e",
        "pesquis", "procur", "busc", "google", "internet", "site", "link",
        "2025", "2026",
    ]
    return any(t in text_lower for t in triggers)
