# CENRIXA Resource Hub

An **independent, general-purpose Meeting Scheduler** built with FastAPI and Vanilla HTML/CSS. Designed to be seamlessly integrated into the CENRIXA ecosystem via **Dynamic Client Registration (DCR)** — zero manual credential copy-pasting.

---

## 🏗️ Architecture Overview

```
CENRIXA (Keycloak + Training Portal)
         │
         │  DCR Registration Handshake
         ▼
Resource Hub (FastAPI)
  - Polls CENRIXA for approval
  - Auto-saves credentials when approved
  - Keycloak SSO Login (OHR ID via Google/Okta)
  - Users dynamically created from Keycloak tokens
```

---

## 🚀 Features

- **Meeting Scheduler** — Book meetings with colleagues, assign rooms, set date & time
- **Room Browser** — View all bookable rooms and their capacity  
- **Dynamic DCR Registration** — Auto-registers with CENRIXA on startup; polls every 10s until Admin approves
- **Zero Copy-Paste** — Credentials are auto-saved to `.env` when approved
- **Role-Based Views** — Manager sees all meetings; Trainee sees only their own
- **CENRIXA SSO Login** — "Login via CENRIXA" button uses Keycloak + Google/Okta federation

---

## 📂 Project Structure

```
resource_hub/
├── main.py           # FastAPI app: routes, DCR polling, Keycloak SSO
├── database.py       # SQLite setup: users, rooms, meetings
├── static/
│   └── style.css     # Premium dark-mode Vanilla CSS
├── templates/
│   ├── base.html     # Shared layout with navigation
│   ├── dashboard.html
│   ├── schedule.html
│   └── rooms.html
├── .env              # Auto-generated after DCR approval (CLIENT_ID, CLIENT_SECRET)
└── resource_hub.db   # Auto-generated SQLite file
```

---

## ⚡ How to Run

### 1. Start the app
```bash
cd resource_hub
pip install fastapi uvicorn jinja2 python-multipart httpx python-dotenv itsdangerous
uvicorn main:app --reload --port 8001
```

### 2. What happens on startup
The app will **automatically**:
1. POST a registration request to `http://localhost:8000/api/v1/apps/register`
2. Begin polling CENRIXA every 10 seconds: `GET /api/v1/apps/status/cenrixa-resource-hub`
3. When a CENRIXA Manager/Admin approves it (see CENRIXA setup below), it auto-saves the `CLIENT_ID` and `CLIENT_SECRET` to `.env`
4. The app then becomes fully operational — users can click **Login via CENRIXA** and authenticate via Keycloak (Google/Okta)

---

## 🔑 CENRIXA Integration (DCR Flow)

### How DCR works (Zero Copy-Paste)

```
1. Resource Hub boots  →  Sends registration to CENRIXA
2. CENRIXA stores it as "PENDING"
3. CENRIXA Manager dashboard shows "App Approvals" section
4. Manager clicks "✅ Approve"
5. CENRIXA generates CLIENT_ID + CLIENT_SECRET, stores them
6. Resource Hub's background poller detects APPROVED status
7. Resource Hub auto-writes credentials to .env
8. App goes live — all CENRIXA users can now use it!
```

### CENRIXA Manager Dashboard
- A new **"🔌 App Approvals (DCR)"** section shows pending requests
- Clicking **Approve** activates the app
- A **"🚀 Active External Apps"** section shows all approved apps as clickable cards for all users

---

## 🔐 Authentication Flow

1. User is in CENRIXA, clicks "Resource Hub" in External Apps
2. Redirected to `http://127.0.0.1:8001/login`
3. Redirected to Keycloak → user logs in with OHR ID via Google/Okta
4. Keycloak returns a token to `/auth/callback`
5. App extracts `ohrid`, `name`, `email`, `role` from token
6. User is upserted into local `resource_hub.db`
7. User is now fully authenticated, their session is active

---

## 🗄️ Database Schema

| Table | Fields |
|-------|--------|
| `users` | `id`, `ohrid`, `name`, `email`, `role` |
| `rooms` | `id`, `name`, `capacity` |
| `meetings` | `id`, `title`, `host_id`, `guest_id`, `room_id`, `datetime` |

> **Users are never hardcoded.** They are created dynamically from Keycloak tokens on first login.

---

## 🔧 Environment Variables (Auto-Generated)

| Variable | Description |
|----------|-------------|
| `CLIENT_ID` | Auto-set after DCR approval |
| `CLIENT_SECRET` | Auto-set after DCR approval |
| `CENRIXA_BASE_URL` | Default: `http://localhost:8000/api/v1` |
| `KEYCLOAK_URL` | Default: `http://localhost:8000` |
