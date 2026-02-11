# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

quesys is a physical queue management system for Raspberry Pi. It issues numbered tickets via an arcade button + thermal printer, displays the currently-serving number on a web page, and provides an admin panel to call numbers (with sound notification).

## Running

Scripts use PEP 723 inline metadata for dependencies. Run with `uv run`:

```bash
uv run main.py        # Main queue system (FastAPI on port 8000)
uv run closed.py      # "Closed" placeholder page
```

## Deployment

```bash
./sync.sh             # rsync to Raspberry Pi (hostname: pi)
```

## Architecture

**main.py** — Single-file FastAPI app containing everything:
- **Web layer**: Public display (`/`), admin panel (`/secret-admin-panel`), API (`/api/status`, `/api/call/{ticket_id}`)
- **Hardware layer**: GPIO pin 17 button monitoring (threaded, 50ms poll), USB thermal printer (ESC/POS via python-escpos)
- **Persistence**: JSON file database (`queue_db.json`) storing current number, next ID, and ticket queue
- **Audio**: Plays `ding.wav` via `aplay` when a number is called

**closed.py** — Standalone FastAPI app showing a "closed" message as an alternative display.

**debug_scripts/** — Standalone test scripts for button and printer hardware.

## Key Details

- HTML/CSS is inline in Python files (no template files)
- Finnish-language UI ("VUORONUMERO" = queue number)
- Hardware config is hardcoded constants at top of main.py (GPIO pin, printer USB IDs, DB path)
- No tests, no linter config
