# Deployment Guide - Hermes v3.0

---

## Prerequisites

- Python 3.11+
- Node.js 18+ (for frontend)
- pip or uv package manager

---

## Local Development

### 1. Clone Repository

```bash
git clone https://github.com/ahmad-ubaidillah/hermes.git
cd hermes
```

### 2. Install Dependencies

```bash
# Python dependencies
pip install -r requirements.txt

# Frontend dependencies
cd web/frontend
npm install
cd ../..
```

### 3. Configure

```bash
# Create config directory
mkdir -p ~/.hermes

# Copy example config
cp config.example.yaml ~/.hermes/config.yaml
```

### 4. Run

```bash
# CLI mode
python cli.py

# Web mode
python -m web.backend.main

# Frontend dev
cd web/frontend && npm run dev
```

---

## Production Deployment

### Option 1: Docker

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "-m", "web.backend.main"]
```

```bash
docker build -t hermes:v3.0 .
docker run -p 8000:8000 hermes:v3.0
```

### Option 2: Systemd Service

```ini
# /etc/systemd/system/hermes.service
[Unit]
Description=Hermes AI Agent
After=network.target

[Service]
Type=simple
User=hermes
WorkingDirectory=/opt/hermes
ExecStart=/opt/hermes/venv/bin/python -m web.backend.main
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable hermes
sudo systemctl start hermes
```

### Option 3: Nginx Reverse Proxy

```nginx
# /etc/nginx/sites-available/hermes
server {
    listen 80;
    server_name hermes.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## Configuration

### config.yaml

```yaml
# Provider Configuration
provider: zai

models:
  fast: mimo-v2-omni-free
  coding: qwen3.6-plus-free
  complex: minimax-m2.5-free

limits:
  daily_tokens: 550000

# Agent Pool
agents:
  max_concurrent: 5
  default_timeout: 300

# Observability
observability:
  tracing:
    enabled: true
    export_file: ~/.hermes/traces.jsonl
  metrics:
    enabled: true
    prometheus_port: 9090

# Web Dashboard
web:
  host: 0.0.0.0
  port: 8000
  cors_origins:
    - http://localhost:3000

# Hooks
hooks:
  validate_file_access: true
  log_tool_execution: true
  auto_continue: true
```

---

## Monitoring

### Prometheus Metrics

```bash
# Metrics endpoint
curl http://localhost:9090/metrics
```

### Health Check

```bash
curl http://localhost:8000/health
```

### Logs

```bash
# View logs
tail -f ~/.hermes/logs/hermes.log

# View traces
tail -f ~/.hermes/traces.jsonl
```

---

## Scaling

### Horizontal Scaling

```
                    ┌─────────────┐
                    │   Nginx     │
                    │ Load Balancer│
                    └──────┬──────┘
           ┌───────────────┼───────────────┐
           │               │               │
     ┌─────▼─────┐   ┌─────▼─────┐   ┌─────▼─────┐
     │  Hermes   │   │  Hermes   │   │  Hermes   │
     │  Node 1   │   │  Node 2   │   │  Node 3   │
     └───────────┘   └───────────┘   └───────────┘
           │               │               │
           └───────────────┼───────────────┘
                           │
                    ┌──────▼──────┐
                    │   Redis     │
                    │ (State)     │
                    └─────────────┘
```

### Redis for State

```yaml
# config.yaml
state:
  backend: redis
  redis_url: redis://localhost:6379/0
```

---

## Security

### 1. API Authentication

```python
# Add to web/backend/main.py
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def verify_token(credentials = Depends(security)):
    if credentials.credentials != os.getenv("API_KEY"):
        raise HTTPException(401, "Invalid API key")
    return credentials

@app.get("/api/protected")
async def protected(user = Depends(verify_token)):
    return {"message": "authenticated"}
```

### 2. CORS

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-domain.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["*"],
)
```

### 3. Rate Limiting

```python
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@app.get("/api/tasks")
@limiter.limit("100/minute")
async def list_tasks(request: Request):
    ...
```

---

## Backup

```bash
# Backup data
tar -czf hermes-backup-$(date +%Y%m%d).tar.gz ~/.hermes/

# Backup to S3
aws s3 cp hermes-backup.tar.gz s3://your-bucket/backups/
```

---

## Troubleshooting

### Port Already in Use

```bash
# Find process
lsof -i :8000

# Kill process
kill -9 <PID>
```

### Memory Issues

```bash
# Check memory
free -h

# Limit memory
ulimit -v 4194304  # 4GB
```

### Logs Not Writing

```bash
# Check permissions
ls -la ~/.hermes/

# Fix permissions
chmod 755 ~/.hermes/
```
