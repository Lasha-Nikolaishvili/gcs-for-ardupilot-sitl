import os
import threading
import json
from pymavlink import mavutil
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QLineEdit, QApplication, QSizePolicy, QMessageBox, QGroupBox
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import Qt, QUrl, Signal, QTimer, Slot

from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore    import QWebEnginePage


class DebugWebEnginePage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        print(f"JS console [{level.name}] {sourceID}:{lineNumber} → {message}")
        super().javaScriptConsoleMessage(level, message, lineNumber, sourceID)


class MissionPlanningTab(QWidget):
    # signal used to marshal JS→Python callbacks back to the GUI thread
    mission_downloaded = Signal(list, list, list)
    # signal when mission download fails (error message)
    mission_download_failed = Signal(str)


    def __init__(self, conn):
        super().__init__()
        self.conn = conn
        self.mission_downloaded.connect(self._update_map_from_download)
        self.mission_download_failed.connect(self.on_download_failed)
        # Main layout of mission planning tab

        # ─── Build the “Connect / Disconnect” panel ────────────────────────────
        # (1) A label to show “Status: Disconnected” or “Status: Connected”
        self.status_label = QLabel("Status: Disconnected")

        # (2) A QLineEdit to type e.g. “udp:127.0.0.1:14550”
        self.uri_edit = QLineEdit()
        self.uri_edit.setPlaceholderText("e.g. udp:127.0.0.1:14550")
        self.uri_edit.setText("udp:127.0.0.1:14550")  # default value

        # (3) “Connect” button
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setCursor(Qt.PointingHandCursor)
        self.connect_btn.clicked.connect(self.on_connect_clicked)

        # (4) “Disconnect” button
        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.setEnabled(False)
        self.disconnect_btn.setCursor(Qt.PointingHandCursor)
        self.disconnect_btn.clicked.connect(self.on_disconnect_clicked)

        connect_layout = QHBoxLayout()
        connect_layout.addWidget(QLabel("SITL URI:"))
        connect_layout.addWidget(self.uri_edit, 1)
        connect_layout.addWidget(self.connect_btn)
        connect_layout.addWidget(self.disconnect_btn)
        connect_layout.addWidget(self.status_label)
        connect_widget = QWidget()
        connect_widget.setLayout(connect_layout)

        connect_widget.setSizePolicy(
            QSizePolicy.Expanding,   # stretch horizontally
            QSizePolicy.Fixed        # fixed vertically
        )
        # (Optional) Lock in the “suggested” height so it never grows:
        connect_widget.setMaximumHeight(connect_widget.sizeHint().height())

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
        self.buttons_widget = QGroupBox("Planning Controls")
        buttons_layout = QVBoxLayout()

        for btn in (
            self.clear_mission_btn,
            self.print_waypoints_btn,
            self.clear_geofence_btn,
            self.print_geofence_btn,
            self.clear_rally_btn,
            self.print_rally_btn,
            self.upload_btn,
            self.download_btn
        ):
            btn.setCursor(Qt.PointingHandCursor)
            buttons_layout.addWidget(btn)

        self.buttons_widget.setLayout(buttons_layout)
        
        # Assemble layout
        main_layout.addWidget(self.map_view, 1)
        main_layout.addWidget(self.buttons_widget)
        # self.setLayout(main_layout)

        # ─── Assemble everything in a single vertical layout ─────────────────
        root_layout = QVBoxLayout(self)
        root_layout.addWidget(connect_widget)   # top bar: connect/disconnect
        root_layout.addLayout(main_layout)      # below: map + side buttons

        self.setLayout(root_layout)

        # ─── Live drone marker updater ─────────────────────────────────────────
        self._pos_timer = QTimer(self)
        self._pos_timer.timeout.connect(self.update_drone_marker)
        self._pos_timer.start(500)
    
    # ─── “Connect” / “Disconnect” handlers ───────────────────────────────────

    def on_connect_clicked(self):
        uri = self.uri_edit.text().strip()
        if not uri:
            self.status_label.setText("Status: Enter a URI first")
            return

        self.status_label.setText("Status: Connecting…")
        QApplication.processEvents()

        try:
            self.conn.connect_sitl(uri)
        except Exception as e:
            self.status_label.setText(f"Status: Error connecting: {e}")
            return

        # If we got here, the connection succeeded:
        self.status_label.setText("Status: Connected")
        self.connect_btn.setEnabled(False)
        self.uri_edit.setEnabled(False)
        self.disconnect_btn.setEnabled(True)

    def on_disconnect_clicked(self):
        try:
            self.conn.disconnect_sitl()
        except Exception as e:
            print("Error while disconnecting:", e)

        self.status_label.setText("Status: Disconnected")
        self.connect_btn.setEnabled(True)
        self.uri_edit.setEnabled(True)
        self.disconnect_btn.setEnabled(False)

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
        self._waypoints = [{'lat':p[0], 'lon':p[1], 'alt':p[2]} for p in self.handle_waypoints(wps)]
        self.map_view.page().runJavaScript("JSON.stringify(getGeofence());", 0, self._got_fence)

    def _got_fence(self, fence):
        self._fence = [{'lat':p[0], 'lon':p[1]} for p in self.handle_geofence(fence)]
        self.map_view.page().runJavaScript("JSON.stringify(getRallyPoints());", 0, self._got_rally)

    def _got_rally(self, rallies_json):
        self._rallies = [{'lat':p[0], 'lon':p[1]} for p in self.handle_rally_points(rallies_json)]

        # ── Now actually upload everything, with popups on success/failure ────
        try:
            self.conn.upload_mission(self._waypoints)
            self.conn.upload_fence(self._fence)
            self.conn.upload_rally(self._rallies)
        except Exception as e:
            QMessageBox.critical(
                self,
                "Upload Failed",
                f"Mission upload failed:\n{e}"
            )
        else:
            QMessageBox.information(
                self,
                "Upload Successful",
                "Mission, geofence, and rally points were uploaded successfully!"
            )
            print("✅ Python: Uploaded mission, geofence, and rally points to UAV")
            print("Waypoints:", self._waypoints)
            print("Geofence:", self._fence)
            print("Rally Points:", self._rallies)

    def _on_download_clicked(self):
        def worker():
            try:
                mts   = self.conn._download_items
                wps   = mts(mavutil.mavlink.MAV_MISSION_TYPE_MISSION)
                fence = mts(mavutil.mavlink.MAV_MISSION_TYPE_FENCE)
                rally = mts(mavutil.mavlink.MAV_MISSION_TYPE_RALLY)

                wps   = [[i['x'], i['y'], i['z']] for i in wps]
                fence = [[i['x'], i['y'], i['z']] for i in fence]
                rally = [[i['x'], i['y'], i['z']] for i in rally]

                # set the last waypoint to match the first one (for closed loops)
                wp_len = len(wps)
                wps[wp_len - 1][0] = wps[0][0]
                wps[wp_len - 1][1] = wps[0][1]
                # update total waypoint count
                self.conn.telemetry['total_mission_points'] = wp_len
                # emit success
                self.mission_downloaded.emit(wps, fence, rally)

            except Exception as e:
                # emit failure message
                self.mission_download_failed.emit(str(e))

        threading.Thread(target=worker, daemon=True).start()

    @Slot(str)
    def on_download_failed(self, error_msg):
        QMessageBox.critical(self, "Download Failed", f"Mission download failed:\n{error_msg}")

    def _update_map_from_download(self, wps, fence, rally):
        # update the map
        self.map_view.page().runJavaScript(f"setWaypoints({json.dumps(wps)})")
        self.map_view.page().runJavaScript(f"setGeofence({json.dumps(fence)})")
        self.map_view.page().runJavaScript(f"setRally({json.dumps(rally)})")

        # then notify the user
        QMessageBox.information(self, "Download Successful",
                                "Mission, geofence, and rally points were downloaded and displayed.")