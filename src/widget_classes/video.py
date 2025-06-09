import cv2
import threading
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSizePolicy,
    QSlider, QGroupBox, QFormLayout
)
from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QImage, QPixmap, QPainter, QFont, QColor


class VideoFeedTab(QWidget):
    # Signals to notify the GUI thread about success/failure of opening the stream
    video_opened = Signal(object)  # carries the OpenCV VideoCapture
    video_failed = Signal()        # no payload, just “failed to open”

    def __init__(self, conn):
        super().__init__()
        self.conn = conn
        self.video_started = False

        # ——— BUILD EACH CONTROL GROUP —————————————————————————————

        # Flight controls
        self._make_flight_controls()

        # Video controls (just the “Start Video” for now)
        self._make_video_controls()

        # Gimbal sliders
        self._make_gimbal_sliders()

        # ——— LIVE VIDEO DISPLAY —————————————————————————————————————
        self.video_label = QLabel("Waiting for video stream…")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color: black; color: white;")
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_label.setMinimumSize(320, 240)

        # ——— ASSEMBLE LAYOUT —————————————————————————————————————
        main_layout = QHBoxLayout(self)

        # Left side: the video
        main_layout.addWidget(self.video_label, 1)

        # Right side: stack three group-boxes vertically
        right_panel = QVBoxLayout()
        right_panel.addWidget(self.flight_group)
        right_panel.addWidget(self.video_group)
        right_panel.addWidget(self.gimbal_group)
        right_panel.addStretch(1)
        main_layout.addLayout(right_panel)

        self.setLayout(main_layout)

        # ——— CAPTURE + TIMER SETUP —————————————————————————————————
        self.cap = None
        self._opening = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)

        # connect our background‐thread signals
        self.video_opened.connect(self._on_video_opened)
        self.video_failed.connect(self._on_video_failed)


    def _make_flight_controls(self):
        """Create a QGroupBox full of arm/disarm/takeoff/mode buttons."""
        self.arm_btn            = QPushButton("Arm")
        self.arm_btn.clicked.connect(self.conn.arm)

        self.disarm_btn         = QPushButton("Disarm")
        self.disarm_btn.clicked.connect(self.conn.disarm)

        self.takeoff_btn        = QPushButton("Takeoff")
        self.takeoff_btn.clicked.connect(lambda: self.conn.takeoff(10))

        self.mode_auto_btn      = QPushButton("Mode: AUTO")
        self.mode_auto_btn.clicked.connect(lambda: self.conn.set_mode("AUTO"))

        self.mode_guided_btn    = QPushButton("Mode: GUIDED")
        self.mode_guided_btn.clicked.connect(lambda: self.conn.set_mode("GUIDED"))

        self.mode_stabilize_btn = QPushButton("Mode: STABILIZE")
        self.mode_stabilize_btn.clicked.connect(lambda: self.conn.set_mode("STABILIZE"))

        self.mode_rtl_btn       = QPushButton("Mode: RTL")
        self.mode_rtl_btn.clicked.connect(lambda: self.conn.set_mode("RTL"))

        layout = QVBoxLayout()
        for btn in (
            self.arm_btn, self.disarm_btn,
            self.takeoff_btn,
            self.mode_auto_btn,
            self.mode_guided_btn,
            self.mode_stabilize_btn,
            self.mode_rtl_btn
        ):
            layout.addWidget(btn)

        self.flight_group = QGroupBox("Flight Controls")
        self.flight_group.setLayout(layout)


    def _make_video_controls(self):
        """Create a small QGroupBox containing the Start Video button."""
        self.start_button = QPushButton("Start Video")
        self.start_button.clicked.connect(self._on_start_button_clicked)

        layout = QVBoxLayout()
        layout.addWidget(self.start_button)
        layout.addStretch(1)

        self.video_group = QGroupBox("Video Controls")
        self.video_group.setLayout(layout)


    def _make_gimbal_sliders(self):
        """Create three labeled sliders for Roll/ Pitch/ Yaw overrides."""
        self.roll_slider  = QSlider(Qt.Horizontal)
        self.pitch_slider = QSlider(Qt.Horizontal)
        self.yaw_slider   = QSlider(Qt.Horizontal)

        for s in (self.roll_slider, self.pitch_slider, self.yaw_slider):
            s.setRange(1000, 2000)
            s.setSingleStep(5)
            s.setPageStep(50)
            s.setTickInterval(100)
            s.setTickPosition(QSlider.TicksBelow)

        # initialize to neutral
        self.roll_slider.setValue(1500)
        self.pitch_slider.setValue(1500)
        self.yaw_slider.setValue(1500)

        # wire up valueChanged → override_rc
        self.roll_slider.valueChanged.connect(lambda v: self.conn.override_rc(6, v))
        self.pitch_slider.valueChanged.connect(lambda v: self.conn.override_rc(7, v))
        self.yaw_slider.valueChanged.connect(lambda v: self.conn.override_rc(8, v))

        # center button
        self.center_btn = QPushButton("Center Gimbal")
        self.center_btn.clicked.connect(self._on_center_gimbal)

        form = QFormLayout()
        form.addRow("Roll  (RC6):",  self.roll_slider)
        form.addRow("Pitch (RC7):",  self.pitch_slider)
        form.addRow("Yaw   (RC8):",  self.yaw_slider)
        form.addRow("", self.center_btn)

        self.gimbal_group = QGroupBox("Gimbal Control")
        self.gimbal_group.setLayout(form)


    def _on_center_gimbal(self):
        """Reset all three sliders → this also sends neutral override on each."""
        for s in (self.roll_slider, self.pitch_slider, self.yaw_slider):
            s.setValue(1500)


    def _on_start_button_clicked(self):
        """User pressed Start Video for the first time."""
        self.start_button.setEnabled(False)
        self.video_label.setText("⚠️ Connecting to video…")
        self.video_started = True
        self.start_video()


    def start_video(self):
        """Called by the main window on tab switches (and by Start Video)."""
        if self.cap is not None:
            # already opened → just resume
            if not self.timer.isActive():
                self.timer.start(30)
            return
        if self._opening:
            return

        self._opening = True
        threading.Thread(target=self._open_stream_thread, daemon=True).start()


    def stop_video(self):
        """Stop frame timer & release capture when leaving the tab."""
        if self.timer.isActive():
            self.timer.stop()
        if self.cap is not None:
            try:
                self.cap.release()
            except:
                pass
            self.cap = None
        self._opening = False
        self.video_label.setText("Video paused")


    def _open_stream_thread(self):
        """Background thread: open the GStreamer pipeline without blocking UI."""
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


    def _on_video_opened(self, cap_obj):
        """Slot once the pipeline opens: start the frame timer."""
        self.cap = cap_obj
        self._opening = False
        self.video_label.setText("")  # clear “Connecting…” text
        if not self.timer.isActive():
            self.timer.start(30)        # ~33 FPS


    def _on_video_failed(self):
        """Slot if opening the pipeline fails."""
        self.cap = None
        self._opening = False
        self.video_label.setText("❌ Unable to open video stream.")


    def update_frame(self):
        """Grab a frame, overlay HUD, and repaint the label."""
        if not self.cap:
            return

        ret, frame = self.cap.read()
        if not ret:
            # stream died mid-flight
            self.timer.stop()
            try: self.cap.release()
            except: pass
            self.cap = None
            self.video_label.setText("⚠️ Video lost. Press Start to retry.")
            return

        # Convert BGR→RGB to QImage
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        qimg = QImage(frame_rgb.data, w, h, ch * w, QImage.Format_RGB888)

        # Build HUD text groups
        tel = self.conn.telemetry
        grpA = [  # top-left
            f"Mode:  {tel.get('mode','—')}",
            f"Armed: {tel.get('armed','—')}",
            f"Alt:   {tel.get('alt',0):.1f} m",
        ]
        grpB = [  # top-right
            f"Lat: {tel.get('lat',0):.6f}",
            f"Lon: {tel.get('lon',0):.6f}",
            f"Hdg: {tel.get('heading',0):.1f}°",
        ]
        grpC = [  # bottom-left
            f"WP: {tel.get('current_mission_point','-')}/{tel.get('total_mission_points','-')}",
        ]
        grpD = [  # bottom-right
            f"Batt: {tel.get('battery_voltage',0):.2f}V ({tel.get('battery_remaining',0)}%)",
            f"GPS: fix {tel.get('gps_fix_type',0)} / {tel.get('gps_satellites_visible',0)} sat",
            f"SPD: {tel.get('groundspeed',0):.1f} m/s",
            f"Clb: {tel.get('climb_rate',0):.1f} m/s",
            f"Thr: {tel.get('throttle',0)}%",
        ]

        painter = QPainter(qimg)
        painter.setFont(QFont("Consolas", 14))
        painter.setPen(QColor("lime"))

        fm = painter.fontMetrics()
        lh = fm.height()
        margin = 10

        # Draw each group in its corner
        # ── A: top-left
        xA, yA = margin, margin + fm.ascent()
        for line in grpA:
            painter.drawText(xA, yA, line)
            yA += lh

        # ── B: top-right
        maxBW = max(fm.horizontalAdvance(l) for l in grpB)
        xB = w - maxBW - margin
        yB = margin + fm.ascent()
        for line in grpB:
            painter.drawText(xB, yB, line)
            yB += lh

        # ── C: bottom-left
        xC = margin
        yC = h - margin - (len(grpC)-1)*lh
        for line in grpC:
            painter.drawText(xC, yC, line)
            yC += lh

        # ── D: bottom-right
        maxDW = max(fm.horizontalAdvance(l) for l in grpD)
        xD = w - maxDW - margin
        yD = h - margin - (len(grpD)-1)*lh
        for line in grpD:
            painter.drawText(xD, yD, line)
            yD += lh

        painter.end()

        # Paint into the label
        pix = QPixmap.fromImage(qimg).scaled(
            self.video_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.video_label.setPixmap(pix)
