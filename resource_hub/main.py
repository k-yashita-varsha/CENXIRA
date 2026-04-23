import os
import asyncio
import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv, set_key

from database import get_db_connection

load_dotenv()

# ─── DCR Config ────────────────────────────────────────────────
CENRIXA_BASE_URL = os.getenv("CENRIXA_BASE_URL", "http://localhost:8000/api/v1")
APP_NAME = "cenrixa-resource-hub"
REDIRECT_URI = "http://127.0.0.1:8001/auth/callback"
POLL_INTERVAL = 10  # seconds between status checks

# ─── Auto DCR Poller ───────────────────────────────────────────
async def dcr_auto_register():
    """
    On startup, register with CENRIXA and poll until approved.
    Once approved, saves CLIENT_ID and CLIENT_SECRET to .env automatically.
    """
    client_id = os.getenv("CLIENT_ID")
    if client_id:
        print(f"[DCR] Already registered with CLIENT_ID={client_id}. Skipping.")
        return

    print("[DCR] Starting Dynamic Client Registration with CENRIXA...")

    async with httpx.AsyncClient() as client:
        # Step 1: Register the app
        try:
            resp = await client.post(f"{CENRIXA_BASE_URL}/apps/register", json={
                "name": APP_NAME,
                "redirect_uris": [REDIRECT_URI],
                "base_url": "http://127.0.0.1:8001"
            }, timeout=10)
            result = resp.json()
            print(f"[DCR] Registration submitted. Status: {result.get('status')}")
        except Exception as e:
            print(f"[DCR] Could not reach CENRIXA. Will retry later. Error: {e}")
            return

        # Step 2: Poll until approved
        print("[DCR] Polling CENRIXA for approval (every 10 seconds)...")
        for attempt in range(180):  # Poll for up to 30 mins
            await asyncio.sleep(POLL_INTERVAL)
            try:
                status_resp = await client.get(
                    f"{CENRIXA_BASE_URL}/apps/status/{APP_NAME}", timeout=10
                )
                data = status_resp.json()
                status = data.get("status")
                print(f"[DCR] Poll #{attempt + 1}: Status = {status}")

                if status == "APPROVED":
                    cid = data.get("client_id")
                    csecret = data.get("client_secret")
                    # Save to .env automatically — Zero copy-paste!
                    env_path = os.path.join(os.path.dirname(__file__), ".env")
                    set_key(env_path, "CLIENT_ID", cid)
                    set_key(env_path, "CLIENT_SECRET", csecret)
                    os.environ["CLIENT_ID"] = cid
                    os.environ["CLIENT_SECRET"] = csecret
                    print(f"[DCR] ✅ APPROVED! Credentials saved to .env. CLIENT_ID={cid}")
                    return
                elif status == "REJECTED":
                    print("[DCR] ❌ Registration was rejected by Admin.")
                    return
            except Exception as e:
                print(f"[DCR] Poll error: {e}")

        print("[DCR] Polling timed out. App was not approved within 30 mins.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fire DCR registration in background — non-blocking
    asyncio.create_task(dcr_auto_register())
    yield


# ─── App Setup ─────────────────────────────────────────────────
app = FastAPI(title="CENRIXA Resource Hub", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key="resource_hub_super_secret_key")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8000")

def get_current_user(request: Request):
    return request.session.get("user")


# ─── Auth Routes ───────────────────────────────────────────────
@app.get("/login")
async def login():
    client_id = os.getenv("CLIENT_ID")
    if not client_id:
        return HTMLResponse("<h2 style='font-family:sans-serif;color:red'>⏳ App not yet approved by CENRIXA Admin. Please wait.</h2>")
    auth_url = f"{KEYCLOAK_URL}/auth/realms/cenrixa/protocol/openid-connect/auth"
    params = f"?client_id={client_id}&response_type=code&redirect_uri={REDIRECT_URI}&scope=openid profile email"
    return RedirectResponse(url=auth_url + params)


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/")


@app.get("/auth/callback")
async def auth_callback(request: Request, code: str):
    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    token_url = f"{KEYCLOAK_URL}/auth/realms/cenrixa/protocol/openid-connect/token"

    async with httpx.AsyncClient() as client:
        resp = await client.post(token_url, data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": REDIRECT_URI
        })
        token_data = resp.json()
        access_token = token_data.get("access_token")
        userinfo_resp = await client.get(
            f"{KEYCLOAK_URL}/auth/realms/cenrixa/protocol/openid-connect/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        user_data = userinfo_resp.json()

    ohrid = user_data.get("sub", "unknown")
    name = user_data.get("name", user_data.get("preferred_username", "Unknown User"))
    email = user_data.get("email", "unknown@cenrixa.com")
    roles = user_data.get("roles", [])
    role = "Manager" if "Manager" in roles or "Admin" in roles else "Trainee"

    # Upsert user
    conn = get_db_connection()
    existing = conn.execute("SELECT id FROM users WHERE ohrid = ?", (ohrid,)).fetchone()
    if existing:
        conn.execute("UPDATE users SET name=?, email=?, role=? WHERE ohrid=?", (name, email, role, ohrid))
        user_id = existing["id"]
    else:
        cursor = conn.execute("INSERT INTO users (ohrid, name, email, role) VALUES (?, ?, ?, ?)", (ohrid, name, email, role))
        user_id = cursor.lastrowid
    conn.commit()
    conn.close()

    request.session["user"] = {"id": user_id, "ohrid": ohrid, "name": name, "role": role}
    return RedirectResponse(url="/")


# ─── Pages ─────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    user = get_current_user(request)
    conn = get_db_connection()
    if user and user["role"] == "Manager":
        meetings = conn.execute('''
            SELECT m.id, m.title, m.datetime, r.name as room_name
            FROM meetings m LEFT JOIN rooms r ON m.room_id = r.id
            ORDER BY m.datetime ASC LIMIT 5
        ''').fetchall()
    elif user:
        meetings = conn.execute('''
            SELECT m.id, m.title, m.datetime, r.name as room_name
            FROM meetings m LEFT JOIN rooms r ON m.room_id = r.id
            WHERE m.host_id = ? OR m.guest_id = ?
            ORDER BY m.datetime ASC LIMIT 3
        ''', (user["id"], user["id"])).fetchall()
    else:
        meetings = []
    conn.close()
    return templates.TemplateResponse(request=request, name="dashboard.html", context={
        "user": user, "meetings": meetings
    })


@app.get("/schedule", response_class=HTMLResponse)
async def schedule_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/")
    conn = get_db_connection()
    users = conn.execute("SELECT id, name FROM users WHERE id != ?", (user["id"],)).fetchall()
    rooms = conn.execute("SELECT id, name FROM rooms").fetchall()
    conn.close()
    return templates.TemplateResponse(request=request, name="schedule.html", context={
        "user": user, "users": users, "rooms": rooms
    })


@app.post("/api/meetings")
async def create_meeting(
    request: Request,
    title: str = Form(...),
    guest_id: int = Form(...),
    room_id: int = Form(None),
    datetime: str = Form(...)
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/")
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO meetings (title, host_id, guest_id, room_id, datetime) VALUES (?, ?, ?, ?, ?)",
        (title, user["id"], guest_id, room_id, datetime)
    )
    conn.commit()
    conn.close()
    return RedirectResponse(url="/", status_code=303)


@app.get("/rooms", response_class=HTMLResponse)
async def rooms_page(request: Request):
    user = get_current_user(request)
    conn = get_db_connection()
    rooms = conn.execute("SELECT * FROM rooms").fetchall()
    conn.close()
    return templates.TemplateResponse(request=request, name="rooms.html", context={
        "user": user, "rooms": rooms
    })
