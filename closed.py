# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "fastapi",
#     "uvicorn",
# ]
# ///

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def closed_page():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Closed</title>
        <style>
            body {
                background-color: #000;
                color: #fff;
                height: 100vh;
                margin: 0;
                display: flex;
                justify-content: center;
                align-items: center;
                font-family: sans-serif;
                overflow: hidden; /* Hide scrollbars */
            }
            h1 {
                font-size: 10vw; /* Responsive huge size */
                font-weight: bold;
                margin: 0;
                letter-spacing: 0.05em;
            }
        </style>
    </head>
    <body>
        <h1>CLOSED til 19:30</h1>
    </body>
    </html>
    """

if __name__ == "__main__":
    # Host 0.0.0.0 makes it accessible to the display
    uvicorn.run(app, host="0.0.0.0", port=8000)
