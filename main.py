import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QTabWidget
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtCore import QUrl

class MissionPlanningTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()

        # Interactive Leaflet Map
        self.map_view = QWebEngineView()
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

        # Assemble layout
        layout.addWidget(self.map_view, 1)
        layout.addWidget(self.clear_mission_btn)
        layout.addWidget(self.print_waypoints_btn)
        layout.addWidget(self.clear_geofence_btn)
        layout.addWidget(self.print_geofence_btn)
        layout.addWidget(self.clear_rally_btn)
        layout.addWidget(self.print_rally_btn)

        self.setLayout(layout)

    def load_map(self):
        map_file = os.path.abspath("map.html")
        self.map_view.setUrl(QUrl.fromLocalFile(map_file))

    def clear_waypoints(self):
        self.map_view.page().runJavaScript("clearWaypoints();")

    def print_waypoints(self):
        self.map_view.page().runJavaScript("getWaypoints();", self.handle_waypoints)

    def handle_waypoints(self, waypoints):
        print("Waypoints:", waypoints)

    def clear_geofence(self):
        self.map_view.page().runJavaScript("clearGeofence();")

    def print_geofence(self):
        self.map_view.page().runJavaScript("getGeofence();", self.handle_geofence)

    def handle_geofence(self, geofence):
        print("Geofence Points:", geofence)

    def clear_rally_points(self):
        self.map_view.page().runJavaScript("clearRallyPoints();")

    def print_rally_points(self):
        self.map_view.page().runJavaScript("getRallyPoints();", self.handle_rally_points)

    def handle_rally_points(self, rally_points):
        print("Rally Points:", rally_points)

class VideoFeedTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()

        self.video_widget = QVideoWidget()

        self.mode_auto_btn = QPushButton("Set Mode: AUTO")
        self.mode_manual_btn = QPushButton("Set Mode: MANUAL")

        layout.addWidget(self.video_widget)
        layout.addWidget(self.mode_auto_btn)
        layout.addWidget(self.mode_manual_btn)

        self.setLayout(layout)

class GCSMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GCS Application")
        self.setGeometry(100, 100, 800, 600)

        self.tabs = QTabWidget()
        self.mission_planning_tab = MissionPlanningTab()
        self.video_feed_tab = VideoFeedTab()

        self.tabs.addTab(self.mission_planning_tab, "Mission Planning")
        self.tabs.addTab(self.video_feed_tab, "Video Feed")

        self.setCentralWidget(self.tabs)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GCSMainWindow()
    window.show()
    sys.exit(app.exec_())
