"""
API Key Tester - Flask Backend
Tests API keys for various providers without storing them.
"""

import time
import requests
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ─────────────────────────────────────────────
# PROVIDER REGISTRY
# Each entry: endpoint, headers builder, body builder, success check
# ─────────────────────────────────────────────

PROVIDERS = {
    # ── AI Providers ──────────────────────────
    "openai": {
        "name": "OpenAI",
        "models": ["gpt-4o", "gpt-4.1", "gpt-4-turbo", "gpt-3.5-turbo"],
        "default_model": "gpt-4o",
    },
    "anthropic": {
        "name": "Anthropic",
        "models": ["claude-sonnet-4-5", "claude-opus-4-5", "claude-haiku-4-5"],
        "default_model": "claude-sonnet-4-5",
    },
    "gemini": {
        "name": "Google Gemini",
        "models": ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-1.5-pro"],
        "default_model": "gemini-2.5-flash",
    },
    "groq": {
        "name": "Groq",
        "models": ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "gemma2-9b-it"],
        "default_model": "llama-3.3-70b-versatile",
    },
    "mistral": {
        "name": "Mistral",
        "models": ["mistral-large-latest", "mistral-small-latest", "open-mistral-7b"],
        "default_model": "mistral-small-latest",
    },
    "cohere": {
        "name": "Cohere",
        "models": ["command-r-plus", "command-r", "command"],
        "default_model": "command-r",
    },
    "together": {
        "name": "Together AI",
        "models": ["meta-llama/Llama-3-70b-chat-hf", "mistralai/Mixtral-8x7B-Instruct-v0.1"],
        "default_model": "meta-llama/Llama-3-70b-chat-hf",
    },
    "perplexity": {
        "name": "Perplexity",
        "models": ["sonar", "sonar-pro", "sonar-reasoning"],
        "default_model": "sonar",
    },
    "deepseek": {
        "name": "DeepSeek",
        "models": ["deepseek-chat", "deepseek-coder"],
        "default_model": "deepseek-chat",
    },
    "openrouter": {
        "name": "OpenRouter",
        "models": ["openai/gpt-4o", "anthropic/claude-3-opus", "google/gemini-pro"],
        "default_model": "openai/gpt-4o",
    },
    "fireworks": {
        "name": "Fireworks AI",
        "models": ["accounts/fireworks/models/llama-v3p1-70b-instruct", "accounts/fireworks/models/mixtral-8x7b-instruct"],
        "default_model": "accounts/fireworks/models/llama-v3p1-70b-instruct",
    },
    "huggingface": {
        "name": "HuggingFace",
        "models": ["meta-llama/Meta-Llama-3-8B-Instruct", "mistralai/Mistral-7B-Instruct-v0.3"],
        "default_model": "meta-llama/Meta-Llama-3-8B-Instruct",
    },
    "stability": {
        "name": "Stability AI",
        "models": ["stable-diffusion-xl-1024-v1-0", "stable-image-core"],
        "default_model": "stable-image-core",
    },
    "replicate": {
        "name": "Replicate",
        "models": ["meta/llama-2-70b-chat", "stability-ai/sdxl"],
        "default_model": "meta/llama-2-70b-chat",
    },
    "xai": {
        "name": "xAI (Grok)",
        "models": ["grok-3", "grok-3-mini", "grok-2"],
        "default_model": "grok-3-mini",
    },
    "ai21": {
        "name": "AI21",
        "models": ["jamba-1.5-large", "jamba-1.5-mini"],
        "default_model": "jamba-1.5-mini",
    },
    "nvidia": {
        "name": "NVIDIA NIM",
        "models": ["meta/llama-3.1-70b-instruct", "nvidia/mistral-nemo-minitron-8b-8k-instruct"],
        "default_model": "meta/llama-3.1-70b-instruct",
    },
    # ── Other API Providers ───────────────────
    "stripe": {
        "name": "Stripe",
        "models": ["N/A"],
        "default_model": "N/A",
    },
    "github": {
        "name": "GitHub",
        "models": ["N/A"],
        "default_model": "N/A",
    },
    "discord": {
        "name": "Discord",
        "models": ["N/A"],
        "default_model": "N/A",
    },
    "telegram": {
        "name": "Telegram Bot API",
        "models": ["N/A"],
        "default_model": "N/A",
    },
    "twilio": {
        "name": "Twilio",
        "models": ["N/A"],
        "default_model": "N/A",
    },
    "cloudflare": {
        "name": "Cloudflare",
        "models": ["N/A"],
        "default_model": "N/A",
    },
    "digitalocean": {
        "name": "DigitalOcean",
        "models": ["N/A"],
        "default_model": "N/A",
    },
}


# ─────────────────────────────────────────────
# PROVIDER TEST FUNCTIONS
# ─────────────────────────────────────────────

