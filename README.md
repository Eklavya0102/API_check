# KeyProbe

A clean, developer-friendly tool to validate API keys across 24+ providers — without ever storing, logging, or sharing them.

---

## Why I built this

Every time I picked up a new project or rotated credentials, I'd spend 10 minutes writing a throwaway curl command just to check whether an API key actually worked. Quota exceeded? Invalid? Expired? The raw HTTP errors were useful but tedious to parse.

KeyProbe wraps that process into a single UI. Paste the key, pick the provider, hit test. You get a plain-English diagnosis back in under a second.

---

## How it works

The flow is intentionally simple:

1. You select a provider and model from the dropdown (or type a custom model name that isn't in the list).
2. You paste your API key into the input field.
3. The frontend POSTs `{ provider, model, api_key }` to the Flask backend at `/api/test`.
4. The backend sends the **smallest possible request** to the provider's real endpoint — typically a 1-token chat completion or an account info call.
5. The response is parsed into one of 10 named error types (or success), and a structured JSON result is returned.
6. The result pops up as a modal with a plain-English explanation, latency, and a "how to fix it" tip if something went wrong.

The key is never written to disk, never printed to logs, and not passed anywhere except the provider's own API.

---

## Features

- **24 providers** — covers the major AI APIs (OpenAI, Anthropic, Gemini, Groq, Mistral, Cohere, Together AI, Perplexity, DeepSeek, OpenRouter, Fireworks AI, HuggingFace, Stability AI, Replicate, xAI, AI21, NVIDIA NIM) and common developer APIs (Stripe, GitHub, Discord, Telegram, Twilio, Cloudflare, DigitalOcean).
- **Searchable provider dropdown** — start typing to filter; keyboard navigation with arrow keys and Enter.
- **Searchable model dropdown with custom entry** — all known models are listed and filterable. If your model isn't there, type it in and a "Use custom name" option appears.
- **10 distinct error types** — the backend doesn't just say "it failed". It distinguishes between: invalid key, permission denied, quota exceeded, billing issue, invalid model, provider server error, timeout, network error, input validation failure, and unknown errors.
- **Modal result popup** — results appear as an overlay with a colour-coded header (green / red / yellow), detail pills, a "what happened" explanation, and a "how to fix it" tip.
- **Latency measurement** — wall-clock time from request dispatch to response, shown in the result.
- **Key masking** — the masked key (`sk-abc•••••xyz`) is shown in the result so you can confirm which key was tested without exposing it.
- **Copy result** — copies a clean plain-text summary of the result to clipboard, useful for pasting into a ticket or a Slack message.
- **Show/hide key toggle** — the input is password-type by default; a toggle reveals it.
- **Paste button** — reads from clipboard directly into the key field.
- **Zero storage** — no database, no session, no analytics, no logs of key material. The key lives in memory for the duration of a single HTTP request.

---

## API endpoints

The Flask backend exposes two endpoints. Both are JSON.

### `GET /api/providers`

Returns the full list of supported providers with their available models.

**Response:**
```json
[
  {
    "id": "openai",
    "name": "OpenAI",
    "models": ["gpt-4o", "gpt-4.1", "gpt-4-turbo", "gpt-3.5-turbo"],
    "default_model": "gpt-4o"
  },
  ...
]
```

---

### `POST /api/test`

Tests an API key for a given provider and model.

**Request body:**
```json
{
  "provider": "openai",
  "model": "gpt-4o",
  "api_key": "sk-..."
}
```

**Success response:**
```json
{
  "success": true,
  "provider": "OpenAI",
  "provider_id": "openai",
  "model": "gpt-4o",
  "message": "Key is valid and working.",
  "latency_ms": 312,
  "masked_key": "sk-abc•••••••••xyz",
  "error_type": null,
  "meta": {}
}
```

**Failure response:**
```json
{
  "success": false,
  "provider": "OpenAI",
  "provider_id": "openai",
  "model": "gpt-4o",
  "message": "Invalid API key — key was rejected by the provider.",
  "latency_ms": 189,
  "masked_key": "sk-abc•••••••••xyz",
  "error_type": "invalid_key",
  "meta": {}
}
```

**Error types returned:**

| `error_type` | Meaning |
|---|---|
| `invalid_key` | The provider rejected the key outright |
| `permission_error` | Key exists but lacks required scope |
| `quota_exceeded` | Key works, account has no remaining credits |
| `billing_issue` | No active subscription or payment method |
| `invalid_model` | Key is fine, model name is wrong or inaccessible |
| `provider_error` | Provider returned a 5xx server error |
| `timeout` | No response within 15 seconds |
| `network_error` | Could not reach the provider at all |
| `validation` | Bad input (missing key, unknown provider, etc.) |
| `unknown_error` | Anything else |

---

## Setup

**Requirements:** Python 3.9+, pip

```bash
# Clone or unzip the project
cd keyprobe-vercel

# Install dependencies
pip install -r requirements.txt

# Run
python app.py
```

Open `http://127.0.0.1:5000` in your browser.

No `.env` file needed. No API keys of your own required. The app just proxies whatever key you paste in the UI to the appropriate provider.

---

## Adding a new provider

Everything lives in `app.py`. Adding a provider is three steps:

**Step 1 — Register it in the `PROVIDERS` dict:**

```python
"myprovider": {
    "name": "My Provider",
    "models": ["model-v1", "model-v2"],
    "default_model": "model-v1",
},
```

**Step 2 — Write a test function:**

The function receives `(api_key, model)` and must return a 4-tuple: `(success: bool, error_type: str, message: str, meta: dict)`.

```python
def test_myprovider(api_key, model):
    url = "https://api.myprovider.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": [{"role": "user", "content": "Hi"}],
        "max_tokens": 1,
    }
    r = requests.post(url, headers=headers, json=body, timeout=15)
    if r.status_code == 200:
        return True, "success", "Key is valid and working.", r.json()
    etype, emsg = classify_error(r.status_code, r.text)
    return False, etype, emsg, {}
```

Use `classify_error(status_code, body_text)` — it maps HTTP status codes and common error strings to the named error types above. Override it if the provider uses non-standard patterns.

**Step 3 — Add it to `TESTER_MAP`:**

```python
TESTER_MAP = {
    ...
    "myprovider": test_myprovider,
}
```

The frontend picks it up automatically on the next page load.

---

## Project structure

```
keyprobe-vercel/
├── app.py                  # Flask app + all 24 provider test functions
├── requirements.txt
├── api/
│   └── index.py            # Same as app.py, with paths adjusted for serverless
├── static/
│   ├── style.css           # All styles — light mode, Google Sans, modal
│   └── script.js           # Dropdowns, form logic, modal rendering
├── templates/
│   └── index.html          # Single-page UI
└── vercel.json             # Routing config for serverless deployment
```

---

## Security notes

- API keys are never written anywhere. They touch memory for the duration of one `requests.post()` call and nothing else.
- Keys are sanitised (length-capped at 512 chars, whitespace stripped) before being used.
- The masked key shown in results is computed from the original: first 6 chars + bullets + last 4 chars.
- There are no analytics, no third-party scripts loaded at runtime, and no cookies.
- CORS is enabled via `flask-cors` to support local development. For production you should restrict the allowed origins.

---

## Future improvements

Things I'd add if this were going into heavier use:

- **Batch testing** — paste multiple keys at once, get a results table. Useful when rotating credentials across a team.
- **History panel** — store recent test results in `localStorage` (not the keys themselves, just the masked key + outcome + timestamp) so you can refer back without re-testing.
- **Response preview** — optionally show a snippet of the actual API response in the success modal, so you can verify the model is producing output correctly, not just accepting the request.
- **Latency benchmark** — run the test 3 times and show min/avg/max, rather than a single sample.
- **Health status badges** — pull from each provider's public status page and show a small indicator next to the provider name in the dropdown.
- **More providers** — AWS Bedrock, Azure OpenAI, Vertex AI, Cohere Embed, ElevenLabs, AssemblyAI, Pinecone, Weaviate.
- **CLI version** — `keyprobe openai sk-... gpt-4o` from the terminal, same logic, JSON output. Would make it useful in CI pipelines.
- **Dark mode** — the CSS variables are set up in a way that makes a dark theme straightforward to add; it just needs a `prefers-color-scheme: dark` media query override.

---

## Dependencies

```
flask==3.0.3
flask-cors==4.0.1
requests==2.32.3
python-dotenv==1.0.1
```

No database. No ORM. No task queue. Intentionally minimal.
