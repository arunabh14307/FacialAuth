# Production Deployment Guide

This document outlines deployment procedures for production environments using Docker, Gunicorn, Nginx, or Cloud platforms (Render, AWS, DigitalOcean).

---

## Production Security Checklist
- [x] `SECRET_KEY` set to a strong random 64-character string in environment variables.
- [x] `FLASK_ENV=production`.
- [x] Secure Cookies enabled (`SESSION_COOKIE_SECURE=True` over HTTPS).
- [x] Security headers active (`X-Frame-Options: DENY`, `Content-Security-Policy`).
- [x] Database path mounted on persistent disk volume.

---

## Deployment Option A: Docker Compose (Recommended)

1. **Build and Launch Container**:
   ```bash
   docker-compose up -d --build
   ```

2. **Check Logs**:
   ```bash
   docker-compose logs -f web
   ```

3. **Check Container Health**:
   ```bash
   curl -f http://localhost:5000/api/v1/health
   ```

---

## Deployment Option B: Render / Cloud PaaS

1. Connect your GitHub repository to **Render** or **Heroku**.
2. Set Environment Variables in dashboard:
   - `SECRET_KEY`: `<Random String>`
   - `RENDER_DISK_PATH`: `/var/data` (for persistent database & encodings)
3. Deploy automatically via `Procfile` / `render.yaml`.

---

## Nginx Reverse Proxy Configuration Template

```nginx
server {
    listen 80;
    server_name faceguard.yourdomain.com;

    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name faceguard.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/faceguard.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/faceguard.yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }
}
```
