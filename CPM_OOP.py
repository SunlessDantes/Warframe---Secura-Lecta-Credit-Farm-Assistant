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
import threading
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
pydirectinput.FAILSAFE = False
import pandas as pd #pip install pandas
import pyqtgraph as pg #pip install pyqtgraph and pip install pyQt5
import matplotlib.pyplot as plt #pip install matplotlib
from screeninfo import get_monitors #pip install screeninfo
from pyqtgraph.Qt import QtWidgets, QtCore, QtGui
from log_reader import LogReader
from fps_tracker import FPSTracker
from bounding_box_setup import ConfigEditor
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
        default_pen = QtGui.QPen(QtGui.QColor(255, 0, 0), 2)
        
        for box in self.boxes:
            if len(box) == 5:
                x, y, w, h, color = box
                painter.setPen(QtGui.QPen(color, 2))
                painter.drawRect(x, y, w, h)
            else:
                x, y, w, h = box
                painter.setPen(default_pen)
                painter.drawRect(x, y, w, h)

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
            "color": color_hex,
            "opacity": self.slider_opacity.value()
        }

class EffigyConfigDialog(QtWidgets.QDialog):
    def __init__(self, current_config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Effigy/Ability Warn Configuration")
        self.config = current_config
        layout = QtWidgets.QVBoxLayout(self)
        
        # Audio Cue
        self.check_audio = QtWidgets.QCheckBox("Enable Audio Alert")
        self.check_audio.setChecked(self.config.get("audio_cue", True))
        layout.addWidget(self.check_audio)

        # Flash Color
        color_layout = QtWidgets.QHBoxLayout()
        color_layout.addWidget(QtWidgets.QLabel("Flash Color:"))
        self.btn_color = QtWidgets.QPushButton()
        c = self.config.get("color", "#0000FF")
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
            "color": color_hex,
            "opacity": self.slider_opacity.value(),
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

class AcolyteWarner(QtWidgets.QLabel):
    def __init__(self, config, monitor_info, initial_pos=None, font_size=48, parent=None):
        super().__init__(parent)
        self.config = config
        self.monitor_info = monitor_info
        self.font_size = font_size
        self.drag_pos = None
        self.acolyte_name = "Acolyte"
        self.persistent = False
        
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.Tool)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        
        # Flashing background is handled by paintEvent
        self.flash_on = False
        
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_tick)
        self.end_time = 0

        self.update_style()
        self.adjustSize()
        self.hide() # Hidden by default

        if initial_pos:
            self.move(initial_pos)
        else:
            # Default to center of screen if no position saved
            w, h = 400, 150
            mon_w, mon_h = self.monitor_info['width'], self.monitor_info['height']
            mon_l, mon_t = self.monitor_info['left'], self.monitor_info['top']
            self.move(mon_l + (mon_w - w) // 2, mon_t + (mon_h - h) // 2)

    def update_style(self):
        self.setStyleSheet(f"color: white; font-weight: bold; font-family: Arial;")
        self.setFont(QtGui.QFont("Arial", self.font_size))
        self.adjustSize()

    def paintEvent(self, event):
        if self.flash_on:
            painter = QtGui.QPainter(self)
            color = QtGui.QColor(self.config.get("color", "#FF0000"))
            opacity_pct = self.config.get("opacity", 50)
            color.setAlphaF(opacity_pct / 100.0)
            painter.fillRect(self.rect(), color)
        # Let the default QLabel paintEvent handle the text on top
        super().paintEvent(event)

    def start_warning(self, name, duration):
        self.persistent = False
        self.acolyte_name = name
        self.end_time = time.perf_counter() + duration
        self.hide_time = 0
        self.flash_on = True
        self.timer.start(100) # Update 10 times a second
        self.show()
        self.raise_()

    def start_persistent_warning(self, text):
        self.persistent = True
        self.setText(text)
        self.flash_on = True
        self.timer.start(100)
        self.show()
        self.raise_()
        self.adjustSize()

    def stop_warning(self):
        self.timer.stop()
        self.hide()
        self.persistent = False

    def update_tick(self):
        if self.persistent:
            self.flash_on = not self.flash_on
            self.update()
            return

        now = time.perf_counter()
        remaining = self.end_time - now

        if remaining > 0:
            self.setText(f"{self.acolyte_name} in: {remaining:.1f}s")
            self.flash_on = not self.flash_on
            self.adjustSize()
            self.update() # Triggers paintEvent
        else:
            self.timer.stop()
            self.hide()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == QtCore.Qt.LeftButton and self.drag_pos:
            desired_pos = event.globalPos() - self.drag_pos
            
            x = max(self.monitor_info["left"], min(desired_pos.x(), self.monitor_info["left"] + self.monitor_info["width"] - self.width()))
            y = max(self.monitor_info["top"], min(desired_pos.y(), self.monitor_info["top"] + self.monitor_info["height"] - self.height()))
            
            self.move(x, y)
            event.accept()

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta > 0:
            self.font_size += 4
        else:
            self.font_size = max(12, self.font_size - 4)
        self.update_style()

    def show_preview(self, text="Acolyte Warner\n(Drag & Scroll)"):
        """Shows the overlay for positioning, without flashing."""
        self.timer.stop() # Ensure no flashing is happening
        self.setText(text)
        self.flash_on = True # Solid background
        self.show()
        self.adjustSize()
        self.raise_()

    def hide_preview(self):
        """Hides the positioning preview."""
        self.flash_on = False
        self.hide()

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
            "audio_cue": True,
            "color": "#FF0000",
            "opacity": 50
        }
        # Default Effigy Config
        self.effigy_config = {
            "audio_cue": True,
            "color": "#0000FF",
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

        self.check_debug = QtWidgets.QCheckBox("DEBUG MODE")
        self.check_debug.setChecked(False)
        self.check_debug.setToolTip("Enables detailed logging and saves screenshots of failed scans to a DEBUG_INFO folder.")
        layout.addWidget(self.check_debug)

        self.check_logs = QtWidgets.QCheckBox("Track Log Data for more Analysis -- WARNING: This reads your EE.log file")
        self.check_logs.setStyleSheet("color: red; font-weight: bold;")
        self.check_logs.setChecked(False)
        self.check_logs.setToolTip("Reads Warframe's EE.log file in real-time to track enemy spawn/death counts.\nThis provides highly accurate, continuous KPM data.")
        layout.addWidget(self.check_logs)
        
        # Log KPM Option
        self.check_log_kpm = QtWidgets.QCheckBox("   └─ Use Log Data for Kills/KPM")
        self.check_log_kpm.setChecked(True)
        self.check_log_kpm.setToolTip("If checked, Kills and KPM are calculated from the log file (Real-time).\nIf unchecked, they are read from the Tab menu via OCR (only updates on scan).")
        layout.addWidget(self.check_log_kpm)

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

        # Effigy Warner (Moved under Log Tracking)
        effigy_group = QtWidgets.QGroupBox("Effigy Warner")
        effigy_layout = QtWidgets.QHBoxLayout()
        self.check_effigy = QtWidgets.QCheckBox("Enable")
        self.check_effigy.setToolTip("Flashes a warning when 'AllyLive' count drops (indicating Effigy death).\nRequires Log Tracking.")
        self.check_effigy.toggled.connect(lambda c: self.btn_conf_effigy.setEnabled(c))
        effigy_layout.addWidget(self.check_effigy)
        
        self.btn_conf_effigy = QtWidgets.QPushButton("Configure...")
        self.btn_conf_effigy.setEnabled(False)
        self.btn_conf_effigy.clicked.connect(self.open_effigy_config)
        effigy_layout.addWidget(self.btn_conf_effigy)
        effigy_group.setLayout(effigy_layout)
        layout.addWidget(effigy_group)

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
        self.check_kills.toggled.connect(self.update_rate_state)
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

    def open_effigy_config(self):
        dlg = EffigyConfigDialog(self.effigy_config, self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            self.effigy_config = dlg.get_config()

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
        kills_enabled = self.check_kills.isChecked()
        
        self.check_acolyte.setEnabled(log_tracking_enabled)
        self.btn_conf_acolyte.setEnabled(log_tracking_enabled and self.check_acolyte.isChecked())
        self.check_effigy.setEnabled(log_tracking_enabled)
        self.btn_conf_effigy.setEnabled(log_tracking_enabled and self.check_effigy.isChecked())
        self.check_log_kpm.setEnabled(log_tracking_enabled and kills_enabled)
        
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
            
            if img is None:
                QtWidgets.QMessageBox.warning(self, "Screenshot Missing", f"Could not find the setup screenshot:\n{screenshot_filename}\n\nCannot edit configuration without the reference image.\nPlease run 'Complete New Bounding Box' to create one.")
                return
            
            self.hide()
            time.sleep(0.2)

            try:
                editor = ConfigEditor(img, data, (monitor['left'], monitor['top']), screenshot_path, self)
                if editor.exec_() == QtWidgets.QDialog.Accepted:
                    with open(config_path, 'w') as f:
                        json.dump(editor.data, f, indent=4)
                    print("[Config] Configuration updated.")
            except Exception as e:
                # Catch errors during editor init or execution
                print(f"[Config] Error inside editor: {e}")
                QtWidgets.QMessageBox.critical(self, "Editor Crash", f"An error occurred while opening the editor:\n{e}")

        except Exception as e:
            print(f"[Config] Error in editor: {e}")
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to initialize editor:\n{e}")
        finally:
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
            self.check_effigy.setChecked(data.get("effigy_warner_enabled", False))
            self.check_on_top.setChecked(data.get("always_on_top", True))
            self.check_sound.setChecked(data.get("use_sound", False))
            self.check_debug.setChecked(data.get("debug_mode", False))
            self.check_logs.setChecked(data.get("track_logs", False))
            self.check_log_kpm.setChecked(data.get("use_log_kpm", True))
            self.check_fps.setChecked(data.get("track_fps", False))
            self.check_overlay.setChecked(data.get("use_overlay", False))
            self.check_acolyte.setChecked(data.get("acolyte_warner_enabled", False))
            if "acolyte_config" in data:
                self.acolyte_config = data["acolyte_config"]
            if "effigy_config" in data:
                self.effigy_config = data["effigy_config"]

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
            "effigy_warner_enabled": self.check_effigy.isChecked(),
            "always_on_top": self.check_on_top.isChecked(),
            "use_sound": self.check_sound.isChecked(),
            "debug_mode": self.check_debug.isChecked(),
            "track_logs": self.check_logs.isChecked(),
            "use_log_kpm": self.check_log_kpm.isChecked(),
            "track_fps": self.check_fps.isChecked(),
            "use_overlay": self.check_overlay.isChecked(),
            "overlay_config": self.overlay_config,
            "acolyte_warner_enabled": self.check_acolyte.isChecked(),
            "acolyte_config": self.acolyte_config,
            "effigy_config": self.effigy_config,
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
    sig_ability_warning = QtCore.pyqtSignal()
    sig_ability_restored = QtCore.pyqtSignal()

    def __init__(self, settings):
        super().__init__() #initializing the QObject parernt class
        self.settings = settings
        
        # Initialize QApplication early so we can use GUI elements (ROI Selector) in __init__
        self.app = QtWidgets.QApplication.instance()
        if self.app is None:
            QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
            QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
            self.app = QtWidgets.QApplication([])

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
        self.acolyte_warner = None
        self.effigy_warner = None
        self.overlay_positions_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "overlay_positions.json")
        self.pb_data = None # DataFrame for Personal Best
        self.is_effigy_dead = False
        self.last_ally_live = 0
        self.log_reader = None
        self.log_file = None
        self.debug_dir = None
        self.ee_log_path = os.path.expandvars(r"%LOCALAPPDATA%\Warframe\EE.log")
        self.ee_log_start_offset = None
        
        self.fps_tracker = FPSTracker()
        self.log_timer = QtCore.QTimer()
        self.log_timer.timeout.connect(self.update_log_data)
        self.initial_log_kills = None
        self.sig_start_log_timer.connect(self._start_log_timer_slot)
        self.sig_stop_log_timer.connect(self._stop_log_timer_slot)
        self.request_run_end.connect(self.run_end)
        self.sig_update_overlay_data.connect(self._update_overlay_slot)
        self.sig_ability_warning.connect(self.trigger_ability_warning)
        self.sig_ability_restored.connect(self.clear_ability_warning)
        self.data_updated.connect(self.update_plot)
        self.request_overlay_toggle.connect(self.toggle_overlay)
        
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

        self.win = None
        self.setup_hotkeys()
        
        # --- Controller Setup (PS4 L3 -> Tab) ---
        self.joystick = None
        self.l3_pressed = False
        self.init_controller()
        self.controller_timer = QtCore.QTimer()
        self.controller_timer.timeout.connect(self.poll_controller)
        self.controller_timer.start(16) # Poll at ~60Hz

        # Setup the session (GUI, Config, etc.)
        self.setup_session()
    
    def get_active_window_title(self):
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
            return buff.value
        except:
            return "Unknown"

    def log(self, message, important=False, is_error=False):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        run_time_str = ""
        if hasattr(self, 'start_time') and self.start_time is not None:
            elapsed = time.perf_counter() - self.start_time
            mins = int(elapsed // 60)
            secs = int(elapsed % 60)
            run_time_str = f" [T+{mins:02d}:{secs:02d}]"

        log_line = f"[{timestamp}]{run_time_str} {message}"
        
        if self.log_file:
            try:
                self.log_file.write(log_line + "\n")
                self.log_file.flush()
            except: pass
            
        if important or is_error:
            print(message)

    def setup_session(self):
        """Initializes or re-initializes the tracker session based on current settings."""
        
        # Reset Data Containers
        self.creds = []
        self.confidences = []
        self.credit_positions = []
        self.kills = []
        self.kpm = []
        self.current_run_time = []
        self.cpm = []
        self.start_time = None
        self.last_tab_time = 0.0 
        
        # Scan Area Defaults
        self.scan_left = self.monitor["left"] + int(self.monitor["width"] * 30 / 100)
        self.scan_top = self.monitor["top"] + int(self.monitor["height"] * 10 / 100)
        self.scan_right = self.scan_left + int(self.monitor["width"] * 30 / 100)
        self.scan_lower = self.scan_top + int(self.monitor["height"] * 50 / 100)
        self.credit_positions_2 = []

        # Config path setup
        application_path = os.path.dirname(os.path.abspath(__file__))
        
        config_filename = "bbox_config_solo.json" if self.settings['mode'] == "Solo" else "bbox_config_duo.json"
        self.config_path = os.path.join(application_path, config_filename)

        # Set tracking flags from settings
        self.track_credits = self.settings['track_credits']
        self.track_kills = self.settings['track_kills']
        self.effigy_enabled = self.settings.get('effigy_warner_enabled', False)
        self.track_logs = self.settings.get('track_logs', False)
        self.use_log_kpm = self.settings.get('use_log_kpm', True)
        self.track_fps = self.settings.get('track_fps', False)
        self.log_update_rate = self.settings.get('log_update_rate', 0.1)
        self.data_recording_interval_ms = self.settings.get('data_recording_rate', 100)
        self.show_pb_live = self.settings.get('show_pb_live', True)
        self.scan_delay = self.settings['scan_delay']
        self.always_on_top = self.settings['always_on_top']
        self.use_sound = self.settings['use_sound']
        self.debug_mode = self.settings['debug_mode']
        self.use_overlay = self.settings.get('use_overlay', False)
        
        self.effigy_threshold = 3 if self.settings.get('mode', 'Solo') == 'Duo' else 2
        print(f"[Init] Effigy Warning Threshold set to {self.effigy_threshold} (Mode: {self.settings.get('mode', 'Solo')})")

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
        if self.win is not None:
            self.win.close()
            
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
                p.setAxisItems({'left': LargeNumberAxisItem(orientation='left')})
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

        # --- Load Overlay Positions (Early) ---
        self.saved_positions = {}
        if os.path.exists(self.overlay_positions_file):
            try:
                with open(self.overlay_positions_file, 'r') as f:
                    self.saved_positions = json.load(f)
            except: pass

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
                    if key in self.saved_positions:
                        saved = self.saved_positions[key]
                        pos = QtCore.QPoint(saved['x'], saved['y'])
                        font_size = saved.get('font_size', 24)
                        self.number_overlays[key] = DraggableNumberOverlay(key, cfg.get("color", defaults[key]), self.monitor, pos, font_size)
                    else:
                        pos = QtCore.QPoint(start_x, current_y)
                        self.number_overlays[key] = DraggableNumberOverlay(key, cfg.get("color", defaults[key]), self.monitor, pos)
                        current_y += 40 # Offset for next overlay
                    self.number_overlays[key].show()

            if self.track_credits: create_ov("CPM")
            if self.track_kills: create_ov("KPM")
            if self.track_logs: create_ov("Num alive")
            if self.track_fps: create_ov("FPS")

        # --- Acolyte Warner Initialization ---
        if self.track_logs and self.settings.get("acolyte_warner_enabled", False):
            acolyte_pos = None
            acolyte_font_size = 48
            if 'acolyte' in self.saved_positions:
                acolyte_pos = QtCore.QPoint(self.saved_positions['acolyte']['x'], self.saved_positions['acolyte']['y'])
                acolyte_font_size = self.saved_positions['acolyte'].get('font_size', 48)

            acolyte_cfg = self.settings.get("acolyte_config", {})
            self.acolyte_warner = AcolyteWarner(acolyte_cfg, self.monitor, acolyte_pos, acolyte_font_size)
            print("[Init] Acolyte Warner enabled and initialized.")
            self.acolyte_warner.show_preview("Acolyte Warner\n(Drag & Scroll)")

        # --- Effigy Warner Initialization ---
        if self.track_logs and self.effigy_enabled:
            effigy_pos = None
            effigy_font_size = 48
            if 'effigy' in self.saved_positions:
                effigy_pos = QtCore.QPoint(self.saved_positions['effigy']['x'], self.saved_positions['effigy']['y'])
                effigy_font_size = self.saved_positions['effigy'].get('font_size', 48)
            
            effigy_cfg = self.settings.get("effigy_config", {})
            self.effigy_warner = AcolyteWarner(effigy_cfg, self.monitor, effigy_pos, effigy_font_size)
            self.effigy_warner.show_preview("Effigy Warn\n(Drag & Scroll)")

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
                # --- End Diagnostic ---
                
                

                # Check if the event is for our target button (L3)
                btn_index = 7 # Changed based on your diagnostic output
                if event.type == pygame.JOYBUTTONDOWN and event.button == btn_index:
                    self.l3_pressed = True
                    self.log(f"[Controller] Button {btn_index} Pressed - Holding TAB")
                    pydirectinput.keyDown('tab')
                elif event.type == pygame.JOYBUTTONUP and event.button == btn_index:
                    self.l3_pressed = False
                    self.log(f"[Controller] Button {btn_index} Released - Releasing TAB")
                    pydirectinput.keyUp('tab')
        except pygame.error as e:
            # This can happen if the controller disconnects
            self.log(f"[Controller] Error: {e}", is_error=True)
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
            if self.acolyte_warner:
                self.acolyte_warner.hide_preview()
            return

        mx = self.monitor['left']
        my = self.monitor['top']
        boxes = []

        # Scan Area (Green)
        boxes.append((self.scan_left - mx, self.scan_top - my, 
                      self.scan_right - self.scan_left, self.scan_lower - self.scan_top, QtGui.QColor('green')))
        
        # Credit Positions (Yellow)
        for l, t, r, b in self.credit_positions:
            boxes.append((l - mx, t - my, r - l, b - t, QtGui.QColor('yellow')))

        # Scan Area 2 (Cyan)
        if hasattr(self, 'scan_left_2') and self.scan_left_2 > 0:
             boxes.append((self.scan_left_2 - mx, self.scan_top_2 - my, 
                      self.scan_right_2 - self.scan_left_2, self.scan_lower_2 - self.scan_top_2, QtGui.QColor('cyan')))

        # Credit Positions 2 (Magenta)
        if hasattr(self, 'credit_positions_2'):
            for l, t, r, b in self.credit_positions_2:
                boxes.append((l - mx, t - my, r - l, b - t, QtGui.QColor('magenta')))
            
        # Kills (Red)
        if self.track_kills and hasattr(self, 'left_kills'):
            boxes.append((self.left_kills - mx, self.top_kills - my, 
                          self.right_kills - self.left_kills, self.lower_kills - self.top_kills, QtGui.QColor('red')))

        self.overlay = OverlayWindow((mx, my, self.monitor['width'], self.monitor['height']), boxes)
        self.overlay.show()

        if self.acolyte_warner:
            self.acolyte_warner.show_preview()
        if self.effigy_warner:
            self.effigy_warner.show_preview("Effigy Warn\n(Drag & Scroll)")

    def load_config(self):
        try:
            with open(self.config_path, 'r') as f:
                data = json.load(f)
            
            self.scan_left = data['scan_area'][0]
            self.scan_top = data['scan_area'][1]
            self.scan_right = data['scan_area'][2]
            self.scan_lower = data['scan_area'][3]

            if data.get('scan_area_2'):
                self.scan_left_2 = data['scan_area_2'][0]
                self.scan_top_2 = data['scan_area_2'][1]
                self.scan_right_2 = data['scan_area_2'][2]
                self.scan_lower_2 = data['scan_area_2'][3]
                self.credit_positions_2 = data.get('credit_positions_2', [])

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

    def save_overlay_positions(self):
        try:
            # Load existing to preserve keys we might not be tracking right now
            current_saved = {}
            if os.path.exists(self.overlay_positions_file):
                try:
                    with open(self.overlay_positions_file, 'r') as f:
                        current_saved = json.load(f)
                except: pass
            
            # Update with current overlays
            for key, ov in self.number_overlays.items():
                pos = ov.pos()
                current_saved[key] = {'x': pos.x(), 'y': pos.y(), 'font_size': ov.font_size}
            
            if self.acolyte_warner:
                pos = self.acolyte_warner.pos()
                current_saved['acolyte'] = {'x': pos.x(), 'y': pos.y(), 'font_size': self.acolyte_warner.font_size}
            
            if self.effigy_warner:
                pos = self.effigy_warner.pos()
                current_saved['effigy'] = {'x': pos.x(), 'y': pos.y(), 'font_size': self.effigy_warner.font_size}

            with open(self.overlay_positions_file, 'w') as f:
                json.dump(current_saved, f, indent=4)
            # print("[System] Overlay positions saved.") 
        except Exception as e:
            print(f"[System] Error saving overlay positions: {e}")

    def start_run(self):
        # Ensure any previous run state is cleared
        self.start_time = None
        
        if self.start_time is not None:
            self.log("Run start attempted but run already in progress.", important=True)
            return
            
        self.start_time = time.perf_counter()
        self.last_plot_update = 0

        # Save overlay positions on run start
        self.save_overlay_positions()

        # Reset data for new run to fix plotting issues
        self.creds = []
        self.confidences = []
        self.kills = []
        self.kpm = []
        self.current_run_time = []
        self.cpm = []
        self.initial_log_kills = None
        self.ee_log_start_offset = None
        
        # Reset Master Log
        self.master_log = []
        self.state_credits = 0
        
        # Hide Acolyte Warner preview if it's visible
        if self.acolyte_warner:
            self.acolyte_warner.hide_preview()
        if self.effigy_warner:
            self.effigy_warner.hide_preview()
        self.state_cpm = 0
        self.state_kills = 0
        self.state_kpm = 0
        self.state_fps = 0
        self.pending_event = "Start"
        self.is_effigy_dead = False
        self.last_ally_live = 0
        
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
            
            # Setup Debug/Log Folder
            if self.debug_mode:
                self.debug_dir = os.path.join(self.run_output_path, "DEBUG_INFO")
                os.makedirs(self.debug_dir, exist_ok=True)
                log_path = os.path.join(self.debug_dir, "runtime_log.txt")
            else:
                self.debug_dir = None
                log_path = os.path.join(self.run_output_path, "runtime_log.txt")
            
            self.log_file = open(log_path, "w", encoding="utf-8")
            
            self.log(f"[Run] Started! Output: {self.run_output_path}", important=True)
            self.log(f"[Run] Debug Mode: {self.debug_mode}")
            
            # --- Verbose Start Info for Players ---
            self.log("-" * 40)
            self.log(f"CONFIGURATION: {self.settings['mode']} Mode")
            self.log(f"Monitor Resolution: {self.monitor['width']}x{self.monitor['height']}")
            self.log(f"Active Features: Credits={self.track_credits}, Kills={self.track_kills}, Logs={self.track_logs}, FPS={self.track_fps}")
            if self.track_logs:
                 self.log(f"Log Path: {self.ee_log_path}")
                 if self.effigy_enabled:
                     self.log(f"Effigy Monitor: ON (Threshold: {self.effigy_threshold}). Warning triggers if allies < {self.effigy_threshold}.")
            self.log("-" * 40)
        except Exception as e:
            print(f"[CRITICAL] Could not create output folder. Error: {e}")
            self.run_output_path = os.path.dirname(os.path.abspath(__file__))
        
        self.log("[Run] Timer started at 0.0.")
        
        if self.track_fps:
            self.fps_tracker.start()
        
        if self.track_logs:
            self.log_reader = LogReader(self.ee_log_path)
            self.log_reader.start()
            self.sig_start_log_timer.emit() # Update every 1 second
            
            if self.debug_mode and os.path.exists(self.ee_log_path):
                try:
                    with open(self.ee_log_path, 'r', encoding='utf-8', errors='ignore') as f:
                        f.seek(0, os.SEEK_END)
                        self.ee_log_start_offset = f.tell()
                    self.log(f"[Debug] EE.log start offset marked at: {self.ee_log_start_offset}")
                except Exception as e:
                    self.log(f"[Debug] Failed to mark EE.log start: {e}", is_error=True)
        
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

    def trigger_ability_warning(self):
        if self.effigy_warner:
            self.effigy_warner.start_persistent_warning("Effigy dead")
            
            # Auto-hide after 8 seconds
            QtCore.QTimer.singleShot(8000, self.effigy_warner.stop_warning)
            
            effigy_cfg = self.settings.get("effigy_config", {})

            if effigy_cfg.get("audio_cue", True):
                # Play sound in a separate thread so it doesn't block the UI update
                def play_alert():
                    for _ in range(3):
                        winsound.Beep(1500, 100)
                        time.sleep(0.05)
                threading.Thread(target=play_alert, daemon=True).start()
    
    def clear_ability_warning(self):
        if self.effigy_warner:
            self.effigy_warner.stop_warning()

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
        self.log("Tab key pressed.")
        self.tab_held = True
        self.tab_action()

    def on_tab_release(self, event):
        self.log("Tab key released.")
        self.tab_held = False

    def tab_action(self):
        try:
            self._tab_action_unsafe()
        except Exception as e:
            self.log(f"[Tab Action] Error: {e}", is_error=True)

    def _tab_action_unsafe(self):
        if self.start_time is None:
            self.log("[Action] Ignored: Run not started.")
            return
        current_time = time.perf_counter()
        if (current_time - self.last_tab_time) < self.cooldown_duration:
            return
        self.last_tab_time = current_time

        time.sleep(self.scan_delay) # Adjustable delay for UI fade-in
        
        elapsed_time = time.perf_counter() - self.start_time
        if elapsed_time < 1.0:
            self.log("[Action] Ignored: Run time < 1 second.")
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
        active_credit_positions = self.credit_positions
        current_scan_left = self.scan_left
        
        if self.track_credits:
            coords = self.find_credits_coords(im_scan)
            
            # If not found in Area 1, try Area 2 if configured
            if not coords and hasattr(self, 'scan_left_2') and self.scan_left_2 > 0:
                 scan_bbox_2 = (self.scan_left_2, self.scan_top_2, self.scan_right_2, self.scan_lower_2)
                 im_scan_2 = self.screenshot(bbox=scan_bbox_2)
                 coords = self.find_credits_coords(im_scan_2)
                 if coords:
                     active_credit_positions = self.credit_positions_2
                     current_scan_left = self.scan_left_2
                     im_scan = im_scan_2 # Use the successful image for debug if needed

            if coords:
                # Calculate alignment to find the correct number box
                text_abs_x = current_scan_left + coords[0]
                text_width = coords[2]
                text_center_x = text_abs_x + (text_width / 2)
                
                min_dist = float('inf')
                for box in active_credit_positions:
                    box_center_x = box[0] + (box[2] - box[0]) / 2
                    dist = abs(text_center_x - box_center_x)
                    if dist < min_dist:
                        min_dist = dist
                        best_box = box
                
                if not best_box:
                    self.log(f"[Scan] ERROR: 'Credits' text found at {coords}, but does not align with any configured credit box.", is_error=True)
                    self.log("[Scan] Hint: Run 'Editing a Bounding Box' and check if your yellow boxes line up with where the numbers appear relative to the 'Credits' text.")
                    return
                self.last_credits_coords = coords
            else:
                self.log("[Scan] Did not find 'Credits' text in scan area.")
                self.log("[Scan] Hint: Ensure the Mission Progress menu is open. Check if the green 'Scan Area' box covers the word 'Credits'.")
                if self.use_sound:
                    winsound.Beep(500, 200) # Low beep for "Not Found"
                if self.debug_mode and self.debug_dir:
                    filename = f"NO_CREDITS_TEXT_AT_{time_mins:.2f}m.png"
                    path = os.path.join(self.debug_dir, filename)
                    cv.imwrite(path, im_scan)
                    self.log(f"Saved debug image: {filename}")
                return

        # --- 2. Capture Data Images ---
        # Now that we know the menu is open, capture the specific data boxes immediately.
        
        im_credits_val = None
        if self.track_credits and best_box:
            im_credits_val = self.screenshot(bbox=tuple(best_box))
            
        im_kills_val = None
        if self.track_kills and (not self.track_logs or not self.use_log_kpm):
            bbox_kills = (self.left_kills, self.top_kills, self.right_kills, self.lower_kills)
            im_kills_val = self.screenshot(bbox=bbox_kills)

        # --- 4. Process Data (OCR) ---
        scan_succeeded = False
        cpm_value = 0
        num = 0
        if self.track_credits and im_credits_val is not None:
            # Pass bbox=None to disable retries (since we can't re-screenshot a closed tab)
            num, confidence, time_cp = self.ocr_function(im_credits_val, bbox=None)

            # Safety Check: Credits jump > 1,000,000
            if len(self.creds) > 0:
                diff = num - self.creds[-1]
                if diff > 1_000_000:
                    self.log(f"[Scan] Warning: Credits jumped by {diff} (Prev: {self.creds[-1]}, New: {num}).", important=True)
                    if self.debug_mode and self.debug_dir:
                        filename = f"CREDIT_JUMP_WARNING_AT_{time_mins:.2f}m.png"
                        path = os.path.join(self.debug_dir, filename)
                        cv.imwrite(path, im_credits_val)
                        self.log(f"Saved debug image: {filename}")

            if num > 0:
                scan_succeeded = True
                cpm_value = num / time_mins
                self.creds.append(num)
                self.confidences.append(confidence)
                self.cpm.append(cpm_value)
                self.state_credits = num
                self.state_cpm = int(cpm_value)
            else:
                active_win = self.get_active_window_title()
                self.log(f"[Scan] FAIL: Could not read credit numbers from image. Active Window: '{active_win}'")
                self.log("[Scan] Hint: Check if the yellow 'Credit Positions' boxes accurately cover the numbers. Ensure no glare/overlay is blocking them.")
                if self.debug_mode and self.debug_dir:
                    filename = f"OCR_CREDITS_FAIL_AT_{time_mins:.2f}m.png"
                    path = os.path.join(self.debug_dir, filename)
                    cv.imwrite(path, im_credits_val)
                    self.log(f"Saved debug image: {filename}")

        # --- Kills Logic (OCR) ---
        kills_num = 0
        if self.track_kills:
            if self.track_logs and self.use_log_kpm and self.log_reader:
                live, spawned = self.log_reader.get_stats()
                kills_num = max(0, spawned - live)
                scan_succeeded = True # Log reading is not an OCR fail state
            elif im_kills_val is not None:
                kills_num, _, _ = self.ocr_function(im_kills_val, bbox=None)
                
                if kills_num == 0 and self.debug_mode and self.debug_dir:
                    filename = f"OCR_KILLS_FAIL_AT_{time_mins:.2f}m.png"
                    path = os.path.join(self.debug_dir, filename)
                    cv.imwrite(path, im_kills_val)
                    self.log(f"Saved debug image: {filename}")

                # Safety Check: Kills jump > 2,500 (OCR only)
                if len(self.kills) > 0:
                    diff = kills_num - self.kills[-1]
                    if diff > 2500:
                        self.log(f"[Scan] Warning: Kills jumped by {diff} (Prev: {self.kills[-1]}, New: {kills_num}).", important=True)
                        if self.debug_mode and self.debug_dir:
                            filename = f"KILL_JUMP_WARNING_AT_{time_mins:.2f}m.png"
                            path = os.path.join(self.debug_dir, filename)
                            cv.imwrite(path, im_kills_val)
                            self.log(f"Saved debug image: {filename}")
            
            if kills_num > 0 and not self.track_logs:
                scan_succeeded = True

            # Only append and update state if we have a valid number
            # (or if we are using logs where 0 is a valid state)
            if (self.track_logs and self.use_log_kpm) or (kills_num > 0):
                kpm_value = kills_num / time_mins
                self.kills.append(kills_num)
                self.kpm.append(kpm_value)
                if not self.track_logs or not self.use_log_kpm:
                    self.state_kills = kills_num
                    self.state_kpm = int(kpm_value)

        # --- 5. Finalize and Signal ---
        if not scan_succeeded:
            self.log("[Scan] FAILURE: No valid data extracted from scan (OCR failed for all metrics).", important=True)
            if self.use_sound:
                winsound.Beep(500, 200) # Low beep for total failure
            return # Exit without appending time or updating plots

        if self.use_sound:
            winsound.Beep(1000, 150) # High beep for success
        self.current_run_time.append(time_mins)

        # Update Kills state if using logs (must happen after success check)
        if self.track_kills and self.track_logs and self.use_log_kpm:
            kpm_value = (kills_num / time_mins) if time_mins > 0.017 else 0
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
        if self.track_credits and num > 0: log_msg += f" | Credits: {num} (CPM: {int(cpm_value)})"
        if self.track_kills and ((self.track_logs and self.use_log_kpm) or kills_num > 0): log_msg += f" | Kills: {kills_num} (KPM: {int(kpm_value)})"
        self.log(log_msg, important=True)
        
        # Update Overlays (Tab Data)
        # Must use signal because tab_action runs in a background thread (keyboard hook)
        overlay_data = {}
        if "CPM" in self.number_overlays and num > 0: overlay_data["CPM"] = int(cpm_value)
        if "KPM" in self.number_overlays and (not self.track_logs or not self.use_log_kpm) and kills_num > 0: overlay_data["KPM"] = int(kpm_value)
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
                self.log(f"  [OCR] Empty scan. Retrying in 0.3s (Attempt {retries + 1}/6)")
                time.sleep(0.3)
                return self.ocr_function(self.screenshot(bbox=bbox), bbox=bbox, retries=retries + 1)
            else:
                self.log("  [OCR] Max retries reached. Returning 0.")
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
            self.log(f"[OCR] Parse Error: {e} | Raw Scan: {scan}", is_error=True)
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

        live, spawned, ally_live = 0, 0, 0
        if self.track_logs and self.log_reader:
            live, spawned, ally_live = self.log_reader.get_stats()
        
        # Check for Acolyte Warning
        if self.track_logs and self.log_reader and self.acolyte_warner:
            acolyte_info = self.log_reader.check_and_clear_acolyte_warning()
            if acolyte_info:
                name, duration = acolyte_info
                self.log(f"[Tracker] Triggering Acolyte Warner for {name} ({duration}s)!", important=True)
                acolyte_cfg = self.settings.get("acolyte_config", {})
                if acolyte_cfg.get("audio_cue", True):
                    # Use a distinct sound for the acolyte
                    # 3 High Beeps
                    for _ in range(3):
                        winsound.Beep(1500, 100)
                        time.sleep(0.05)
                self.acolyte_warner.start_warning(name, duration)
                if self.pending_event:
                    self.pending_event += f" | {name} Spawned"
                else:
                    self.pending_event = f"{name} Spawned"

        # Check for Effigy Warning (Log Based)
        if self.track_logs and self.effigy_enabled:
            # If ally count drops, trigger warning
            # Logic: Trigger if we drop FROM the active threshold (or higher) TO below it.
            if self.last_ally_live >= self.effigy_threshold and ally_live < self.effigy_threshold:
                self.log(f"[Tracker] Effigy Warning Triggered: Ally count dropped from {self.last_ally_live} to {ally_live} (Threshold: {self.effigy_threshold}).")
                self.sig_ability_warning.emit()
            self.last_ally_live = ally_live

        # Check for General Log Events (Acolyte Death)
        if self.track_logs and self.log_reader:
            log_event = self.log_reader.check_and_clear_general_events()
            if log_event:
                self.log(f"[Tracker] Event: {log_event}", important=True)
                if self.pending_event:
                    self.pending_event += f" | {log_event}"
                else:
                    self.pending_event = log_event

        kills = 0
        kpm = 0.0
        
        if self.track_kills:
            if self.track_logs and self.use_log_kpm:
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
            output_dir = os.path.join(os.getcwd(), "False_or_unfinished_runs")
            os.makedirs(output_dir, exist_ok=True)
            self.run_output_path = os.path.join(output_dir, "unsaved_run")
            os.makedirs(self.run_output_path, exist_ok=True)
            self.log(f"[End] Warning: Run was not started. Saving to '{self.run_output_path}'", important=True)

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
        if self.effigy_warner:
            self.effigy_warner.timer.stop()
            self.effigy_warner.close()
        
        # Save EE.log recording if debug mode
        if self.track_logs and self.debug_mode and self.ee_log_start_offset is not None and self.debug_dir:
            try:
                if os.path.exists(self.ee_log_path):
                    dest_log = os.path.join(self.debug_dir, "ee_recording.log")
                    self.log(f"[Debug] Saving EE.log recording to: {dest_log}")
                    
                    with open(self.ee_log_path, 'r', encoding='utf-8', errors='ignore') as src:
                        # Check if file was truncated (game restart)
                        src.seek(0, os.SEEK_END)
                        end_pos = src.tell()
                        
                        if self.ee_log_start_offset > end_pos:
                            self.log("[Debug] EE.log seems to have been truncated or rotated. Skipping recording.", is_error=True)
                        else:
                            src.seek(self.ee_log_start_offset)
                            with open(dest_log, 'w', encoding='utf-8') as dst:
                                shutil.copyfileobj(src, dst)
            except Exception as e:
                self.log(f"[Debug] Failed to save EE.log recording: {e}", is_error=True)
        
        # Save Overlay Positions
        self.save_overlay_positions()
        self.log("[End] Overlay positions saved.")
        self.log("[End] Stopping trackers and saving data...", important=True)
        save_path = os.path.join(self.run_output_path, "master_run_log.csv")
        
        try:
            df_master = pd.DataFrame(self.master_log)
            df_master.to_csv(save_path, index=False)
            self.log(f"[End] Data saved to: {save_path}", important=True)
        except Exception as e:
            self.log(f"[End] Error saving Master CSV: {e}", is_error=True)

        if self.log_file:
            self.log("-" * 40)
            self.log("Run ended.")
            if self.current_run_time:
                self.log(f"Total Duration: {self.current_run_time[-1]:.2f} minutes")
            self.log(f"Total Credits: {self.state_credits}")
            self.log("-" * 40)
            self.log_file.close()
            self.log_file = None

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
            print(f"[End] Plots saved to: {plot_path}") # Keep print here as log file is closed? No, log file closed above.
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
                print(f"[End] Enemy plots saved to: {enemy_plot_path}") # Keep print
                plt.close(fig_enemy)
                
        except Exception as e:
            print(f"[End] Error generating plots: {e}")

        # Reset run state so a new run can be started
        self.run_output_path = None
        print("[End] Run finished. Ready for new run.\n") # Keep print
        
        # Prompt for next run
        QtCore.QTimer.singleShot(100, self.prompt_next_run)

    def prompt_next_run(self):
        # Open Settings Dialog again to allow user to start next run
        dlg = SettingsDialog()
        # Pre-load current settings
        dlg.check_load_prev.setChecked(True)
        dlg.load_previous_settings(True)
        
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            self.settings = dlg.get_settings()
            self.setup_session()


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