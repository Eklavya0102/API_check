# LLM API Key Checker

Validate API keys for 11 LLM providers — with detailed failure reasons.
Vercel-ready with a Python serverless backend and a zero-dependency frontend.

## Providers supported

| Provider       | Key format      |
|----------------|-----------------|
| OpenAI         | `sk-...`        |
| Anthropic      | `sk-ant-...`    |
| Google Gemini  | `AIza...`       |
| Mistral AI     | any             |
| Groq           | `gsk_...`       |
| xAI (Grok)     | `xai-...`       |
| DeepSeek       | `sk-...`        |
| Cohere         | any             |
| Together AI    | any             |
| Perplexity     | `pplx-...`      |
| Hugging Face   | `hf_...`        |

## Failure reasons detected

- **invalid** — wrong key, typo, or copy-paste error
- **expired** — key has expired (OpenAI)
- **deactivated** — key was manually revoked
- **quota_exceeded** — billing limit reached
- **rate_limited** — key is valid but temporarily throttled
- **forbidden** — account lacks permissions
- **api_disabled** — API not enabled in cloud project (Gemini)
- **no_balance** — insufficient credits (DeepSeek)
- **network_error** — couldn't reach the provider
- **server_error** — provider outage (not your key)

## Deploy to Vercel

```bash
npm i -g vercel
vercel
```

That's it. Vercel auto-detects `vercel.json` and deploys:
- `api/check.py`  →  serverless function at `/api/check`
- `public/`       →  static frontend

## Run locally

```bash
# Python check from CLI
python3 - <<'EOF'
from api.check import check_key
print(check_key("openai", "sk-your-key-here"))
EOF

# Or just open public/index.html in a browser
# (frontend calls /api/check — works after `vercel dev`)
```

## API

**POST** `/api/check`

```json
{ "provider": "openai", "key": "sk-..." }
```

Response:
```json
{
  "valid": false,
  "status": "quota_exceeded",
  "reason": "Usage quota exceeded. Add billing or upgrade your plan at platform.openai.com.",
  "detail": "...(raw API response excerpt)...",
  "latency_ms": 312,
  "provider": "OpenAI"
}
```

`valid` is `true` (working), `false` (broken), or `null` (provider outage).

## File structure

```
llm-key-checker/
├── api/
│   └── check.py        ← Python serverless function
├── public/
│   └── index.html      ← Frontend (zero deps)
├── vercel.json
├── requirements.txt
└── README.md
```
