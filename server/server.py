#!/usr/bin/env python3
"""
DestiWake (GeoNap) Backend Service
----------------------------------
Zero-dependency transit alarm REST API & static file server.
Runs on standard Python 3 with built-in libraries.
"""

import http.server
import socketserver
import json
import math
import random
import os
import mimetypes
from pathlib import Path
from urllib.parse import urlparse, parse_qs

PORT = int(os.environ.get("PORT", 5000))
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(__file__).resolve().parent / "data"

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Helper: Haversine distance in kilometers
def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0 # Earth's radius in km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(R * c, 2)

# Helper: Load JSON file safely
def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

# Helper: Save JSON file safely
def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            return True
    except Exception as e:
        print(f"Error saving {path}: {e}")
        return False

# In-memory active live trip shares
active_shares = {}

class DestiWakeHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Enable CORS for API routes
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def send_json(self, status_code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json_body(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length > 0:
                raw_body = self.rfile.read(content_length).decode("utf-8")
                return json.loads(raw_body)
        except Exception as e:
            print("Failed to read JSON body:", e)
        return {}

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        # REST API Routes
        if path == "/api/health":
            self.send_json(200, {
                "status": "online",
                "service": "DestiWake GeoNap Backend",
                "version": "1.0.0",
                "engine": "Client/Server Hybrid GIS",
                "activeTripShares": len(active_shares)
            })
            return

        elif path == "/api/stations":
            stations = load_json(DATA_DIR / "stations.json", [])
            query = params.get("q", [""])[0].strip().lower()
            if query:
                stations = [
                    s for s in stations
                    if query in s.get("name", "").lower() or query in s.get("city", "").lower()
                ]
            self.send_json(200, {"stations": stations})
            return

        elif path == "/api/history":
            history = load_json(DATA_DIR / "history.json", {
                "totalNaps": 0,
                "onTimePercentage": 100,
                "totalSleepMinutes": 0,
                "averageBufferMinutes": 0,
                "recentSessions": []
            })
            self.send_json(200, history)
            return

        elif path == "/api/puzzle/new":
            # Generate a cognitive arithmetic wake-up puzzle
            num1 = random.randint(11, 49)
            num2 = random.randint(11, 49)
            correct = num1 + num2
            
            # Generate 3 plausible distractors
            distractors = set()
            while len(distractors) < 3:
                offset = random.choice([-10, -2, -1, 1, 2, 10, -8, 8])
                candidate = correct + offset
                if candidate > 0 and candidate != correct:
                    distractors.add(candidate)

            choices = list(distractors) + [correct]
            random.shuffle(choices)

            puzzle_id = f"puz_{random.randint(1000, 9999)}"
            self.send_json(200, {
                "puzzleId": puzzle_id,
                "equation": f"{num1} + {num2} = ?",
                "num1": num1,
                "num2": num2,
                "choices": choices,
                "correctAnswer": correct
            })
            return

        elif path.startswith("/api/share/"):
            share_id = path.split("/api/share/")[-1]
            if share_id in active_shares:
                self.send_json(200, {"share": active_shares[share_id]})
            else:
                self.send_json(404, {"error": "Trip share not found or expired"})
            return

        # Serve static files from workspace root
        return self.serve_static(path)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        body = self.read_json_body()

        # 1. Geofence & Proximity Detection Calculation Engine
        if path == "/api/geofence/check":
            curr_lat = float(body.get("currentLat", 0))
            curr_lng = float(body.get("currentLng", 0))
            dest_lat = float(body.get("destLat", 0))
            dest_lng = float(body.get("destLng", 0))
            radius_km = float(body.get("radiusKm", 10.0))
            speed_kmh = max(5.0, float(body.get("speedKmH", 80.0)))

            dist_km = haversine_km(curr_lat, curr_lng, dest_lat, dest_lng)
            is_breached = dist_km <= radius_km
            remaining_km = max(0.0, dist_km - radius_km)
            safe_nap_min = round((remaining_km / speed_kmh) * 60)
            total_eta_min = round((dist_km / speed_kmh) * 60)

            # Alert Escalation Stage determination
            alert_stage = 0
            if dist_km <= 3.0:
                alert_stage = 3 # Urgent siren failsafe
            elif is_breached:
                alert_stage = 2 # Main geofence alarm
            elif dist_km <= (radius_km * 1.5):
                alert_stage = 1 # Soft pre-chime warning

            self.send_json(200, {
                "distanceKm": dist_km,
                "geofenceRadiusKm": radius_km,
                "isBreached": is_breached,
                "alertStage": alert_stage,
                "safeNapMinutes": safe_nap_min,
                "totalEtaMinutes": total_eta_min,
                "currentSpeedKmH": speed_kmh
            })
            return

        # 2. Record Completed Nap Session in History
        elif path == "/api/history":
            history_file = DATA_DIR / "history.json"
            history = load_json(history_file, {
                "totalNaps": 0,
                "onTimePercentage": 100,
                "totalSleepMinutes": 0,
                "averageBufferMinutes": 8.0,
                "recentSessions": []
            })

            new_session = {
                "id": f"nap_{random.randint(100, 999)}",
                "date": body.get("date", "2026-10-05T12:00:00Z"),
                "origin": body.get("origin", "Transit Origin"),
                "destination": body.get("destination", "Wake Destination"),
                "vehicle": body.get("vehicle", "train"),
                "speedAvgKmH": body.get("speedAvgKmH", 85),
                "distanceCoveredKm": body.get("distanceCoveredKm", 25.0),
                "napDurationMinutes": body.get("napDurationMinutes", 20),
                "geofenceRadiusKm": body.get("geofenceRadiusKm", 10.0),
                "status": body.get("status", "COMPLETED"),
                "cognitiveSolved": body.get("cognitiveSolved", True)
            }

            history["recentSessions"].insert(0, new_session)
            history["totalNaps"] += 1
            history["totalSleepMinutes"] += new_session["napDurationMinutes"]
            save_json(history_file, history)

            self.send_json(201, {"success": True, "session": new_session, "history": history})
            return

        # 3. Create Live Emergency Trip Share Link
        elif path == "/api/share/live":
            share_id = f"trip_{random.randint(10000, 99999)}"
            active_shares[share_id] = {
                "shareId": share_id,
                "origin": body.get("origin", ""),
                "destination": body.get("destination", ""),
                "currentLat": body.get("currentLat", 0),
                "currentLng": body.get("currentLng", 0),
                "distanceLeftKm": body.get("distanceLeftKm", 0),
                "etaMinutes": body.get("etaMinutes", 0),
                "timestamp": "2026-10-05T12:00:00Z",
                "shareUrl": f"http://localhost:{PORT}/#share={share_id}"
            }
            self.send_json(201, {"shareId": share_id, "share": active_shares[share_id]})
            return

        # 4. Puzzle Verification
        elif path == "/api/puzzle/verify":
            num1 = int(body.get("num1", 0))
            num2 = int(body.get("num2", 0))
            submitted = int(body.get("submitted", 0))
            is_correct = (num1 + num2) == submitted

            self.send_json(200, {
                "verified": is_correct,
                "correctAnswer": num1 + num2,
                "message": "Cognitive Awake Verification Passed!" if is_correct else "Incorrect answer, try again."
            })
            return

        self.send_json(404, {"error": "Endpoint not found"})

    def serve_static(self, path):
        if path == "/" or path == "":
            path = "/index.html"

        file_path = BASE_DIR / path.lstrip("/")

        # Prevent directory traversal
        try:
            file_path = file_path.resolve()
            if not str(file_path).startswith(str(BASE_DIR)):
                self.send_error(403, "Access denied")
                return
        except Exception:
            self.send_error(404, "File not found")
            return

        if not file_path.is_file():
            # Fallback to index.html for SPA routing
            file_path = BASE_DIR / "index.html"

        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            mime_type = "application/octet-stream"

        try:
            file_size = file_path.stat().st_size
            
            # Support HTTP Range requests for video streaming
            range_header = self.headers.get("Range")
            if range_header and range_header.startswith("bytes="):
                parts = range_header.replace("bytes=", "").split("-")
                start = int(parts[0]) if parts[0] else 0
                end = int(parts[1]) if len(parts) > 1 and parts[1] else file_size - 1

                length = (end - start) + 1
                self.send_response(206)
                self.send_header("Content-Type", mime_type)
                self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                self.send_header("Content-Length", str(length))
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()

                with open(file_path, "rb") as f:
                    f.seek(start)
                    self.wfile.write(f.read(length))
                return

            self.send_response(200)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(file_size))
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()

            with open(file_path, "rb") as f:
                self.wfile.write(f.read())

        except Exception as e:
            print("Error serving static file:", e)
            self.send_error(500, "Internal server error")

def run():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), DestiWakeHandler) as httpd:
        print(f"🚆 DestiWake (GeoNap) Backend running at: http://localhost:{PORT}")
        print(f"📁 Serving static files and REST API from: {BASE_DIR}")
        print("Press Ctrl+C to stop.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down DestiWake backend.")

if __name__ == "__main__":
    run()
