import sys
import os
import cv2
import threading
from src.utils.mavlink import mavlink_listener
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSizePolicy
) 
from PyQt5.QtCore import QTimer, Qt, QMutex
from PyQt5.QtGui import QImage, QPixmap, QPainter, QFont, QColor


class VideoFeedTab(QWidget):
    def __init__(self):
        super().__init__()

        self.video_label = QLabel("Waiting for video stream...")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color: black; color: white;")
        self.video_label.setScaledContents(False)
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_label.setMinimumSize(320, 240)

        self.mode_auto_btn = QPushButton("Set Mode: AUTO")
        self.mode_manual_btn = QPushButton("Set Mode: MANUAL")

        layout = QVBoxLayout()
        layout.addWidget(self.video_label, stretch=1)
        layout.addWidget(self.mode_auto_btn)
        layout.addWidget(self.mode_manual_btn)
        self.setLayout(layout)

        self.cap = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)

        # Telemetry state and lock
        self.telemetry = {
            'mode': 'UNKNOWN',
            'alt': 0,
            'lat': 0.0,
            'lon': 0.0,
            'heading': 0,
            'wp_seq': 0,
            'wp_total': 0
        }
        self.telemetry_lock = QMutex()

        self.telemetry_thread = threading.Thread(target=mavlink_listener, daemon=True)
        self.telemetry_thread.start()

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

        # Draw HUD overlay
        painter = QPainter()
        painter.begin(qimg)
        painter.setFont(QFont("Arial", 14))
        painter.setPen(QColor("lime"))

        self.telemetry_lock.lock()
        hud_text = [
            f"Mode: {self.telemetry['mode']}",
            f"Alt: {self.telemetry['alt']:.1f} m",
            f"Lat: {self.telemetry['lat']:.6f}",
            f"Lon: {self.telemetry['lon']:.6f}",
            f"Heading: {self.telemetry['heading']}°",
            f"Mission WP: {self.telemetry['wp_seq']} / {self.telemetry['wp_total']}"
        ]
        self.telemetry_lock.unlock()

        y = 20
        for line in hud_text:
            painter.drawText(10, y, line)
            y += 22

        painter.end()

        self.video_label.setPixmap(QPixmap.fromImage(qimg).scaled(
            self.video_label.width(), self.video_label.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        ))