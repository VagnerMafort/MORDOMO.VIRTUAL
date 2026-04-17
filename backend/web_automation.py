"""
Web Automation Skill (Playwright) — FASE 5 Roadmap.
Executa sequências de ações em um navegador headless real.

Uso:
    [SKILL:browser_automation] {
      "url": "https://example.com",
      "actions": [
          {"type": "fill", "selector": "#q", "value": "buscar"},
          {"type": "click", "selector": "#submit"},
          {"type": "wait", "ms": 1500},
          {"type": "extract", "selector": ".result", "as": "text"}
      ]
    }

Actions suportadas:
    goto       → {url}
    fill       → {selector, value}
    click      → {selector}
    wait       → {ms}
    wait_for   → {selector}
    press      → {selector, key}          (ex: "Enter")
    extract    → {selector, as}           (as = "text" | "html" | "attr:<name>")
    screenshot → {path?}  retorna base64
    scroll     → {to: "bottom"|"top"|N}

Retorna um relatório texto com cada passo + valores extraídos.
"""
from typing import Dict, Any, List
import base64
import logging
import os

# Garantir que playwright ache os browsers mesmo se o env var não foi propagado pelo supervisor
if not os.environ.get("PLAYWRIGHT_BROWSERS_PATH") and os.path.isdir("/pw-browsers"):
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/pw-browsers"

logger = logging.getLogger(__name__)

# Lazy import — Playwright pesado
_playwright_async = None


async def _ensure_playwright():
    global _playwright_async
    if _playwright_async is None:
        from playwright.async_api import async_playwright
        _playwright_async = async_playwright
    return _playwright_async


async def execute_browser_automation(args: Dict[str, Any], user_id: str = None) -> str:
    url = args.get("url", "").strip()
    actions: List[Dict[str, Any]] = args.get("actions") or []
    if not url and not actions:
        return "Erro: informe 'url' e/ou 'actions'"
    if url and not any(a.get("type") == "goto" for a in actions):
        actions.insert(0, {"type": "goto", "url": url})

    ap_factory = await _ensure_playwright()
    log_lines = []
    extracted = {}
    try:
        async with ap_factory() as p:
            browser = await p.chromium.launch(headless=True, args=[
                "--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"
            ])
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (MordomoVirtual) AppleWebKit/537.36 Chrome/120 Safari/537.36",
                viewport={"width": 1280, "height": 800},
            )
            page = await context.new_page()
            for i, a in enumerate(actions):
                t = a.get("type", "")
                try:
                    if t == "goto":
                        u = a.get("url", "")
                        await page.goto(u, wait_until="domcontentloaded", timeout=20000)
                        log_lines.append(f"{i+1}. goto {u} → {page.url}")
                    elif t == "fill":
                        await page.fill(a["selector"], a.get("value", ""))
                        log_lines.append(f"{i+1}. fill {a['selector']}")
                    elif t == "click":
                        await page.click(a["selector"], timeout=10000)
                        log_lines.append(f"{i+1}. click {a['selector']}")
                    elif t == "press":
                        await page.press(a["selector"], a.get("key", "Enter"))
                        log_lines.append(f"{i+1}. press {a['selector']} ({a.get('key','Enter')})")
                    elif t == "wait":
                        ms = int(a.get("ms", 1000))
                        await page.wait_for_timeout(ms)
                        log_lines.append(f"{i+1}. wait {ms}ms")
                    elif t == "wait_for":
                        await page.wait_for_selector(a["selector"], timeout=15000)
                        log_lines.append(f"{i+1}. wait_for {a['selector']}")
                    elif t == "extract":
                        sel = a["selector"]
                        mode = a.get("as", "text")
                        key = a.get("var", f"extract_{i}")
                        if mode == "text":
                            els = await page.locator(sel).all_text_contents()
                            val = "\n".join(e.strip() for e in els if e.strip())[:3000]
                        elif mode == "html":
                            val = await page.locator(sel).first.inner_html()
                            val = val[:3000]
                        elif mode.startswith("attr:"):
                            attr = mode.split(":", 1)[1]
                            val = await page.locator(sel).first.get_attribute(attr)
                        else:
                            val = ""
                        extracted[key] = val
                        log_lines.append(f"{i+1}. extract {sel} ({mode}) → {str(val)[:120]}")
                    elif t == "screenshot":
                        buf = await page.screenshot(full_page=bool(a.get("full_page", False)))
                        b64 = base64.b64encode(buf).decode()[:4000]
                        extracted[a.get("var", f"screenshot_{i}")] = f"data:image/png;base64,{b64}..."
                        log_lines.append(f"{i+1}. screenshot ({len(buf)} bytes)")
                    elif t == "scroll":
                        target = a.get("to", "bottom")
                        if target == "bottom":
                            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        elif target == "top":
                            await page.evaluate("window.scrollTo(0, 0)")
                        else:
                            await page.evaluate(f"window.scrollTo(0, {int(target)})")
                        log_lines.append(f"{i+1}. scroll {target}")
                    else:
                        log_lines.append(f"{i+1}. [ignorado: type '{t}' desconhecido]")
                except Exception as step_err:
                    log_lines.append(f"{i+1}. ERRO {t}: {str(step_err)[:200]}")
                    # segue tentando as próximas actions
            await browser.close()
    except Exception as e:
        return f"Falha Playwright: {str(e)[:300]}"

    # Monta resultado
    out = "Navegação concluída:\n" + "\n".join(log_lines)
    if extracted:
        out += "\n\n--- Dados extraídos ---\n"
        for k, v in extracted.items():
            out += f"[{k}]:\n{str(v)[:1500]}\n\n"
    return out[:5000]
