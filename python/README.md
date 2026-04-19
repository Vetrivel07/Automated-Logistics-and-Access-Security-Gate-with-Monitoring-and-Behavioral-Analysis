# Automated Logistics and Access Security Gate with Monitoring and Behavioral Analysis

> An IoT-based smart access control system using RFID authentication, real-time monitoring dashboard, and hybrid anomaly detection (rule-based + Isolation Forest ML).

**Author:** Vetrivel Maheswaran  
**Course:** ISTE730 — Foundations of IoT  | Spring 2026
**Institution:** Rochester Institute of Technology  

---

## 📋 Table of Contents

- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Features](#features)
- [Hardware Requirements](#hardware-requirements)
- [Hardware Pin Mapping](#hardware-pin-mapping)
- [Software Requirements](#software-requirements)
- [Project Structure](#project-structure)
- [Setup Instructions](#setup-instructions)
- [Running the System](#running-the-system)
- [Dashboard](#dashboard)
- [API Endpoints](#api-endpoints)
- [Anomaly Detection](#anomaly-detection)
- [Configuration](#configuration)
- [Serial Message Format](#serial-message-format)

---

## Overview

Traditional access control systems authenticate users at the point of entry and do nothing beyond that. This project extends basic gate control by integrating:

- **RFID-based authentication** at the edge (Arduino)
- **Real-time event logging** to a local SQLite database
- **Live web dashboard** for monitoring access activity
- **Behavioral analysis** per user (entry times, stay durations, visit frequency)
- **Hybrid anomaly detection** using rule-based logic and Isolation Forest ML

The entire system runs locally — no cloud dependency, no internet required.

---

## System Architecture

```
RFID Card Scan
      ↓
Arduino UNO R3  (Edge Layer)
  ├── RC522 reads UID
  ├── Authorization check (hardcoded UIDs)
  ├── IN/OUT toggle per user
  ├── Servo + LED + Buzzer + LCD feedback
  └── JSON over USB Serial → COM3
            ↓
Python Backend  (localhost)
  ├── SerialReader  → background daemon thread
  ├── AccessService → validation + pipeline
  ├── AnomalyService → rule-based + ML detection
  ├── Repository → SQLAlchemy → SQLite
  └── FastAPI → REST API + Dashboard
            ↓
http://localhost:8000
  ├── Live dashboard (auto-refresh 5s)
  ├── User detail pages
  └── Anomaly alerts page
```

---

## Features

### Hardware (Edge)
- RFID card scanning via RC522 (SPI)
- Servo motor gate control (0° closed / 90° open)
- Green LED — access granted
- Red LED — access denied
- Blue LED — idle state
- Buzzer — audio feedback (chirp for grant, alert for deny)
- Grove LCD RGB — status display with color backlight
- IN/OUT toggle logic per card

### Backend
- FastAPI REST API
- SQLAlchemy ORM with SQLite
- Background serial reader thread (independent of API layer)
- Repository pattern — all DB queries isolated
- Service layer — all business logic isolated
- Pydantic schema validation
- Local timestamp storage

### Dashboard
- **Live Scan Panel** — real-time display of last scan (name, UID, status, event, timestamp, presence)
- **Allowed vs Denied Chart** — doughnut chart (all-time)
- **Today's Stats** — Total Scans, Allowed, Denied, Anomalies, Unique Users (resets at midnight)
- **Live Clock** — updates every second
- **Users Panel** — all users with Inside/Outside presence badge, clickable
- **Anomaly Alerts** — latest alerts with reason and timestamp
- **Log Filter** — filter by date range and time window
- **User Detail Page** — per-user analytics, charts, stay durations, full history
- **Full Anomaly Page** — all flagged events

### Anomaly Detection
- Off-hours access detection (configurable window)
- Rapid scan detection (sliding window algorithm)
- Consecutive denied streak detection
- Isolation Forest ML — detects unusual access hour patterns per user

---

## Hardware Requirements

| Component | Model | Notes |
|---|---|---|
| Microcontroller | Arduino UNO R3 | Main control board |
| Base Shield | Grove Base Shield | For Grove module connectivity |
| RFID Reader | RC522 | 13.56 MHz, SPI communication |
| RFID Cards/Fobs | MIFARE Classic | Must be 13.56 MHz |
| Servo Motor | Grove Analog Servo | Gate actuation |
| Green LED | Grove LED | D4 |
| Red LED | Grove LED | D5 |
| Blue LED | Grove LED | D6 |
| Buzzer | Grove Buzzer | D8 |
| LCD Display | Grove LCD RGB Backlight v4.0 | I2C |
| Jumper Wires | Female-to-Male | For RC522 connection |
| USB Cable | USB-A to USB-B | Arduino to laptop |

> ⚠️ **RC522 must be powered from 3.3V only. Connecting to 5V will permanently damage the module.**

---

## Hardware Pin Mapping

### RC522 RFID (Jumper Wires — SPI)

| RC522 Pin | Arduino Pin | Notes |
|---|---|---|
| SDA (SS) | D10 | SPI Chip Select |
| SCK | D13 | SPI Clock |
| MOSI | D11 | SPI Data Out |
| MISO | D12 | SPI Data In |
| RST | D7 | Reset |
| GND | GND | Ground |
| 3.3V | 3.3V | **NOT 5V** |

### Grove Modules (Base Shield)

| Component | Grove Port | Arduino Pins |
|---|---|---|
| Servo | D3 | D3 (PWM) |
| Green LED | D4 | D4 |
| Red LED | D5 | D5 |
| Blue LED | D6 | D6 |
| Buzzer | D8 | D8 |
| LCD RGB | I2C | A4 (SDA), A5 (SCL) |

---

## Software Requirements

### Arduino Libraries
Install via Arduino IDE → Library Manager:
- `MFRC522` by GithubCommunity
- `Grove LCD RGB Backlight` by Seeed Studio
- `Servo` (built-in, no install needed)

### Python Dependencies

```
fastapi==0.115.0
uvicorn==0.30.6
sqlalchemy==2.0.35
pyserial==3.5
pydantic==2.9.2
pydantic-settings==2.5.2
scikit-learn==1.5.2
numpy==2.1.1
pandas==2.2.3
jinja2==3.1.4
```

### System Requirements
- Python 3.10+
- Windows (tested on Windows with COM3)
- Arduino IDE 2.x


---

## Setup Instructions

### Step 1 — Arduino Setup

1. Wire all hardware as per the pin mapping table above
2. Open Arduino IDE
3. Install required libraries via **Tools → Manage Libraries**
4. Open `arduino/SecurityGate.ino`
5. Upload the sketch to Arduino UNO
6. Open **Serial Monitor** at **9600 baud**
7. Scan each RFID card — copy the printed UID (format: `XX XX XX XX`)
8. Close Serial Monitor
9. Open `SecurityGate.ino` and replace the dummy UIDs:

```cpp
const char AUTHORIZED_UIDS[][12] = {
  "XX XX XX XX",    // replace with your real UID
  "XX XX XX XX",    // replace with your real UID
  "XX XX XX XX"     // replace with your real UID
};
```

10. Upload again

### Step 2 — Python Environment Setup

```bash
# Create and activate virtual environment
uv init
uv venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# Install dependencies
uv pip install -r requirements.txt
```

### Step 3 — Configure User Names

Edit `core/user_map.py` to map UIDs to display names:

```python
USER_MAP = {
    "XX XX XX XX": "Alice",
    "XX XX XX XX": "Bob",
    "XX XX XX XX": "Charlie",
}
```

### Step 4 — Configure Settings (Optional)

Edit `core/config.py` to change:

```python
SERIAL_PORT: str = "COM3"          # change to your Arduino port
SERIAL_BAUD_RATE: int = 9600       # must match Arduino Serial.begin()
ANOMALY_HOUR_START: int = 10       # start of normal operating hours
ANOMALY_HOUR_END: int = 15         # end of normal operating hours
ANOMALY_RAPID_SCAN_LIMIT: int = 5  # max scans before rapid scan alert
ANOMALY_RAPID_SCAN_WINDOW: int = 60 # seconds for rapid scan window
```

---

## Running the System

### Important Rules
- ❌ Serial Monitor must be **CLOSED** before starting Python
- ✅ Arduino must be **plugged in** via USB
- ✅ Virtual environment must be **activated**

### Start the System

```bash
# Make sure you are in the project directory
cd security_gate

# Activate venv (if not already)
venv\Scripts\activate

# Run the backend
uvicorn main:app --port 8000
```

### Open Dashboard

```
http://localhost:8000
```

### Expected Terminal Output on Startup

```
[Main] Starting Security Gate System v1.0.0
[Main] Database initialized.
[SerialReader] Thread started on COM3
[Main] Serial reader started on COM3
[SerialReader] Connected to COM3
[SerialReader] Non-scan message received: {'event': 'system_ready', ...}
```

### Expected Terminal Output on Card Scan

```
[SerialReader] Received → uid=C3 22 E0 56 status=allowed event=IN
[AccessService] Saved → id=1 uid=C3 22 E0 56 status=allowed event=IN
[AccessService] ✓ Pipeline complete → anomaly=False
```

### Fresh Start (Reset Database)

```bash
# Stop Python first (Ctrl+C)
# Delete database
del access_logs.db        # Windows
# rm access_logs.db       # Mac/Linux

# Restart
uvicorn main:app --port 8000
```

---

## Dashboard

| URL | Description |
|---|---|
| `http://localhost:8000` | Main dashboard |
| `http://localhost:8000/dashboard/user.html?uid=XX XX XX XX` | User detail page |
| `http://localhost:8000/dashboard/anomalies.html` | All anomaly alerts |
| `http://localhost:8000/docs` | Auto-generated API documentation |

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/latest` | Most recent scan event |
| GET | `/api/logs` | Recent 50 logs |
| GET | `/api/logs/filter` | Filter by date and time range |
| GET | `/api/logs/{id}` | Single log by ID |
| GET | `/api/logs/user/{uid}` | All logs for one UID |
| GET | `/api/anomalies` | All anomaly-flagged logs |
| GET | `/api/stats` | All-time statistics |
| GET | `/api/stats/today` | Today's statistics (resets at midnight) |
| GET | `/api/users` | All unique users with stats |
| GET | `/api/behaviour/{uid}` | Behavioral analysis for one user |

### Filter Endpoint Parameters

```
GET /api/logs/filter?date_from=2026-04-18&date_to=2026-04-18&time_from=10:00&time_to=15:00
```

| Parameter | Required | Format | Description |
|---|---|---|---|
| `date_from` | Yes | YYYY-MM-DD | Start date |
| `date_to` | Yes | YYYY-MM-DD | End date |
| `time_from` | No | HH:MM | Start time within day |
| `time_to` | No | HH:MM | End time within day |

---

## Anomaly Detection

### Layer 1 — Rule Based

| Rule | Trigger | Config Key |
|---|---|---|
| Off-hours | Scan before 10AM or after 3PM | `ANOMALY_HOUR_START`, `ANOMALY_HOUR_END` |
| Rapid scan | 5+ scans of same card in 60 seconds | `ANOMALY_RAPID_SCAN_LIMIT`, `ANOMALY_RAPID_SCAN_WINDOW` |
| Denied streak | 3+ consecutive denied scans for same UID | Hardcoded (3) |

### Layer 2 — Isolation Forest ML

- **Algorithm:** `sklearn.ensemble.IsolationForest`
- **Feature:** Hour of day (0–23)
- **Training:** Retrained fresh on every scan using full user history
- **Activation:** Requires minimum 10 historical scans per user
- **Contamination:** 0.1 (expects ~10% anomalies in training data)
- **Output:** -1 = anomaly, 1 = normal

### Detection Flow

```
Every scan →
  Rule 1: Off-hours check     (fast, always runs)
  Rule 2: Rapid scan check    (DB query, sliding window)
  Rule 3: Denied streak check (last 5 records)
  ML:     Isolation Forest    (only if 10+ history records)
  → First match wins → is_anomaly=True, reason saved to DB
```

---

## Configuration

All configuration is in `core/config.py`:

```python
# Serial
SERIAL_PORT: str = "COM3"
SERIAL_BAUD_RATE: int = 9600
SERIAL_TIMEOUT: int = 2
SERIAL_RECONNECT_DELAY: int = 5

# Database
DATABASE_URL: str = "sqlite:///./access_logs.db"

# Anomaly Detection
ANOMALY_HOUR_START: int = 10     # scans before this hour = suspicious
ANOMALY_HOUR_END: int = 15       # scans after this hour = suspicious
ANOMALY_RAPID_SCAN_LIMIT: int = 5
ANOMALY_RAPID_SCAN_WINDOW: int = 60  # seconds

# Dashboard
DASHBOARD_RECENT_LOGS_LIMIT: int = 50
```

---

## Serial Message Format

Arduino sends JSON wrapped in start/end markers:

```
<{"uid":"C3 22 E0 56","status":"allowed","event":"IN"}>
<{"uid":"C3 22 E0 56","status":"allowed","event":"OUT"}>
<{"uid":"AE F3 10 06","status":"denied","event":"NONE"}>
```

| Field | Values | Description |
|---|---|---|
| `uid` | `XX XX XX XX` | RFID card UID in hex |
| `status` | `allowed` / `denied` | Authorization result |
| `event` | `IN` / `OUT` / `NONE` | Entry/exit toggle (NONE for denied) |

The `<` and `>` markers allow the Python serial reader to reliably frame messages even if bytes are lost during transmission.

---

## Database Schema

**Table:** `access_logs`

| Column | Type | Description |
|---|---|---|
| `id` | Integer | Auto-increment primary key |
| `uid` | String(20) | RFID card UID |
| `status` | String(10) | `allowed` or `denied` |
| `event` | String(4) | `IN`, `OUT`, or `NONE` |
| `timestamp` | DateTime | Local time of scan |
| `is_anomaly` | Boolean | True if flagged |
| `anomaly_reason` | String(200) | Description of anomaly |

---

## Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| `PermissionError: COM3` | Serial Monitor is open | Close Arduino IDE Serial Monitor |
| `ModuleNotFoundError: serial` | Folder named `serial` conflicts with pyserial | Rename folder to `serial_comm` |
| RC522 Firmware: `0x00` | Wiring issue or wrong voltage | Check 3.3V power, verify SPI pin connections |
| Today stats showing 0 | Timezone mismatch | Ensure `datetime.now()` used (not `utcnow()`) |
| Card not reading | Weak antenna | Call `rfid.PCD_SetAntennaGain(rfid.RxGain_max)` |
| Dashboard not updating | Filter is active | Click Reset button on log filter |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Embedded | Arduino C/C++, MFRC522, Servo, rgb_lcd |
| Communication | USB Serial, JSON, Marker-based framing |
| Backend | Python 3.10+, FastAPI, Uvicorn |
| Database | SQLite, SQLAlchemy ORM |
| Validation | Pydantic v2 |
| Serial | PySerial |
| ML | scikit-learn (IsolationForest), NumPy |
| Frontend | HTML5, CSS3, JavaScript, Chart.js |
| Fonts | IBM Plex Sans, IBM Plex Mono |