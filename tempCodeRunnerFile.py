# main.py
import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget
from src.widget_classes.video import VideoFeedTab
from src.widget_classes.mission_planning import MissionPlanningTab
from src.widget_classes.config import ConfigTab
from src.connection import Connection

class GCSMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GCS Application")
        self.setGeometry(100, 100, 800, 600)
        
        # 1) Create one Connection (no SITL connect at init)
        conn = Connection()
        
        # 2) Create tabs
        self.tabs = QTabWidget()
        self.mission_planning_tab = MissionPlanningTab(conn)
        self.video_feed_tab       = VideoFeedTab(conn)
        self.config_tab           = ConfigTab(conn, self.mission_planning_tab)

        self.tabs.addTab(self.mission_planning_tab, "Mission Planning")
        self.tabs.addTab(self.video_feed_tab,       "Video Feed")
        self.tabs.addTab(self.config_tab,           "Config")

        self.setCentralWidget(self.tabs)

        # start/stop video on tab changes
        self.tabs.currentChanged.connect(self.on_tab_changed)

    def on_tab_changed(self, index):
        if self.tabs.widget(index) is self.video_feed_tab:
            # Only auto-start if the user has pressed Start Video at least once
            if self.video_feed_tab.video_started:
                self.video_feed_tab.start_video()
        else:
            # Always stop when leaving the video tab
            self.video_feed_tab.stop_video()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    with open("palette.qss", "r") as f:
        app.setStyleSheet(f.read())

    window = GCSMainWindow()
    window.show()
    sys.exit(app.exec())
