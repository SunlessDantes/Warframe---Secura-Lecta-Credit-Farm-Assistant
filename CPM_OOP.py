import os
import ctypes
import sys
import shutil
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame
pygame.init() # Initialize all imported pygame modules

# Ensure local modules in the same directory are found
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import time
import json
import winsound
import random
import string
import warnings
import subprocess
from datetime import datetime
import cv2 as cv #pip install opencv-python
import easyocr as ocr #pip install easyocr
import mss #pip install mss
import keyboard as key #pip install keyboard
import numpy as np #pip install numpy
import pydirectinput #pip install pydirectinput
import pandas as pd #pip install pandas
import pyqtgraph as pg #pip install pyqtgraph and pip install pyQt5
import matplotlib.pyplot as plt #pip install matplotlib
from screeninfo import get_monitors #pip install screeninfo
from pyqtgraph.Qt import QtWidgets, QtCore, QtGui
from log_reader import LogReader
from fps_tracker import FPSTracker
warnings.filterwarnings("ignore", message=".pin_memory.")



class LargeNumberAxisItem(pg.AxisItem):
    def tickStrings(self, values, scale, spacing):
        strings = []
        for v in values:
            if v >= 1_000_000:
                strings.append(f"{v/1_000_000:.2f}M")
            elif v >= 1_000:
                val = v / 1_000
                strings.append(f"{int(val)}k" if val.is_integer() else f"{val:.1f}k")
            else:
                strings.append(f"{int(v)}")
        return strings

class OverlayWindow(QtWidgets.QWidget):
    def __init__(self, geometry, boxes):
        super().__init__()
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.Tool)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        self.setGeometry(*geometry)
        self.boxes = boxes

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        pen = QtGui.QPen(QtGui.QColor(255, 0, 0), 2)
        painter.setPen(pen)
        for x, y, w, h in self.boxes:
            painter.drawRect(x, y, w, h)

class ConfigEditor(QtWidgets.QDialog):
    def __init__(self, img_np, config_data, monitor_offset, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Config Editor - Drag/Resize Boxes")
        self.resize(1200, 800)
        self.img_np = img_np
        self.data = config_data
        self.offset_x, self.offset_y = monitor_offset
        
        self.layout = QtWidgets.QVBoxLayout(self)
        
        # Instructions
        lbl = QtWidgets.QLabel("Drag boxes to move. Drag handles to resize. Click Save to apply.")
        self.layout.addWidget(lbl)

        self.glw = pg.GraphicsLayoutWidget()
        self.layout.addWidget(self.glw)
        
        self.vb = self.glw.addViewBox()
        self.vb.setAspectLocked()
        self.vb.invertY() 
        
        # Convert BGRA/BGR to RGB and Transpose for pyqtgraph (w, h, c)
        if img_np.shape[2] == 4:
            img_rgb = cv.cvtColor(img_np, cv.COLOR_BGRA2RGB)
        else:
            img_rgb = cv.cvtColor(img_np, cv.COLOR_BGR2RGB)
        img_t = np.transpose(img_rgb, (1, 0, 2))
        
        self.img_item = pg.ImageItem(img_t)
        self.vb.addItem(self.img_item)
        
        self.rois = {}
        self.labels = []
        
        self.load_boxes()
        
        self.btn_save = QtWidgets.QPushButton("Save Changes")
        self.btn_save.clicked.connect(self.save_and_close)
        self.layout.addWidget(self.btn_save)

    def add_roi(self, name, coords, color):
        # coords: [l, t, r, b]
        l, t, r, b = coords
        x = l - self.offset_x
        y = t - self.offset_y
        w = r - l
        h = b - t
        
        roi = pg.RectROI([x, y], [w, h], pen=pg.mkPen(color, width=2), removable=False)
        roi.addScaleHandle([1, 1], [0, 0])
        roi.addScaleHandle([0, 0], [1, 1])
        self.vb.addItem(roi)
        
        lbl = pg.TextItem(name, color=color, anchor=(0, 1))
        lbl.setPos(x, y)
        self.vb.addItem(lbl)
        
        roi.sigRegionChanged.connect(lambda: lbl.setPos(roi.pos()))
        
        self.rois[name] = roi
        self.labels.append(lbl)

class AcolyteConfigDialog(QtWidgets.QDialog):
    def __init__(self, current_config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Acolyte Warner Configuration")
        self.config = current_config
        layout = QtWidgets.QVBoxLayout(self)
        
        # Audio Cue
        self.check_audio = QtWidgets.QCheckBox("Enable Audio Alert")
        self.check_audio.setChecked(self.config.get("audio_cue", True))
        layout.addWidget(self.check_audio)

        # Countdown Duration
        duration_layout = QtWidgets.QHBoxLayout()
        duration_layout.addWidget(QtWidgets.QLabel("Countdown Duration (seconds):"))
        self.spin_duration = QtWidgets.QDoubleSpinBox()
        self.spin_duration.setRange(1.0, 60.0)
        self.spin_duration.setSingleStep(0.5)
        self.spin_duration.setValue(self.config.get("duration", 12.0))
        duration_layout.addWidget(self.spin_duration)
        layout.addLayout(duration_layout)

        # Flash Color
        color_layout = QtWidgets.QHBoxLayout()
        color_layout.addWidget(QtWidgets.QLabel("Flash Color:"))
        self.btn_color = QtWidgets.QPushButton()
        c = self.config.get("color", "#FF0000")
        self.btn_color.setStyleSheet(f"background-color: {c};")
        self.btn_color.clicked.connect(self.pick_color)
        color_layout.addWidget(self.btn_color)
        layout.addLayout(color_layout)

        # Opacity
        opacity_layout = QtWidgets.QHBoxLayout()
        opacity_layout.addWidget(QtWidgets.QLabel("Flash Opacity:"))
        self.slider_opacity = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_opacity.setRange(10, 100) # 10% to 100%
        self.slider_opacity.setValue(self.config.get("opacity", 50))
        self.slider_opacity.valueChanged.connect(lambda v: self.label_opacity.setText(f"{v}%"))
        opacity_layout.addWidget(self.slider_opacity)
        self.label_opacity = QtWidgets.QLabel(f"{self.slider_opacity.value()}%")
        opacity_layout.addWidget(self.label_opacity)
        layout.addLayout(opacity_layout)

        # OK/Cancel buttons
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def pick_color(self):
        color = QtWidgets.QColorDialog.getColor(QtGui.QColor(self.btn_color.styleSheet().split(":")[1].strip().rstrip(';')))
        if color.isValid():
            self.btn_color.setStyleSheet(f"background-color: {color.name()};")

    def get_config(self):
        style = self.btn_color.styleSheet()
        color_hex = style.split(":")[1].strip().rstrip(';')
        return {
            "audio_cue": self.check_audio.isChecked(),
            "duration": self.spin_duration.value(),
            "color": color_hex,
            "opacity": self.slider_opacity.value()
        }

class DraggableNumberOverlay(QtWidgets.QLabel):
    def __init__(self, label_key, color_hex, monitor_info, initial_pos=None, font_size=24, parent=None):
        super().__init__(parent)
        self.monitor_info = monitor_info
        self.label_key = label_key
        self.setText(f"{label_key}: --")
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.Tool)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.color_hex = color_hex
        self.font_size = font_size
        self.update_style()
        self.drag_pos = None
        self.adjustSize()
        if initial_pos:
            self.move(initial_pos)

    def update_style(self):
        # Add a slight shadow/outline effect for readability on game backgrounds
        self.setStyleSheet(f"color: {self.color_hex}; font-weight: bold; font-family: Arial; "
                           f"qproperty-alignment: AlignCenter;")
        self.setFont(QtGui.QFont("Arial", self.font_size))
        self.adjustSize()

    def update_value(self, value):
        self.setText(f"{self.label_key}: {value}")
        self.adjustSize()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == QtCore.Qt.LeftButton and self.drag_pos:
            desired_pos = event.globalPos() - self.drag_pos
            
            # Constrain to monitor bounds
            x = desired_pos.x()
            y = desired_pos.y()
            
            if self.monitor_info:
                min_x = self.monitor_info["left"]
                min_y = self.monitor_info["top"]
                max_x = min_x + self.monitor_info["width"] - self.width()
                max_y = min_y + self.monitor_info["height"] - self.height()
                
                x = max(min_x, min(x, max_x))
                y = max(min_y, min(y, max_y))
            
            self.move(x, y)
            event.accept()

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta > 0:
            self.font_size += 2
        else:
            self.font_size = max(10, self.font_size - 2)
        self.update_style()

class OverlayConfigDialog(QtWidgets.QDialog):
    def __init__(self, current_config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Overlay Configuration")
        self.config = current_config
        layout = QtWidgets.QVBoxLayout(self)
        
        grid = QtWidgets.QGridLayout()
        layout.addLayout(grid)
        
        headers = ["Metric", "Show", "Color"]
        for col, h in enumerate(headers):
            grid.addWidget(QtWidgets.QLabel(f"<b>{h}</b>"), 0, col)

        self.widgets = {}
        metrics = ["CPM", "KPM", "Num alive", "FPS"]
        
        for i, m in enumerate(metrics):
            row = i + 1
            grid.addWidget(QtWidgets.QLabel(m), row, 0)
            
            chk = QtWidgets.QCheckBox()
            chk.setChecked(self.config.get(m, {}).get("show", True))
            grid.addWidget(chk, row, 1)
            
            btn_color = QtWidgets.QPushButton()
            c = self.config.get(m, {}).get("color", "#FF0000")
            btn_color.setStyleSheet(f"background-color: {c}")
            btn_color.clicked.connect(lambda _, b=btn_color: self.pick_color(b))
            grid.addWidget(btn_color, row, 2)
            
            self.widgets[m] = (chk, btn_color)

        btn_ok = QtWidgets.QPushButton("OK")
        btn_ok.clicked.connect(self.accept)
        layout.addWidget(btn_ok)

    def pick_color(self, btn):
        color = QtWidgets.QColorDialog.getColor()
        if color.isValid():
            btn.setStyleSheet(f"background-color: {color.name()}")

    def get_config(self):
        new_config = {}
        for m, (chk, btn) in self.widgets.items():
            # Extract hex color from stylesheet string
            style = btn.styleSheet()
            color = style.split(":")[1].strip()
            new_config[m] = {"show": chk.isChecked(), "color": color}
        return new_config

class AcolyteWarner(QtWidgets.QWidget):
    def __init__(self, config, monitor_info):
        super().__init__()
        self.config = config
        self.monitor_info = monitor_info
        
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.Tool)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        
        # Center on primary monitor
        w, h = 400, 150
        mon_w, mon_h = self.monitor_info['width'], self.monitor_info['height']
        mon_l, mon_t = self.monitor_info['left'], self.monitor_info['top']
        self.setGeometry(mon_l + (mon_w - w) // 2, mon_t + (mon_h - h) // 2, w, h)

        self.label = QtWidgets.QLabel("", self)
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setStyleSheet("color: white; font-size: 48pt; font-weight: bold;")
        
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.label)
        
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_tick)
        
        self.end_time = 0
        self.flash_on = False
        self.hide_time = 0

    def paintEvent(self, event):
        if self.flash_on:
            painter = QtGui.QPainter(self)
            color = QtGui.QColor(self.config.get("color", "#FF0000"))
            opacity_pct = self.config.get("opacity", 50)
            color.setAlphaF(opacity_pct / 100.0)
            painter.fillRect(self.rect(), color)

    def start_warning(self, duration):
        self.end_time = time.perf_counter() + duration
        self.hide_time = 0
        self.flash_on = True
        self.timer.start(100) # Update 10 times a second
        self.show()
        self.raise_()

    def update_tick(self):
        now = time.perf_counter()
        if self.hide_time > 0:
            if now >= self.hide_time:
                self.timer.stop()
                self.hide()
            return
        remaining = self.end_time - now
        if remaining > 0:
            self.label.setText(f"Acolyte in: {remaining:.1f}s")
            self.flash_on = not self.flash_on
        else:
            self.label.setText("ACOLYTE SPAWNED")
            self.flash_on = True # Solid color on spawn
            if self.hide_time == 0: # Set hide timer only once
                self.hide_time = now + 2.0 
        self.update() # Triggers paintEvent

    def load_boxes(self):
        if 'scan_area' in self.data:
            self.add_roi("Scan Area", self.data['scan_area'], 'g')
        if 'credit_positions' in self.data:
            for i, box in enumerate(self.data['credit_positions']):
                self.add_roi(f"Credit {i+1}", box, 'y')
        if self.data.get('track_kills') and 'kills' in self.data and self.data['kills']:
             self.add_roi("Kills", self.data['kills'], 'r')

    def save_and_close(self):
        def get_abs_coords(roi):
            pos = roi.pos()
            size = roi.size()
            l = int(pos.x() + self.offset_x)
            t = int(pos.y() + self.offset_y)
            r = int(l + size.x())
            b = int(t + size.y())
            return [l, t, r, b]

        if "Scan Area" in self.rois:
            self.data['scan_area'] = get_abs_coords(self.rois["Scan Area"])
        if 'credit_positions' in self.data:
            new_creds = []
            for i in range(len(self.data['credit_positions'])):
                name = f"Credit {i+1}"
                if name in self.rois:
                    new_creds.append(get_abs_coords(self.rois[name]))
            self.data['credit_positions'] = new_creds
        if "Kills" in self.rois:
            self.data['kills'] = get_abs_coords(self.rois["Kills"])
        self.accept()

    def keyPressEvent(self, event):
        if event.key() in (QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return):
            self.save_and_close()
        else:
            super().keyPressEvent(event)

