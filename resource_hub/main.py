from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from database import get_db_connection

app = FastAPI(title="Cenrixa Resource Hub")

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def read_dashboard(request: Request):
    conn = get_db_connection()
    meetings = conn.execute('''
        SELECT m.id, m.title, m.datetime, r.name as room_name 
        FROM meetings m 
        LEFT JOIN rooms r ON m.room_id = r.id 
        ORDER BY m.datetime ASC LIMIT 3
    ''').fetchall()
    
    tickets = conn.execute('SELECT id, title, status FROM tickets ORDER BY id DESC LIMIT 3').fetchall()
    conn.close()
    
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "meetings": meetings,
            "tickets": tickets
        }
    )

@app.get("/schedule", response_class=HTMLResponse)
async def read_schedule(request: Request):
    conn = get_db_connection()
    users = conn.execute('SELECT id, name FROM users').fetchall()
    rooms = conn.execute('SELECT id, name FROM rooms').fetchall()
    conn.close()
    
    return templates.TemplateResponse(
        request=request,
        name="schedule.html",
        context={
            "users": users,
            "rooms": rooms
        }
    )

@app.post("/api/meetings")
async def create_meeting(
    title: str = Form(...),
    host_id: int = Form(...),
    guest_id: int = Form(...),
    room_id: int = Form(None),
    datetime: str = Form(...)
):
    conn = get_db_connection()
    conn.execute(
        'INSERT INTO meetings (title, host_id, guest_id, room_id, datetime) VALUES (?, ?, ?, ?, ?)',
        (title, host_id, guest_id, room_id, datetime)
    )
    conn.commit()
    conn.close()
    
    # Redirect back to dashboard after standard HTML form submission
    return RedirectResponse(url="/", status_code=303)

@app.get("/rooms", response_class=HTMLResponse)
async def read_rooms(request: Request):
    conn = get_db_connection()
    rooms = conn.execute('SELECT * FROM rooms').fetchall()
    conn.close()
    
    return templates.TemplateResponse(
        request=request,
        name="rooms.html",
        context={
            "rooms": rooms
        }
    )

@app.get("/helpdesk", response_class=HTMLResponse)
async def read_helpdesk(request: Request):
    conn = get_db_connection()
    users = conn.execute('SELECT id, name FROM users').fetchall()
    conn.close()
    
    return templates.TemplateResponse(
        request=request,
        name="helpdesk.html",
        context={
            "users": users
        }
    )

@app.post("/api/tickets")
async def create_ticket(
    title: str = Form(...),
    description: str = Form(...),
    creator_id: int = Form(...)
):
    conn = get_db_connection()
    conn.execute(
        'INSERT INTO tickets (title, description, creator_id) VALUES (?, ?, ?)',
        (title, description, creator_id)
    )
    conn.commit()
    conn.close()
    
    return RedirectResponse(url="/", status_code=303)
