# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "fastapi",
#     "uvicorn",
#     "python-escpos[usb]",
#     "gpiozero",
#     "jinja2",
#     "rpi-lgpio",
# ]
# ///

import json
import time
import os
import subprocess
from datetime import datetime
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, BackgroundTasks, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from escpos.printer import Usb, Dummy
from gpiozero import Button

# --- CONFIGURATION ---
DB_FILE = "queue_db.json"
ADMIN_URL = "secret-admin-panel" # Access at http://pi-ip:8000/secret-admin-panel
SOUND_FILE = "ding.wav"          # Put a wav file in the same folder
GPIO_PIN = 17                    # Wire Button: GPIO17 & GND

# PRINTER CONFIG (Run 'lsusb' to find these!)
PRINTER_VENDOR_ID = 0x04b8       # Replace with your Vendor ID
PRINTER_PRODUCT_ID = 0x0202      # Replace with your Product ID

# --- HARDWARE SETUP ---
try:
    # Try connecting to real printer
    p = Usb(PRINTER_VENDOR_ID, PRINTER_PRODUCT_ID)
except Exception:
    print("⚠️ Printer not found. Using Dummy mode (printing to console).")
    p = Dummy()

# Button setup (connects to GPIO and Ground)
# bounce_time prevents double clicks
btn = Button(GPIO_PIN, pull_up=True, bounce_time=0.5)

# --- DATABASE HELPERS ---
def load_db():
    if not os.path.exists(DB_FILE):
        return {"current": "---", "next_id": 1, "queue": []}
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

# --- HARDWARE FUNCTIONS ---
def play_sound():
    """Plays sound via HDMI/Audio Jack using ALSA"""
    if os.path.exists(SOUND_FILE):
        # -N prevents blocking the thread
        subprocess.Popen(["aplay", "-N", SOUND_FILE])

def print_ticket(number):
    """Prints a ticket with HUGE numbers"""
    try:
        p.text("\n")
        p.set(align='center')
        p.text("YOUR NUMBER\n")
        p.text("----------------\n")
        
        # 4x Height and 4x Width (Max typically 8, but 4 is safe)
        p.set(align='center', width=4, height=4) 
        p.text(f"{number}\n")
        
        # Reset and cut
        p.set(align='center', width=1, height=1)
        p.text("\n")
        p.text(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        p.cut()
    except Exception as e:
        print(f"Print Error: {e}")

def handle_physical_button():
    """Called when GPIO button is pressed"""
    db = load_db()
    ticket_num = db["next_id"]
    
    # 1. Add to queue
    ticket = {
        "number": ticket_num,
        "timestamp": datetime.now().strftime("%H:%M:%S")
    }
    db["queue"].append(ticket)
    db["next_id"] += 1
    save_db(db)
    
    # 2. Print
    print(f"🔘 Button Pressed! Printing ticket #{ticket_num}")
    print_ticket(ticket_num)

# Link GPIO event
btn.when_pressed = handle_physical_button

# --- FASTAPI APP ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("✅ System Started. Press Ctrl+C to stop.")
    yield
    print("🛑 Shutting down.")

app = FastAPI(lifespan=lifespan)

# --- ROUTES ---

@app.get("/", response_class=HTMLResponse)
async def display_page():
    """The Big Display (Kiosk)"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Queue Display</title>
        <style>
            body { background: #222; color: #fff; font-family: sans-serif; 
                   display: flex; justify-content: center; align-items: center; 
                   height: 100vh; margin: 0; text-align: center; }
            h1 { font-size: 5vw; margin: 0; color: #aaa; }
            #number { font-size: 35vw; font-weight: bold; line-height: 1; color: #0f0; }
        </style>
    </head>
    <body>
        <div>
            <h1>NOW SERVING</h1>
            <div id="number">...</div>
        </div>
        <script>
            async function poll() {
                try {
                    let res = await fetch('/api/status');
                    let data = await res.json();
                    document.getElementById('number').innerText = data.current;
                } catch(e) { console.log(e); }
            }
            setInterval(poll, 1000); // Check every 1 second
            poll();
        </script>
    </body>
    </html>
    """
    return html

@app.get(f"/{ADMIN_URL}", response_class=HTMLResponse)
async def admin_page():
    """The Secret Admin Panel"""
    db = load_db()
    queue_list_html = ""
    for ticket in db["queue"]:
        queue_list_html += f"""
        <div class="ticket">
            <span>#{ticket['number']} <small>({ticket['timestamp']})</small></span>
            <button onclick="callNumber({ticket['number']})">CALL</button>
        </div>
        """
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Admin Queue</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: sans-serif; padding: 20px; max-width: 600px; margin: 0 auto; }}
            .ticket {{ border: 1px solid #ccc; padding: 15px; margin-bottom: 10px; 
                       display: flex; justify-content: space-between; align-items: center; 
                       border-radius: 8px; background: #f9f9f9; }}
            button {{ background: #007bff; color: white; border: none; padding: 10px 20px; 
                      font-size: 16px; border-radius: 5px; cursor: pointer; }}
            button:active {{ background: #0056b3; }}
            h2 {{ border-bottom: 2px solid #333; padding-bottom: 10px; }}
        </style>
    </head>
    <body>
        <h2>Uncalled Tickets</h2>
        <div id="list">{queue_list_html or "No one in queue!"}</div>
        
        <script>
            async function callNumber(id) {{
                await fetch('/api/call/' + id, {{ method: 'POST' }});
                location.reload(); // Simple reload to refresh list
            }}
            // Auto refresh admin list every 5 seconds to see new tickets
            setTimeout(() => location.reload(), 5000);
        </script>
    </body>
    </html>
    """
    return html

@app.get("/api/status")
async def get_status():
    print("get status called")
    db = load_db()
    return {"current": db["current"]}

@app.post("/api/call/{ticket_id}")
async def call_number(ticket_id: int, background_tasks: BackgroundTasks):
    db = load_db()
    
    # Find ticket
    found = False
    new_queue = []
    for t in db["queue"]:
        if t["number"] == ticket_id:
            found = True
        else:
            new_queue.append(t)
            
    if found:
        db["current"] = ticket_id
        db["queue"] = new_queue
        save_db(db)
        
        # Trigger sound in background
        background_tasks.add_task(play_sound)
        return {"status": "called", "number": ticket_id}
    
    raise HTTPException(status_code=404, detail="Ticket not found")

if __name__ == "__main__":
    import uvicorn
    # 0.0.0.0 makes it accessible from other computers on the network
    uvicorn.run(app, host="0.0.0.0", port=8000)

