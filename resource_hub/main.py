import os
import httpx
from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv

from database import get_db_connection

load_dotenv()

app = FastAPI(title="Cenrixa Resource Hub")

# Add Session Middleware for storing the logged in user
app.add_middleware(SessionMiddleware, secret_key="resource_hub_super_secret_key")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# CENRIXA KEYCLOAK CONFIG
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8000") # Assume central auth runs on 8000
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = "http://127.0.0.1:8001/auth/callback"

# Dependency to get current user
def get_current_user(request: Request):
    user = request.session.get("user")
    return user

@app.get("/login")
async def login():
    # Redirect to Keycloak authorization endpoint
    auth_url = f"{KEYCLOAK_URL}/auth/realms/cenrixa/protocol/openid-connect/auth"
    params = f"?client_id={CLIENT_ID}&response_type=code&redirect_uri={REDIRECT_URI}&scope=openid profile email"
    return RedirectResponse(url=auth_url + params)

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/")

@app.get("/auth/callback")
async def auth_callback(request: Request, code: str):
    # Exchange code for token
    token_url = f"{KEYCLOAK_URL}/auth/realms/cenrixa/protocol/openid-connect/token"
    async with httpx.AsyncClient() as client:
        # If DCR hasn't happened yet, we will mock the user for testing if there's no CLIENT_ID
        if not CLIENT_ID:
            # Mock SSO for demo if DCR wasn't run
            user_data = {
                "sub": "u-mock",
                "name": "Mock DCR User",
                "email": "mock@cenrixa.com",
                "roles": ["Trainee"]
            }
        else:
            resp = await client.post(token_url, data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "redirect_uri": REDIRECT_URI
            })
            token_data = resp.json()
            access_token = token_data.get("access_token")
            
            # Fetch user info
            userinfo_url = f"{KEYCLOAK_URL}/auth/realms/cenrixa/protocol/openid-connect/userinfo"
            userinfo_resp = await client.get(userinfo_url, headers={"Authorization": f"Bearer {access_token}"})
            user_data = userinfo_resp.json()

    # Extract dynamic user data
    ohrid = user_data.get("sub", "unknown")
    name = user_data.get("name", user_data.get("preferred_username", "Unknown User"))
    email = user_data.get("email", "unknown@cenrixa.com")
    
    # Simple role extraction (assuming roles are in the token)
    roles = user_data.get("roles", [])
    primary_role = "Admin" if "Admin" in roles or "IT_Support" in roles else "Trainee"

    # Upsert user in database
    conn = get_db_connection()
    existing = conn.execute("SELECT id FROM users WHERE ohrid = ?", (ohrid,)).fetchone()
    if existing:
        conn.execute("UPDATE users SET name=?, email=?, role=? WHERE ohrid=?", (name, email, primary_role, ohrid))
        user_id = existing["id"]
    else:
        cursor = conn.execute("INSERT INTO users (ohrid, name, email, role) VALUES (?, ?, ?, ?)", (ohrid, name, email, primary_role))
        user_id = cursor.lastrowid
    conn.commit()
    conn.close()

    # Save to session
    request.session["user"] = {
        "id": user_id,
        "ohrid": ohrid,
        "name": name,
        "role": primary_role
    }

    return RedirectResponse(url="/")


@app.get("/", response_class=HTMLResponse)
async def read_dashboard(request: Request):
    user = get_current_user(request)
    conn = get_db_connection()
    
    # Role-based meeting visibility
    if user and user["role"] == "Admin":
        meetings = conn.execute('''
            SELECT m.id, m.title, m.datetime, r.name as room_name 
            FROM meetings m 
            LEFT JOIN rooms r ON m.room_id = r.id 
            ORDER BY m.datetime ASC LIMIT 5
        ''').fetchall()
        tickets = conn.execute('SELECT id, title, status FROM tickets ORDER BY id DESC LIMIT 5').fetchall()
    elif user:
        meetings = conn.execute('''
            SELECT m.id, m.title, m.datetime, r.name as room_name 
            FROM meetings m 
            LEFT JOIN rooms r ON m.room_id = r.id 
            WHERE m.host_id = ? OR m.guest_id = ?
            ORDER BY m.datetime ASC LIMIT 3
        ''', (user["id"], user["id"])).fetchall()
        tickets = conn.execute('SELECT id, title, status FROM tickets WHERE creator_id = ? ORDER BY id DESC LIMIT 3', (user["id"],)).fetchall()
    else:
        meetings, tickets = [], []

    conn.close()
    return templates.TemplateResponse(request=request, name="dashboard.html", context={
        "user": user,
        "meetings": meetings,
        "tickets": tickets
    })

@app.get("/schedule", response_class=HTMLResponse)
async def read_schedule(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/")

    conn = get_db_connection()
    users = conn.execute('SELECT id, name FROM users WHERE id != ?', (user["id"],)).fetchall()
    rooms = conn.execute('SELECT id, name FROM rooms').fetchall()
    conn.close()
    
    return templates.TemplateResponse(request=request, name="schedule.html", context={
        "user": user,
        "users": users,
        "rooms": rooms
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
        'INSERT INTO meetings (title, host_id, guest_id, room_id, datetime) VALUES (?, ?, ?, ?, ?)',
        (title, user["id"], guest_id, room_id, datetime)
    )
    conn.commit()
    conn.close()
    return RedirectResponse(url="/", status_code=303)

@app.get("/rooms", response_class=HTMLResponse)
async def read_rooms(request: Request):
    user = get_current_user(request)
    conn = get_db_connection()
    rooms = conn.execute('SELECT * FROM rooms').fetchall()
    conn.close()
    
    return templates.TemplateResponse(request=request, name="rooms.html", context={
        "user": user,
        "rooms": rooms
    })

@app.get("/helpdesk", response_class=HTMLResponse)
async def read_helpdesk(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/")

    return templates.TemplateResponse(request=request, name="helpdesk.html", context={
        "user": user
    })

@app.post("/api/tickets")
async def create_ticket(
    request: Request,
    title: str = Form(...),
    description: str = Form(...)
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/")

    conn = get_db_connection()
    conn.execute(
        'INSERT INTO tickets (title, description, creator_id) VALUES (?, ?, ?)',
        (title, description, user["id"])
    )
    conn.commit()
    conn.close()
    return RedirectResponse(url="/", status_code=303)
