"""
Dork Optimizer — Configuration & LLM Client.

All settings, API keys, and LLM call logic in one place.
Supports OpenRouter, Groq, and OpenAI seamlessly via standard openai client.
"""

import os
import json
import re
from dotenv import load_dotenv

# Ensure we load from the correct directory (dork_optimizer root)
env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=env_path)

# ── API Keys & Provider ──────────────────────────────────────
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()
NEWSDATA_API_KEY = os.getenv("NEWSDATA_API_KEY", "")

API_KEY = None
BASE_URL = None

if LLM_PROVIDER == "openrouter":
    API_KEY = os.getenv("OPENROUTER_API_KEY")
    BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
elif LLM_PROVIDER == "openai":
    API_KEY = os.getenv("OPENAI_API_KEY")
    BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
elif LLM_PROVIDER == "groq":
    API_KEY = os.getenv("GROQ_API_KEY")
    BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
else:
    # Unsupported provider, API_KEY will remain None.
    pass

# ── Models ──────────────────────────────────────────────────
# Default to llama-3.1-8b-instant if not specified
TREND_MODEL = os.getenv("TREND_MODEL", "llama-3.1-8b-instant")
DORK_MODEL = os.getenv("DORK_MODEL", "llama-3.1-8b-instant")

# Print safe startup logs
print("=== Dork Optimizer LLM Config ===")
print(f"[LLM Config] Provider: {LLM_PROVIDER}")
print(f"[LLM Config] Trend Model: {TREND_MODEL}")
print(f"[LLM Config] Dork Model: {DORK_MODEL}")
print(f"[LLM Config] Base URL: {BASE_URL}")
print(f"[LLM Config] API Key Present: {bool(API_KEY)}")
print("=================================")

# ── Database ────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "dork_optimizer.db")

# ── Demo mode ───────────────────────────────────────────────
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

# ── Source settings ─────────────────────────────────────────
TARGET_COUNTRIES = ["India", "UAE", "Saudi Arabia", "UK", "USA", "Australia", "Canada", "Singapore", "Qatar"]

SECTOR_KEYWORDS = {
    "real estate": ["real estate", "property market", "property investment"],
    "tourism": ["tourism", "hotel booking", "travel industry"],
    "healthcare": ["healthcare", "medical clinic", "dental clinic"],
    "ecommerce": ["ecommerce", "online shopping", "shopify"],
    "ai digital transformation": ["digital transformation", "AI business", "automation"],
    "manufacturing": ["manufacturing", "industrial growth", "factory"],
    "education": ["education technology", "training institute"],
    "b2b services": ["business services", "consulting firm"],
    "wedding events": ["wedding planner", "event organizer"],
}

# 3FI Tech services list
SERVICES_LIST = [
    "Website Development",
    "Website Redesign",
    "Landing Page Development",
    "Local SEO",
    "Google Business Profile Optimization",
    "Booking Website / Booking System",
    "WhatsApp Automation",
    "AI Chatbot",
    "CRM Automation",
    "Lead Generation System",
    "Portfolio Website",
    "Travel/Hotel Package Website",
    "Real Estate Property Website",
    "B2B Product Catalog Website",
    "Shopify SEO",
    "Ecommerce Conversion Optimization",
    "Email Marketing Automation",
]

# ═══════════════════════════════════════════════════════════
# LLM CLIENT
# ═══════════════════════════════════════════════════════════
_client = None

def _get_client():
    """Lazy-init unified OpenAI-compatible client."""
    global _client
    if _client is None:
        if LLM_PROVIDER not in ["openrouter", "openai", "groq"]:
            raise ValueError(f"Unsupported LLM_PROVIDER '{LLM_PROVIDER}'. Supported: openrouter, groq, openai")
        
        if not API_KEY:
            expected_env = f"{LLM_PROVIDER.upper()}_API_KEY"
            raise ValueError(f"{expected_env} not set in .env")

        from openai import OpenAI
        _client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    return _client


def call_llm(prompt: str, system_prompt: str = None, model: str = None, temperature: float = 0.3) -> str:
    """Call LLM API and return raw JSON-mode text response."""
    try:
        client = _get_client()
    except Exception as e:
        return f'{{"error": "{str(e)}"}}'

    model_name = model or TREND_MODEL

    # Log LLM details before making the call
    print("--- [LLM API Request] ---")
    print(f"Provider: {LLM_PROVIDER}")
    print(f"Model: {model_name}")
    print(f"Base URL: {BASE_URL}")
    print(f"API Key Present: {bool(API_KEY)}")
    print("-------------------------")

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=temperature,
            response_format={"type": "json_object"}
        )
        return completion.choices[0].message.content or ""
    except Exception as e:
        err_str = str(e)
        if "401" in err_str or "unauthorized" in err_str.lower() or "invalid api key" in err_str.lower():
            return f'{{"error": "401 Unauthorized - Provider/BaseURL/Key mismatch likely for {LLM_PROVIDER}"}}'
        return f'{{"error": "{err_str}"}}'


# Backwards compatibility alias
call_gemini = call_llm


def extract_json_from_response(response: str):
    """Parse JSON from LLM response. Returns dict or list, never crashes."""
    if not response:
        return {"error": "Empty response"}

    # 1. Direct parse
    try:
        return json.loads(response)
    except (json.JSONDecodeError, TypeError):
        pass

    # 2. Markdown fence extraction
    fence = re.search(r"```(?:json)?\s*\n?([\s\S]*?)\n?\s*```", response, re.IGNORECASE)
    if fence:
        try:
            return json.loads(fence.group(1).strip())
        except (json.JSONDecodeError, TypeError):
            pass

    # 3. Find JSON object or array
    for pattern in [r"\{[\s\S]*\}", r"\[[\s\S]*\]"]:
        match = re.search(pattern, response)
        if match:
            try:
                return json.loads(match.group(0))
            except (json.JSONDecodeError, TypeError):
                pass

    return {"error": "Failed to parse JSON", "raw": response[:300]}
