import sys
import os
import cv2

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSizePolicy
) 
from PyQt5.QtCore import QTimer, Qt 
from PyQt5.QtGui import QImage, QPixmap 
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

class VideoFeedTab(QWidget):
    def __init__(self):
        super().__init__()

        self.video_label = QLabel("Waiting for video stream...")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color: black; color: white;")
        self.video_label.setScaledContents(False)

        # Set size policy: expanding but resizable
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_label.setMinimumSize(320, 240)  # prevent shrink to zero

        self.mode_auto_btn = QPushButton("Set Mode: AUTO")
        self.mode_manual_btn = QPushButton("Set Mode: MANUAL")

        # Main layout
        main_layout = QHBoxLayout()
        
        # Layout and widget for side buttons tab
        self.buttons_widget = QWidget()
        buttons_layout = QVBoxLayout()

        buttons_layout.addWidget(self.mode_auto_btn)
        buttons_layout.addWidget(self.mode_manual_btn)
        self.buttons_widget.setLayout(buttons_layout)
        
        main_layout.addWidget(self.video_label, stretch=1)
        main_layout.addWidget(self.buttons_widget)
        self.setLayout(main_layout)

        self.cap = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)

    def init_video_stream(self):
        pipeline = (
            "udpsrc port=5600 "
            "! application/x-rtp, encoding-name=H264, payload=96 ! "
            "rtpjitterbuffer ! rtph264depay ! avdec_h264 ! videoconvert ! appsink"
        )
        self.cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)

        if not self.cap.isOpened():
            self.video_label.setText("❌ Unable to open video stream.")
            self.cap = None

    def start_video(self):
        if self.cap is None:
            self.init_video_stream()
        if self.cap and not self.timer.isActive():
            self.timer.start(30)

    def stop_video(self):
        if self.timer.isActive():
            self.timer.stop()
        if self.cap and self.cap.isOpened():
            self.cap.release()
        self.cap = None
        self.video_label.setText("Video stream paused")

    def update_frame(self):
        if self.cap is None:
            return
        ret, frame = self.cap.read()
        if not ret:
            return

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w
        qimg = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)

        self.video_label.setPixmap(QPixmap.fromImage(qimg).scaled(
            self.video_label.width(), self.video_label.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        ))

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
        self.tabs.currentChanged.connect(self.on_tab_changed)

    def on_tab_changed(self, index):
        if self.tabs.widget(index) is self.video_feed_tab:
            self.video_feed_tab.start_video()
        else:
            self.video_feed_tab.stop_video()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GCSMainWindow()
    window.show()
    sys.exit(app.exec_())
