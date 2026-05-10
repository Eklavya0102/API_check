"""
LLM API Key Checker — Vercel Serverless Function
POST /api/check  { "provider": "openai", "key": "sk-..." }
Returns: { valid, status, reason, detail, latency_ms, provider }
"""

import json
import time
import http.client
import urllib.parse
from http.server import BaseHTTPRequestHandler


# ── per-provider response parsers ─────────────────────────────────────────────

def _parse_openai(status, body):
    if status == 200:
        return True, "valid", "Key is active and working."
    if status == 401:
        err  = body.get("error", {})
        code = err.get("code", "")
        msg  = err.get("message", "")
        if "expired" in msg.lower():
            return False, "expired", "Your API key has expired. Regenerate it in the OpenAI dashboard."
        if "invalid" in msg.lower() or code == "invalid_api_key":
            return False, "invalid", "Key not recognised. Check for typos or copy-paste errors."
        if "deactivated" in msg.lower():
            return False, "deactivated", "This key has been deactivated. Generate a new one at platform.openai.com."
        return False, "unauthorized", msg or "Unauthorized — check your key."
    if status == 403:
        return False, "forbidden", "Access denied. Your account may be restricted or the key lacks permissions."
    if status == 429:
        body_msg = body.get("error", {}).get("message", "")
        if "quota" in body_msg.lower():
            return False, "quota_exceeded", "Usage quota exceeded. Add billing or upgrade your plan at platform.openai.com."
        return True, "rate_limited", "Key is valid but currently rate-limited. Try again shortly."
    if status >= 500:
        return None, "server_error", "OpenAI server error — not a key issue. Try again later."
    return False, "unknown", f"Unexpected HTTP {status}."


def _parse_anthropic(status, body):
    if status in (200, 400):
        return True, "valid", "Key is active and working."
    if status == 401:
        err_type = body.get("error", {}).get("type", "")
        err_msg  = body.get("error", {}).get("message", "")
        if "invalid" in err_type.lower() or "invalid" in err_msg.lower():
            return False, "invalid", "Key not recognised. Copy the full key from console.anthropic.com."
        return False, "unauthorized", err_msg or "Unauthorized — check your key."
    if status == 403:
        return False, "forbidden", "Your account does not have permission to use this API."
    if status == 429:
        return True, "rate_limited", "Key is valid but you have hit a rate limit. Wait a moment and retry."
    if status == 529:
        return None, "overloaded", "Anthropic API is temporarily overloaded — not a key issue."
    if status >= 500:
        return None, "server_error", "Anthropic server error — not a key issue."
    return False, "unknown", f"Unexpected HTTP {status}."


def _parse_gemini(status, body):
    if status == 200:
        return True, "valid", "Key is active and working."
    if status == 400:
        msg = body.get("error", {}).get("message", "")
        if "api_key_invalid" in msg.lower() or "invalid" in msg.lower():
            return False, "invalid", "API key is invalid. Regenerate it in Google AI Studio (aistudio.google.com)."
        return False, "bad_request", msg or "Bad request — check your key format."
    if status == 403:
        msg = body.get("error", {}).get("message", "")
        if "disabled" in msg.lower():
            return False, "api_disabled", "Generative Language API not enabled. Enable it in Google Cloud Console."
        return False, "forbidden", msg or "Access denied — check project permissions."
    if status == 429:
        return True, "rate_limited", "Key valid but quota exceeded. Check Gemini quota in Google Cloud Console."
    if status >= 500:
        return None, "server_error", "Google server error — not a key issue."
    return False, "unknown", f"Unexpected HTTP {status}."


def _parse_mistral(status, body):
    if status == 200:
        return True, "valid", "Key is active and working."
    if status == 401:
        msg = body.get("message", "")
        return False, "invalid", msg or "Unauthorized. Check your key at console.mistral.ai."
    if status == 403:
        return False, "forbidden", "Access denied. Your subscription may not include API access."
    if status == 429:
        return True, "rate_limited", "Key valid but rate-limited. Upgrade your plan for higher limits."
    if status >= 500:
        return None, "server_error", "Mistral server error — not a key issue."
    return False, "unknown", f"Unexpected HTTP {status}."


def _parse_cohere(status, body):
    if status == 200:
        return True, "valid", "Key is active and working."
    if status == 401:
        msg = body.get("message", "")
        if "invalid" in str(msg).lower():
            return False, "invalid", "Invalid API key. Regenerate at dashboard.cohere.com."
        return False, "unauthorized", str(msg) or "Unauthorized — check your key."
    if status == 403:
        return False, "forbidden", "Access denied. Your plan may not include API access."
    if status == 429:
        return True, "rate_limited", "Rate limited. Consider upgrading your Cohere plan."
    if status >= 500:
        return None, "server_error", "Cohere server error — not a key issue."
    return False, "unknown", f"Unexpected HTTP {status}."


