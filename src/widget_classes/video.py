import cv2, threading, json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSizePolicy
)
from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QImage, QPixmap, QPainter, QFont, QColor


class VideoFeedTab(QWidget):
    # Signals to notify the GUI thread about success/failure of opening the stream
    video_opened = Signal(object)  # will carry the OpenCV VideoCapture instance
    video_failed = Signal()        # no payload, just “failed to open”

    def __init__(self, conn):
        super().__init__()
        self.conn = conn

        # Track whether the user has ever pressed “Start Video”
        self.video_started = False

        # ——— Build UI ——————————————————————————————————————————————
        # 1) A “Start Video” button at the very top
        self.start_button = QPushButton("Start Video")
        self.start_button.clicked.connect(self._on_start_button_clicked)

        # 2) The video display label + control buttons side-bar
        self.video_label = QLabel("Waiting for video stream...")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color: black; color: white;")
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_label.setMinimumSize(320, 240)

        self.arm_btn            = QPushButton("Arm");       self.arm_btn.clicked.connect(self.conn.arm)
        self.disarm_btn         = QPushButton("Disarm");    self.disarm_btn.clicked.connect(self.conn.disarm)
        self.takeoff_btn        = QPushButton("Takeoff");   self.takeoff_btn.clicked.connect(lambda: self.conn.takeoff(10))
        self.mode_auto_btn      = QPushButton("Mode: AUTO");    self.mode_auto_btn.clicked.connect(lambda: self.conn.set_mode("AUTO"))
        self.mode_guided_btn    = QPushButton("Mode: GUIDED"); self.mode_guided_btn.clicked.connect(lambda: self.conn.set_mode("GUIDED"))
        self.mode_stabilize_btn = QPushButton("Mode: STABILIZE"); self.mode_stabilize_btn.clicked.connect(lambda: self.conn.set_mode("STABILIZE"))
        self.mode_rtl_btn       = QPushButton("Mode: RTL");     self.mode_rtl_btn.clicked.connect(lambda: self.conn.set_mode("RTL"))

        buttons_layout = QVBoxLayout()
        for btn in (
            self.arm_btn, self.disarm_btn,
            self.takeoff_btn,
            self.mode_auto_btn,
            self.mode_guided_btn,
            self.mode_stabilize_btn,
            self.mode_rtl_btn
        ):
            buttons_layout.addWidget(btn)
        self.buttons_widget = QWidget()
        self.buttons_widget.setLayout(buttons_layout)

        # Place video + controls side by side
        inner_layout = QHBoxLayout()
        inner_layout.addWidget(self.video_label, 1)
        inner_layout.addWidget(self.buttons_widget)

        # Now stack Start button above that
        root_layout = QVBoxLayout(self)
        root_layout.addWidget(self.start_button)
        root_layout.addLayout(inner_layout)
        self.setLayout(root_layout)

        # ——— Internal state & threading —————————————————————————————
        self.cap = None
        self._opening = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)

        # Connect background-thread signals
        self.video_opened.connect(self._on_video_opened)
        self.video_failed.connect(self._on_video_failed)


    # ——— Button click handler —————————————————————————————————————
    def _on_start_button_clicked(self):
        # First‐time user pressed Start
        self.start_button.setEnabled(False)
        self.video_label.setText("⚠️ Connecting to video…")
        self.video_started = True
        self.start_video()


    # ——— Called by GCSMainWindow on tab switches —————————————————————————
    def start_video(self):
        if self.cap is not None:
            # Already open: just resume
            if not self.timer.isActive():
                self.timer.start(30)
            return

        if self._opening:
            # Already in the middle of opening
            return

        self._opening = True
        # Launch background thread so we don't block the UI
        threading.Thread(target=self._open_stream_thread, daemon=True).start()


    def stop_video(self):
        # Stop the frame timer
        if self.timer.isActive():
            self.timer.stop()
        # Release the capture if it was open
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
        # Reset opening flag
        self._opening = False
        self.video_label.setText("Video paused")


    # ——— Thread: open the GStreamer pipeline —————————————————————————
    def _open_stream_thread(self):
        pipeline = (
            "udpsrc port=5600 "
            "! application/x-rtp, encoding-name=H264, payload=96 "
            "! rtpjitterbuffer ! rtph264depay ! avdec_h264 ! videoconvert ! appsink"
        )
        cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
        if not cap.isOpened():
            self.video_failed.emit()
        else:
            self.video_opened.emit(cap)


    # ——— Slots for open success / failure ———————————————————————————

    def _on_video_opened(self, cap_obj):
        self.cap = cap_obj
        self._opening = False
        self.video_label.setText("")         # clear “Connecting…” text
        if not self.timer.isActive():
            self.timer.start(30)             # ~33 FPS

    def _on_video_failed(self):
        self.cap = None
        self._opening = False
        self.video_label.setText("❌ Unable to open video stream.")


    # ——— Grabs a frame + overlays HUD —————————————————————————————
    def update_frame(self):
        if not self.cap:
            return

        ret, frame = self.cap.read()
        if not ret:
            # Stream died mid‐flight
            self.timer.stop()
            try: self.cap.release()
            except: pass
            self.cap = None
            self.video_label.setText("⚠️ Video lost. Press Start to retry.")
            return

        # Convert to QImage
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        qimg = QImage(frame_rgb.data, w, h, ch * w, QImage.Format_RGB888)

        # Draw HUD
        painter = QPainter(qimg)
        painter.setFont(QFont("Arial", 14))
        painter.setPen(QColor("lime"))
        tel = self.conn.telemetry
        lines = [
            f"Mode: {tel.get('mode','—')}",
            f"Armed: {tel.get('armed','—')}",
            f"Alt: {tel.get('alt',0):.1f} m",
            f"Lat: {tel.get('lat',0):.6f}",
            f"Lon: {tel.get('lon',0):.6f}",
            f"Hdg: {tel.get('heading',0)}°",
            f"WP: {tel.get('current_mission_point','-')}/{tel.get('total_mission_points','-')}"
        ]
        y = 20
        for line in lines:
            painter.drawText(10, y, line)
            y += 22
        painter.end()

        # Display
        pix = QPixmap.fromImage(qimg).scaled(
            self.video_label.size(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.video_label.setPixmap(pix)
