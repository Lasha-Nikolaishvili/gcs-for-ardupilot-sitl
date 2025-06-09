# src/widget_classes/config.py
import os
import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QComboBox,
    QLineEdit, QPushButton, QHBoxLayout, QMessageBox
)
from PySide6.QtCore import Qt

class ConfigTab(QWidget):
    CONFIG_FILE = "map_sources.json"

    def __init__(self, conn, mission_tab):
        super().__init__()
        self.conn = conn
        self.mission_tab = mission_tab

        # ─── Load (or create) JSON of map sources ────────────────────────────
        self._load_map_sources()

        layout = QVBoxLayout(self)

        # ─── Map Source Selector ────────────────────────────────────────────
        layout.addWidget(QLabel("Map Tile Source:"))
        self.tile_combo = QComboBox()
        for name, url in self.map_sources.items():
            self.tile_combo.addItem(name, url)
        layout.addWidget(self.tile_combo)

        # ─── Custom Source: Name + URL + Add ─────────────────────────────────
        form_layout = QHBoxLayout()
        # Name field
        self.custom_name_edit = QLineEdit()
        self.custom_name_edit.setPlaceholderText("Name")
        self.custom_name_edit.setFixedWidth(120)
        # URL field
        self.custom_url_edit = QLineEdit()
        self.custom_url_edit.setPlaceholderText("Custom tile URL…")
        # Ensure paste/drag works
        self.custom_url_edit.setAcceptDrops(True)
        self.custom_url_edit.setDragEnabled(True)
        form_layout.addWidget(self.custom_name_edit)
        form_layout.addWidget(self.custom_url_edit, 1)

        self.add_btn = QPushButton("Add")
        self.add_btn.setCursor(Qt.PointingHandCursor)
        form_layout.addWidget(self.add_btn)
        layout.addLayout(form_layout)

        # ─── Apply Button ────────────────────────────────────────────────────
        self.apply_map_btn = QPushButton("Apply Map Source")
        self.apply_map_btn.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.apply_map_btn)
        layout.addSpacing(20)

        # ─── Parameter Controls ─────────────────────────────────────────────
        layout.addWidget(QLabel("Parameter ID:"))
        self.param_id_edit = QLineEdit()
        layout.addWidget(self.param_id_edit)

        layout.addWidget(QLabel("Parameter Value:"))
        self.param_value_edit = QLineEdit()
        layout.addWidget(self.param_value_edit)

        btn_layout = QHBoxLayout()
        self.get_btn = QPushButton("Get Param")
        self.get_btn.setCursor(Qt.PointingHandCursor)
        self.set_btn = QPushButton("Set Param")
        self.set_btn.setCursor(Qt.PointingHandCursor)
        btn_layout.addWidget(self.get_btn)
        btn_layout.addWidget(self.set_btn)
        layout.addLayout(btn_layout)

        layout.addStretch(1)
        layout.setContentsMargins(20, 20, 20, 20)

        # ─── Signal connections ──────────────────────────────────────────────
        self.add_btn.clicked.connect(self.on_add_custom)
        self.apply_map_btn.clicked.connect(self.on_apply_map)
        self.get_btn.clicked.connect(self.on_get_param)
        self.set_btn.clicked.connect(self.on_set_param)

    def _load_map_sources(self):
        """Load map_sources.json or initialize with defaults."""
        defaults = {
            "OpenStreetMap":    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
            "CartoDB Positron": "https://cartodb-basemaps-{s}.global.ssl.fastly.net/light_all/{z}/{x}/{y}.png",
            "ESRI Satellite":   "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
        }
        path = ConfigTab.CONFIG_FILE
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                self.map_sources = data if isinstance(data, dict) else defaults.copy()
            except Exception:
                self.map_sources = defaults.copy()
        else:
            self.map_sources = defaults.copy()
            self._save_map_sources()

    def _save_map_sources(self):
        """Persist map_sources to JSON."""
        try:
            with open(ConfigTab.CONFIG_FILE, "w") as f:
                json.dump(self.map_sources, f, indent=4)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save map config:\n{e}")

    def on_add_custom(self):
        """Add a new named URL to the combo and JSON."""
        name = self.custom_name_edit.text().strip()
        url  = self.custom_url_edit.text().strip()

        if not name or not url:
            QMessageBox.warning(self, "Add URL", "Please enter both a Name and a URL.")
            return
        if name in self.map_sources:
            QMessageBox.warning(self, "Add URL", f"Name '{name}' already exists.")
            return

        # Save to in-memory and to disk
        self.map_sources[name] = url
        self._save_map_sources()

        # Add to combo and select it
        self.tile_combo.addItem(name, url)
        self.tile_combo.setCurrentIndex(self.tile_combo.count() - 1)

        # Clear inputs
        self.custom_name_edit.clear()
        self.custom_url_edit.clear()

    def on_apply_map(self):
        """Swap out the Leaflet tile layer for the selected URL."""
        url = self.tile_combo.currentData()
        if not url:
            QMessageBox.warning(self, "Apply Map", "No tile URL selected.")
            return

        js = f"""
            map.eachLayer(function(layer) {{
                if (layer instanceof L.TileLayer) {{
                    map.removeLayer(layer);
                }}
            }});
            L.tileLayer("{url}", {{ maxZoom: 19 }}).addTo(map);
        """
        view = self.mission_tab.map_view
        view.page().runJavaScript(js)
        QMessageBox.information(self, "Map Source", "Map source updated.")

    def on_get_param(self):
        pid = self.param_id_edit.text().strip()
        if not pid:
            QMessageBox.warning(self, "Get Param", "Enter a parameter ID.")
            return
        try:
            msg = self.conn.get_param(pid)
            QMessageBox.information(self, "Get Param", f"{pid} = {msg.param_value}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to get param:\n{e}")

    def on_set_param(self):
        pid = self.param_id_edit.text().strip()
        val_str = self.param_value_edit.text().strip()
        if not pid or not val_str:
            QMessageBox.warning(self, "Set Param", "Enter both ID and value.")
            return
        try:
            val = float(val_str)
        except ValueError:
            QMessageBox.warning(self, "Set Param", "Value must be numeric.")
            return
        try:
            new_val = self.conn.set_param(pid, val)
            QMessageBox.information(self, "Set Param", f"{pid} set to {new_val}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to set param:\n{e}")