def _parse_groq(status, body):
    if status == 200:
        return True, "valid", "Key is active and working."
    if status == 401:
        err = body.get("error", {})
        msg = err.get("message", "") if isinstance(err, dict) else str(err)
        if "invalid" in msg.lower():
            return False, "invalid", "Invalid API key. Generate a new one at console.groq.com."
        return False, "unauthorized", msg or "Unauthorized — check your key."
    if status == 429:
        return True, "rate_limited", "Key valid but rate-limited. Groq free tier has strict per-minute limits."
    if status >= 500:
        return None, "server_error", "Groq server error — not a key issue."
    return False, "unknown", f"Unexpected HTTP {status}."


def _parse_together(status, body):
    if status == 200:
        return True, "valid", "Key is active and working."
    if status == 401:
        msg = body.get("error", "") or body.get("message", "")
        return False, "invalid", str(msg) or "Invalid key — check api.together.ai."
    if status == 429:
        return True, "rate_limited", "Key valid but rate-limited."
    if status >= 500:
        return None, "server_error", "Together AI server error — not a key issue."
    return False, "unknown", f"Unexpected HTTP {status}."


def _parse_perplexity(status, body):
    if status == 200:
        return True, "valid", "Key is active and working."
    if status == 401:
        err = body.get("error", {})
        msg = err.get("message", "") if isinstance(err, dict) else str(err)
        return False, "invalid", msg or "Invalid key — check your Perplexity dashboard."
    if status == 403:
        return False, "forbidden", "Access denied. Ensure your account has API access enabled."
    if status == 429:
        return True, "rate_limited", "Key valid but rate-limited."
    if status >= 500:
        return None, "server_error", "Perplexity server error — not a key issue."
    return False, "unknown", f"Unexpected HTTP {status}."


def _parse_huggingface(status, body):
    if status == 200:
        user = body.get("name", "")
        return True, "valid", f"Token valid — authenticated as: {user}" if user else "Token is active."
    if status == 401:
        msg = body.get("error", "")
        if "invalid" in str(msg).lower() or "token" in str(msg).lower():
            return False, "invalid", "Invalid or revoked token. Generate a new one at huggingface.co/settings/tokens."
        return False, "unauthorized", str(msg) or "Unauthorized."
    if status == 403:
        return False, "forbidden", "Token lacks required permissions. Try a token with 'read' scope."
    if status >= 500:
        return None, "server_error", "Hugging Face server error — not a key issue."
    return False, "unknown", f"Unexpected HTTP {status}."


def _parse_xai(status, body):
    if status == 200:
        return True, "valid", "Key is active and working."
    if status == 401:
        err = body.get("error", {})
        msg = err.get("message", "") if isinstance(err, dict) else str(err)
        return False, "invalid", msg or "Invalid key — check your xAI console."
    if status == 403:
        return False, "forbidden", "Access denied. Your account may not have API access yet."
    if status == 429:
        return True, "rate_limited", "Key valid but rate-limited."
    if status >= 500:
        return None, "server_error", "xAI server error — not a key issue."
    return False, "unknown", f"Unexpected HTTP {status}."


def _parse_deepseek(status, body):
    if status == 200:
        return True, "valid", "Key is active and working."
    if status == 401:
        err = body.get("error", {})
        msg = err.get("message", "") if isinstance(err, dict) else str(err)
        if "balance" in msg.lower():
            return False, "no_balance", "Insufficient balance. Top up at platform.deepseek.com."
        return False, "invalid", msg or "Invalid API key."
    if status == 402:
        return False, "no_balance", "Insufficient balance. Please top up your DeepSeek account."
    if status == 429:
        return True, "rate_limited", "Key valid but rate-limited."
    if status >= 500:
        return None, "server_error", "DeepSeek server error — not a key issue."
    return False, "unknown", f"Unexpected HTTP {status}."


# ── provider registry ─────────────────────────────────────────────────────────

