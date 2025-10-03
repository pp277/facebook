## News Auto Publisher (Fresh Build)

This is a clean, production-ready starter that:

- Ingests RSS/Atom feeds
- Rewrites items to engaging social copy using Groq LLM
- Publishes to Facebook Pages via the Graph API

### Features
- Environment-based config (.env)
- Safe secret handling (no hardcoded tokens)
- Retries, timeouts, and structured logging
- Modular architecture (LLM client, Facebook client, RSS fetcher)
 - Multi-account Facebook pages
 - Optional Twitter/X support (multi-account)

### Quick start
1. Create and activate a Python 3.10+ virtualenv.
2. Copy `.env.example` to `.env` and fill values.
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run a one-off publish from CLI:
   ```bash
   python -m app.cli.publish_once
   ```
5. Start the webhook/health server (optional):
   ```bash
   uvicorn app.server:app --host 0.0.0.0 --port 8000
   ```

### Environment variables (.env)
See `.env.example` for all options (feeds, delays, Tiri/Groq keys, Facebook multi-accounts, Twitter tokens, platforms).

### Structure
```
app/
  config.py           # loads env and validates
  logging.py          # logger setup
  clients/
    facebook.py       # Facebook Graph API client
    groq_llm.py       # Groq chat completions client
    twitter.py        # Twitter/X client
  rss/
    fetch.py          # feed fetch and parse
  cli/
    publish_once.py   # simple CLI: fetch, rewrite, post
  server.py           # FastAPI app with /health and /webhook
```

### Notes
- This project is independent of existing files; it does not modify them.
- Add a webhook server later if you want WebSub push.
 - For Facebook posts, ensure items have an image URL; otherwise, extend to use a link post endpoint.

### Ubuntu deployment
See `DEPLOY_UBUNTU.md` for a full step-by-step guide (systemd timer, server service, and cron alternative).


