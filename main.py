# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "fastapi",
#     "uvicorn",
#     "python-escpos[usb]",
#     "jinja2",
#     "rpi-lgpio",
# ]
# ///

import json
import logging
import sys
import time
import os
import subprocess
import threading
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse

DISPLAY_ONLY = "--display-only" in sys.argv

if not DISPLAY_ONLY:
    from escpos.printer import Usb, Dummy
    import RPi.GPIO as GPIO

# --- CONFIGURATION ---
DB_FILE = "queue_db.json"
ADMIN_URL = "secret-admin-panel" 
SOUND_FILE = "ding.wav"
GPIO_PIN = 17  

# PRINTER CONFIG (Run 'lsusb' to find these!)
PRINTER_VENDOR_ID = 0x0fe6
PRINTER_PRODUCT_ID = 0x811e      

# --- HARDWARE SETUP: PRINTER ---
if not DISPLAY_ONLY:
    try:
        p = Usb(PRINTER_VENDOR_ID, PRINTER_PRODUCT_ID,  in_ep=0x82, out_ep=0x02)
    except Exception:
        print("⚠️ Printer not found. Using Dummy mode.")
        p = Dummy()

# --- DATABASE HELPERS ---
def load_db():
    if not os.path.exists(DB_FILE):
        return {"current": "---", "next_id": 1, "queue": [], "history": []}
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

# --- ACTION FUNCTIONS ---
#def play_sound():
#    if os.path.exists(SOUND_FILE):
#        subprocess.Popen(["aplay", "-N", SOUND_FILE])
current_sound_process = None

def play_sound():
    global current_sound_process
    
    # 1. If a sound is currently running, stop it to free the audio device
    if current_sound_process is not None and current_sound_process.poll() is None:
        try:
            current_sound_process.terminate()
            current_sound_process.wait(timeout=0.1) # Wait for it to actually let go
        except Exception:
            pass # Force kill if necessary or ignore errors

    # 2. Play the new sound
    if os.path.exists(SOUND_FILE):
        # -q quiets the text output
        current_sound_process = subprocess.Popen(["aplay", "-q", SOUND_FILE])

def print_ticket(number):
    try:
        p.text("\n")
        p.set(align='center')
        p.text("VUORONUMERO\n")
        p.text("----------------\n")
        p.set(align='center', width=4, height=4) 
        p.text(f"{number}\n")
        p.set(align='center', width=1, height=1)
        #p.text("\n")
        #p.text(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        p.cut()
    except Exception as e:
        print(f"❌ Print Error: {e}")

def handle_physical_button():
    """Logic to run when button is pressed"""
    print("🔘 Button press detected! Processing...")
    
    db = load_db()
    ticket_num = db["next_id"]
    
    # 1. Update DB
    ticket = {
        "number": ticket_num,
        "timestamp": datetime.now().strftime("%H:%M:%S")
    }
    db["queue"].append(ticket)
    db["next_id"] += 1
    save_db(db)
    
    # 2. Print
    print(f"🖨️ Printing ticket #{ticket_num}")
    print_ticket(ticket_num)
    play_sound()

# --- BACKGROUND BUTTON MONITOR ---
def monitor_button_loop():
    """
    Runs in a background thread. 
    Polls the GPIO pin exactly like your working script.
    """
    print(f"👀 Monitoring GPIO {GPIO_PIN} for presses...")
    
    # Setup GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(GPIO_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    
    last_state = 1 # 1 is unpressed (Pull Up)
    
    while True:
        try:
            current_state = GPIO.input(GPIO_PIN)
            
            # If button went from HIGH (1) to LOW (0)
            if current_state == 0 and last_state == 1:
                handle_physical_button()
                time.sleep(0.5) # Debounce delay
            
            last_state = current_state
            time.sleep(0.05) # Small sleep to save CPU
            
        except Exception as e:
            print(f"GPIO Error: {e}")
            time.sleep(1)

