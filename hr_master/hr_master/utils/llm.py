"""Reusable LLM helper for HR Master.

Provider-agnostic wrapper around Google Gemini (free tier, recommended),
any OpenAI-compatible endpoint (OpenAI, Groq, DeepSeek) and local Ollama.
Configuration lives in Recruitment Settings → AI Configuration.

Every call fails soft: on any error it logs the issue and returns an empty
string / {} so callers can fall back to rule-based logic without breaking
the pipeline.
"""

from __future__ import unicode_literals

import json

import frappe

DEFAULT_MODELS = {
    "gemini": "gemini-1.5-flash",
    "openai": "gpt-4o-mini",
    "groq": "llama-3.3-70b-versatile",
    "deepseek": "deepseek-chat",
    "ollama": "llama3.2",
}

BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "groq": "https://api.groq.com/openai/v1",
    "deepseek": "https://api.deepseek.com/v1",
}


def get_ai_config():
    """Return the Recruitment Settings singleton holding AI configuration.

    Uses the cached copy to avoid a DB hit on every LLM call (ranking runs
    call this per candidate).
    """
    return frappe.get_cached_doc("Recruitment Settings")


def is_llm_configured():
    """Return True when AI is enabled and the provider is usable.

    Ollama is local and needs no API key; all cloud providers need one.
    """
    cfg = get_ai_config()
    if not getattr(cfg, "ai_enabled", 0):
        return False
    provider = (getattr(cfg, "ai_provider", "") or "").strip().lower()
    if provider == "ollama":
        return True
    return bool((getattr(cfg, "ai_api_key", "") or "").strip())


def _model(cfg):
    """Resolve the model name: explicit override, else provider default."""
    model = (getattr(cfg, "ai_model", "") or "").strip()
    if model:
        return model
    provider = (getattr(cfg, "ai_provider", "") or "").strip().lower()
    return DEFAULT_MODELS.get(provider, DEFAULT_MODELS["gemini"])


def call_llm(prompt, system=None, max_tokens=1024, temperature=0.2):
    """Send a prompt to the configured LLM and return the text reply.

    Returns "" on any failure (unconfigured, network, API error).
    """
    if not is_llm_configured():
        return ""

    cfg = get_ai_config()
    provider = (getattr(cfg, "ai_provider", "") or "").strip().lower()
    api_key = (getattr(cfg, "ai_api_key", "") or "").strip()
    model = _model(cfg)

    try:
        import requests

        # Google Gemini (free tier via AI Studio key)
        if provider == "gemini":
            url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                "{0}:generateContent?key={1}".format(model, api_key)
            )
            payload = {
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {
                    "maxOutputTokens": max_tokens,
                    "temperature": temperature,
                },
            }
            if system:
                payload["systemInstruction"] = {"parts": [{"text": system}]}
            resp = requests.post(url, json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            candidates = data.get("candidates") or []
            if not candidates:
                return ""
            parts = (candidates[0].get("content") or {}).get("parts") or []
            return "".join(p.get("text", "") for p in parts).strip()

        # Local Ollama (no key)
        if provider == "ollama":
            base = (
                (getattr(cfg, "ai_base_url", "") or "").strip().rstrip("/")
                or "http://localhost:11434"
            )
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system or ""},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
                "options": {"num_predict": max_tokens, "temperature": temperature},
            }
            resp = requests.post(base + "/api/chat", json=payload, timeout=120)
            resp.raise_for_status()
            data = resp.json()
            return (data.get("message") or {}).get("content", "").strip()

        # OpenAI-compatible chat completions (OpenAI / Groq / DeepSeek)
        base = (
            (getattr(cfg, "ai_base_url", "") or "").strip().rstrip("/")
            or BASE_URLS.get(provider, BASE_URLS["openai"])
        )
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = "Bearer {0}".format(api_key)
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        resp = requests.post(base + "/chat/completions", json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        choices = data.get("choices") or []
        if not choices:
            return ""
        return (choices[0].get("message") or {}).get("content", "").strip()

    except Exception as e:
        frappe.log_error(
            message="LLM call failed ({0}): {1}".format(provider, str(e)),
            title="HR Master LLM Error",
        )
        return ""


def call_llm_json(prompt, system=None, max_tokens=1024, temperature=0.1):
    """Call the LLM and parse the reply as a JSON object.

    Returns {} on any failure. Tolerates markdown fences and stray prose
    by extracting the outermost {...} block.
    """
    raw = call_llm(prompt, system=system, max_tokens=max_tokens, temperature=temperature)
    if not raw:
        return {}
    try:
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start : end + 1])
        return json.loads(text)
    except Exception:
        return {}
