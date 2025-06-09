# GCS Application

A **Ground Control Station (GCS)** desktop application built with PySide6 (Qt for Python) that lets you plan, upload, download, and visualize ArduPilot missions using MAVLink, view live video & telemetry, control an on-board gimbal, and tweak autopilot parameters — all in one GUI.

---

## Table of Contents

1. [Key Features](#key-features)
2. [Architecture & Components](#architecture--components)
3. [Installation & Setup](#installation--setup)
4. [Usage](#usage)

   * [Connecting to SITL](#connecting-to-sitl)
   * [Mission Planning](#mission-planning)
   * [Live Video & Telemetry](#live-video--telemetry)
   * [Gimbal Control](#gimbal-control)
   * [Parameter Editing](#parameter-editing)
5. [Styling & Themes](#styling--themes)
6. [File Structure](#file-structure)
7. [Dependencies](#dependencies)
8. [License](#license)

---

## Key Features

* **Map-based Mission Planning**

  * Click to add waypoints, geofence vertices, rally points
  * Drag, edit or delete markers; polylines update automatically
  * Upload/download missions via MAVLink

* **Live Video & OSD**

  * H.264 video stream (GStreamer) in a Qt widget
  * Overlay HUD: mode, armed state, position, altitude, battery, GPS fix, speed, climb rate, throttle, mission progress
  * Transparent, grouped HUD sections in each corner

* **Gimbal Control**

  * Smooth sliders for RC channel overrides (roll, pitch, yaw)
  * “Center” button resets to neutral

* **Config & Parameters Tab**

  * Select or add custom map tile sources (persistent in `maps.json`)
  * Read/write ArduPilot parameters (`PARAM_REQUEST_READ`, `PARAM_SET`) with real-time feedback

* **Modern, Responsive UI**

  * Custom Qt Style Sheet (`palette.qss`)
  * Clear hover/pressed/disabled states
  * Consistent button, input, slider, tab styling

---

## Architecture & Components

### Main Window & Tabs

* **`main.py`**

  * Initializes `QApplication` & `QMainWindow`
  * Creates three tabs:

    1. **Mission Planning**
    2. **Video Feed**
    3. **Config**

* **`Connection`** class

  * Manages MAVLink connection, background listener
  * Methods:

    * `connect_sitl(uri)` / `disconnect_sitl()`
    * `upload_mission()`, `download_mission()`
    * `set_param()`, `get_param()`
    * `override_rc(channel, pwm)`

### Mission Planning Tab (`mission_planning.py`)

* **Map** via `QWebEngineView` + Leaflet
* **JS ↔ Python** bridge for waypoint/geofence/rally operations
* **Connect panel**: SITL URI input, Connect/Disconnect, status label
* **Buttons**: Clear, Print (console), Upload, Download

### Video Feed Tab (`video.py`)

* **Start Video** button to open GStreamer pipeline in background thread
* **Video** displayed in `QLabel`
* **OSD HUD** drawn onto each frame in 4 corners
* **Flight controls**: Arm/Disarm, Takeoff, Mode switches
* **Gimbal sliders** and Center button

### Config Tab (`config.py`)

* **Map Source** selector + add new URL (stores to `maps.json`)
* **Parameter editor**: list, Read/Write buttons, status feedback

---

## Installation & Setup
much more complicated (will be updated later)

1. **Clone repository**

   ```bash
   git clone https://github.com/yourusername/gcs-application.git
   cd gcs-application
   ```

2. **Create & activate a virtual environment**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Ensure assets** are in place:

   * `map.html`, Leaflet assets, `media/drone.svg`
   * `palette.qss`, `maps.json` (with default entries)

5. **Run the application**

   ```bash
   python main.py
   ```

---

## Usage

### Connecting to SITL

1. Go to **Mission Planning** tab.
2. Enter SITL URI (e.g. `udp:127.0.0.1:14550`) and click **Connect**.
3. Status updates to **Connected**.

### Mission Planning

1. **Click** on map for waypoints.
2. **Ctrl+Click** for geofence, **Shift+Click** for rally points.
3. **Drag** markers to reposition; **Right-click** to delete.
4. **Upload** to send mission/fence/rally.
5. **Download** to fetch current plan back.

### Live Video & Telemetry

1. Switch to **Video Feed** tab.
2. Click **Start Video** (first time) or it will auto-resume.
3. View live video with overlaid HUD.
4. Switch tabs to pause stream without freezing UI.

### Gimbal Control

* Use sliders under **Gimbal Control** to override RC6,7,8.
* Click **Center Gimbal** to reset to 1500.

### Parameter Editing

1. Open **Config** tab.
2. Select a parameter or type its name.
3. Click **Read** to fetch current value.
4. Enter new value and click **Write**.
5. Confirmation message on success/failure.

---

## Styling & Themes

* Style sheet in `palette.qss` defines colors, fonts, borders, hovers, etc.
* Edit `palette.qss` to adapt to your brand or preferences.

---

## File Structure

```
.
├── main.py
├── palette.qss
├── requirements.txt
├── map_sources.json
├── map.html
├── map.js
├── requirements.txt
├── .gitignore
├── media/
│   └── drone.svg
└── src/
    ├── connection.py
    ├── joystick.py
    └── utils/
        ├── connection_utils.py
    └── widget_classes/
        ├── mission_planning.py
        ├── video.py
        └── config.py
```

---

## Dependencies

* Python 3.10+
* PySide6
* pymavlink
* OpenCV (with GStreamer support)
* Qt WebEngine
* PyGame