# 🚆 DestiWake (GeoNap)
### *Intelligent Location-Based Transit Wake-Up Alarm & Nap Assistant*

[![Project Status](https://img.shields.io/badge/Status-Design%20%26%20Architecture-blue.svg)]()
[![Platform](https://img.shields.io/badge/Platform-Web%20%2F%20PWA%20%2F%20Mobile-green.svg)]()
[![License](https://img.shields.io/badge/License-MIT-purple.svg)]()

---

## 📌 Problem Statement

Every day, millions of students, commuters, and long-distance travelers face a common dilemma: they want to rest or nap during train, bus, or metro journeys, but **fear oversleeping and missing their station or stop**. 

Traditional time-based alarms are unreliable for transit because:
- Public transport frequently faces unexpected delays or speed fluctuations.
- Arrival times cannot be predicted accurately using simple clock alarms.
- Missed stations cause significant stress, safety risks, delays, and extra travel costs.

**DestiWake** solves this problem by using live GPS geofencing to wake travelers up exactly when they enter their chosen proximity radius (e.g., $10\text{ km}$, $2\text{ km}$, or custom time window) of their destination—allowing for peaceful, anxiety-free sleep.

---

## 💡 The Solution

DestiWake is a smart, client-side, offline-resilient location alarm system that monitors the traveler's live coordinates, models transit speed based on the vehicle type, calculates real-time distances, and sounds an unmissable alarm before arrival.

```
       [ Starting Point ]
              │
              │  🚄 Transit in progress (User asleep)
              ▼
   ┌──────────────────────┐
   │  15 km: Soft Chime   │  (Stage 1: Pre-wake warning)
   ├──────────────────────┤
   │  10 km: Main Alarm   │  (Stage 2: Geofence Triggered 🔔)
   ├──────────────────────┤
   │   3 km: Urgent Siren │  (Stage 3: Failsafe if not dismissed)
   └──────────────────────┘
              ▼
       [ 🏁 Destination Station ]
```

---

## ✨ Key Features

### 1. 🎯 Three-Way Custom Trigger Controls
- **Distance-Based Trigger**: Set custom radius via slider or direct input ($200\text{ m}$ to $50\text{ km}$).
- **Time-Based Trigger (ETA)**: Set wake-up time in advance (e.g., *"Wake me up 15 minutes before arrival"*).
- **Interactive Visual Geofence**: Expand or shrink the dynamic radius circle directly on the live map.

### 2. 🚄 Vehicle Profiles & Adaptive Speed Prediction
Eliminates the "Cold-Start" and "Signal Stoppage" calculation errors by utilizing pre-calibrated transit velocity models:
- 🚄 **Express / High-Speed Train** ($\sim 80\text{--}110\text{ km/h}$)
- 🚆 **Metro / Suburban Local Train** ($\sim 35\text{--}50\text{ km/h}$)
- 🚌 **Intercity Highway Bus** ($\sim 55\text{--}75\text{ km/h}$)
- 🚕 **City Cab / Auto / Car** ($\sim 25\text{--}40\text{ km/h}$)
- ⚙️ **Custom User Profile**

### 3. 🔊 Fail-Safe Audio & Vibration Engine
- **Synthesized Alarm Tones**: Generates sound using the **Web Audio API** oscillator hardware buffer—works 100% offline without needing external audio files to download.
- **Multi-Tone Library**: Classic Alarm, Train Whistle, Gentle Chime, Urgent Siren.
- **Vibration Feedback**: Rhythmic hardware vibration patterns via the `navigator.vibrate` API.
- **Two-Stage / Escalating Wake-Up**: Gentle reminder $\to$ full alarm $\to$ high-intensity alert.

### 4. 🧠 Cognitive Wake-Up Verification (Anti-Oversleep)
- Prevents groggy passengers from accidentally dismissing the alarm and falling back asleep.
- Requires completing a simple confirmation slider or mini math puzzle (e.g., $14 + 19 = ?$) to silence the alarm.

### 5. ⚡ Battery-Conscious Adaptive GPS Polling
- **Long Distance ($> 50\text{ km}$)**: Low-power interval polling (every 90s).
- **Medium Distance ($20\text{--}50\text{ km}$)**: Balanced polling (every 30s).
- **Near Geofence ($\le 20\text{ km}$)**: High-accuracy continuous tracking.
- **Screen Wake Lock API**: Keeps the browser process active and prevents OS sleep interruptions.

### 6. 🧪 Built-In Transit Simulator
- Test and demo the app without boarding a real train!
- Simulate custom routes, virtual speeds ($30\text{--}120\text{ km/h}$), signal stoppages, and verify geofence alarm triggers in real time.

### 7. 📶 Offline-Ready & Tunnel Resilience
- 100% client-side distance computation.
- **Vector Extrapolation**: If satellite GPS drops inside a tunnel or remote mountain, the app extrapolates position based on the last known velocity vector until GPS reconnects.

---

## 📐 Mathematical & Algorithmic Foundation

### 1. Great-Circle Distance (Haversine Formula)
To calculate true surface distance between user coordinate $(\phi_1, \lambda_1)$ and destination $(\phi_2, \lambda_2)$:

$$\Delta\phi = \phi_2 - \phi_1 \quad (\text{latitude difference in radians})$$

$$\Delta\lambda = \lambda_2 - \lambda_1 \quad (\text{longitude difference in radians})$$

$$a = \sin^2\left(\frac{\Delta\phi}{2}\right) + \cos(\phi_1)\cdot\cos(\phi_2)\cdot\sin^2\left(\frac{\Delta\lambda}{2}\right)$$

$$c = 2 \cdot \operatorname{atan2}\left(\sqrt{a}, \sqrt{1-a}\right)$$

$$d = R \cdot c \quad (\text{Earth Radius } R \approx 6,371\text{ km})$$

### 2. Velocity Smoothing (Exponential Moving Average)
Filters out raw GPS jitter and signal noise:

$$v_{\text{smooth}}(t) = \alpha \cdot v_{\text{current}} + (1 - \alpha) \cdot v_{\text{smooth}}(t-1)$$

### 3. Safe Nap Window Calculation

$$\text{Time to Alarm} = \frac{d_{\text{current}} - R_{\text{trigger}}}{v_{\text{effective}}}$$

---

## 🔄 State Machine Architecture

```
                 ┌───────────────┐
                 │     IDLE      │
                 └───────┬───────┘
                         │ User selects destination & vehicle profile
                         ▼
             ┌───────────────────────┐
             │   CONFIGURING_TRIP    │
             └───────────┬───────────┘
                         │ User taps "Start Nap Mode"
                         ▼
             ┌───────────────────────┐
             │    TRACKING_ACTIVE    │◄─────────────────┐
             └───────────┬───────────┘                  │
                         │ Distance <= Geofence Radius  │
                         ▼                              │
             ┌───────────────────────┐                  │
             │    ALARM_TRIGGERED    │                  │
             └───────────┬───────────┘                  │
                         │                              │
          ┌──────────────┴──────────────┐               │
          │                             │               │
    (User Dismisses)              (User Snoozes)        │
          │                             │               │
          ▼                             ▼               │
   ┌─────────────┐             ┌─────────────────┐      │
   │  COMPLETED  │             │     SNOOZED     ├──────┘
   └─────────────┘             └─────────────────┘ (Re-checks in 5m / 1km)
```

---

## 🛠️ Technology Stack

| Domain | Technology / API | Purpose |
| :--- | :--- | :--- |
| **Framework** | React 18 + TypeScript + Vite | Modular, type-safe, high-performance UI |
| **Styling** | Tailwind CSS + Lucide Icons | Responsive modern design, Dark/AMOLED themes |
| **Maps & GIS** | Leaflet / OpenStreetMap | Interactive maps, geofence radius rendering |
| **Location Engine** | HTML5 Geolocation API | Real-time GPS coordinates and velocity |
| **Sound Synthesis** | Web Audio API (`AudioContext`) | Zero-dependency, offline-ready alarm synthesis |
| **Haptics** | Navigator Vibration API | Hardware vibration patterns |
| **Background Keepalive** | Screen Wake Lock API | Prevents device sleep during transit |
| **PWA / Offline** | Service Workers & Cache API | Installable on iOS/Android home screens |

---

## 📂 Project Structure

```
destiwake/
├── public/
│   ├── favicon.ico
│   └── manifest.json          # PWA configuration
├── src/
│   ├── core/
│   │   ├── geo.ts             # Haversine, bearing, speed smoothing, ETA math
│   │   ├── audio.ts           # Web Audio synthesizer & sound presets
│   │   ├── wakeLock.ts        # Screen wake lock & background manager
│   │   └── state.ts           # State machine & trip manager
│   ├── components/
│   │   ├── MapView.tsx        # Interactive Leaflet map & dynamic circle
│   │   ├── VehiclePicker.tsx  # Transport profile selector
│   │   ├── TriggerControls.tsx# Radius slider, numeric & ETA input
│   │   ├── Dashboard.tsx      # Live telemetry (Speed, Distance, Safe Nap Time)
│   │   ├── AlarmModal.tsx     # Wake-up screen with vibration & math verification
│   │   └── Simulator.tsx      # Virtual transit route testing tool
│   ├── types/
│   │   └── index.ts           # TypeScript interfaces & data models
│   ├── App.tsx                # Main application coordinator
│   └── main.tsx               # Entry point
├── package.json
├── tsconfig.json
├── tailwind.config.js
└── README.md
```

---

## 🚀 Quick Start Guide

### Prerequisites
- [Node.js](https://nodejs.org/) (version 18 or higher)
- npm or yarn

### Installation & Local Run

```bash
# 1. Clone or navigate to the repository
cd Project_3

# 2. Install dependencies
npm install

# 3. Start local development server
npm run dev
```

Open your browser at `http://localhost:5173` to view and use the app.

---

## 🌟 Future Roadmap

- [ ] **WhatsApp / SMS Emergency Live Sharing**: Send auto-update link to family with live ETA.
- [ ] **Headphone-First Audio Routing**: Ring inside earphones first; escalate to loud speaker if not dismissed.
- [ ] **Capacitor Mobile Build**: Direct export to native Android APK with foreground service notification.
- [ ] **Offline Station Database**: Instant station-code lookup (e.g., NDLS, CSMT, HWH) with zero network dependency.

---

## 👨‍💻 Author & Contributions

Created as a practical Computer Science & Engineering project to solve real-world transit anxiety for daily commuters and travelers.

Contributions, feature requests, and suggestions are welcome!
