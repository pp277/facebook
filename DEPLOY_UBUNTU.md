## Ubuntu 22.04+ Deployment Guide (Beginner Friendly)

### 1) Install prerequisites
```bash
sudo apt update && sudo apt install -y git python3 python3-venv python3-pip
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
nano .env   # fill FEEDS, PLATFORMS, TIRI_*, FACEBOOK_*, TWITTER_* values
```

### 3) Test a one-off publish
```bash
source .venv/bin/activate
python -m app.cli.publish_once
```

### 4) Optional API server (health/webhook)
```bash
source .venv/bin/activate
uvicorn app.server:app --host 0.0.0.0 --port 8000
```

### 5) Keep the server running with systemd (optional)
```bash
sudo tee /etc/systemd/system/news-server.service >/dev/null <<'EOF'
[Unit]
Description=News Auto Publisher API
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
sudo systemctl enable --now news-server
systemctl status news-server
```

### 6) Schedule publishing

Option A: Cron (simple)
```bash
crontab -e
# every 10 minutes
*/10 * * * * cd $HOME/news-auto && . .venv/bin/activate && python -m app.cli.publish_once >> $HOME/news-auto/cron.log 2>&1
```

Option B: systemd timer (robust)
```bash
sudo tee /etc/systemd/system/news-publish.service >/dev/null <<'EOF'
[Unit]
Description=News Auto Publish Once

[Service]
WorkingDirectory=%h/news-auto
ExecStart=%h/news-auto/.venv/bin/python -m app.cli.publish_once
EnvironmentFile=%h/news-auto/.env
User=%u
EOF

sudo tee /etc/systemd/system/news-publish.timer >/dev/null <<'EOF'
[Unit]
Description=Run News Publish every 10 minutes

[Timer]
OnBootSec=2min
OnUnitActiveSec=10min
Unit=news-publish.service

[Install]
WantedBy=timers.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now news-publish.timer
systemctl list-timers | grep news-publish
```

### 7) Logs
- App logs: `logs/app.log` (rotated daily, keep 1 day)
- Cron logs: `cron.log` in project root (if using cron)

### 8) Updates
```bash
cd ~/news-auto
git pull
source .venv/bin/activate
pip install -r requirements.txt
```


