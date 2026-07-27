# FaceGuard Enterprise — Facial Recognition & Access System

[![CI Pipeline](https://github.com/arunabh14307/FacialAuth/actions/workflows/ci.yml/badge.svg)](https://github.com/arunabh14307/FacialAuth/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Flask 3.0+](https://img.shields.io/badge/flask-3.0+-green.svg)](https://flask.palletsprojects.com/)

**FaceGuard Enterprise** is a high-performance, production-ready facial authentication access system built on Flask, OpenCV YuNet, MediaPipe, and SFace Deep Learning embeddings. Designed following **OWASP Top 10** guidelines, it provides biometric access control, liveness/gesture verification, account protection, audit logging, and responsive administrative dashboards.

---

## Key Features

### Security & Compliance
- **OWASP Top 10 Hardened**: CSRF Protection, Rate Limiting, Input Sanitization, and Secure HTTP Headers (`X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Content-Security-Policy`).
- **Encrypted Face Embeddings**: All 128-dimensional SFace feature vectors are encrypted using AES-256 Fernet key encryption before database storage.
- **Account Lockout & Protection**: Automatically locks accounts after multiple consecutive failed authentication attempts.
- **Session Hardening**: HttpOnly, SameSite=Lax, and configurable session inactivity timeouts.
- **Audit Logging**: Comprehensive security audit trail (`audit_logs`) tracking user registrations, status toggles, password updates, and login attempts.

### Facial & Liveness Verification
- **DNN Face Detection**: Uses OpenCV YuNet ONNX neural network for ultra-fast, accurate face localization and landmarking.
- **Image Quality Checks**: Real-time evaluation of camera lighting (brightness) and blur (Laplacian variance) before accepting biometrics.
- **Multi-Face & Distance Guard**: Prevents spoofing by warning against multiple faces in frame or distant captures.
- **Gesture Verification**: Random dynamic gesture challenges (smile, blink, head movements) powered by MediaPipe Face Landmarker.

### Administration & User Dashboards
- **Responsive Admin Panel**: Real-time access analytics, success rate metrics, and login attempt logs.
- **Data Export**: One-click CSV exports for registered users, login access logs, and security audit records.
- **User Management**: Activate/deactivate accounts, view facial registration details, and delete users safely.

### RESTful API & OpenAPI Documentation
- Clean REST API endpoints (`/api/v1/health`, `/api/v1/users`, `/api/v1/analytics`).
- Live OpenAPI 3.0 JSON Specification at `/api/v1/docs`.

---

## System Architecture

```text
                               ┌─────────────────────────┐
                               │   Client Browser / UI   │
                               └────────────┬────────────┘
                                            │ HTTP / WebCam
                                            ▼
 ┌─────────────────────────────────────────────────────────────────────────────────────┐
 │                                   Flask Application                                 │
 │                                                                                     │
 │  ┌───────────────────────┐   ┌───────────────────────────┐   ┌───────────────────┐  │
 │  │   Security Middleware  │   │  User / Admin Blueprints  │   │   REST API v1     │  │
 │  │ (Headers, Sanitizer)  │   │   (Flask Routes & Session)│   │  (OpenAPI Spec)   │  │
 │  └───────────┬───────────┘   └─────────────┬─────────────┘   └─────────┬─────────┘  │
 └──────────────┼─────────────────────────────┼───────────────────────────┼────────────┘
                │                             │                           │
                ▼                             ▼                           ▼
 ┌──────────────────────────┐   ┌───────────────────────────┐   ┌───────────────────┐
 │   OpenCV YuNet & SFace   │   │ AES-256 Embedding Engine  │   │ SQLite / Postgres │
 │ (Detection / Quality)    │   │ (Encryption / Decryption) │   │ (Indexed Database)│
 └──────────────────────────┘   └───────────────────────────┘   └───────────────────┘
```

---

## Quick Start

### 1. Prerequisites
- Python 3.10+
- Webcam / Camera hardware

### 2. Installation
```bash
git clone https://github.com/arunabh14307/FacialAuth.git
cd "Facial recognition login system"
python -m pip install -r requirements.txt
```

### 3. Running Locally
```bash
python app.py
```
Access the portals:
- **User Authentication**: [http://127.0.0.1:5000](http://127.0.0.1:5000)
- **Admin Portal**: [http://127.0.0.1:5000/admin/login](http://127.0.0.1:5000/admin/login)

---

## Docker Deployment

Build and run using Docker Compose:
```bash
docker-compose up --build -d
```

---

## Running Test Suite

Execute the native verification suite:
```bash
python -m unittest discover tests
```

---

## License
Licensed under the [MIT License](LICENSE).
