## Ubuntu 22.04+ Deployment Guide (WebSub - Instant News Drops)

### 1) Install prerequisites
```bash
sudo apt update && sudo apt install -y git python3 python3-venv python3-pip nginx
```

### 2) Clone the repo and set up virtualenv
```bash
cd ~
git clone <YOUR_REPO_URL> news-auto
cd news-auto
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env   # fill SUPERFEEDR_*, CALLBACK_URL, TIRI_*, FACEBOOK_*, TWITTER_* values
```

### 3) Subscribe to feeds (one-time setup)
```bash
source .venv/bin/activate
python -m app.cli.subscribe_feeds
```

### 4) Start the WebSub server
```bash
source .venv/bin/activate
uvicorn app.server:app --host 0.0.0.0 --port 8000
```

### 5) Keep the server running with systemd
```bash
sudo tee /etc/systemd/system/news-websub.service >/dev/null <<'EOF'
[Unit]
Description=News Auto Publisher WebSub Server
After=network.target

[Service]
WorkingDirectory=%h/news-auto
ExecStart=%h/news-auto/.venv/bin/uvicorn app.server:app --host 0.0.0.0 --port 8000
Restart=always
User=%u
EnvironmentFile=%h/news-auto/.env

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now news-websub
systemctl status news-websub
```

### 6) Set up Nginx reverse proxy (recommended)
```bash
sudo tee /etc/nginx/sites-available/news-websub >/dev/null <<'EOF'
server {
    listen 80;
    server_name yourdomain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/news-websub /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 7) SSL with Let's Encrypt (recommended)
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

### 8) Logs and monitoring
- App logs: `logs/app.log` (rotated daily, keep 1 day)
- Server logs: `journalctl -u news-websub -f`
- Nginx logs: `/var/log/nginx/access.log` and `/var/log/nginx/error.log`

### 9) Updates
```bash
cd ~/news-auto
git pull
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart news-websub
```

### 10) How it works
1. **WebSub subscriptions**: Superfeedr monitors RSS feeds
2. **Instant notifications**: When news drops, Superfeedr pushes to your webhook
3. **AI rephrasing**: Each item gets rewritten by Tiri/Groq LLM
4. **Multi-platform posting**: Posts to all configured Facebook pages and Twitter accounts
5. **No polling**: Only processes when news actually drops (instant)

### 11) Troubleshooting
- Check server status: `systemctl status news-websub`
- View logs: `journalctl -u news-websub -f`
- Test webhook: `curl https://yourdomain.com/health`
- Re-subscribe feeds: `python -m app.cli.subscribe_feeds`