PROVIDERS = {
    "openai": {
        "name": "OpenAI",
        "host": "api.openai.com",
        "path": "/v1/models",
        "method": "GET",
        "headers": lambda key: {"Authorization": f"Bearer {key}"},
        "body": None,
        "parse": _parse_openai,
    },
    "anthropic": {
        "name": "Anthropic",
        "host": "api.anthropic.com",
        "path": "/v1/messages",
        "method": "POST",
        "headers": lambda key: {
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        "body": json.dumps({
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 1,
            "messages": [{"role": "user", "content": "hi"}],
        }),
        "parse": _parse_anthropic,
    },
    "gemini": {
        "name": "Google Gemini",
        "host": "generativelanguage.googleapis.com",
        "path": None,
        "method": "GET",
        "headers": lambda key: {},
        "body": None,
        "parse": _parse_gemini,
    },
    "mistral": {
        "name": "Mistral AI",
        "host": "api.mistral.ai",
        "path": "/v1/models",
        "method": "GET",
        "headers": lambda key: {"Authorization": f"Bearer {key}"},
        "body": None,
        "parse": _parse_mistral,
    },
    "cohere": {
        "name": "Cohere",
        "host": "api.cohere.com",
        "path": "/v2/models",
        "method": "GET",
        "headers": lambda key: {"Authorization": f"Bearer {key}"},
        "body": None,
        "parse": _parse_cohere,
    },
    "groq": {
        "name": "Groq",
        "host": "api.groq.com",
        "path": "/openai/v1/models",
        "method": "GET",
        "headers": lambda key: {"Authorization": f"Bearer {key}"},
        "body": None,
        "parse": _parse_groq,
    },
    "together": {
        "name": "Together AI",
        "host": "api.together.xyz",
        "path": "/v1/models",
        "method": "GET",
        "headers": lambda key: {"Authorization": f"Bearer {key}"},
        "body": None,
        "parse": _parse_together,
    },
    "perplexity": {
        "name": "Perplexity AI",
        "host": "api.perplexity.ai",
        "path": "/models",
        "method": "GET",
        "headers": lambda key: {"Authorization": f"Bearer {key}"},
        "body": None,
        "parse": _parse_perplexity,
    },
    "huggingface": {
        "name": "Hugging Face",
        "host": "huggingface.co",
        "path": "/api/whoami-v2",
        "method": "GET",
        "headers": lambda key: {"Authorization": f"Bearer {key}"},
        "body": None,
        "parse": _parse_huggingface,
    },
    "xai": {
        "name": "xAI (Grok)",
        "host": "api.x.ai",
        "path": "/v1/models",
        "method": "GET",
        "headers": lambda key: {"Authorization": f"Bearer {key}"},
        "body": None,
        "parse": _parse_xai,
    },
    "deepseek": {
        "name": "DeepSeek",
        "host": "api.deepseek.com",
        "path": "/models",
        "method": "GET",
        "headers": lambda key: {"Authorization": f"Bearer {key}"},
        "body": None,
        "parse": _parse_deepseek,
    },
}


# ── core checker ──────────────────────────────────────────────────────────────

def check_key(provider_id: str, key: str, model: str = None) -> dict:
    if provider_id not in PROVIDERS:
        return {
            "valid": False,
            "status": "unknown_provider",
            "reason": f"Provider '{provider_id}' is not supported.",
            "detail": f"Supported providers: {', '.join(PROVIDERS.keys())}",
            "latency_ms": 0,
            "provider": provider_id,
        }

    cfg  = PROVIDERS[provider_id]
    path = cfg["path"]

    if provider_id == "gemini":
        path = f"/v1beta/models?key={urllib.parse.quote(key)}"

    headers = cfg["headers"](key)
    body    = cfg["body"]

    # override model in Anthropic body if caller specified one
    if provider_id == "anthropic" and model:
        body = json.dumps({
            "model": model,
            "max_tokens": 1,
            "messages": [{"role": "user", "content": "hi"}],
        })
    if body:
        headers["Content-Length"] = str(len(body.encode("utf-8")))

    t0 = time.time()
    try:
        conn = http.client.HTTPSConnection(cfg["host"], timeout=10)
        conn.request(cfg["method"], path, body=body, headers=headers)
        resp   = conn.getresponse()
        status = resp.status
        raw    = resp.read().decode("utf-8", errors="replace")
        conn.close()
    except Exception as exc:
        return {
            "valid": False,
            "status": "network_error",
            "reason": "Could not reach the provider's API endpoint.",
            "detail": str(exc),
            "latency_ms": int((time.time() - t0) * 1000),
            "provider": cfg["name"],
        }

    latency_ms = int((time.time() - t0) * 1000)

    try:
        body_json = json.loads(raw)
    except Exception:
        body_json = {}

    valid, status_code, reason = cfg["parse"](status, body_json)

    return {
        "valid": valid,
        "status": status_code,
        "reason": reason,
        "detail": raw[:400] if valid is False else "",
        "latency_ms": latency_ms,
        "provider": cfg["name"],
    }


# ── Vercel serverless handler ─────────────────────────────────────────────────

class handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send_json(self, code: int, data: dict):
        body = json.dumps(data).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        self._send_json(200, {"providers": list(PROVIDERS.keys())})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw    = self.rfile.read(length)

        try:
            payload = json.loads(raw)
        except Exception:
            return self._send_json(400, {"error": "Invalid JSON body."})

        provider = str(payload.get("provider", "")).strip().lower()
        key      = str(payload.get("key", "")).strip()
        model    = str(payload.get("model", "")).strip() or None

        if not provider or not key:
            return self._send_json(400, {"error": "Both 'provider' and 'key' fields are required."})

        result = check_key(provider, key, model=model)
        self._send_json(200, result)
