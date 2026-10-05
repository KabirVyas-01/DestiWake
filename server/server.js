/**
 * DestiWake (GeoNap) Backend Service (Node.js)
 * --------------------------------------------
 * Zero-dependency native Node.js REST API & static file server.
 * Supports geofencing engine, station database, commute session logging,
 * puzzle verification, and video streaming with HTTP byte-range requests.
 */

const http = require('http');
const fs = require('fs');
const path = require('path');
const url = require('url');

const PORT = process.env.PORT || 5000;
const BASE_DIR = path.resolve(__dirname, '..');
const DATA_DIR = path.resolve(__dirname, 'data');

// MIME types dictionary
const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.mp4': 'video/mp4',
  '.webm': 'video/webm',
  '.wav': 'audio/wav',
  '.mp3': 'audio/mpeg'
};

// In-memory active live trip shares
const activeShares = new Map();

// Helper: Haversine distance in kilometers
function haversineKm(lat1, lon1, lat2, lon2) {
  const R = 6371.0;
  const toRad = (deg) => (deg * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) *
    Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return Math.round(R * c * 100) / 100;
}

// Helper: Safe JSON file reader
function readJsonFile(filePath, fallback) {
  try {
    if (fs.existsSync(filePath)) {
      const data = fs.readFileSync(filePath, 'utf8');
      return JSON.parse(data);
    }
  } catch (err) {
    console.error(`Error reading ${filePath}:`, err.message);
  }
  return fallback;
}

// Helper: Safe JSON file writer
function writeJsonFile(filePath, data) {
  try {
    fs.writeFileSync(filePath, JSON.stringify(data, null, 2), 'utf8');
    return true;
  } catch (err) {
    console.error(`Error writing ${filePath}:`, err.message);
    return false;
  }
}

// Helper: Send JSON response
function sendJson(res, statusCode, data) {
  const body = Buffer.from(JSON.stringify(data));
  res.writeHead(statusCode, {
    'Content-Type': 'application/json; charset=utf-8',
    'Content-Length': body.length,
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization'
  });
  res.end(body);
}

// Parse JSON request body
function parseRequestBody(req) {
  return new Promise((resolve) => {
    let raw = '';
    req.on('data', chunk => { raw += chunk; });
    req.on('end', () => {
      try {
        resolve(raw ? JSON.parse(raw) : {});
      } catch (e) {
        resolve({});
      }
    });
    req.on('error', () => resolve({}));
  });
}

