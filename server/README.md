# 🚆 DestiWake (GeoNap) Backend Service

This directory contains the zero-dependency backend server for **DestiWake (GeoNap)**, implementing the GIS geofencing engine, station search, commute history logging, dynamic cognitive math puzzles, and byte-range video streaming.

Both **Node.js** and **Python 3** implementations are provided with 100% feature parity and zero external third-party dependencies required.

---

## 🚀 Quick Start

### Option A: Run with Node.js
```bash
# From the project root
npm start
# or
node server/server.js
```

### Option B: Run with Python 3
```bash
# From the project root
npm run dev:py
# or
python server/server.py
```

The server will start at: `http://localhost:5000`

---

## 📡 REST API Reference

### 1. Health Status
* **Endpoint**: `GET /api/health`
* **Response**:
```json
{
  "status": "online",
  "service": "DestiWake GeoNap Backend",
  "version": "1.0.0",
  "uptimeSec": 124
}
```

### 2. Search Transit Stations
* **Endpoint**: `GET /api/stations?q=grand`
* **Response**:
```json
{
  "stations": [
    {
      "id": "gct",
      "name": "Grand Central Terminal",
      "city": "New York, NY",
      "lat": 40.7527,
      "lng": -73.9772,
      "lines": ["Metro-North Hudson", "Harlem", "Subway 4/5/6/7/S"],
      "type": "terminal",
      "defaultRadiusKm": 10.0
    }
  ]
}
```

### 3. Geofence & Proximity Detection Check
* **Endpoint**: `POST /api/geofence/check`
* **Request Body**:
```json
{
  "currentLat": 41.002,
  "currentLng": -73.650,
  "destLat": 40.7527,
  "destLng": -73.9772,
  "radiusKm": 10.0,
  "speedKmH": 86.0
}
```
* **Response**:
```json
{
  "distanceKm": 24.8,
  "geofenceRadiusKm": 10.0,
  "isBreached": false,
  "alertStage": 0,
  "safeNapMinutes": 10,
  "totalEtaMinutes": 17,
  "currentSpeedKmH": 86.0
}
```

### 4. Commute Nap History & Metrics
* **Endpoint**: `GET /api/history`
* **Response**:
```json
{
  "totalNaps": 48,
  "onTimePercentage": 100,
  "totalSleepMinutes": 2055,
  "averageBufferMinutes": 8.4,
  "recentSessions": [...]
}
```

### 5. Record Completed Nap Session
* **Endpoint**: `POST /api/history`
* **Request Body**:
```json
{
  "origin": "Stamford Station",
  "destination": "Grand Central Terminal",
  "vehicle": "train",
  "speedAvgKmH": 88,
  "distanceCoveredKm": 54.2,
  "napDurationMinutes": 38,
  "geofenceRadiusKm": 10.0,
  "status": "COMPLETED",
  "cognitiveSolved": true
}
```

### 6. Dynamic Cognitive Arithmetic Puzzle
* **Endpoint**: `GET /api/puzzle/new`
* **Response**:
```json
{
  "puzzleId": "puz_8241",
  "equation": "18 + 14 = ?",
  "num1": 18,
  "num2": 14,
  "choices": [30, 32, 34, 28],
  "correctAnswer": 32
}
```

### 7. Live Emergency Trip Share
* **Endpoint**: `POST /api/share/live`
* **Request Body**:
```json
{
  "origin": "Stamford Station",
  "destination": "Grand Central Terminal",
  "distanceLeftKm": 24.8,
  "etaMinutes": 18
}
```

---

## 🎥 Byte-Range Video Streaming Support
The server natively handles `Range: bytes=start-end` headers, allowing seamless scrubbing, seeking, and streaming of your demo AI video (`videos/demo.mp4`) in modern browsers.