# --- FASTAPI APP ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    if not DISPLAY_ONLY:
        # STARTUP: Launch the button listener thread
        t = threading.Thread(target=monitor_button_loop, daemon=True)
        t.start()

    mode = " (display only)" if DISPLAY_ONLY else ""
    print(f"✅ System Started{mode}. Go to http://localhost:8000")
    yield
    # SHUTDOWN
    print("🛑 Shutting down.")
    if not DISPLAY_ONLY:
        try:
            GPIO.cleanup()
        except:
            pass

app = FastAPI(lifespan=lifespan)

# --- ROUTES ---
@app.get("/", response_class=HTMLResponse)
async def display_page():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Queue Display</title>
        <style>
            body { background: #222; color: #fff; font-family: monospace;
                   display: flex; justify-content: center; align-items: center; 
                   height: 100vh; margin: 0; text-align: center; }
            h1 { font-size: 3vw; margin: 0; color: #aaa; }
            #number { font-size: 25vw; font-weight: bold; line-height: 1; color: #f00; }
            #also { font-size: 2.5vw; margin-top: 2vh; color: #aaa; }
            #history { font-size: 5vw; color: #f00; margin-top: 1vh; letter-spacing: 0.1em; white-space: pre-line; }
        </style>
    </head>
    <body>
        <div>
            <h1>palvelemme numeroa / we serve number</h1>
            <div id="number">...</div>
            <div id="also">ja myös / and also</div>
            <div id="history"></div>
        </div>
        <script>
            async function poll() {
                try {
                    let res = await fetch('/api/status');
                    let data = await res.json();
                    document.getElementById('number').innerText = data.current;
                    let past = data.history.filter(n => n !== data.current).slice(0, 10);
                    document.getElementById('history').innerText = past.slice(0, 5).join('  ') + '\\n' + past.slice(5, 10).join('  ');
                } catch(e) { console.log(e); }
            }
            setInterval(poll, 200);
            poll();
        </script>
    </body>
    </html>
    """
    return html

@app.get(f"/{ADMIN_URL}", response_class=HTMLResponse)
async def admin_page():
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
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: sans-serif; padding: 20px; max-width: 600px; margin: 0 auto; }}
            .ticket {{ border: 1px solid #ccc; padding: 15px; margin-bottom: 10px; 
                       display: flex; justify-content: space-between; align-items: center; 
                       border-radius: 8px; background: #f9f9f9; }}
            button {{ background: #007bff; color: white; border: none; padding: 10px 20px; 
                      font-size: 16px; border-radius: 5px; cursor: pointer; }}
            button:active {{ background: #0056b3; }}
        </style>
    </head>
    <body>
        <h2>Now Serving: {db["current"]}</h2>
        <h2>Uncalled Tickets</h2>
        <div id="list">{queue_list_html or "No one in queue!"}</div>
        <script>
            async function callNumber(id) {{
                await fetch('/api/call/' + id, {{ method: 'POST' }});
                location.reload();
            }}
            setTimeout(() => location.reload(), 5000);
        </script>
    </body>
    </html>
    """
    return html

@app.get("/api/status")
async def get_status():
    if DISPLAY_ONLY:
        return {"current": 42, "history": [42, 41, 40, 39, 38, 37, 36, 35, 34, 33, 32]}
    db = load_db()
    return {"current": db["current"], "history": db.get("history", [])}

@app.post("/api/call/{ticket_id}")
async def call_number(ticket_id: int, background_tasks: BackgroundTasks):
    db = load_db()
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
        history = db.get("history", [])
        history = [n for n in history if n != ticket_id]
        history.insert(0, ticket_id)
        db["history"] = history[:11]
        save_db(db)
        background_tasks.add_task(play_sound)
        return {"status": "called", "number": ticket_id}
    
    raise HTTPException(status_code=404, detail="Ticket not found")
class StatusFilter(logging.Filter):
    def filter(self, record):
        return "/api/status" not in record.getMessage()

if __name__ == "__main__":
    import uvicorn
    logging.getLogger("uvicorn.access").addFilter(StatusFilter())
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    # 0.0.0.0 makes it accessible from other computers on the network
    uvicorn.run(app, host="0.0.0.0", port=port)