class SettingsDialog(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tracker Settings")
        self.resize(300, 300)
        layout = QtWidgets.QVBoxLayout()

        self.settings_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "last_run_settings.json")
        self.path_config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "path_config.json")

        # --- Output Path Setup ---
        self.output_path = os.path.join(os.getcwd(), "OUTPUT")
        if os.path.exists(self.path_config_file):
            try:
                with open(self.path_config_file, 'r') as f:
                    self.output_path = json.load(f).get("output_path", self.output_path)
            except: pass
        else:
            # First time setup: Ask user for folder
            d = QtWidgets.QFileDialog.getExistingDirectory(None, "Select Folder for Run Data Storage")
            if d:
                self.output_path = d
                # Save immediately to prevent re-prompting if the user closes the dialog without starting
                try:
                    with open(self.path_config_file, 'w') as f:
                        json.dump({"output_path": self.output_path}, f, indent=4)
                except Exception as e:
                    print(f"[Settings] Error saving initial path config: {e}")

        # Default Overlay Config
        self.overlay_config = {
            "CPM": {"show": True, "color": "#FF0000"},
            "KPM": {"show": True, "color": "#FF0000"},
            "Num alive": {"show": True, "color": "#FF0000"},
            "FPS": {"show": True, "color": "#FF0000"},
        }
        # Default Acolyte Config
        self.acolyte_config = {
            "enabled": False,
            "audio_cue": True,
            "duration": 12.0,
            "color": "#FF0000",
            "opacity": 50
        }

        # Output Path UI
        path_layout = QtWidgets.QHBoxLayout()
        path_layout.addWidget(QtWidgets.QLabel("Data Folder:"))
        self.line_path = QtWidgets.QLineEdit(self.output_path)
        self.line_path.setReadOnly(True)
        path_layout.addWidget(self.line_path)
        self.btn_browse = QtWidgets.QPushButton("...")
        self.btn_browse.setFixedWidth(30)
        self.btn_browse.clicked.connect(self.browse_output_folder)
        path_layout.addWidget(self.btn_browse)
        layout.addLayout(path_layout)

        # Previous Settings Checkbox
        self.check_load_prev = QtWidgets.QCheckBox("Load Last Used Settings")
        self.check_load_prev.setToolTip("If checked, restores all settings from the last time you started the tracker.")
        self.check_load_prev.toggled.connect(self.load_previous_settings)
        layout.addWidget(self.check_load_prev)
        
        if not os.path.exists(self.settings_file):
            self.check_load_prev.setEnabled(False)
            self.check_load_prev.setText("Load Last Used Settings (None found)")

        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setFrameShadow(QtWidgets.QFrame.Sunken)
        layout.addWidget(line)

        # Config Mode
        self.mode_group = QtWidgets.QGroupBox("Configuration Mode")
        self.mode_group.setToolTip("Selects which configuration file to use.\nRun the bounding box setup for both 'Solo' and 'Duo' modes if needed.")
        mode_layout = QtWidgets.QHBoxLayout()
        self.radio_solo = QtWidgets.QRadioButton("Solo")
        self.radio_duo = QtWidgets.QRadioButton("Duo")
        self.radio_solo.setChecked(True)
        mode_layout.addWidget(self.radio_solo)
        mode_layout.addWidget(self.radio_duo)
        self.mode_group.setLayout(mode_layout)
        layout.addWidget(self.mode_group)

        # Scan Delay
        layout.addWidget(QtWidgets.QLabel("Scan Delay (sec) [Wait after Tab]:"))
        self.spin_delay = QtWidgets.QDoubleSpinBox()
        self.spin_delay.setRange(0.1, 2.0)
        self.spin_delay.setSingleStep(0.1)
        self.spin_delay.setValue(0.3)
        self.spin_delay.setToolTip("How long to wait (in seconds) after you press TAB before taking a screenshot.\nIncrease if the UI takes longer to fade in.")
        layout.addWidget(self.spin_delay)

        # Cooldown
        layout.addWidget(QtWidgets.QLabel("Cooldown (sec) [Min time between scans]:"))
        self.spin_cooldown = QtWidgets.QDoubleSpinBox()
        self.spin_cooldown.setRange(0.5, 10.0)
        self.spin_cooldown.setSingleStep(0.5)
        self.spin_cooldown.setValue(3.0)
        self.spin_cooldown.setToolTip("The minimum time (in seconds) required between two consecutive TAB scans.\nPrevents accidental double-scanning.")
        layout.addWidget(self.spin_cooldown)

        # Toggles
        self.check_credits = QtWidgets.QCheckBox("Track Credits")
        self.check_credits.setChecked(True)
        self.check_credits.setToolTip("Enables tracking of Credits and Credits Per Minute (CPM) via OCR.")
        layout.addWidget(self.check_credits)

        self.check_kills = QtWidgets.QCheckBox("Track Kills")
        self.check_kills.setChecked(False)
        self.check_kills.setToolTip("Enables tracking of Kills and Kills Per Minute (KPM).\nIf 'Track Enemy data' is also checked, this uses the accurate log data instead of OCR.")
        layout.addWidget(self.check_kills)

        # Extras
        self.check_on_top = QtWidgets.QCheckBox("Window Always on Top")
        self.check_on_top.setChecked(True)
        self.check_on_top.setToolTip("Keeps the live graph window always visible on top of other applications.")
        layout.addWidget(self.check_on_top)

        self.check_sound = QtWidgets.QCheckBox("Sound Alert on Scan")
        self.check_sound.setChecked(False)
        self.check_sound.setToolTip("Plays a short 'beep' sound to confirm a successful scan has been processed.")
        layout.addWidget(self.check_sound)

        self.check_debug = QtWidgets.QCheckBox("Debug: Save Images on Fail")
        self.check_debug.setChecked(False)
        self.check_debug.setToolTip("If an OCR scan fails to read a number, it will save the screenshot to the run's output folder for troubleshooting.")
        layout.addWidget(self.check_debug)

        self.check_logs = QtWidgets.QCheckBox("Track Enemy data. WARNING THIS READS LOG.EE DATA")
        self.check_logs.setStyleSheet("color: red; font-weight: bold;")
        self.check_logs.setChecked(False)
        self.check_logs.setToolTip("Reads Warframe's EE.log file in real-time to track enemy spawn/death counts.\nThis provides highly accurate, continuous KPM data.")
        layout.addWidget(self.check_logs)
        
        # Acolyte Warner (only available if log tracking is on)
        acolyte_group = QtWidgets.QGroupBox("Acolyte Warner")
        acolyte_layout = QtWidgets.QHBoxLayout()
        self.check_acolyte = QtWidgets.QCheckBox("Enable")
        self.check_acolyte.setToolTip("Flashes a warning on-screen when an Acolyte is about to spawn.\nRequires 'Track Enemy data' to be enabled.")
        self.check_acolyte.toggled.connect(lambda c: self.btn_conf_acolyte.setEnabled(c))
        acolyte_layout.addWidget(self.check_acolyte)
        
        self.btn_conf_acolyte = QtWidgets.QPushButton("Configure...")
        self.btn_conf_acolyte.setEnabled(False)
        self.btn_conf_acolyte.clicked.connect(self.open_acolyte_config)
        acolyte_layout.addWidget(self.btn_conf_acolyte)
        acolyte_group.setLayout(acolyte_layout)
        layout.addWidget(acolyte_group)

        # FPS Checkbox
        self.check_fps = QtWidgets.QCheckBox("Track FPS (Requires PresentMon.exe)")
        self.check_fps.setChecked(False)
        self.check_fps.setToolTip("Tracks Frames Per Second using PresentMon.\nRequires PresentMon.exe in the same folder.")
        layout.addWidget(self.check_fps)

        # Number Overlay
        overlay_group = QtWidgets.QGroupBox("In-Game Overlay")
        overlay_layout = QtWidgets.QHBoxLayout()
        self.check_overlay = QtWidgets.QCheckBox("Enable Number Overlay")
        self.check_overlay.setToolTip("Displays draggable, resizable numbers (CPM, KPM, etc.) over the game.")
        self.check_overlay.toggled.connect(lambda c: self.btn_conf_overlay.setEnabled(c))
        overlay_layout.addWidget(self.check_overlay)
        
        self.btn_conf_overlay = QtWidgets.QPushButton("Configure Colors/Metrics")
        self.btn_conf_overlay.setEnabled(False)
        self.btn_conf_overlay.clicked.connect(self.open_overlay_config)
        overlay_layout.addWidget(self.btn_conf_overlay)
        overlay_group.setLayout(overlay_layout)
        layout.addWidget(overlay_group)

        # Personal Best Selection
        pb_group = QtWidgets.QGroupBox("Compare to Personal Best")
        pb_layout = QtWidgets.QVBoxLayout()
        
        pb_file_layout = QtWidgets.QHBoxLayout()
        self.line_pb = QtWidgets.QLineEdit()
        self.line_pb.setReadOnly(True)
        self.line_pb.setPlaceholderText("No run selected")
        pb_file_layout.addWidget(self.line_pb)
        
        self.btn_pb = QtWidgets.QPushButton("Select Master CSV")
        self.btn_pb.clicked.connect(self.browse_pb_file)
        pb_file_layout.addWidget(self.btn_pb)
        
        self.btn_clear_pb = QtWidgets.QPushButton("X")
        self.btn_clear_pb.setFixedWidth(30)
        self.btn_clear_pb.clicked.connect(lambda: self.line_pb.setText(""))
        pb_file_layout.addWidget(self.btn_clear_pb)
        pb_layout.addLayout(pb_file_layout)

        self.check_pb_live = QtWidgets.QCheckBox("Animate PB Progress")
        self.check_pb_live.setChecked(True)
        self.check_pb_live.setToolTip("Checked: PB line grows with time (Live).\nUnchecked: PB line is fully visible from start (Static).")
        pb_layout.addWidget(self.check_pb_live)
        
        pb_group.setLayout(pb_layout)
        layout.addWidget(pb_group)

        # Data Recording Rate
        rec_row = QtWidgets.QWidget()
        rec_layout = QtWidgets.QHBoxLayout(rec_row)
        rec_layout.setContentsMargins(0, 0, 0, 0)
        rec_layout.addWidget(QtWidgets.QLabel("Data Recording Rate:"))
        self.combo_rec_rate = QtWidgets.QComboBox()
        self.combo_rec_rate.addItem("High Precision (100ms)", 100)
        self.combo_rec_rate.addItem("Balanced (500ms)", 500)
        self.combo_rec_rate.addItem("Low Resource (1000ms)", 1000)
        self.combo_rec_rate.setToolTip("Controls how often data is saved to the CSV.\n• 100ms: Large files, high RAM, smooth 'Live' graphs.\n• 1000ms: Small files, low RAM.\nNote: Total Kills and KPM remain accurate regardless of this setting.")
        rec_layout.addWidget(self.combo_rec_rate)
        layout.addWidget(rec_row)
        
        # Log Update Rate Input
        self.log_rate_container = QtWidgets.QWidget()
        self.log_rate_container.setToolTip("These settings only affect how often the live graphs are visually updated.\nData is always recorded at the highest possible frequency in the background.")
        self.log_rate_layout = QtWidgets.QVBoxLayout(self.log_rate_container)
        self.log_rate_layout.setContentsMargins(20, 0, 0, 0)
        
        # Explanation Label 1
        lbl_info1 = QtWidgets.QLabel("<b>Visual Update Settings:</b><br/>"
                                     "Controls how often new points appear on the plots.<br/>"
                                     "<i>(Data is always recorded at high precision in background)</i>")
        lbl_info1.setWordWrap(True)
        self.log_rate_layout.addWidget(lbl_info1)

        # Spinner Row
        rate_row = QtWidgets.QWidget()
        rate_layout = QtWidgets.QHBoxLayout(rate_row)
        rate_layout.setContentsMargins(0, 0, 0, 0)
        rate_layout.addWidget(QtWidgets.QLabel("Plot Update Interval:"))
        self.combo_log_rate = QtWidgets.QComboBox()
        self.combo_log_rate.addItem("Real-time (0.1s)", 0.1)
        self.combo_log_rate.addItem("Fast (0.3s)", 0.3)
        self.combo_log_rate.addItem("Normal (1.0s)", 1.0)
        self.combo_log_rate.addItem("Slow (5.0s)", 5.0)
        rate_layout.addWidget(self.combo_log_rate)
        self.log_rate_layout.addWidget(rate_row)

        layout.addWidget(self.log_rate_container)
        
        self.check_logs.toggled.connect(self.update_rate_state)
        self.update_rate_state()

        # Start Button
        self.btn_start = QtWidgets.QPushButton("Start Tracker")
        self.btn_start.clicked.connect(self.validate_and_accept)
        layout.addWidget(self.btn_start)
        
        # Add New Config Button
        self.btn_reconfig = QtWidgets.QPushButton("Refresh/Add New Bounding Box")
        self.btn_reconfig.setToolTip("Create a new configuration or edit the current one.")
        self.btn_reconfig.clicked.connect(self.handle_config_button)
        layout.addWidget(self.btn_reconfig)

        # Import Config Button
        self.btn_import = QtWidgets.QPushButton("Import Config from Previous Version")
        self.btn_import.setToolTip("Select the main folder of your previous version to import bounding boxes and settings.")
        self.btn_import.clicked.connect(self.import_old_config)
        layout.addWidget(self.btn_import)

        self.setLayout(layout)

    def open_acolyte_config(self):
        dlg = AcolyteConfigDialog(self.acolyte_config, self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            self.acolyte_config = dlg.get_config()

    def open_overlay_config(self):
        dlg = OverlayConfigDialog(self.overlay_config, self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            self.overlay_config = dlg.get_config()

    def import_old_config(self):
        src_dir = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Previous Version Folder")
        if not src_dir:
            return

        # Smart Search: Check root, then check standard subfolders
        candidates = [
            src_dir,
            os.path.join(src_dir, "python_and_required_packages", "LECTA_SCRIPTS"),
            os.path.join(src_dir, "Source")
        ]
        
        real_src = None
        for d in candidates:
            if os.path.exists(os.path.join(d, "bbox_config_solo.json")) or \
               os.path.exists(os.path.join(d, "bbox_config_duo.json")):
                real_src = d
                break
        
        if not real_src:
             QtWidgets.QMessageBox.warning(self, "Config Not Found", 
                                           "Could not find configuration files in the selected folder.\n"
                                           "Tried looking in root and 'python_and_required_packages/LECTA_SCRIPTS'.")
             return

        files_to_copy = [
            "bbox_config_solo.json",
            "bbox_config_duo.json",
            "last_run_settings.json",
            "path_config.json",
            "setup_screenshot_solo.png",
            "setup_screenshot_duo.png"
        ]
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        count = 0
        
        for filename in files_to_copy:
            s = os.path.join(real_src, filename)
            d = os.path.join(current_dir, filename)
            if os.path.exists(s):
                try:
                    shutil.copy2(s, d)
                    count += 1
                except Exception: pass

        if count > 0:
            QtWidgets.QMessageBox.information(self, "Import Successful", f"Imported {count} files.\nSettings will reload.")
            # Reload settings immediately
            self.check_load_prev.setEnabled(True)
            self.check_load_prev.setText("Load Last Used Settings")
            self.check_load_prev.setChecked(True)
            self.load_previous_settings(True)
            
            # Reload path config
            if os.path.exists(self.path_config_file):
                try:
                    with open(self.path_config_file, 'r') as f:
                        new_path = json.load(f).get("output_path")
                        if new_path:
                            self.line_path.setText(new_path)
                except: pass
        else:
            QtWidgets.QMessageBox.warning(self, "Import Failed", "Found the folder but no valid config files were inside.")

    def update_rate_state(self):
        log_tracking_enabled = self.check_logs.isChecked()
        self.check_acolyte.setEnabled(log_tracking_enabled)
        self.btn_conf_acolyte.setEnabled(log_tracking_enabled and self.check_acolyte.isChecked())
        enabled = self.check_logs.isChecked() or self.check_fps.isChecked()
        self.log_rate_container.setEnabled(enabled)

    def browse_output_folder(self):
        d = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Output Folder", self.line_path.text())
        if d:
            self.line_path.setText(d)

    def browse_pb_file(self):
        d, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select Master Run Log", self.line_path.text(), "CSV Files (*.csv)")
        if d:
            self.line_pb.setText(d)

    def browse_pb_folder(self):
        d = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Personal Best Run Folder", self.line_path.text())
        if d:
            self.line_pb.setText(d)

    def validate_and_accept(self):
        if not self.check_credits.isChecked() and not self.check_kills.isChecked():
            QtWidgets.QMessageBox.warning(self, "Invalid Settings", "You must track at least Credits or Kills.")
            return

        if self.check_fps.isChecked():
            try:
                is_admin = ctypes.windll.shell32.IsUserAnAdmin()
            except Exception:
                is_admin = False
            
            if not is_admin:
                reply = QtWidgets.QMessageBox.question(
                    self, "Admin Privileges Required",
                    "Tracking FPS requires Administrator privileges (for PresentMon).\n\n"
                    "Restart the application as Administrator?",
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
                )
                if reply == QtWidgets.QMessageBox.Yes:
                    try:
                        with open(self.settings_file, 'w') as f:
                            json.dump(self.get_settings(), f, indent=4)
                    except Exception: pass
                    # Only this line is needed:
                    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{os.path.abspath(__file__)}"', os.getcwd(), 1)
                    sys.exit(0)
                else:
                    self.check_fps.setChecked(False)
        
        # Save Path Config
        try:
            with open(self.path_config_file, 'w') as f:
                json.dump({"output_path": self.line_path.text()}, f, indent=4)
        except Exception as e:
            print(f"[Settings] Error saving path config: {e}")

        # Save settings
        try:
            settings = self.get_settings()
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=4)
        except Exception as e:
            print(f"[Settings] Error saving settings: {e}")
            
        self.accept()

    def handle_config_button(self):
        msg = QtWidgets.QMessageBox(self)
        msg.setWindowTitle("Config Options")
        msg.setText("Choose an action:")
        btn_new = msg.addButton("Complete New Bounding Box", QtWidgets.QMessageBox.ActionRole)
        btn_edit = msg.addButton("Editing a Bounding Box", QtWidgets.QMessageBox.ActionRole)
        msg.addButton(QtWidgets.QMessageBox.Cancel)
        msg.exec_()
        
        if msg.clickedButton() == btn_new:
            self.run_setup_wizard()
        elif msg.clickedButton() == btn_edit:
            # Ask for mode
            mode_msg = QtWidgets.QMessageBox(self)
            mode_msg.setWindowTitle("Select Mode")
            mode_msg.setText("Which configuration do you want to edit?")
            btn_solo = mode_msg.addButton("Solo", QtWidgets.QMessageBox.ActionRole)
            btn_duo = mode_msg.addButton("Duo", QtWidgets.QMessageBox.ActionRole)
            mode_msg.addButton(QtWidgets.QMessageBox.Cancel)
            mode_msg.exec_()
            
            if mode_msg.clickedButton() == btn_solo:
                self.run_config_editor("Solo")
            elif mode_msg.clickedButton() == btn_duo:
                self.run_config_editor("Duo")

    def run_config_editor(self, mode):
        # Determine config file
        config_filename = "bbox_config_solo.json" if mode == "Solo" else "bbox_config_duo.json"
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), config_filename)
        
        if not os.path.exists(config_path):
            QtWidgets.QMessageBox.warning(self, "Error", f"Config file not found:\n{config_filename}\nPlease run 'Complete New Bounding Box' first.")
            return

        # Load Config
        try:
            with open(config_path, 'r') as f:
                data = json.load(f)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Error", f"Failed to load config: {e}")
            return

        # Capture Screen
        # Capture Screen or Load
        try:
            # Monitor detection logic
            primary_x, primary_y = 0, 0
            for m in get_monitors():
                if m.is_primary:
                    primary_x, primary_y = m.x, m.y
                    break
            monitor = mss.mss().monitors[1]
            for m in mss.mss().monitors[1:]:
                if m["left"] == primary_x and m["top"] == primary_y:
                    monitor = m
                    break
            
            # Determine screenshot path
            screenshot_filename = "setup_screenshot_solo.png" if mode == "Solo" else "setup_screenshot_duo.png"
            screenshot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), screenshot_filename)
            
            img = None
            if os.path.exists(screenshot_path):
                img = cv.imread(screenshot_path, cv.IMREAD_UNCHANGED)
                if img is not None:
                    print(f"[Config] Loaded screenshot from: {screenshot_path}")
            
            if img is None:
                QtWidgets.QMessageBox.warning(self, "Screenshot Missing", f"Could not find the setup screenshot:\n{screenshot_filename}\n\nCannot edit configuration without the reference image.\nPlease run 'Complete New Bounding Box' to create one.")
                return
            
            self.hide()
            time.sleep(0.2)
            
            editor = ConfigEditor(img, data, (monitor['left'], monitor['top']), self)
            if editor.exec_() == QtWidgets.QDialog.Accepted:
                with open(config_path, 'w') as f:
                    json.dump(editor.data, f, indent=4)
                print("[Config] Configuration updated.")
        except Exception as e:
            print(f"[Config] Error in editor: {e}")
        self.show()

    def run_setup_wizard(self):
        self.hide()
        try:
            print("\n--- Launching Bounding Box Setup ---")
            subprocess.check_call([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "bounding_box_setup.py")])
            print("--- Setup Finished ---\n")
        except Exception as e:
            print(f"[Config] Error running setup: {e}")
        self.show()

    def load_previous_settings(self, checked):
        if not checked:
            return
            
        try:
            with open(self.settings_file, 'r') as f:
                data = json.load(f)
            
            if data.get("mode") == "Solo":
                self.radio_solo.setChecked(True)
            else:
                self.radio_duo.setChecked(True)
                
            self.spin_delay.setValue(data.get("scan_delay", 0.3))
            self.spin_cooldown.setValue(data.get("cooldown", 3.0))
            self.check_credits.setChecked(data.get("track_credits", True))
            self.check_kills.setChecked(data.get("track_kills", False))
            self.check_on_top.setChecked(data.get("always_on_top", True))
            self.check_sound.setChecked(data.get("use_sound", False))
            self.check_debug.setChecked(data.get("debug_mode", False))
            self.check_logs.setChecked(data.get("track_logs", False))
            self.check_fps.setChecked(data.get("track_fps", False))
            self.check_overlay.setChecked(data.get("use_overlay", False))
            self.check_acolyte.setChecked(data.get("acolyte_warner_enabled", False))
            if "acolyte_config" in data:
                self.acolyte_config = data["acolyte_config"]

            if "overlay_config" in data:
                self.overlay_config = data["overlay_config"]
            self.line_pb.setText(data.get("pb_file", ""))
            self.check_pb_live.setChecked(data.get("show_pb_live", True))
            
            saved_rec_rate = data.get("data_recording_rate", 100)
            for i in range(self.combo_rec_rate.count()):
                if self.combo_rec_rate.itemData(i) == saved_rec_rate:
                    self.combo_rec_rate.setCurrentIndex(i)
                    break
            
            saved_rate = data.get("log_update_rate", 0.1)
            for i in range(self.combo_log_rate.count()):
                if QtCore.qFuzzyCompare(self.combo_log_rate.itemData(i), saved_rate):
                    self.combo_log_rate.setCurrentIndex(i)
                    break
        except Exception as e:
            print(f"[Settings] Error loading settings: {e}")

    def get_settings(self):
        return {
            "mode": "Solo" if self.radio_solo.isChecked() else "Duo",
            "scan_delay": self.spin_delay.value(),
            "cooldown": self.spin_cooldown.value(),
            "track_credits": self.check_credits.isChecked(),
            "track_kills": self.check_kills.isChecked(),
            "always_on_top": self.check_on_top.isChecked(),
            "use_sound": self.check_sound.isChecked(),
            "debug_mode": self.check_debug.isChecked(),
            "track_logs": self.check_logs.isChecked(),
            "track_fps": self.check_fps.isChecked(),
            "use_overlay": self.check_overlay.isChecked(),
            "overlay_config": self.overlay_config,
            "acolyte_warner_enabled": self.check_acolyte.isChecked(),
            "acolyte_config": self.acolyte_config,
            "data_recording_rate": self.combo_rec_rate.currentData(),
            "log_update_rate": self.combo_log_rate.currentData(),
            "output_path": self.line_path.text(),
            "pb_file": self.line_pb.text(),
            "show_pb_live": self.check_pb_live.isChecked()
        }