// Create HTTP Server
const server = http.createServer(async (req, res) => {
  // CORS Preflight
  if (req.method === 'OPTIONS') {
    res.writeHead(204, {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization'
    });
    return res.end();
  }

  const parsedUrl = url.parse(req.url, true);
  const pathname = parsedUrl.pathname;

  // --- REST API ENDPOINTS ---
  if (pathname.startsWith('/api/')) {
    
    // 1. Health Status
    if (req.method === 'GET' && pathname === '/api/health') {
      return sendJson(res, 200, {
        status: 'online',
        service: 'DestiWake GeoNap Backend (Node.js)',
        version: '1.0.0',
        uptimeSec: Math.round(process.uptime()),
        timestamp: new Date().toISOString()
      });
    }

    // 2. Stations Database Search
    if (req.method === 'GET' && pathname === '/api/stations') {
      const stations = readJsonFile(path.join(DATA_DIR, 'stations.json'), []);
      const query = (parsedUrl.query.q || '').trim().toLowerCase();
      const results = query
        ? stations.filter(s => s.name.toLowerCase().includes(query) || s.city.toLowerCase().includes(query))
        : stations;
      return sendJson(res, 200, { stations: results });
    }

    // 3. Commute Nap History & Metrics
    if (req.method === 'GET' && pathname === '/api/history') {
      const history = readJsonFile(path.join(DATA_DIR, 'history.json'), {
        totalNaps: 0,
        onTimePercentage: 100,
        totalSleepMinutes: 0,
        averageBufferMinutes: 8.4,
        recentSessions: []
      });
      return sendJson(res, 200, history);
    }

    // 4. Record Completed Nap Session
    if (req.method === 'POST' && pathname === '/api/history') {
      const body = await parseRequestBody(req);
      const historyFile = path.join(DATA_DIR, 'history.json');
      const history = readJsonFile(historyFile, {
        totalNaps: 0,
        onTimePercentage: 100,
        totalSleepMinutes: 0,
        averageBufferMinutes: 8.4,
        recentSessions: []
      });

      const newSession = {
        id: `nap_${Date.now()}`,
        date: new Date().toISOString(),
        origin: body.origin || 'Origin Station',
        destination: body.destination || 'Destination Station',
        vehicle: body.vehicle || 'train',
        speedAvgKmH: body.speedAvgKmH || 86,
        distanceCoveredKm: body.distanceCoveredKm || 24.8,
        napDurationMinutes: body.napDurationMinutes || 20,
        geofenceRadiusKm: body.geofenceRadiusKm || 10.0,
        status: body.status || 'COMPLETED',
        cognitiveSolved: body.cognitiveSolved !== false
      };

      history.recentSessions.unshift(newSession);
      history.totalNaps += 1;
      history.totalSleepMinutes += newSession.napDurationMinutes;
      writeJsonFile(historyFile, history);

      return sendJson(res, 201, { success: true, session: newSession, history });
    }

    // 5. Dynamic Cognitive Arithmetic Puzzle Generator
    if (req.method === 'GET' && pathname === '/api/puzzle/new') {
      const num1 = Math.floor(Math.random() * 38) + 11;
      const num2 = Math.floor(Math.random() * 38) + 11;
      const correct = num1 + num2;

      const distractors = new Set();
      while (distractors.size < 3) {
        const offset = [-10, -2, -1, 1, 2, 10, -8, 8][Math.floor(Math.random() * 8)];
        const cand = correct + offset;
        if (cand > 0 && cand !== correct) distractors.add(cand);
      }

      const choices = [...distractors, correct].sort(() => Math.random() - 0.5);
      return sendJson(res, 200, {
        puzzleId: `puz_${Date.now()}`,
        equation: `${num1} + ${num2} = ?`,
        num1,
        num2,
        choices,
        correctAnswer: correct
      });
    }

    // 6. Geofence & Proximity Detection Verification
    if (req.method === 'POST' && pathname === '/api/geofence/check') {
      const body = await parseRequestBody(req);
      const currLat = parseFloat(body.currentLat || 0);
      const currLng = parseFloat(body.currentLng || 0);
      const destLat = parseFloat(body.destLat || 0);
      const destLng = parseFloat(body.destLng || 0);
      const radiusKm = parseFloat(body.radiusKm || 10.0);
      const speedKmH = Math.max(5.0, parseFloat(body.speedKmH || 80.0));

      const distKm = haversineKm(currLat, currLng, destLat, destLng);
      const isBreached = distKm <= radiusKm;
      const remainingKm = Math.max(0.0, distKm - radiusKm);
      const safeNapMin = Math.round((remainingKm / speedKmH) * 60);
      const totalEtaMin = Math.round((distKm / speedKmH) * 60);

      let alertStage = 0;
      if (distKm <= 3.0) alertStage = 3;
      else if (isBreached) alertStage = 2;
      else if (distKm <= (radiusKm * 1.5)) alertStage = 1;

      return sendJson(res, 200, {
        distanceKm: distKm,
        geofenceRadiusKm: radiusKm,
        isBreached,
        alertStage,
        safeNapMinutes: safeNapMin,
        totalEtaMinutes: totalEtaMin,
        currentSpeedKmH: speedKmH
      });
    }

    // 7. Live Emergency Trip Share
    if (req.method === 'POST' && pathname === '/api/share/live') {
      const body = await parseRequestBody(req);
      const shareId = `trip_${Math.floor(Math.random() * 89999 + 10000)}`;
      const shareData = {
        shareId,
        origin: body.origin || '',
        destination: body.destination || '',
        distanceLeftKm: body.distanceLeftKm || 0,
        etaMinutes: body.etaMinutes || 0,
        createdAt: new Date().toISOString()
      };
      activeShares.set(shareId, shareData);
      return sendJson(res, 201, { shareId, share: shareData });
    }

    return sendJson(res, 404, { error: 'API route not found' });
  }

  // --- STATIC FILE SERVING & VIDEO STREAMING ---
  let safePath = path.normalize(decodeURIComponent(pathname)).replace(/^(\.\.[\/\\])+/, '');
  if (safePath === '/' || safePath === '\\') safePath = '/index.html';

  let filePath = path.join(BASE_DIR, safePath);

  // Fallback to index.html if file doesn't exist
  if (!fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
    filePath = path.join(BASE_DIR, 'index.html');
  }

  const ext = path.extname(filePath).toLowerCase();
  const contentType = MIME_TYPES[ext] || 'application/octet-stream';
  const stat = fs.statSync(filePath);
  const fileSize = stat.size;

  // Support Byte-Range requests for video scrubbing & streaming
  const range = req.headers.range;
  if (range && range.startsWith('bytes=')) {
    const parts = range.replace(/bytes=/, '').split('-');
    const start = parseInt(parts[0], 10);
    const end = parts[1] ? parseInt(parts[1], 10) : fileSize - 1;
    const chunkSize = (end - start) + 1;

    res.writeHead(206, {
      'Content-Range': `bytes ${start}-${end}/${fileSize}`,
      'Accept-Ranges': 'bytes',
      'Content-Length': chunkSize,
      'Content-Type': contentType,
      'Access-Control-Allow-Origin': '*'
    });

    const fileStream = fs.createReadStream(filePath, { start, end });
    return fileStream.pipe(res);
  }

  res.writeHead(200, {
    'Content-Length': fileSize,
    'Content-Type': contentType,
    'Accept-Ranges': 'bytes',
    'Access-Control-Allow-Origin': '*'
  });

  fs.createReadStream(filePath).pipe(res);
});

server.listen(PORT, () => {
  console.log(`🚆 DestiWake (GeoNap) Node.js Backend listening on: http://localhost:${PORT}`);
  console.log(`📁 Serving client UI and REST API from: ${BASE_DIR}`);
});
