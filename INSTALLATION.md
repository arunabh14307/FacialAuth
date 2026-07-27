# Installation & Environment Setup Guide

Follow this guide to set up **FaceGuard Enterprise** on Linux, macOS, or Windows environments.

---

## System Requirements
- **Operating System**: Linux (Ubuntu 20.04+), macOS 12+, or Windows 10/11
- **Python Version**: Python 3.10, 3.11, or 3.12
- **Memory**: Minimum 2 GB RAM (4 GB recommended)
- **Webcam**: Integrated or USB camera for facial capture

---

## Step 1: Clone Repository
```bash
git clone https://github.com/arunabh14307/FacialAuth.git
cd "Facial recognition login system"
```

---

## Step 2: Set Up Python Virtual Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment (Linux/macOS)
source venv/bin/activate

# Activate virtual environment (Windows PowerShell)
.\venv\Scripts\Activate.ps1
```

---

## Step 3: Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Step 4: Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Edit `.env` to set your custom production variables:
```env
SECRET_KEY=your-custom-production-secret-key
SESSION_TIMEOUT_MINUTES=30
MAX_LOGIN_ATTEMPTS=5
```

---

## Step 5: Start Application
```bash
python app.py
```

The application starts on `http://127.0.0.1:5000`.