class WarframeTracker(QtCore.QObject):
    data_updated = QtCore.pyqtSignal()
    request_overlay_toggle = QtCore.pyqtSignal()
    sig_start_log_timer = QtCore.pyqtSignal()
    sig_stop_log_timer = QtCore.pyqtSignal()
    request_run_end = QtCore.pyqtSignal()
    sig_update_overlay_data = QtCore.pyqtSignal(dict)

    def __init__(self, settings):
        super().__init__() #initializing the QObject parernt class
        self.settings = settings
        
        # Initialize QApplication early so we can use GUI elements (ROI Selector) in __init__
        self.app = QtWidgets.QApplication.instance()
        if self.app is None:
            QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
            QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
            self.app = QtWidgets.QApplication([])

        self.creds = []
        self.confidences = []
        self.credit_positions = []
        self.kills = []
        self.kpm = []
        self.current_run_time = []
        self.cpm = []
        self.start_time = None
        self.last_tab_time = 0.0 
        self.cooldown_duration = self.settings['cooldown']
        self.run_output_path = None
        self.overlay = None
        
        # Master Log & State Variables
        self.master_log = []
        self.state_credits = 0
        self.state_cpm = 0
        self.state_kills = 0
        self.state_kpm = 0
        self.state_fps = 0
        self.pending_event = ""
        self.tab_held = False
        
        self.track_logs = self.settings.get('track_logs', False)
        self.track_fps = self.settings.get('track_fps', False)
        self.log_update_rate = self.settings.get('log_update_rate', 0.1)
        self.acolyte_warner = None
        self.data_recording_interval_ms = self.settings.get('data_recording_rate', 100)
        self.show_pb_live = self.settings.get('show_pb_live', True)
        self.pb_data = None # DataFrame for Personal Best
        

        self.log_reader = None
        self.fps_tracker = FPSTracker()
        self.log_timer = QtCore.QTimer()
        self.log_timer.timeout.connect(self.update_log_data)
        self.initial_log_kills = None
        self.sig_start_log_timer.connect(self._start_log_timer_slot)
        self.sig_stop_log_timer.connect(self._stop_log_timer_slot)
        self.request_run_end.connect(self.run_end)
        self.sig_update_overlay_data.connect(self._update_overlay_slot)
        
        # OCR intilasiation
        print("\n[Init] Initializing OCR Model... (This may take a moment)")
        try:
            self.reader = ocr.Reader(['en'], gpu=True)
        except Exception as e:
            print(f"\n[CRITICAL] Failed to initialize OCR model: {e}")
            sys.exit(1)

        primary_x, primary_y = 0, 0
        for m in get_monitors(): #from screeninfo module
            if m.is_primary:
                primary_x, primary_y = m.x, m.y
                break
                
        self.monitor = mss.mss().monitors[1] # Fallback
        for m in mss.mss().monitors[1:]:
            if m["left"] == primary_x and m["top"] == primary_y:
                self.monitor = m
                break
        
        self.scan_left = self.monitor["left"] + int(self.monitor["width"] * 30 / 100)
        self.scan_top = self.monitor["top"] + int(self.monitor["height"] * 10 / 100)
        self.scan_right = self.scan_left + int(self.monitor["width"] * 30 / 100)
        self.scan_lower = self.scan_top + int(self.monitor["height"] * 50 / 100)

        # Config path setup
        application_path = os.path.dirname(os.path.abspath(__file__))
        
        config_filename = "bbox_config_solo.json" if self.settings['mode'] == "Solo" else "bbox_config_duo.json"
        self.config_path = os.path.join(application_path, config_filename)

        # Set tracking flags from settings
        self.track_credits = self.settings['track_credits']
        self.track_kills = self.settings['track_kills']
        self.scan_delay = self.settings['scan_delay']
        self.always_on_top = self.settings['always_on_top']
        self.use_sound = self.settings['use_sound']
        self.debug_mode = self.settings['debug_mode']
        self.use_overlay = self.settings.get('use_overlay', False)

        # Initial Setup Loop
        while True:
            if self.load_config():
                break
            
            print(f"[Config] Warning: Configuration '{config_filename}' not found or invalid (Need 5 boxes).")
            print("[Config] Launching Bounding Box Setup...")
            try:
                subprocess.check_call([sys.executable, os.path.join(application_path, "bounding_box_setup.py")])
            except Exception as e:
                print(f"[Config] Error running setup: {e}")
            
            if self.load_config():
                break
                
            reply = QtWidgets.QMessageBox.question(
                None, "Setup Incomplete",
                "Configuration is still invalid (requires 5 credit boxes).\nRetry setup?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )
            if reply == QtWidgets.QMessageBox.No:
                sys.exit(0)

        #Setup the Live GUI (Must be on the main thread)
        self.win = pg.GraphicsLayoutWidget(show=True, title="Warframe Tracker")
        if self.always_on_top:
            self.win.setWindowFlags(self.win.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        self.win.show()
        self.win.resize(800, 500)
        self.win.ci.layout.setSpacing(30)
        
        #setting tick font size
        my_font = QtGui.QFont()
        my_font.setPointSize(12) 

        # --- Dynamic Plot Layout ---
        active_plots = []
        if self.track_credits:
            active_plots.extend(['cpm', 'creds'])
        if self.track_kills:
            active_plots.append('kpm')
        if self.track_logs:
            active_plots.extend(['spawned', 'live'])
        if self.track_fps:
            active_plots.append('fps')

        num_plots = len(active_plots)
        use_grid = num_plots >= 4

        for i, p_type in enumerate(active_plots):
            # Grid Management
            if use_grid:
                if i > 0 and i % 2 == 0:
                    self.win.nextRow()
            else:
                if i > 0:
                    self.win.nextRow()

            # Plot Creation
            args = {}
            # Special case: 5 plots -> last one spans 2 columns
            if use_grid and num_plots == 5 and i == 4:
                args['colspan'] = 2
            
            # Axis items for Credits (only if not video)
            if p_type == 'creds':
                args['axisItems'] = {'left': LargeNumberAxisItem(orientation='left')}

            p = self.win.addPlot(**args)
            p.showGrid(x=True, y=True)
            p.getAxis('bottom').setTickFont(my_font)
            p.getAxis('left').setTickFont(my_font)
            p.getAxis('bottom').enableAutoSIPrefix(False)
            p.setLabel('bottom', 'Time (min)')
            
            # We will add PB curves here, but initialize them as None first

            # Specific Configuration
            if p_type == 'cpm':
                self.plot_cpm = p
                p.setTitle("Credits Per Minute (CPM)", size="16pt")
                p.setLabel('left', 'CPM')
                self.curve_cpm = p.plot(pen='y', symbol='o')
                self.curve_cpm_pb = p.plot(pen=pg.mkPen('y', style=QtCore.Qt.DotLine))
            
            elif p_type == 'creds':
                self.plot_creds = p
                p.setTitle("Total Credits", size="16pt")
                p.setLabel('left', 'Credits')
                self.curve_creds = p.plot(pen='g', symbol='o')
                self.curve_creds_pb = p.plot(pen=pg.mkPen('g', style=QtCore.Qt.DotLine))

            elif p_type == 'kpm':
                self.plot_kpm = p
                p.setTitle("Kills Per Minute (KPM)", size="16pt")
                p.setLabel('left', 'KPM')
                symbol = None if self.track_logs else 'o'
                self.curve_kpm = p.plot(pen='r', symbol=symbol)
                self.curve_kpm_pb = p.plot(pen=pg.mkPen('r', style=QtCore.Qt.DotLine))

            elif p_type == 'spawned':
                self.plot_spawned = p
                p.setTitle("Total Enemies spawned", size="16pt")
                p.setLabel('left', 'Count')
                self.curve_spawned = p.plot(pen='m', name='Spawned')
                self.curve_spawned_pb = p.plot(pen=pg.mkPen('m', style=QtCore.Qt.DotLine))

            elif p_type == 'live':
                self.plot_live = p
                p.setTitle("Amount of alive enemies", size="16pt")
                p.setLabel('left', 'Count')
                self.curve_live = p.plot(pen='c', name='num alive')
                self.curve_live_pb = p.plot(pen=pg.mkPen('c', style=QtCore.Qt.DotLine))

            elif p_type == 'fps':
                self.plot_fps = p
                p.setTitle("Frames Per Second", size="16pt")
                p.setLabel('left', 'FPS')
                self.curve_fps = p.plot(pen='c', name='FPS')
                self.curve_fps_pb = p.plot(pen=pg.mkPen('c', style=QtCore.Qt.DotLine))

        # --- Overlay Initialization ---
        self.number_overlays = {}
        if self.use_overlay:
            ov_cfg = self.settings.get("overlay_config", {})
            # Define defaults if missing
            defaults = {"CPM": "#FF0000", "KPM": "#FF0000", "Num alive": "#FF0000", "FPS": "#FF0000"}
            
            # Start positions (Top-Left of Main Monitor)
            start_x = self.monitor["left"] + 20
            current_y = self.monitor["top"] + 50
            
            # Helper to create overlay
            def create_ov(key):
                nonlocal current_y
                cfg = ov_cfg.get(key, {"show": True, "color": defaults[key]})
                if cfg.get("show", True):
                    pos = QtCore.QPoint(start_x, current_y)
                    self.number_overlays[key] = DraggableNumberOverlay(key, cfg.get("color", defaults[key]), self.monitor, pos)
                    self.number_overlays[key].show()
                    current_y += 40 # Offset for next overlay

            if self.track_credits: create_ov("CPM")
            if self.track_kills: create_ov("KPM")
            if self.track_logs: create_ov("Num alive")
            if self.track_fps: create_ov("FPS")

        # --- Acolyte Warner Initialization ---
        if self.track_logs and self.settings.get("acolyte_warner_enabled", False):
            acolyte_cfg = self.settings.get("acolyte_config", {})
            self.acolyte_warner = AcolyteWarner(acolyte_cfg, self.monitor)
            print("[Init] Acolyte Warner enabled and initialized.")

        # Data Structures Initialization
        if self.track_logs:
            self.enemy_data = {"time": [], "live": [], "spawned": []}
            if self.track_kills:
                self.enemy_data["kills"] = []
                self.enemy_data["kpm"] = []
            self.plot_data_live = {"t": [], "y": []}
            self.plot_data_spawned = {"t": [], "y": []}
            self.plot_data_kpm = {"t": [], "y": []}
            
        if self.track_fps:
            self.plot_data_fps = {"t": [], "y": []}

        #connecting signal to plot update function
        self.data_updated.connect(self.update_plot)
        self.request_overlay_toggle.connect(self.toggle_overlay)
        self.setup_hotkeys()
        
        # --- Controller Setup (PS4 L3 -> Tab) ---
        self.joystick = None
        self.l3_pressed = False
        self.init_controller()
        self.controller_timer = QtCore.QTimer()
        self.controller_timer.timeout.connect(self.poll_controller)
        self.controller_timer.start(16) # Poll at ~60Hz

    def setup_hotkeys(self):
        key.add_hotkey('f8', self.start_run)
        # Use on_press_key for TAB to ensure it triggers even if other keys (like WASD) are held
        key.on_press_key('tab', self.on_tab_press)
        key.on_release_key('tab', self.on_tab_release)
        key.add_hotkey('f9', self.request_overlay_toggle.emit)
        key.add_hotkey('f10', self.request_run_end.emit)

    def init_controller(self):
        try:
            # Init joystick module. Main pygame.init() is at top of file.
            pygame.joystick.init()
            
            joystick_count = pygame.joystick.get_count()
            if joystick_count > 0:
                # If we don't already have a joystick, or if the one we had is gone.
                if self.joystick is None:
                    self.joystick = pygame.joystick.Joystick(0)
                    self.joystick.init()
                    print(f"[Controller] Connected: {self.joystick.get_name()}")
                    print(f"[Controller] It has {self.joystick.get_numbuttons()} buttons. Press L3 to see its number in the diagnostic.")
            elif self.joystick is not None:
                # We had a joystick, but now we don't
                print("[Controller] Disconnected.")
                self.joystick = None

        except Exception as e:
            print(f"[Controller] Error initializing: {e}")
            self.joystick = None

    def poll_controller(self):
        # If no joystick, try to initialize one periodically
        if not self.joystick:
            if not hasattr(self, 'last_joystick_check') or time.perf_counter() - self.last_joystick_check > 3.0:
                self.last_joystick_check = time.perf_counter()
                self.init_controller()
            return
        
        try:
            # Process all events from the queue. This is the standard pygame way.
            for event in pygame.event.get():
                # --- Diagnostic: Print all button presses ---
                if event.type == pygame.JOYBUTTONDOWN:
                    print(f"[Controller Diagnostic] Button {event.button} PRESSED")
                # --- End Diagnostic ---

                # Check if the event is for our target button (L3)
                btn_index = 7 # Changed based on your diagnostic output
                if event.type == pygame.JOYBUTTONDOWN and event.button == btn_index:
                    self.l3_pressed = True
                    print(f"[Controller] Button {btn_index} Pressed - Holding TAB")
                    pydirectinput.keyDown('tab')
                elif event.type == pygame.JOYBUTTONUP and event.button == btn_index:
                    self.l3_pressed = False
                    print(f"[Controller] Button {btn_index} Released - Releasing TAB")
                    pydirectinput.keyUp('tab')
        except pygame.error as e:
            # This can happen if the controller disconnects
            print(f"[Controller] Polling error (likely disconnected): {e}")
            self.joystick = None

    def _start_log_timer_slot(self):
        self.log_timer.start(self.data_recording_interval_ms) 

    def _stop_log_timer_slot(self):
        self.log_timer.stop()

    def _update_overlay_slot(self, data):
        for k, v in data.items():
            if k in self.number_overlays:
                self.number_overlays[k].update_value(v)

    def toggle_overlay(self):
        if self.overlay and self.overlay.isVisible():
            self.overlay.close()
            self.overlay = None
            return

        mx = self.monitor['left']
        my = self.monitor['top']
        boxes = []

        # Scan Area
        boxes.append((self.scan_left - mx, self.scan_top - my, 
                      self.scan_right - self.scan_left, self.scan_lower - self.scan_top))
        
        # Credit Positions
        for l, t, r, b in self.credit_positions:
            boxes.append((l - mx, t - my, r - l, b - t))
            
        # Kills
        if self.track_kills and hasattr(self, 'left_kills'):
            boxes.append((self.left_kills - mx, self.top_kills - my, 
                          self.right_kills - self.left_kills, self.lower_kills - self.top_kills))

        self.overlay = OverlayWindow((mx, my, self.monitor['width'], self.monitor['height']), boxes)
        self.overlay.show()

    def load_config(self):
        try:
            with open(self.config_path, 'r') as f:
                data = json.load(f)
            
            self.scan_left = data['scan_area'][0]
            self.scan_top = data['scan_area'][1]
            self.scan_right = data['scan_area'][2]
            self.scan_lower = data['scan_area'][3]

            self.credit_positions = data.get('credit_positions', [])
            if len(self.credit_positions) != 5:
                print(f"[Config] Validation failed: Found {len(self.credit_positions)} credit boxes, expected 5.")
                return False
            
            # Validate Kills
            if self.track_kills:
                if data.get('track_kills') and 'kills' in data:
                    self.left_kills = data['kills'][0]
                    self.top_kills = data['kills'][1]
                    self.right_kills = data['kills'][2]
                    self.lower_kills = data['kills'][3]
                else:
                    print("[Config] Warning: Kill tracking enabled in settings, but config file has no kill coordinates. Disabling Kills.")
                    self.track_kills = False
            

            self.UI = "y" # Ensure shift() uses these coordinates
            print("[Config] Configuration loaded successfully.")
            return True
        except Exception as e:
            print(f"[Config] Error loading config: {e}")
            return False

    def load_pb_data(self):
        path = self.settings.get("pb_file", "")
        if not path or not os.path.exists(path):
            return
        
        # If user selected a folder by mistake (legacy support), try to find csv
        if os.path.isdir(path):
            path = os.path.join(path, "master_run_log.csv")

        if not os.path.exists(path):
            print(f"[PB] Warning: File not found: {path}")
            return
            
        try:
            print(f"[PB] Loading Personal Best data from: {os.path.basename(os.path.dirname(path))}/{os.path.basename(path)}")
            self.pb_data = pd.read_csv(path)
            if 'Time' not in self.pb_data.columns:
                print("[PB] Error: CSV missing 'Time' column.")
                self.pb_data = None
                return
            # Convert Time from seconds to minutes for plotting
            self.pb_data['Time_Min'] = self.pb_data['Time'] / 60.0
        except Exception as e:
            print(f"[PB] Error loading CSV: {e}")

    def start_run(self):
        # Ensure any previous run state is cleared
        self.start_time = None
        
        if self.start_time is not None:
            print("\n[Run] Run is already in progress. Press F10 to save and end the current run first.")
            return
            
        self.start_time = time.perf_counter()
        self.last_plot_update = 0

        # Reset data for new run to fix plotting issues
        self.creds = []
        self.confidences = []
        self.kills = []
        self.kpm = []
        self.current_run_time = []
        self.cpm = []
        self.initial_log_kills = None
        
        # Reset Master Log
        self.master_log = []
        self.state_credits = 0
        self.state_cpm = 0
        self.state_kills = 0
        self.state_kpm = 0
        self.state_fps = 0
        self.pending_event = "Start"
        
        # Clear PB Curves (in case they were shown in a previous run)
        if self.track_credits:
            self.curve_cpm_pb.setData([], [])
            self.curve_creds_pb.setData([], [])
        if self.track_kills:
            self.curve_kpm_pb.setData([], [])
        if self.track_logs:
            self.curve_spawned_pb.setData([], [])
            self.curve_live_pb.setData([], [])
        if self.track_fps:
            self.curve_fps_pb.setData([], [])
        
        if self.track_logs:
            self.enemy_data = {"time": [], "live": [], "spawned": []}
            if self.track_kills:
                self.enemy_data["kills"] = []
                self.enemy_data["kpm"] = []
            self.plot_data_live = {"t": [], "y": []}
            self.plot_data_spawned = {"t": [], "y": []}
            self.plot_data_kpm = {"t": [], "y": []}
            self.curve_live.setData([], [])
            self.curve_spawned.setData([], [])
            
        if self.track_fps:
            self.plot_data_fps = {"t": [], "y": []}
            self.curve_fps.setData([], [])
        
        # --- Create Run Folder ---
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H-%M-%S')
            folder_name = f"{timestamp}"
            
            output_dir = self.settings.get("output_path", os.path.join(os.getcwd(), "OUTPUT"))
            os.makedirs(output_dir, exist_ok=True)
            self.run_output_path = os.path.join(output_dir, folder_name)
            os.makedirs(self.run_output_path, exist_ok=True)
            
            print(f"\n[Run] Started! Output will be saved to: {self.run_output_path}")
        except Exception as e:
            print(f"[CRITICAL] Could not create output folder. Error: {e}")
            self.run_output_path = os.path.dirname(os.path.abspath(__file__))
        
        print("[Run] Timer started at 0.0.")
        
        if self.track_fps:
            self.fps_tracker.start()
        
        if self.track_logs:
            log_path = os.path.expandvars(r"%LOCALAPPDATA%\Warframe\EE.log")
            self.log_reader = LogReader(log_path)
            self.log_reader.start()
            self.sig_start_log_timer.emit() # Update every 1 second
        
        # Always start the timer now to record FPS even if logs are off
        self.sig_start_log_timer.emit()
        
        # Load PB Data
        self.load_pb_data()
        
        # If Static Mode (show_pb_live is False), plot full data immediately
        if self.pb_data is not None and not self.show_pb_live:
            t = self.pb_data['Time_Min'].to_numpy()
            if self.track_credits:
                if 'CPM' in self.pb_data: self.curve_cpm_pb.setData(t, self.pb_data['CPM'].to_numpy())
                if 'Credits' in self.pb_data: self.curve_creds_pb.setData(t, self.pb_data['Credits'].to_numpy())
            if self.track_kills:
                if 'KPM' in self.pb_data: self.curve_kpm_pb.setData(t, self.pb_data['KPM'].to_numpy())
            if self.track_logs:
                if 'Spawned' in self.pb_data: self.curve_spawned_pb.setData(t, self.pb_data['Spawned'].to_numpy())
                if 'Live' in self.pb_data: self.curve_live_pb.setData(t, self.pb_data['Live'].to_numpy())
            if self.track_fps:
                if 'FPS' in self.pb_data: self.curve_fps_pb.setData(t, self.pb_data['FPS'].to_numpy())

    def find_credits_coords(self, im):
        # Convert to gray for OCR
        im_gray = cv.cvtColor(im, cv.COLOR_BGRA2GRAY)
        # Read text without allowlist to find letters
        results = self.reader.readtext(im_gray)
        
        for (bbox, text, prob) in results:
            if "credits" in text.lower():
                # bbox is [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
                (tl, tr, br, bl) = bbox
                x = int(tl[0])
                y = int(tl[1])
                w = int(tr[0] - tl[0])
                h = int(bl[1] - tl[1])
                return (x, y, w, h)
        return None

    def on_tab_press(self, event):
        if self.tab_held:
            return
        self.tab_held = True
        self.tab_action()

    def on_tab_release(self, event):
        self.tab_held = False

    def tab_action(self):
        try:
            self._tab_action_unsafe()
        except Exception as e:
            print(f"[Tab Action] Error: {e}")

    def _tab_action_unsafe(self):
        if self.start_time is None:
            print("[Action] Ignored: Press F8 to start the run timer first!")
            return
        current_time = time.perf_counter()
        if (current_time - self.last_tab_time) < self.cooldown_duration:
            return
        self.last_tab_time = current_time

        time.sleep(self.scan_delay) # Adjustable delay for UI fade-in
        
        elapsed_time = time.perf_counter() - self.start_time
        if elapsed_time < 1.0:
            print("[Action] Ignored: Run time < 1 second.")
            if self.use_sound:
                winsound.Beep(500, 200) # Low beep to indicate ignore
            return

        time_mins = elapsed_time / 60
        # Update FPS state on Tab press too
        if self.track_fps:
            self.state_fps = self.fps_tracker.get_fps()
        
        # --- 1. Capture & Validate ---
        # Capture Scan Area first to check for menu presence
        scan_bbox = (self.scan_left, self.scan_top, self.scan_right, self.scan_lower)
        im_scan = self.screenshot(bbox=scan_bbox)
        
        best_box = None
        coords = None
        
        if self.track_credits:
            coords = self.find_credits_coords(im_scan)
            if coords:
                # Calculate alignment to find the correct number box
                text_abs_x = self.scan_left + coords[0]
                text_width = coords[2]
                text_center_x = text_abs_x + (text_width / 2)
                
                min_dist = float('inf')
                for box in self.credit_positions:
                    box_center_x = box[0] + (box[2] - box[0]) / 2
                    dist = abs(text_center_x - box_center_x)
                    if dist < min_dist:
                        min_dist = dist
                        best_box = box
                
                if not best_box:
                    print("[Scan] Error: Could not match Credits text to any configured box.")
                    return
                self.last_credits_coords = coords
            else:
                print("[Scan] Did not find 'Credits' text in scan area.")
                if self.debug_mode and self.run_output_path:
                    filename = f"scan_fail_no_credits_text_at_{time_mins:.2f}m.png"
                    path = os.path.join(self.run_output_path, filename)
                    cv.imwrite(path, im_scan)
                return

        # --- 2. Capture Data Images ---
        # Now that we know the menu is open, capture the specific data boxes immediately.
        
        im_credits_val = None
        if self.track_credits and best_box:
            im_credits_val = self.screenshot(bbox=tuple(best_box))
            
        im_kills_val = None
        if self.track_kills and not self.track_logs:
            bbox_kills = (self.left_kills, self.top_kills, self.right_kills, self.lower_kills)
            im_kills_val = self.screenshot(bbox=bbox_kills)

        # --- 3. Signal Success (BEEP) ---
        # Images are secured. User can now close the Tab.
        if self.use_sound:
            winsound.Beep(1000, 150) 

        # --- 4. Process Data (OCR) ---
        cpm_value = 0
        num = 0
        
        if self.track_credits and im_credits_val is not None:
            # Pass bbox=None to disable retries (since we can't re-screenshot a closed tab)
            num, confidence, time_cp = self.ocr_function(im_credits_val, bbox=None)

            if num == 0:
                print("[Scan] Failed to read numbers.")
                if self.debug_mode and self.run_output_path:
                    filename = f"scan_fail_credits_at_{time_mins:.2f}m.png"
                    path = os.path.join(self.run_output_path, filename)
                    cv.imwrite(path, im_credits_val)
                return

            # Safety Check: Credits jump > 1,000,000
            if len(self.creds) > 0:
                diff = num - self.creds[-1]
                if diff > 1_000_000:
                    print(f"[Scan] Warning: Credits jumped by {diff}. Saving debug image.")
                    if self.run_output_path:
                        filename = f"credit_possible_mistake_{time_mins:.2f}m.png"
                        path = os.path.join(self.run_output_path, filename)
                        cv.imwrite(path, im_credits_val)

            cpm_value = num / time_mins
            self.creds.append(num)
            self.confidences.append(confidence)
            self.cpm.append(cpm_value)
            
            # Update State for Master Log
            self.state_credits = num
            self.state_cpm = int(cpm_value)
        
        self.current_run_time.append(time_mins)

        # --- Kills Logic (OCR) ---
        kills_num = 0
        if self.track_kills:
            if self.track_logs and self.log_reader:
                live, spawned = self.log_reader.get_stats()
                kills_num = max(0, spawned - live)
            elif im_kills_val is not None:
                kills_num, _, _ = self.ocr_function(im_kills_val, bbox=None)
                
                if kills_num == 0 and self.debug_mode and self.run_output_path:
                    filename = f"scan_fail_kills_at_{time_mins:.2f}m.png"
                    path = os.path.join(self.run_output_path, filename)
                    cv.imwrite(path, im_kills_val)

                # Safety Check: Kills jump > 2,500 (OCR only)
                if len(self.kills) > 0:
                    diff = kills_num - self.kills[-1]
                    if diff > 2500:
                        print(f"[Scan] Warning: Kills jumped by {diff}. Saving debug image.")
                        if self.run_output_path:
                            filename = f"kill_possible_mistake_{time_mins:.2f}m.png"
                            path = os.path.join(self.run_output_path, filename)
                            cv.imwrite(path, im_kills_val)
            
            kpm_value = kills_num / time_mins
            self.kills.append(kills_num)
            self.kpm.append(kpm_value)
            
            if not self.track_logs:
                self.state_kills = kills_num
                self.state_kpm = int(kpm_value)

        # Mark Event
        if self.track_logs:
            self.pending_event = "Scan"
        else:
            # If logs aren't running, we must record the row manually here
            self.master_log.append({
                "Time": round(elapsed_time, 2), "Live": 0, "Spawned": 0,
                "Credits": self.state_credits, "CPM": self.state_cpm,
                "Kills": self.state_kills, "KPM": self.state_kpm,
                "FPS": self.state_fps,
                "Event": "Scan"
            })

        # --- Console Output ---
        log_msg = f"Scanned - Time: {time_mins:.2f}m"
        if self.track_credits: log_msg += f" | Credits: {num} (CPM: {int(cpm_value)})"
        if self.track_kills:   log_msg += f" | Kills: {kills_num} (KPM: {int(kpm_value)})"
        print(log_msg)
        
        # Update Overlays (Tab Data)
        # Must use signal because tab_action runs in a background thread (keyboard hook)
        overlay_data = {}
        if "CPM" in self.number_overlays: overlay_data["CPM"] = int(cpm_value)
        if "KPM" in self.number_overlays and not self.track_logs: overlay_data["KPM"] = int(kpm_value)
        if "FPS" in self.number_overlays: overlay_data["FPS"] = self.state_fps
        
        if overlay_data:
            self.sig_update_overlay_data.emit(overlay_data)

        self.data_updated.emit()

    def screenshot(self, bbox=None):
        with mss.mss() as sct:
            if bbox is None:
                bbox = (self.scan_left, self.scan_top, self.scan_right, self.scan_lower)
            im = np.array(sct.grab(bbox))
        return im

    def ocr_function(self, im, bbox=None, retries=0):
        if im is None:
            return 0, 0.0, time.perf_counter() - self.start_time
        im = cv.cvtColor(im, cv.COLOR_BGRA2GRAY) 
        scan = self.reader.readtext(im, allowlist="0123456789,")
        
        if len(scan) == 0:
            if retries < 6 and bbox is not None:
                print(f"  [OCR] Empty scan. Retrying in 0.3s (Attempt {retries + 1}/6)")
                time.sleep(0.3)
                return self.ocr_function(self.screenshot(bbox=bbox), bbox=bbox, retries=retries + 1)
            else:
                print("  [OCR] Max retries reached. Returning 0.")
                # Return zeros so the script doesn't append bad data or crash
                return 0, 0.0, time.perf_counter() - self.start_time
        
        try:
            # Extract the highest confidence match
            best_match = max(scan, key=lambda x: x[2])
            result, confidence = best_match[1], best_match[2] 
            
            num = int(result.replace(",", "")) 
            time_cp = time.perf_counter() - self.start_time
            return num, confidence, time_cp 
        except Exception as e:
            print(f"[OCR] Parse Error: {e}")
            return 0, 0.0, time.perf_counter() - self.start_time


    def update_plot(self):
        #triggered by the QTimer. It safely pushes data to the window.
        if len(self.current_run_time) > 0:
            # Safe slicing to ensure lengths match (Fixes race condition crash)
            n = len(self.current_run_time)
            if self.track_credits:
                n_cpm = len(self.cpm)
                n_creds = len(self.creds)
                limit = min(n, n_cpm, n_creds)
                self.curve_cpm.setData(self.current_run_time[:limit], self.cpm[:limit])
                self.curve_creds.setData(self.current_run_time[:limit], self.creds[:limit])
                
            if self.track_kills and not self.track_logs:
                n_kpm = len(self.kpm)
                limit = min(n, n_kpm)
                self.curve_kpm.setData(self.current_run_time[:limit], self.kpm[:limit])

    def update_log_data(self):
        if self.start_time is None:
            return
        
        current_perf_time = time.perf_counter()
        elapsed_seconds = current_perf_time - self.start_time
        t = elapsed_seconds / 60
        
        # Get FPS
        if self.track_fps:
            fps = self.fps_tracker.get_fps()
            self.state_fps = fps

        live, spawned = 0, 0
        if self.track_logs and self.log_reader:
            live, spawned = self.log_reader.get_stats()
        
        # Check for Acolyte Warning
        if self.track_logs and self.log_reader and self.acolyte_warner:
            if self.log_reader.check_and_clear_acolyte_warning():
                print("[Tracker] Triggering Acolyte Warner Popup!")
                acolyte_cfg = self.settings.get("acolyte_config", {})
                if acolyte_cfg.get("audio_cue", True):
                    # Use a distinct sound for the acolyte
                    winsound.Beep(1500, 500)
                duration = acolyte_cfg.get("duration", 12.0)
                self.acolyte_warner.start_warning(duration)

        kills = 0
        kpm = 0.0
        
        if self.track_kills:
            if self.track_logs:
                current_mission_kills = max(0, spawned - live)
                
                if self.initial_log_kills is None:
                    # Wait briefly for valid data to avoid 0-spike if reader is catching up
                    if (spawned == 0 and live == 0) and t < 0.03:
                        return
                    self.initial_log_kills = current_mission_kills
                
                kills = max(0, current_mission_kills - self.initial_log_kills)
                if t > 0.017: # Wait ~1 second to avoid high KPM spikes at start
                    kpm = kills / t
                
                self.state_kills = kills
                self.state_kpm = int(kpm)
            else:
                # If logs are off, keep the last known Kills/KPM from Tab scans
                kills = self.state_kills
                kpm = self.state_kpm
            
        # Append data only if we didn't return early
        if self.track_logs:
            self.enemy_data["time"].append(t)
            self.enemy_data["live"].append(live)
            self.enemy_data["spawned"].append(spawned)

            if self.track_kills:
                self.enemy_data["kills"].append(kills)
                self.enemy_data["kpm"].append(kpm)
            
        # --- Master Log Recording (Forward Fill) ---
        self.master_log.append({
            "Time": round(elapsed_seconds, 2),
            "Live": live,
            "Spawned": spawned,
            "Credits": self.state_credits,
            "CPM": self.state_cpm,
            "Kills": self.state_kills,
            "KPM": self.state_kpm,
            "FPS": self.state_fps,
            "Event": self.pending_event
        })
        self.pending_event = "" # Reset event after writing

            # Update Overlays (Log Data)
        if "Num alive" in self.number_overlays: self.number_overlays["Num alive"].update_value(live)
        if "KPM" in self.number_overlays and self.track_kills: self.number_overlays["KPM"].update_value(int(kpm))
        if "FPS" in self.number_overlays: self.number_overlays["FPS"].update_value(self.state_fps)

        # Update Plots Independently
        if (current_perf_time - self.last_plot_update) >= self.log_update_rate:
            # Only update Live/Spawned graphs if we are actually tracking logs
            if self.track_logs:
                self.plot_data_live["t"].append(t)
                self.plot_data_live["y"].append(live)
                self.curve_live.setData(self.plot_data_live["t"], self.plot_data_live["y"])
                
                self.plot_data_spawned["t"].append(t)
                self.plot_data_spawned["y"].append(spawned)
                self.curve_spawned.setData(self.plot_data_spawned["t"], self.plot_data_spawned["y"])
            
            # KPM Graph (Only update here if using logs. If using Tab, it updates on Tab press)
            if self.track_kills and self.track_logs:
                self.plot_data_kpm["t"].append(t)
                self.plot_data_kpm["y"].append(kpm)
                self.curve_kpm.setData(self.plot_data_kpm["t"], self.plot_data_kpm["y"])
            
            if self.track_fps:
                self.plot_data_fps["t"].append(t)
                self.plot_data_fps["y"].append(self.state_fps)
                self.curve_fps.setData(self.plot_data_fps["t"], self.plot_data_fps["y"])
            
            # --- Update Personal Best (Ghost) Curves ---
            if self.pb_data is not None and self.show_pb_live:
                # Filter PB data to only show up to current time (Growing effect)
                mask = self.pb_data['Time_Min'] <= t
                if mask.any():
                    pb_slice = self.pb_data[mask]
                    t_pb = pb_slice['Time_Min'].to_numpy()

                    if self.track_credits:
                        if 'CPM' in pb_slice: self.curve_cpm_pb.setData(t_pb, pb_slice['CPM'].to_numpy())
                        if 'Credits' in pb_slice: self.curve_creds_pb.setData(t_pb, pb_slice['Credits'].to_numpy())
                    
                    if self.track_kills:
                        if 'KPM' in pb_slice: self.curve_kpm_pb.setData(t_pb, pb_slice['KPM'].to_numpy())
                    
                    if self.track_logs:
                        if 'Spawned' in pb_slice: self.curve_spawned_pb.setData(t_pb, pb_slice['Spawned'].to_numpy())
                        if 'Live' in pb_slice: self.curve_live_pb.setData(t_pb, pb_slice['Live'].to_numpy())
                    
                    if self.track_fps:
                        if 'FPS' in pb_slice: self.curve_fps_pb.setData(t_pb, pb_slice['FPS'].to_numpy())

            self.last_plot_update = current_perf_time

    def run_end(self):
        # Stop accepting new data immediately to prevent race conditions
        self.start_time = None
        
        if not self.run_output_path:
            output_dir = os.path.join(os.getcwd(), "OUTPUT")
            os.makedirs(output_dir, exist_ok=True)
            self.run_output_path = os.path.join(output_dir, "unsaved_run")
            os.makedirs(self.run_output_path, exist_ok=True)
            print(f"\n[End] Warning: Run was not started. Saving to '{self.run_output_path}'")

        if self.track_logs and self.log_reader:
            self.log_reader.stop()
            self.sig_stop_log_timer.emit()
        if self.track_fps:
            self.fps_tracker.stop()

        # Close Overlays
        for ov in self.number_overlays.values():
            ov.close()
        if self.acolyte_warner:
            self.acolyte_warner.timer.stop()
            self.acolyte_warner.close()

        print("\n[End] Stopping trackers and saving data...")
        save_path = os.path.join(self.run_output_path, "master_run_log.csv")
        
        try:
            df_master = pd.DataFrame(self.master_log)
            df_master.to_csv(save_path, index=False)
            print(f"[End] Data saved to: {save_path}")
        except Exception as e:
            print(f"[End] Error saving Master CSV: {e}")

        # Matplotlib Plotting
        try:
            num_plots = 0
            if self.track_credits: num_plots += 2
            if self.track_kills: num_plots += 1
            if self.track_fps: num_plots += 1
            
            if num_plots > 0:
                fig, axes = plt.subplots(num_plots, 1, figsize=(10, 5 * num_plots), constrained_layout=True)
                if num_plots == 1: axes = [axes]
                
                # PB Label
                pb_label = None
                if self.pb_data is not None:
                    pb_path = self.settings.get('pb_file', 'Unknown')
                    pb_label = f"PB: {os.path.basename(os.path.dirname(pb_path))}"
                
                idx = 0
            if self.track_credits:
                # CPM
                axes[idx].plot(self.current_run_time, self.cpm, 'yo-', label='CPM')
                if self.pb_data is not None and 'CPM' in self.pb_data:
                    axes[idx].plot(self.pb_data['Time_Min'], self.pb_data['CPM'], 'y--', alpha=0.6, label=pb_label)
                axes[idx].set_title('Credits Per Minute (CPM)')
                axes[idx].set_ylabel('CPM'); axes[idx].set_xlabel('Time (min)'); axes[idx].grid(True); axes[idx].legend(); idx += 1
                # Credits
                axes[idx].plot(self.current_run_time, self.creds, 'go-', label='Credits')
                if self.pb_data is not None and 'Credits' in self.pb_data:
                    axes[idx].plot(self.pb_data['Time_Min'], self.pb_data['Credits'], 'g--', alpha=0.6, label=pb_label)
                axes[idx].set_title('Total Credits')
                axes[idx].set_ylabel('Credits'); axes[idx].set_xlabel('Time (min)'); axes[idx].grid(True); axes[idx].legend(); idx += 1
            
            # KPM
            if self.track_kills:
                # Choose data source based on preference (Logs vs Tab)
                if self.track_logs and self.enemy_data["time"]:
                    axes[idx].plot(self.enemy_data["time"], self.enemy_data["kpm"], 'r-', label='KPM (Log)')
                else:
                    axes[idx].plot(self.current_run_time, self.kpm, 'ro-', label='KPM (Tab)')
                
                if self.pb_data is not None and 'KPM' in self.pb_data:
                    axes[idx].plot(self.pb_data['Time_Min'], self.pb_data['KPM'], 'r--', alpha=0.6, label=pb_label)
                
                axes[idx].set_title('Kills Per Minute (KPM)')
                axes[idx].set_ylabel('KPM')
                axes[idx].set_xlabel('Time (min)')
                axes[idx].grid(True)
                axes[idx].legend()
                idx += 1
                
            # FPS
            if self.track_fps:
                axes[idx].plot(self.plot_data_fps["t"], self.plot_data_fps["y"], 'k-', label='FPS')
                if self.pb_data is not None and 'FPS' in self.pb_data:
                    axes[idx].plot(self.pb_data['Time_Min'], self.pb_data['FPS'], 'k--', alpha=0.6, label=pb_label)
                axes[idx].set_title('Frames Per Second')
                axes[idx].set_ylabel('FPS')
                axes[idx].set_xlabel('Time (min)')
                axes[idx].grid(True)
                axes[idx].legend()
                idx += 1
            
            plot_path = os.path.join(self.run_output_path, "run_plots.png")
            plt.savefig(plot_path)
            print(f"[End] Plots saved to: {plot_path}")
            plt.close(fig)
            
            # Separate Enemy Data Plots
            if self.track_logs and self.enemy_data["time"]:
                fig_enemy, axes_enemy = plt.subplots(2, 1, figsize=(10, 10), constrained_layout=True)
                
                # Spawned
                axes_enemy[0].plot(self.enemy_data["time"], self.enemy_data["spawned"], 'm-', label='Spawned')
                if self.pb_data is not None and 'Spawned' in self.pb_data:
                    axes_enemy[0].plot(self.pb_data['Time_Min'], self.pb_data['Spawned'], 'm--', alpha=0.6, label=pb_label)
                axes_enemy[0].set_title('Total Enemies spawned')
                axes_enemy[0].set_ylabel('Count')
                axes_enemy[0].set_xlabel('Time (min)')
                axes_enemy[0].grid(True)
                axes_enemy[0].legend()
                
                # Live
                axes_enemy[1].plot(self.enemy_data["time"], self.enemy_data["live"], 'c-', label='Live')
                if self.pb_data is not None and 'Live' in self.pb_data:
                    axes_enemy[1].plot(self.pb_data['Time_Min'], self.pb_data['Live'], 'c--', alpha=0.6, label=pb_label)
                axes_enemy[1].set_title('Amount of alive enemies')
                axes_enemy[1].set_ylabel('Count')
                axes_enemy[1].set_xlabel('Time (min)')
                axes_enemy[1].grid(True)
                axes_enemy[1].legend()
                
                enemy_plot_path = os.path.join(self.run_output_path, "enemy_plots.png")
                plt.savefig(enemy_plot_path)
                print(f"[End] Enemy plots saved to: {enemy_plot_path}")
                plt.close(fig_enemy)
                
        except Exception as e:
            print(f"[End] Error generating plots: {e}")

        # Reset run state so a new run can be started
        self.run_output_path = None
        print("[End] Run finished. Ready for new run.\n")


# ==========================================
# Main Execution
# ==========================================
if __name__ == "__main__":
    # Initialize App first for the Dialog
    app = QtWidgets.QApplication.instance()
    if app is None:
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
        app = QtWidgets.QApplication([])

    # --- Dark Theme Setup ---
    app.setStyle("Fusion")
    dark_palette = QtGui.QPalette()
    dark_bg = QtGui.QColor(45, 45, 45)
    dark_input = QtGui.QColor(25, 25, 25)
    text_color = QtGui.QColor(230, 230, 230)
    
    dark_palette.setColor(QtGui.QPalette.Window, dark_bg)
    dark_palette.setColor(QtGui.QPalette.WindowText, text_color)
    dark_palette.setColor(QtGui.QPalette.Base, dark_input)
    dark_palette.setColor(QtGui.QPalette.AlternateBase, dark_bg)
    dark_palette.setColor(QtGui.QPalette.ToolTipBase, text_color)
    dark_palette.setColor(QtGui.QPalette.ToolTipText, dark_input)
    dark_palette.setColor(QtGui.QPalette.Text, text_color)
    dark_palette.setColor(QtGui.QPalette.Button, dark_bg)
    dark_palette.setColor(QtGui.QPalette.ButtonText, text_color)
    dark_palette.setColor(QtGui.QPalette.BrightText, QtCore.Qt.red)
    dark_palette.setColor(QtGui.QPalette.Link, QtGui.QColor(42, 130, 218))
    dark_palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor(42, 130, 218))
    dark_palette.setColor(QtGui.QPalette.HighlightedText, QtCore.Qt.black)
    app.setPalette(dark_palette)
    
    pg.setConfigOption('background', '#191919')
    pg.setConfigOption('foreground', '#E6E6E6')

    # Show Settings Dialog
    dialog = SettingsDialog()
    if dialog.exec_() == QtWidgets.QDialog.Accepted:
        settings = dialog.get_settings()
        tracker = WarframeTracker(settings)
        
        print("\n========================================")
        print("   WARFRAME CPM Lecta Tracker")
        print("========================================")
        print("REQUIREMENTS: Warframe must be on Main Monitor | Custom Menu Scale = 100")
        print("CONTROLS:")
        print("  [F8]  Start Run Timer")
        print("  [TAB] Scan Credits (Open Mission Progress)")
        print("  [F9]  Toggle Bounding Box Overlay")
        print("  [F10] Save Data & End Run")
        print("========================================\n")
        
        # Replaces key.wait(). This keeps the script alive AND runs the draggable window.
        QtWidgets.QApplication.instance().exec_()
    else:
        print("\n[Setup] Cancelled by user.")