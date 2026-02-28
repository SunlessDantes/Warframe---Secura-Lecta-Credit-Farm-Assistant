import os
import time
import winsound
import threading
import pygame
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore, QtGui

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

class SoundSettingWidget(QtWidgets.QWidget):
    def __init__(self, label, config, parent=None):
        super().__init__(parent)
        self.config = config
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        layout.addWidget(QtWidgets.QLabel(label))
        
        self.combo = QtWidgets.QComboBox()
        self.combo.addItems(["Custom File", "Custom Beep"])
        
        current_type = config.get("type", "Custom Beep")
        if current_type not in ["Custom File", "Custom Beep"]:
            current_type = "Custom Beep"
        self.combo.setCurrentText(current_type)
        layout.addWidget(self.combo)
        
        self.spin_freq = QtWidgets.QSpinBox()
        self.spin_freq.setRange(37, 32767)
        self.spin_freq.setSuffix(" Hz")
        self.spin_freq.setValue(config.get("freq", 1000))
        layout.addWidget(self.spin_freq)
        
        self.spin_dur = QtWidgets.QSpinBox()
        self.spin_dur.setRange(1, 5000)
        self.spin_dur.setSuffix(" ms")
        self.spin_dur.setValue(config.get("dur", 150))
        layout.addWidget(self.spin_dur)
        
        self.slider_vol = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_vol.setRange(0, 100)
        self.slider_vol.setValue(config.get("vol", 100))
        self.slider_vol.setFixedWidth(80)
        layout.addWidget(self.slider_vol)
        
        # File Selection UI
        self.file_widget = QtWidgets.QWidget()
        file_layout = QtWidgets.QHBoxLayout(self.file_widget)
        file_layout.setContentsMargins(0, 0, 0, 0)
        
        self.line_file = QtWidgets.QLineEdit(config.get("file", ""))
        self.line_file.setPlaceholderText("Path to .wav/.mp3")
        file_layout.addWidget(self.line_file)
        
        self.btn_browse = QtWidgets.QPushButton("...")
        self.btn_browse.setFixedWidth(30)
        self.btn_browse.clicked.connect(self.browse_file)
        file_layout.addWidget(self.btn_browse)
        
        layout.addWidget(self.file_widget)

        self.btn_test = QtWidgets.QPushButton("Test")
        self.btn_test.clicked.connect(self.test_sound)
        layout.addWidget(self.btn_test)
        
        self.combo.currentTextChanged.connect(self.update_visibility)
        self.update_visibility(self.combo.currentText())

    def update_visibility(self, text):
        is_beep = (text == "Custom Beep")
        is_file = (text == "Custom File")
        self.spin_freq.setVisible(is_beep)
        self.spin_dur.setVisible(is_beep)
        self.slider_vol.setVisible(is_file)
        self.file_widget.setVisible(is_file)

    def browse_file(self):
        f, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select Sound File", "", "Audio Files (*.wav *.mp3 *.ogg)")
        if f:
            try:
                s = pygame.mixer.Sound(f)
                self.line_file.setText(f)
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "Error", f"Could not load sound file: {e}")

    def get_config(self):
        return {
            "type": self.combo.currentText(),
            "freq": self.spin_freq.value(),
            "dur": self.spin_dur.value(),
            "file": self.line_file.text(),
            "vol": self.slider_vol.value()
        }

    def test_sound(self):
        cfg = self.get_config()
        if cfg["type"] == "Custom File":
            if os.path.exists(cfg["file"]):
                try:
                    s = pygame.mixer.Sound(cfg["file"])
                    s.set_volume(cfg["vol"] / 100.0)
                    s.play()
                except Exception as e:
                    print(f"Error playing sound: {e}")
        elif cfg["type"] == "Custom Beep":
            winsound.Beep(cfg["freq"], cfg["dur"])

class SoundConfigDialog(QtWidgets.QDialog):
    def __init__(self, current_config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sound Configuration")
        self.resize(550, 300)
        self.config = current_config
        layout = QtWidgets.QVBoxLayout(self)
        
        self.widgets = {}
        labels = {
            "scan_success": "Scan Success",
            "scan_fail": "Scan Failure",
            "acolyte": "Acolyte Warning (Plays 3x)",
            "effigy": "Effigy Warning (Plays 3x)"
        }
        
        # Define defaults if missing
        defaults = {
            "scan_success": {"type": "Custom Beep", "freq": 1000, "dur": 150},
            "scan_fail": {"type": "Custom Beep", "freq": 500, "dur": 200},
            "acolyte": {"type": "Custom Beep", "freq": 1500, "dur": 100},
            "effigy": {"type": "Custom Beep", "freq": 1500, "dur": 100}
        }
        
        for key, label in labels.items():
            cfg = self.config.get(key, defaults.get(key))
            w = SoundSettingWidget(label, cfg)
            layout.addWidget(w)
            self.widgets[key] = w
            
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_config(self):
        return {k: w.get_config() for k, w in self.widgets.items()}