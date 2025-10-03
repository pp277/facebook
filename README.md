## News Auto Publisher (WebSub - Instant News Drops)

This is a production-ready system that:

- **Instant news processing** via Superfeedr WebSub (no polling!)
- **Robust XML parsing** for any RSS/Atom format
- **AI rephrasing** using Tiri/Groq LLM with automatic failover
- **Multi-platform posting** to Facebook pages and Twitter accounts
- **WebSub webhook server** for instant notifications

### Features
- **WebSub-based**: Instant processing when news drops (not polling)
- **Robust XML parser**: Handles any RSS/Atom format with fallbacks
- **Multi-account support**: Multiple Facebook pages and Twitter accounts
- **AI failover**: 3 API keys with automatic retry and key rotation
- **Production-ready**: Structured logging, error handling, systemd service
- **Secure**: Environment-based config, no hardcoded secrets

### Quick start
1. Create and activate a Python 3.10+ virtualenv.
2. Copy `.env.example` to `.env` and fill values (Superfeedr credentials, callback URL, API keys).
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Subscribe to feeds (one-time setup):
   ```bash
   python -m app.cli.subscribe_feeds
   ```
5. Start the WebSub server:
   ```bash
   uvicorn app.server:app --host 0.0.0.0 --port 8000
   ```

### Environment variables (.env)
See `.env.example` for all options (Superfeedr credentials, callback URL, Tiri/Groq keys, Facebook multi-accounts, Twitter tokens, platforms).

### Structure
```
app/
  config.py              # loads env and validates
  logging.py             # logger setup
  server.py              # FastAPI WebSub server
  clients/
    facebook.py          # Facebook Graph API client
    groq_llm.py          # Groq chat completions client
    twitter.py           # Twitter/X client
  websub/
    superfeedr.py        # WebSub subscription manager
  xml/
    parser.py            # robust RSS/Atom parser
  cli/
    subscribe_feeds.py   # one-time feed subscription
  storage/
    db.py                # SQLite storage with TTL
```

### How it works
1. **Subscribe to feeds**: `python -m app.cli.subscribe_feeds` (one-time)
2. **Start server**: `uvicorn app.server:app --host 0.0.0.0 --port 8000`
3. **Instant processing**: When news drops, Superfeedr pushes to your webhook
4. **AI rephrasing**: Each item gets rewritten by Tiri/Groq LLM
5. **Multi-platform posting**: Posts to all configured accounts

### Ubuntu deployment
See `DEPLOY_UBUNTU.md` for a complete step-by-step guide (systemd service, Nginx, SSL).


