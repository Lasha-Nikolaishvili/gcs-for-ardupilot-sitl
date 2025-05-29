import os
import threading
import json
from pymavlink import mavutil
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl, Signal, QTimer

from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore    import QWebEnginePage

class DebugWebEnginePage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        print(f"JS console [{level.name}] {sourceID}:{lineNumber} → {message}")
        super().javaScriptConsoleMessage(level, message, lineNumber, sourceID)


class MissionPlanningTab(QWidget):
    # signal used to marshal JS→Python callbacks back to the GUI thread
    mission_downloaded = Signal(list, list, list)

    def __init__(self, conn):
        super().__init__()
        self.conn = conn
        self.mission_downloaded.connect(self._update_map_from_download)
        # Main layout of mission planning tab
        main_layout = QHBoxLayout()

        # Interactive Leaflet Map
        self.map_view = QWebEngineView()
        self.map_view.setPage(DebugWebEnginePage(self.map_view))
        self.load_map()

        # Mission waypoint controls
        self.clear_mission_btn = QPushButton("Clear Mission")
        self.clear_mission_btn.clicked.connect(self.clear_waypoints)

        self.print_waypoints_btn = QPushButton("Print Waypoints")
        self.print_waypoints_btn.clicked.connect(self.print_waypoints)

        # Geofence controls
        self.clear_geofence_btn = QPushButton("Clear Geofence")
        self.clear_geofence_btn.clicked.connect(self.clear_geofence)

        self.print_geofence_btn = QPushButton("Print Geofence")
        self.print_geofence_btn.clicked.connect(self.print_geofence)

        # Rally point controls
        self.clear_rally_btn = QPushButton("Clear Rally Points")
        self.clear_rally_btn.clicked.connect(self.clear_rally_points)

        self.print_rally_btn = QPushButton("Print Rally Points")
        self.print_rally_btn.clicked.connect(self.print_rally_points)

        # Mission upload and download buttons
        self.upload_btn = QPushButton("Upload to UAV")
        self.upload_btn.clicked.connect(self._on_upload_clicked)

        self.download_btn = QPushButton("Download from UAV")
        self.download_btn.clicked.connect(self._on_download_clicked)

        # Layout and widget for side buttons tab
        self.buttons_widget = QWidget()
        buttons_layout = QVBoxLayout()

        buttons_layout.addWidget(self.clear_mission_btn)
        buttons_layout.addWidget(self.print_waypoints_btn)
        buttons_layout.addWidget(self.clear_geofence_btn)
        buttons_layout.addWidget(self.print_geofence_btn)
        buttons_layout.addWidget(self.clear_rally_btn)
        buttons_layout.addWidget(self.print_rally_btn)
        buttons_layout.addWidget(self.upload_btn)
        buttons_layout.addWidget(self.download_btn)

        self.buttons_widget.setLayout(buttons_layout)
        
        # Assemble layout
        main_layout.addWidget(self.map_view, 1)
        main_layout.addWidget(self.buttons_widget)
        self.setLayout(main_layout)

        # ─── Live drone marker updater ─────────────────────────────────────────
        self._pos_timer = QTimer(self)
        self._pos_timer.timeout.connect(self.update_drone_marker)
        self._pos_timer.start(500)

    def load_map(self):
        map_file = os.path.abspath("map.html")
        self.map_view.setUrl(QUrl.fromLocalFile(map_file))

    def update_drone_marker(self):        
        lat = self.conn.telemetry.get('lat')
        lon = self.conn.telemetry.get('lon')
        if lat is not None and lon is not None:
            js = f"updateDroneMarker({lat}, {lon});"
            # print("Calling JS:", js)
            self.map_view.page().runJavaScript(js)

    def clear_waypoints(self):
        self.map_view.page().runJavaScript("clearWaypoints();")

    def print_waypoints(self):
        print("✅ Python: Requesting waypoints from JS")
        self.map_view.page().runJavaScript("JSON.stringify(getWaypoints());", 0, self.handle_waypoints)

    def handle_waypoints(self, json_str):
        try:
            wps = json.loads(json_str) if json_str else []
        except json.JSONDecodeError:
            print("⚠️ Failed to parse waypoints JSON:", json_str)
            wps = []
        print("✅ Python: Received waypoints from JS")
        print("Waypoints:", wps)
        return wps
    
    # def handle_waypoints(self, waypoints):
    #     print("✅ Python: Received waypoints from JS")
    #     print("Waypoints:", waypoints)

    def clear_geofence(self):
        self.map_view.page().runJavaScript("clearGeofence();")

    def print_geofence(self):
        self.map_view.page().runJavaScript("JSON.stringify(getGeofence());", 0, self.handle_geofence)

    def handle_geofence(self, geofence):
        try:
            geofence = json.loads(geofence) if geofence else []
        except json.JSONDecodeError:
            print("⚠️ Failed to parse geofence JSON:", geofence)
            geofence = []
        print("✅ Python: Received geofence from JS")
        print("Geofence Points:", geofence)
        return geofence

    def clear_rally_points(self):
        self.map_view.page().runJavaScript("clearRallyPoints();")

    def print_rally_points(self):
        self.map_view.page().runJavaScript("JSON.stringify(getRallyPoints());", 0, self.handle_rally_points)

    def handle_rally_points(self, rally_points):
        try:
            rally_points = json.loads(rally_points) if rally_points else []
        except json.JSONDecodeError:
            print("⚠️ Failed to parse rally points JSON:", rally_points)
            rally_points = []
        print("✅ Python: Received rally points from JS")
        print("Rally Points:", rally_points)
        return rally_points
    
    def _on_upload_clicked(self):
        # fetch waypoints → geofence → rally, then uplink
        self.map_view.page().runJavaScript("JSON.stringify(getWaypoints());", 0, self._got_waypoints)

    def _got_waypoints(self, wps):
        self._waypoints = [{'lat':p[0], 'lon':p[1], 'alt':50} for p in self.handle_waypoints(wps)]
        self.map_view.page().runJavaScript("JSON.stringify(getGeofence());", 0, self._got_fence)

    def _got_fence(self, fence):
        self._fence = [{'lat':p[0], 'lon':p[1], 'alt':50} for p in self.handle_geofence(fence)]
        self.map_view.page().runJavaScript("JSON.stringify(getRallyPoints());", 0, self._got_rally)

    def _got_rally(self, rallies):
        self._rallies = [{'lat':p[0], 'lon':p[1], 'alt':50} for p in self.handle_rally_points(rallies)]
        # now push to UAV
        self.conn.upload_mission(self._waypoints)
        self.conn.upload_fence(self._fence)
        self.conn.upload_rally(self._rallies)

    def _on_download_clicked(self):
        # do download in thread to avoid blocking UI
        threading.Thread(target=self._download_thread, daemon=True).start()

    def _download_thread(self):
        mts = self.conn._download_items  # shorthand
        wps   = mts(mavutil.mavlink.MAV_MISSION_TYPE_MISSION)
        fence = mts(mavutil.mavlink.MAV_MISSION_TYPE_FENCE)
        rally = mts(mavutil.mavlink.MAV_MISSION_TYPE_RALLY)

        # convert to simple [lat, lon, alt]
        wps   = [[i['x'], i['y'], i['z']] for i in wps]
        fence = [[i['x'], i['y'], i['z']] for i in fence]
        rally = [[i['x'], i['y'], i['z']] for i in rally]

        # emit back into GUI thread
        self.mission_downloaded.emit(wps, fence, rally)

    def _update_map_from_download(self, wps, fence, rally):
        # assumes your map.html defines setWaypoints(), setGeofence(), setRally()
        self.map_view.page().runJavaScript(f"setWaypoints({json.dumps(wps)})")
        self.map_view.page().runJavaScript(f"setGeofence({json.dumps(fence)})")
        self.map_view.page().runJavaScript(f"setRally({json.dumps(rally)})")
