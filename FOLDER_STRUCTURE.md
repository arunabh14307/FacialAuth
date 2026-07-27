# Directory Architecture & Module Map

```text
Facial recognition login system/
├── admin/                      # Admin Panel Blueprint & Views
│   ├── routes.py               # Dashboard, Settings, CSV Export, Audit Logs
│   └── templates/admin/        # Glassmorphic Admin HTML Templates
│       ├── base.html
│       ├── dashboard.html
│       ├── logs.html
│       ├── settings.html
│       └── users.html
├── api/                        # RESTful API Blueprint
│   └── routes.py               # Health Check, Analytics, OpenAPI Specs
├── backend/                    # Core Business Logic & AI Engines
│   ├── config.py               # Environment & Enterprise Settings
│   ├── face_detection_yunet.onnx # YuNet Face Detection DNN Model
│   ├── face_landmarker.task    # MediaPipe 478 Landmark Model
│   ├── face_recognition_sface.onnx # SFace 128D Embedding Model
│   ├── models/
│   │   └── database.py         # Dual SQLite/Postgres DB & Audit Manager
│   └── modules/
│       ├── face_detection.py   # Detection, Blur & Brightness Checks
│       ├── face_recognition_mod.py # SFace Embedding & Cosine Matching
│       ├── gesture_detection.py # Liveness Gesture Analyzer
│       ├── logger.py           # Structured Logging Engine
│       ├── otp_service.py      # Multi-Port SMTP & API Email Dispatcher
│       └── security.py         # AES-256 Embedding Encryption & Sanitizer
├── data/                       # Application Storage & Logs
│   ├── face_encodings/         # Cropped Profile Avatars
│   └── logs/                   # app.log & security.log
├── static/                     # Web Frontend Assets
│   ├── css/                    # Glassmorphism Design System
│   └── js/                     # Camera Feed, Modal & Trigger Handlers
├── tests/                      # Verification Test Suite
│   ├── test_auth.py            # Integration & Health Tests
│   └── test_security.py        # Security & Encryption Tests
├── user/                       # User Panel Blueprint & Templates
│   ├── routes.py               # Registration, Login & User Dashboard
│   └── templates/              # User Portal HTML Templates
├── .env.example                # Environment Variable Template
├── app.py                      # Main Flask Entry Point & Security Middleware
├── Dockerfile                  # Production Multi-Stage Container Setup
├── docker-compose.yml          # Container Orchestration Spec
├── Procfile                    # Render / Heroku Deployment Entry
└── requirements.txt            # Python Dependencies
```