def classify_error(status_code, body_text):
    """Map HTTP status + body text to human-readable error reason."""
    body_lower = body_text.lower()
    if status_code == 401 or "invalid_api_key" in body_lower or "unauthorized" in body_lower or "invalid api key" in body_lower:
        return "invalid_key", "Invalid API key — key was rejected by the provider."
    if status_code == 403 or "forbidden" in body_lower or "permission" in body_lower:
        return "permission_error", "Permission denied — key lacks required permissions."
    if status_code == 429 or "rate_limit" in body_lower or "quota" in body_lower or "exceeded" in body_lower:
        return "quota_exceeded", "Quota or rate limit exceeded — key works but has no remaining credits."
    if status_code == 402 or "billing" in body_lower or "payment" in body_lower:
        return "billing_issue", "Billing issue — account has no active subscription or credits."
    if "model" in body_lower and ("not found" in body_lower or "invalid" in body_lower or "does not exist" in body_lower):
        return "invalid_model", "Invalid model name — key works but the model is unavailable."
    if status_code >= 500:
        return "provider_error", "Provider server error — the API is temporarily unavailable."
    return "unknown_error", f"Unexpected error (HTTP {status_code})."


def test_openai(api_key, model):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = {"model": model, "messages": [{"role": "user", "content": "Hi"}], "max_tokens": 1}
    r = requests.post(url, headers=headers, json=body, timeout=15)
    if r.status_code == 200:
        return True, "success", "Key is valid and working.", r.json()
    etype, emsg = classify_error(r.status_code, r.text)
    return False, etype, emsg, {}


def test_anthropic(api_key, model):
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    body = {"model": model, "max_tokens": 1, "messages": [{"role": "user", "content": "Hi"}]}
    r = requests.post(url, headers=headers, json=body, timeout=15)
    if r.status_code == 200:
        return True, "success", "Key is valid and working.", r.json()
    etype, emsg = classify_error(r.status_code, r.text)
    return False, etype, emsg, {}


def test_gemini(api_key, model):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    body = {"contents": [{"parts": [{"text": "Hi"}]}], "generationConfig": {"maxOutputTokens": 1}}
    r = requests.post(url, json=body, timeout=15)
    if r.status_code == 200:
        return True, "success", "Key is valid and working.", r.json()
    etype, emsg = classify_error(r.status_code, r.text)
    return False, etype, emsg, {}


def test_groq(api_key, model):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = {"model": model, "messages": [{"role": "user", "content": "Hi"}], "max_tokens": 1}
    r = requests.post(url, headers=headers, json=body, timeout=15)
    if r.status_code == 200:
        return True, "success", "Key is valid and working.", r.json()
    etype, emsg = classify_error(r.status_code, r.text)
    return False, etype, emsg, {}


def test_mistral(api_key, model):
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = {"model": model, "messages": [{"role": "user", "content": "Hi"}], "max_tokens": 1}
    r = requests.post(url, headers=headers, json=body, timeout=15)
    if r.status_code == 200:
        return True, "success", "Key is valid and working.", r.json()
    etype, emsg = classify_error(r.status_code, r.text)
    return False, etype, emsg, {}


def test_cohere(api_key, model):
    url = "https://api.cohere.ai/v1/generate"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = {"model": model, "prompt": "Hi", "max_tokens": 1}
    r = requests.post(url, headers=headers, json=body, timeout=15)
    if r.status_code == 200:
        return True, "success", "Key is valid and working.", r.json()
    etype, emsg = classify_error(r.status_code, r.text)
    return False, etype, emsg, {}


def test_together(api_key, model):
    url = "https://api.together.xyz/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = {"model": model, "messages": [{"role": "user", "content": "Hi"}], "max_tokens": 1}
    r = requests.post(url, headers=headers, json=body, timeout=15)
    if r.status_code == 200:
        return True, "success", "Key is valid and working.", r.json()
    etype, emsg = classify_error(r.status_code, r.text)
    return False, etype, emsg, {}


def test_perplexity(api_key, model):
    url = "https://api.perplexity.ai/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = {"model": model, "messages": [{"role": "user", "content": "Hi"}], "max_tokens": 1}
    r = requests.post(url, headers=headers, json=body, timeout=15)
    if r.status_code == 200:
        return True, "success", "Key is valid and working.", r.json()
    etype, emsg = classify_error(r.status_code, r.text)
    return False, etype, emsg, {}


def test_deepseek(api_key, model):
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = {"model": model, "messages": [{"role": "user", "content": "Hi"}], "max_tokens": 1}
    r = requests.post(url, headers=headers, json=body, timeout=15)
    if r.status_code == 200:
        return True, "success", "Key is valid and working.", r.json()
    etype, emsg = classify_error(r.status_code, r.text)
    return False, etype, emsg, {}


