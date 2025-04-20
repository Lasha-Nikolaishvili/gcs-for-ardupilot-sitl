import os
from src.utils.mavlink import mavlink_listener
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton
) 
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtCore import QUrl


class MissionPlanningTab(QWidget):
    def __init__(self):
        super().__init__()
        # Main layout of mission planning tab
        main_layout = QHBoxLayout()

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


        # Layout and widget for side buttons tab
        self.buttons_widget = QWidget()
        buttons_layout = QVBoxLayout()

        buttons_layout.addWidget(self.clear_mission_btn)
        buttons_layout.addWidget(self.print_waypoints_btn)
        buttons_layout.addWidget(self.clear_geofence_btn)
        buttons_layout.addWidget(self.print_geofence_btn)
        buttons_layout.addWidget(self.clear_rally_btn)
        buttons_layout.addWidget(self.print_rally_btn)

        self.buttons_widget.setLayout(buttons_layout)
        
        # Assemble layout
        main_layout.addWidget(self.map_view, 1)
        main_layout.addWidget(self.buttons_widget)
        self.setLayout(main_layout)

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
