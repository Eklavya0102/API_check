# KeyProbe — API Key Tester

A modern, production-style web app to validate API keys for 24+ providers — instantly, securely, without ever storing your keys.

---

## Features

- **24+ providers** — OpenAI, Anthropic, Gemini, Groq, Stripe, GitHub, Discord, and more
- **Live validation** — sends a minimal real request to the provider's official endpoint
- **Detailed error diagnosis** — invalid key vs. quota exceeded vs. permission error vs. timeout
- **Zero storage** — keys are never logged, saved, or sent anywhere except the provider
- **Modern dark UI** — glassmorphism, animated blobs, smooth transitions

---

## Quick Start

### 1. Clone / set up

```bash
cd project
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Run

```bash
python app.py
```

Open → [http://127.0.0.1:5000](http://127.0.0.1:5000)

---

## Project Structure

```
project/
├── app.py              # Flask backend + all provider test logic
├── requirements.txt
├── README.md
├── static/
│   ├── style.css       # Dark glassmorphism styles
│   └── script.js       # Frontend interactions
└── templates/
    └── index.html      # Main page
```

---

## Adding a New Provider

**1. Register it in `PROVIDERS` dict (app.py):**

```python
"myprovider": {
    "name": "My Provider",
    "models": ["model-a", "model-b"],
    "default_model": "model-a",
},
```

**2. Write a test function:**

```python
def test_myprovider(api_key, model):
    url = "https://api.myprovider.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = {"model": model, "messages": [{"role": "user", "content": "Hi"}], "max_tokens": 1}
    r = requests.post(url, headers=headers, json=body, timeout=15)
    if r.status_code == 200:
        return True, "success", "Key is valid and working.", r.json()
    etype, emsg = classify_error(r.status_code, r.text)
    return False, etype, emsg, {}
```

**3. Register in `TESTER_MAP`:**

```python
TESTER_MAP = {
    ...
    "myprovider": test_myprovider,
}
```

That's it — the frontend will pick it up automatically.

---

## Security

- API keys are **never** stored in memory beyond the single request lifecycle
- Keys are **never** logged to disk or console
- Masked key representation (`sk-abc•••••••xyz`) is shown in results
- Input validation + length checks on the backend
- No database, no analytics, no third-party tracking

---

## Supported Providers

| Provider       | Category    |
|---------------|-------------|
| OpenAI        | AI          |
| Anthropic     | AI          |
| Google Gemini | AI          |
| Groq          | AI          |
| Mistral       | AI          |
| Cohere        | AI          |
| Together AI   | AI          |
| Perplexity    | AI          |
| DeepSeek      | AI          |
| OpenRouter    | AI          |
| Fireworks AI  | AI          |
| HuggingFace   | AI          |
| Stability AI  | AI/Image    |
| Replicate     | AI          |
| xAI (Grok)    | AI          |
| AI21          | AI          |
| NVIDIA NIM    | AI          |
| Stripe        | Payments    |
| GitHub        | Dev         |
| Discord       | Messaging   |
| Telegram      | Messaging   |
| Twilio        | Comms       |
| Cloudflare    | Infra       |
| DigitalOcean  | Infra       |

---

## Deploy to Vercel

### One-click via Vercel CLI

```bash
npm i -g vercel
cd keyprobe-vercel
vercel
```

Follow the prompts — Vercel auto-detects the Python runtime via `api/index.py`.

### Via Vercel Dashboard

1. Push this folder to a GitHub repo
2. Go to [vercel.com/new](https://vercel.com/new)
3. Import the repo — Vercel picks up `vercel.json` automatically
4. Click **Deploy**

### Project structure Vercel uses

```
keyprobe-vercel/
├── api/
│   └── index.py        ← Vercel serverless entry point (Flask WSGI)
├── static/             ← Served as static assets
├── templates/          ← Jinja2 templates (loaded by api/index.py)
├── vercel.json         ← Routing rules
└── requirements.txt    ← Python deps (auto-installed by Vercel)
```

> **Note:** The original `app.py` at the root still works for local `python app.py` — it's kept for local dev convenience.