def test_openrouter(api_key, model):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = {"model": model, "messages": [{"role": "user", "content": "Hi"}], "max_tokens": 1}
    r = requests.post(url, headers=headers, json=body, timeout=15)
    if r.status_code == 200:
        return True, "success", "Key is valid and working.", r.json()
    etype, emsg = classify_error(r.status_code, r.text)
    return False, etype, emsg, {}


def test_fireworks(api_key, model):
    url = "https://api.fireworks.ai/inference/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = {"model": model, "messages": [{"role": "user", "content": "Hi"}], "max_tokens": 1}
    r = requests.post(url, headers=headers, json=body, timeout=15)
    if r.status_code == 200:
        return True, "success", "Key is valid and working.", r.json()
    etype, emsg = classify_error(r.status_code, r.text)
    return False, etype, emsg, {}


def test_huggingface(api_key, model):
    url = f"https://api-inference.huggingface.co/models/{model}"
    headers = {"Authorization": f"Bearer {api_key}"}
    body = {"inputs": "Hi", "parameters": {"max_new_tokens": 1}}
    r = requests.post(url, headers=headers, json=body, timeout=20)
    if r.status_code in (200, 503):  # 503 = model loading (key still valid)
        return True, "success", "Key is valid and working." + (" (Model loading)" if r.status_code == 503 else ""), {}
    etype, emsg = classify_error(r.status_code, r.text)
    return False, etype, emsg, {}


def test_stability(api_key, model):
    url = "https://api.stability.ai/v1/user/account"
    headers = {"Authorization": f"Bearer {api_key}"}
    r = requests.get(url, headers=headers, timeout=10)
    if r.status_code == 200:
        return True, "success", "Key is valid and working.", r.json()
    etype, emsg = classify_error(r.status_code, r.text)
    return False, etype, emsg, {}


def test_replicate(api_key, model):
    url = "https://api.replicate.com/v1/account"
    headers = {"Authorization": f"Token {api_key}"}
    r = requests.get(url, headers=headers, timeout=10)
    if r.status_code == 200:
        return True, "success", "Key is valid and working.", r.json()
    etype, emsg = classify_error(r.status_code, r.text)
    return False, etype, emsg, {}


def test_xai(api_key, model):
    url = "https://api.x.ai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = {"model": model, "messages": [{"role": "user", "content": "Hi"}], "max_tokens": 1}
    r = requests.post(url, headers=headers, json=body, timeout=15)
    if r.status_code == 200:
        return True, "success", "Key is valid and working.", r.json()
    etype, emsg = classify_error(r.status_code, r.text)
    return False, etype, emsg, {}


def test_ai21(api_key, model):
    url = "https://api.ai21.com/studio/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = {"model": model, "messages": [{"role": "user", "content": "Hi"}], "max_tokens": 1}
    r = requests.post(url, headers=headers, json=body, timeout=15)
    if r.status_code == 200:
        return True, "success", "Key is valid and working.", r.json()
    etype, emsg = classify_error(r.status_code, r.text)
    return False, etype, emsg, {}


def test_nvidia(api_key, model):
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = {"model": model, "messages": [{"role": "user", "content": "Hi"}], "max_tokens": 1}
    r = requests.post(url, headers=headers, json=body, timeout=15)
    if r.status_code == 200:
        return True, "success", "Key is valid and working.", r.json()
    etype, emsg = classify_error(r.status_code, r.text)
    return False, etype, emsg, {}


def test_stripe(api_key, model):
    url = "https://api.stripe.com/v1/balance"
    r = requests.get(url, auth=(api_key, ""), timeout=10)
    if r.status_code == 200:
        return True, "success", "Key is valid and working.", r.json()
    etype, emsg = classify_error(r.status_code, r.text)
    return False, etype, emsg, {}


def test_github(api_key, model):
    url = "https://api.github.com/user"
    headers = {"Authorization": f"token {api_key}"}
    r = requests.get(url, headers=headers, timeout=10)
    if r.status_code == 200:
        return True, "success", "Key is valid and working.", {"login": r.json().get("login")}
    etype, emsg = classify_error(r.status_code, r.text)
    return False, etype, emsg, {}


def test_discord(api_key, model):
    url = "https://discord.com/api/v10/users/@me"
    headers = {"Authorization": f"Bot {api_key}"}
    r = requests.get(url, headers=headers, timeout=10)
    if r.status_code == 200:
        return True, "success", "Key is valid and working.", {"username": r.json().get("username")}
    etype, emsg = classify_error(r.status_code, r.text)
    return False, etype, emsg, {}


def test_telegram(api_key, model):
    url = f"https://api.telegram.org/bot{api_key}/getMe"
    r = requests.get(url, timeout=10)
    data = r.json()
    if data.get("ok"):
        return True, "success", "Key is valid and working.", {"username": data["result"].get("username")}
    return False, "invalid_key", "Invalid Telegram bot token.", {}


