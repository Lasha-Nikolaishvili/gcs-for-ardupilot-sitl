import sys
import threading
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget
)
from src.widget_classes.video import VideoFeedTab
from src.widget_classes.mission_planning import MissionPlanningTab
from src.connection import Connection


class GCSMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GCS Application")
        self.setGeometry(100, 100, 800, 600)
        
        # 1) Create one Connection and start its listener
        conn = Connection()
        # 2) Pass the same conn into both tabs
        self.tabs = QTabWidget()
        self.mission_planning_tab = MissionPlanningTab(conn)
        self.video_feed_tab       = VideoFeedTab(conn)

        self.tabs.addTab(self.mission_planning_tab, "Mission Planning")
        self.tabs.addTab(self.video_feed_tab, "Video Feed")

        self.setCentralWidget(self.tabs)

        # start/stop video on tab changes
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
    sys.exit(app.exec())
