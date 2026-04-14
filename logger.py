#!/usr/bin/env python3
"""
logger.py — fetches current occupancy from SafeSpace and appends to docs/data/occupancy.csv
Only runs during gym hours (ET):
  Weekdays : 5:00 AM – 10:00 PM
  Weekends : 10:00 AM –  5:00 PM
"""

import csv
import json
import os
import re
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import pytz
import requests
import websocket

# ── Config ────────────────────────────────────────────────────────────────────
SPACE_ID      = "86fb9e11"
FULL_SPACE_ID = "86fb9e11-6795-4e98-ac36-67262d509fc6"
BASE_HTTP     = "https://app.safespace.io/veart/socket.io/"
BASE_WS       = "wss://app.safespace.io/veart/socket.io/"
CSV_PATH      = Path("docs/data/occupancy.csv")   # inside docs/ so GitHub Pages can serve it
TIMEZONE      = pytz.timezone("America/New_York")

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Origin":     "https://app.safespace.io",
    "Referer":    f"https://app.safespace.io/api/display/live-occupancy/{SPACE_ID}?view=number",
}

# ── Hours check ───────────────────────────────────────────────────────────────
def is_within_hours() -> bool:
    now     = datetime.now(TIMEZONE)
    weekday = now.weekday()          # 0=Mon … 6=Sun
    hour    = now.hour + now.minute / 60.0

    if weekday < 5:                  # Monday–Friday
        return 5.50 <= hour < 22.5   # 6:00 AM – 10:00 PM
    else:                            # Saturday–Sunday
        return 9.50 <= hour < 17.5  # 10:00 AM – 5:00 PM

# ── WebSocket fetch ───────────────────────────────────────────────────────────
def get_sid():
    r = requests.get(BASE_HTTP, params={"EIO": 3, "transport": "polling"},
                     headers=HEADERS, timeout=10)
    r.raise_for_status()
    m = re.search(r'\{.*\}', r.text)
    if not m:
        raise ValueError(f"No JSON in handshake: {r.text[:200]}")
    data   = json.loads(m.group(0))
    cookie = "; ".join(f"{k}={v}" for k, v in r.cookies.items())
    return data["sid"], cookie

def fetch_occupancy(timeout: int = 20) -> int:
    sid, cookie = get_sid()
    ws_url = BASE_WS + f"?EIO=3&transport=websocket&sid={sid}"

    ws_headers = {"Origin": HEADERS["Origin"], "User-Agent": HEADERS["User-Agent"]}
    if cookie:
        ws_headers["Cookie"] = cookie

    result = {"value": None, "done": threading.Event()}

    def on_open(ws):
        ws.send("2probe")

    def on_message(ws, msg):
        if msg == "3probe":
            ws.send("5")
            time.sleep(0.1)
            ws.send("40")
            time.sleep(0.1)
            ws.send(f'42["manualoccupancy:subscribe","{FULL_SPACE_ID}"]')
        elif msg == "2":
            ws.send("3")
        elif msg.startswith("42"):
            try:
                arr = json.loads(msg[2:])
                if (isinstance(arr, list) and len(arr) >= 2
                        and arr[0] == "manualoccupancy:data"
                        and "occupants" in arr[1]):
                    result["value"] = int(arr[1]["occupants"])
                    ws.close()
                    result["done"].set()
            except Exception:
                pass

    def on_error(ws, err):
        print(f"[ws] error: {err}", file=sys.stderr)
        result["done"].set()

    def on_close(ws, *_):
        result["done"].set()

    ws = websocket.WebSocketApp(
        ws_url, header=ws_headers,
        on_open=on_open, on_message=on_message,
        on_error=on_error, on_close=on_close,
    )
    t = threading.Thread(target=ws.run_forever, kwargs={"ping_interval": 0}, daemon=True)
    t.start()
    result["done"].wait(timeout=timeout)
    ws.close()

    if result["value"] is None:
        raise RuntimeError("Timed out waiting for occupancy data")
    return result["value"]

# ── CSV logging ───────────────────────────────────────────────────────────────
def append_csv(count: int):
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    write_header = not CSV_PATH.exists() or CSV_PATH.stat().st_size == 0

    now = datetime.now(TIMEZONE)
    row = {
        "timestamp": now.isoformat(timespec="seconds"),
        "day":       now.strftime("%A"),
        "date":      now.strftime("%Y-%m-%d"),
        "hour":      round(now.hour + now.minute / 60.0, 4),
        "count":     count,
    }

    with CSV_PATH.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if write_header:
            writer.writeheader()
        writer.writerow(row)

    print(f"Logged: {count} people at {row['timestamp']}")

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not is_within_hours():
        now = datetime.now(TIMEZONE)
        print(f"Outside gym hours ({now.strftime('%A %I:%M %p ET')}) — skipping.")
        sys.exit(0)

    count = fetch_occupancy()
    append_csv(count)