def test_twilio(api_key, model):
    # api_key should be "AccountSID:AuthToken"
    if ":" not in api_key:
        return False, "invalid_key", "Twilio needs AccountSID:AuthToken format.", {}
    sid, token = api_key.split(":", 1)
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}.json"
    r = requests.get(url, auth=(sid, token), timeout=10)
    if r.status_code == 200:
        return True, "success", "Key is valid and working.", {}
    etype, emsg = classify_error(r.status_code, r.text)
    return False, etype, emsg, {}


def test_cloudflare(api_key, model):
    url = "https://api.cloudflare.com/client/v4/user/tokens/verify"
    headers = {"Authorization": f"Bearer {api_key}"}
    r = requests.get(url, headers=headers, timeout=10)
    data = r.json()
    if data.get("success"):
        return True, "success", "Key is valid and working.", {}
    etype, emsg = classify_error(r.status_code, r.text)
    return False, etype, emsg, {}


def test_digitalocean(api_key, model):
    url = "https://api.digitalocean.com/v2/account"
    headers = {"Authorization": f"Bearer {api_key}"}
    r = requests.get(url, headers=headers, timeout=10)
    if r.status_code == 200:
        return True, "success", "Key is valid and working.", {}
    etype, emsg = classify_error(r.status_code, r.text)
    return False, etype, emsg, {}


# ─────────────────────────────────────────────
# PROVIDER DISPATCH MAP
# ─────────────────────────────────────────────
TESTER_MAP = {
    "openai": test_openai,
    "anthropic": test_anthropic,
    "gemini": test_gemini,
    "groq": test_groq,
    "mistral": test_mistral,
    "cohere": test_cohere,
    "together": test_together,
    "perplexity": test_perplexity,
    "deepseek": test_deepseek,
    "openrouter": test_openrouter,
    "fireworks": test_fireworks,
    "huggingface": test_huggingface,
    "stability": test_stability,
    "replicate": test_replicate,
    "xai": test_xai,
    "ai21": test_ai21,
    "nvidia": test_nvidia,
    "stripe": test_stripe,
    "github": test_github,
    "discord": test_discord,
    "telegram": test_telegram,
    "twilio": test_twilio,
    "cloudflare": test_cloudflare,
    "digitalocean": test_digitalocean,
}


# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/providers", methods=["GET"])
def get_providers():
    """Return provider list and their models."""
    result = []
    for pid, pdata in PROVIDERS.items():
        result.append({
            "id": pid,
            "name": pdata["name"],
            "models": pdata["models"],
            "default_model": pdata["default_model"],
        })
    return jsonify(result)


@app.route("/api/test", methods=["POST"])
def test_key():
    """Test an API key for a given provider and model."""
    data = request.get_json(silent=True) or {}

    provider_id = (data.get("provider") or "").strip().lower()
    model = (data.get("model") or "").strip()
    api_key = (data.get("api_key") or "").strip()

    # ── Input validation ─────────────────────
    if not provider_id:
        return jsonify({"success": False, "error_type": "validation", "message": "Provider is required."}), 400
    if not api_key:
        return jsonify({"success": False, "error_type": "validation", "message": "API key is required."}), 400
    if len(api_key) > 512:
        return jsonify({"success": False, "error_type": "validation", "message": "API key too long."}), 400
    if provider_id not in TESTER_MAP:
        return jsonify({"success": False, "error_type": "validation", "message": f"Unknown provider: {provider_id}"}), 400

    if not model or model == "N/A":
        model = PROVIDERS[provider_id]["default_model"]

    tester = TESTER_MAP[provider_id]
    provider_name = PROVIDERS[provider_id]["name"]

    start = time.time()
    try:
        success, error_type, message, meta = tester(api_key, model)
    except requests.exceptions.Timeout:
        success, error_type, message, meta = False, "timeout", "Request timed out — provider did not respond in time.", {}
    except requests.exceptions.ConnectionError:
        success, error_type, message, meta = False, "network_error", "Network error — could not reach the provider.", {}
    except Exception as e:
        success, error_type, message, meta = False, "unknown_error", f"Unexpected error: {str(e)[:120]}", {}

    latency_ms = round((time.time() - start) * 1000)

    # Mask the key in any response metadata (safety)
    masked_key = api_key[:6] + "•" * max(0, len(api_key) - 10) + api_key[-4:] if len(api_key) >= 10 else "••••••"

    return jsonify({
        "success": success,
        "provider": provider_name,
        "provider_id": provider_id,
        "model": model,
        "error_type": error_type if not success else None,
        "message": message,
        "latency_ms": latency_ms,
        "masked_key": masked_key,
        "meta": meta if success else {},
    })


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
