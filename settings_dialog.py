import os
import json
import ctypes
import sys
import shutil
import subprocess
import time
import cv2 as cv
import mss
import urllib.request
from screeninfo import get_monitors
from pyqtgraph.Qt import QtWidgets, QtCore, QtGui
from gui_components import AcolyteConfigDialog, EffigyConfigDialog, OverlayConfigDialog, SoundConfigDialog, AnimatedToggle
from bounding_box_setup import ConfigEditor

class ProfileManagerDialog(QtWidgets.QDialog):
    def __init__(self, current_settings, profiles_file, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Profile Manager")
        self.resize(400, 300)
        self.current_settings = current_settings
        self.profiles_file = profiles_file
        self.profiles = {}
        self.load_profiles()

        # Different Theme (Dark Blue/Purple background to distinguish)
        palette = self.palette()
        palette.setColor(QtGui.QPalette.Window, QtGui.QColor(40, 40, 80))
        palette.setColor(QtGui.QPalette.WindowText, QtGui.QColor(220, 220, 255))
        palette.setColor(QtGui.QPalette.Base, QtGui.QColor(20, 20, 50))
        palette.setColor(QtGui.QPalette.Text, QtGui.QColor(220, 220, 255))
        palette.setColor(QtGui.QPalette.Button, QtGui.QColor(60, 60, 100))
        palette.setColor(QtGui.QPalette.ButtonText, QtGui.QColor(220, 220, 255))
        self.setPalette(palette)

        layout = QtWidgets.QVBoxLayout(self)
        
        layout.addWidget(QtWidgets.QLabel("<b>Manage Settings Profiles</b>"))
        
        self.list_profiles = QtWidgets.QListWidget()
        self.list_profiles.addItems(sorted(self.profiles.keys()))
        layout.addWidget(self.list_profiles)

        btn_layout = QtWidgets.QVBoxLayout()
        
        self.btn_create = QtWidgets.QPushButton("Save Current UI Settings as New Profile")
        self.btn_create.clicked.connect(self.create_profile)
        btn_layout.addWidget(self.btn_create)

        self.btn_delete = QtWidgets.QPushButton("Delete Selected Profile")
        self.btn_delete.clicked.connect(self.delete_profile)
        btn_layout.addWidget(self.btn_delete)

        layout.addLayout(btn_layout)
        
        self.btn_close = QtWidgets.QPushButton("Close")
        self.btn_close.clicked.connect(self.accept)
        layout.addWidget(self.btn_close)

    def load_profiles(self):
        if os.path.exists(self.profiles_file):
            try:
                with open(self.profiles_file, 'r') as f:
                    self.profiles = json.load(f)
            except: self.profiles = {}

    def save_profiles(self):
        with open(self.profiles_file, 'w') as f:
            json.dump(self.profiles, f, indent=4)

    def create_profile(self):
        name, ok = QtWidgets.QInputDialog.getText(self, "New Profile", "Enter Profile Name:")
        if ok and name:
            if name in self.profiles:
                QtWidgets.QMessageBox.warning(self, "Error", "Profile already exists. Delete it first or choose a different name.")
                return
            self.profiles[name] = self.current_settings
            self.save_profiles()
            self.list_profiles.addItem(name)
            self.list_profiles.sortItems()

    def delete_profile(self):
        item = self.list_profiles.currentItem()
        if item:
            name = item.text()
            del self.profiles[name]
            self.save_profiles()
            self.list_profiles.takeItem(self.list_profiles.row(item))

class UpdateChecker(QtCore.QThread):
    sig_update_found = QtCore.pyqtSignal(str, str) # version, title

    def __init__(self, current_version):
        super().__init__()
        self.current_version = current_version

    def run(self):
        url = "https://api.github.com/repos/SilberKomet/Warframe---Secura-Lecta-Credit-Farm-Assistant/releases/latest"
        try:
            # User-Agent is required by GitHub API
            req = urllib.request.Request(url, headers={'User-Agent': 'Warframe-Lecta-Tracker'})
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                latest_tag = data.get("tag_name", "")
                name = data.get("name", "")
                
                if latest_tag:
                    # Helper to parse version string into a comparable tuple
                    def version_tuple(v):
                        try:
                            # Handles x.y.z vs x.y correctly (e.g. 2.0 > 1.6.9)
                            return tuple(int(x) for x in v.lower().lstrip('v').split('.') if x.isdigit())
                        except:
                            return (0,)

                    if version_tuple(latest_tag) > version_tuple(self.current_version):
                        self.sig_update_found.emit(latest_tag, name)

        except Exception:
            pass # Fail silently if no internet or API error

class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, version="Unknown"):
        super().__init__()
        self.setWindowTitle("Tracker Settings")
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowMinimizeButtonHint)
        self.resize(740, 930)
        self.version = version

        # --- Background Image Setup ---
        self.setObjectName("SettingsDialog")
        app_dir = os.path.dirname(os.path.abspath(__file__))
        bg_path = os.path.join(app_dir, "Background.png")
        if not os.path.exists(bg_path):
            bg_path = os.path.join(app_dir, "..", "Background.png")
        
        if os.path.exists(bg_path):
            bg_path = bg_path.replace("\\", "/")
            self.setStyleSheet(f"""
                QDialog#SettingsDialog {{
                    background-image: url({bg_path});
                    background-position: center;
                    background-repeat: no-repeat;
                    background-color: #1e1e1e;
                }}
                QTabWidget {{
                    background: transparent;
                }}
                QStackedWidget {{
                    background: transparent;
                }}
                QTabWidget::pane {{
                    background: rgba(30, 30, 30, 100);
                    border: 1px solid #444;
                }}
                QWidget#TabPage {{
                    background: transparent;
                }}
                QGroupBox {{
                    background-color: rgba(30, 30, 30, 150);
                    border: 1px solid #444;
                    border-radius: 5px;
                    margin-top: 20px;
                }}
            """)

        main_layout = QtWidgets.QVBoxLayout(self)

        self.settings_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "last_run_settings.json")
        self.path_config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "path_config.json")
        self.profiles_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profiles.json")

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
            "KPM TAB": {"show": True, "color": "#FF0000"},
            "KPM LOG": {"show": True, "color": "#FF0000"},
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
        # Default Sound Config
        self.sound_config = {
            "scan_success": {"type": "Custom Beep", "freq": 1000, "dur": 150, "vol": 100},
            "scan_fail": {"type": "Custom Beep", "freq": 500, "dur": 200, "vol": 100},
            "acolyte": {"type": "Custom Beep", "freq": 1500, "dur": 100, "vol": 100},
            "effigy": {"type": "Custom Beep", "freq": 1500, "dur": 100, "vol": 100}
        }
        # Default Plot Config
        self.plot_config = {
            "background_opacity": 100,
            "plots": {
                "cpm": {"line": "#FFFF00", "axis": "#FFFFFF"},     # Yellow
                "creds": {"line": "#00FF00", "axis": "#FFFFFF"},   # Green
                "kpm": {"line": "#FF0000", "axis": "#FFFFFF"},     # Red
                "log_kpm": {"line": "#FF00FF", "axis": "#FFFFFF"}, # Magenta
                "live": {"line": "#00FFFF", "axis": "#FFFFFF"},    # Cyan
                "fps": {"line": "#00FFFF", "axis": "#FFFFFF"}      # Cyan
            }
        }

        # --- Tabs Setup ---
        self.tabs = QtWidgets.QTabWidget()
        main_layout.addWidget(self.tabs)

        # ================= TAB 1: GENERAL =================
        tab_general = QtWidgets.QWidget()
        tab_general.setObjectName("TabPage")
        layout_gen = QtWidgets.QVBoxLayout(tab_general)

        # --- Profile Selection UI ---
        profile_group = QtWidgets.QGroupBox("Settings Profiles")
        profile_layout = QtWidgets.QHBoxLayout()
        
        self.combo_profiles = QtWidgets.QComboBox()
        self.load_profiles_to_combo()
        self.combo_profiles.currentIndexChanged.connect(self.on_profile_changed)
        profile_layout.addWidget(self.combo_profiles)
        
        self.btn_save_profile = QtWidgets.QPushButton("Save")
        self.btn_save_profile.setToolTip("Overwrite the selected profile with current settings.")
        self.btn_save_profile.clicked.connect(self.save_current_profile)
        profile_layout.addWidget(self.btn_save_profile)

        self.btn_manage_profiles = QtWidgets.QPushButton("Manage Profiles")
        self.btn_manage_profiles.clicked.connect(self.open_profile_manager)
        profile_layout.addWidget(self.btn_manage_profiles)
        
        profile_group.setLayout(profile_layout)
        layout_gen.addWidget(profile_group)

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
        layout_gen.addLayout(path_layout)

        # Previous Settings Checkbox
        self.check_load_prev = AnimatedToggle("Load Last Used Settings")
        self.check_load_prev.setToolTip("If checked, automatically loads all settings from the previous run when this dialog opens.")
        self.check_load_prev.toggled.connect(self.load_previous_settings)
        layout_gen.addWidget(self.check_load_prev)
        
        if not os.path.exists(self.settings_file):
            self.check_load_prev.setEnabled(False)
            self.check_load_prev.setText("Load Last Used Settings (None found)")

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
        layout_gen.addWidget(self.mode_group)
        
        self.check_on_top = AnimatedToggle("Live Plots Always on Top")
        self.check_on_top.setChecked(True)
        layout_gen.addWidget(self.check_on_top)
        
        layout_gen.addStretch()
        self.tabs.addTab(tab_general, "General")

        # ================= TAB 2: TRACKING =================
        tab_tracking = QtWidgets.QWidget()
        tab_tracking.setObjectName("TabPage")
        layout_track = QtWidgets.QVBoxLayout(tab_tracking)

        # --- Credits ---
        credits_group = QtWidgets.QGroupBox("Credits Tracking")
        credits_layout = QtWidgets.QVBoxLayout()
        
        self.check_credits = AnimatedToggle("Track Credits")
        self.check_credits.setChecked(True)
        self.check_credits.setToolTip("Enables tracking of Credits and Credits Per Minute (CPM) via OCR.")
        credits_layout.addWidget(self.check_credits)

        self.check_high_cpm = AnimatedToggle("Show High CPM Line")
        self.check_high_cpm.setChecked(False)
        self.check_high_cpm.setToolTip("Displays a horizontal line on the live CPM graph at the highest CPM value reached.")
        self.check_high_cpm.setEnabled(self.check_credits.isChecked())
        self.check_credits.toggled.connect(self.check_high_cpm.setEnabled)
        credits_layout.addWidget(self.check_high_cpm)

        # CPM Calculation Mode
        cpm_calc_group = QtWidgets.QWidget()
        cpm_calc_layout = QtWidgets.QHBoxLayout(cpm_calc_group)
        cpm_calc_layout.setContentsMargins(0, 0, 0, 0)
        
        cpm_calc_layout.addWidget(QtWidgets.QLabel("CPM Mode:"))
        self.combo_cpm_mode = QtWidgets.QComboBox()
        self.combo_cpm_mode.addItems(["Cumulative Average", "Rolling Average"])
        self.combo_cpm_mode.setToolTip("<b>Cumulative:</b> Average CPM over the entire run duration.<br><b>Rolling:</b> Average CPM over the last X seconds (more responsive to recent farming).")
        self.combo_cpm_mode.currentIndexChanged.connect(self.update_rate_state)
        cpm_calc_layout.addWidget(self.combo_cpm_mode)
        
        self.spin_cpm_window = QtWidgets.QSpinBox()
        self.spin_cpm_window.setRange(60, 3600)
        self.spin_cpm_window.setValue(300)
        self.spin_cpm_window.setSuffix(" s")
        cpm_calc_layout.addWidget(self.spin_cpm_window)
        credits_layout.addWidget(cpm_calc_group)
        credits_group.setLayout(credits_layout)
        layout_track.addWidget(credits_group)

        # --- Kills ---
        kills_group = QtWidgets.QGroupBox("Kills Tracking")
        kills_layout = QtWidgets.QVBoxLayout()
        
        self.check_kills = AnimatedToggle("Track Kills (Snapshot on Tab)")
        self.check_kills.setChecked(False)
        self.check_kills.setToolTip("Enables tracking of Kills and KPM based on a snapshot taken when you press TAB.<br>If 'Track Log Data' is also enabled, the kill count is taken from the log at that moment instead of using OCR.")
        kills_layout.addWidget(self.check_kills)
        
        # Tab KPM Calculation Mode
        tab_kpm_calc_group = QtWidgets.QWidget()
        tab_kpm_calc_layout = QtWidgets.QHBoxLayout(tab_kpm_calc_group)
        tab_kpm_calc_layout.setContentsMargins(0, 0, 0, 0)
        
        tab_kpm_calc_layout.addWidget(QtWidgets.QLabel("Tab KPM Mode:"))
        self.combo_tab_kpm_mode = QtWidgets.QComboBox()
        self.combo_tab_kpm_mode.addItems(["Cumulative Average", "Rolling Average"])
        self.combo_tab_kpm_mode.setToolTip("<b>Cumulative:</b> Average KPM over the entire run duration.<br><b>Rolling:</b> Average KPM over the last X seconds (more responsive).")
        self.combo_tab_kpm_mode.currentIndexChanged.connect(self.update_rate_state)
        tab_kpm_calc_layout.addWidget(self.combo_tab_kpm_mode)
        
        self.spin_tab_kpm_window = QtWidgets.QSpinBox()
        self.spin_tab_kpm_window.setRange(60, 3600)
        self.spin_tab_kpm_window.setValue(300)
        self.spin_tab_kpm_window.setSuffix(" s")
        tab_kpm_calc_layout.addWidget(self.spin_tab_kpm_window)
        kills_layout.addWidget(tab_kpm_calc_group)
        kills_group.setLayout(kills_layout)
        layout_track.addWidget(kills_group)

        # --- Logs ---
        logs_group = QtWidgets.QGroupBox("Log Tracking (EE.log)")
        logs_layout = QtWidgets.QVBoxLayout()
        
        self.check_logs = AnimatedToggle("Track Log Data")
        self.check_logs.setStyleSheet("color: red; font-weight: bold;")
        self.check_logs.setChecked(False)
        self.check_logs.setToolTip("Reads Warframe's EE.log file in real-time to track enemy spawns, and other game events.<br>This provides highly accurate, continuous data for KPM, ally counts (for Effigy), and Acolyte spawns.<br>")
        logs_layout.addWidget(self.check_logs)
        
        # Add Log KPM Plot Option
        self.check_add_log_kpm = AnimatedToggle("Plot KPM (Continuous from Log)")
        self.check_add_log_kpm.setToolTip("Adds a separate plot showing the continuous KPM calculated from the log file.<br>This is useful for comparing against the snapshot-based KPM.")
        logs_layout.addWidget(self.check_add_log_kpm)

        # Log KPM Calculation Mode
        kpm_calc_group = QtWidgets.QWidget()
        kpm_calc_layout = QtWidgets.QHBoxLayout(kpm_calc_group)
        kpm_calc_layout.setContentsMargins(0, 0, 0, 0)
        
        kpm_calc_layout.addWidget(QtWidgets.QLabel("Log KPM Mode:"))
        self.combo_kpm_mode = QtWidgets.QComboBox()
        self.combo_kpm_mode.addItems(["Cumulative Average", "Rolling Average"])
        self.combo_kpm_mode.setToolTip("<b>Cumulative:</b> Average KPM over the entire run duration.<br><b>Rolling:</b> Average KPM over the last X seconds (more responsive to recent activity).")
        self.combo_kpm_mode.currentIndexChanged.connect(self.update_rate_state)
        kpm_calc_layout.addWidget(self.combo_kpm_mode)
        
        self.spin_kpm_window = QtWidgets.QSpinBox()
        self.spin_kpm_window.setRange(10, 600)
        self.spin_kpm_window.setValue(60)
        self.spin_kpm_window.setSuffix(" s")
        self.spin_kpm_window.setToolTip("The time window in seconds for the 'Rolling Average' KPM calculation.")
        kpm_calc_layout.addWidget(self.spin_kpm_window)
        logs_layout.addWidget(kpm_calc_group)
        logs_group.setLayout(logs_layout)
        layout_track.addWidget(logs_group)

        # Personal Best Selection (Moved from Overlay Tab)
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

        self.check_pb_live = AnimatedToggle("Animate PB Progress")
        self.check_pb_live.setChecked(True)
        self.check_pb_live.setToolTip("<b>Checked:</b> The Personal Best line on the graph will be drawn in real-time, growing along with your current run.<br><b>Unchecked:</b> The full PB line will be shown from the start.")
        pb_layout.addWidget(self.check_pb_live)
        
        pb_group.setLayout(pb_layout)
        layout_track.addWidget(pb_group)

        # FPS Checkbox
        self.check_fps = AnimatedToggle("Track FPS (Requires PresentMon.exe)")
        self.check_fps.setChecked(False)
        self.check_fps.setToolTip("Tracks Frames Per Second using PresentMon.exe.<br><b>Requires the tracker to be run as Administrator.</b>")
        layout_track.addWidget(self.check_fps)
        
        layout_track.addStretch()
        self.tabs.addTab(tab_tracking, "Tracking")

        # ================= TAB 3: ALERTS =================
        tab_alerts = QtWidgets.QWidget()
        tab_alerts.setObjectName("TabPage")
        layout_alerts = QtWidgets.QVBoxLayout(tab_alerts)

        # Acolyte Warner (only available if log tracking is on)
        acolyte_group = QtWidgets.QGroupBox("Acolyte Warner")
        acolyte_layout = QtWidgets.QHBoxLayout()
        self.check_acolyte = AnimatedToggle("Enable")
        self.check_acolyte.setToolTip("Flashes a warning on-screen when an Acolyte taunt is detected in the log.<br>Requires 'Track Log Data' to be enabled.")
        self.check_acolyte.toggled.connect(lambda c: self.btn_conf_acolyte.setEnabled(c))
        acolyte_layout.addWidget(self.check_acolyte)
        
        self.btn_conf_acolyte = QtWidgets.QPushButton("Configure...")
        self.btn_conf_acolyte.setEnabled(False)
        self.btn_conf_acolyte.clicked.connect(self.open_acolyte_config)
        acolyte_layout.addWidget(self.btn_conf_acolyte)
        acolyte_group.setLayout(acolyte_layout)
        layout_alerts.addWidget(acolyte_group)

        # Effigy Warner (Moved under Log Tracking)
        effigy_group = QtWidgets.QGroupBox("Effigy Warner")
        effigy_layout = QtWidgets.QHBoxLayout()
        self.check_effigy = AnimatedToggle("Enable")
        self.check_effigy.setToolTip("Flashes a warning when the number of active allies drops below a threshold, which can indicate Chroma's Effigy has been destroyed.<br>Requires 'Track Log Data' to be enabled.")
        self.check_effigy.toggled.connect(lambda c: self.btn_conf_effigy.setEnabled(c))
        effigy_layout.addWidget(self.check_effigy)
        
        self.btn_conf_effigy = QtWidgets.QPushButton("Configure...")
        self.btn_conf_effigy.setEnabled(False)
        self.btn_conf_effigy.clicked.connect(self.open_effigy_config)
        effigy_layout.addWidget(self.btn_conf_effigy)
        effigy_group.setLayout(effigy_layout)
        layout_alerts.addWidget(effigy_group)

        # Sound
        sound_group = QtWidgets.QGroupBox("Audio Alerts")
        sound_layout = QtWidgets.QHBoxLayout()
        self.check_sound = AnimatedToggle("Sound Alert on Scan")
        self.check_sound.setChecked(False)
        self.check_sound.setToolTip("Enables audio cues for events like successful/failed scans and warnings.<br>Click 'Configure Sounds...' to customize.")
        sound_layout.addWidget(self.check_sound)
        self.btn_sound_config = QtWidgets.QPushButton("Configure Sounds...")
        self.btn_sound_config.clicked.connect(self.open_sound_config)
        sound_layout.addWidget(self.btn_sound_config)
        sound_group.setLayout(sound_layout)
        layout_alerts.addWidget(sound_group)
        
        layout_alerts.addStretch()
        self.tabs.addTab(tab_alerts, "Alerts")

        # ================= TAB 4: APPEARANCE =================
        tab_appearance = QtWidgets.QWidget()
        tab_appearance.setObjectName("TabPage")
        layout_appear = QtWidgets.QVBoxLayout(tab_appearance)

        # Background Opacity
        opacity_group = QtWidgets.QGroupBox("Window Background")
        opacity_layout = QtWidgets.QHBoxLayout()
        self.check_transparent_graphs = QtWidgets.QCheckBox("Transparent Graphs")
        self.check_transparent_graphs.setToolTip("If checked, the graph window background will be transparent during the run.\nIf unchecked, it will be a solid dark color.")
        
        # Initialize state (If previously < 99, assume they wanted transparency)
        current_opacity = self.plot_config.get("background_opacity", 100)
        self.check_transparent_graphs.setChecked(current_opacity < 99)
        
        opacity_layout.addWidget(self.check_transparent_graphs)
        opacity_group.setLayout(opacity_layout)
        layout_appear.addWidget(opacity_group)

        # Plot Colors
        colors_group = QtWidgets.QGroupBox("Plot Colors")
        colors_layout = QtWidgets.QGridLayout()
        
        headers = ["Metric", "Line Color", "Axis/Text Color"]
        for col, h in enumerate(headers):
            colors_layout.addWidget(QtWidgets.QLabel(f"<b>{h}</b>"), 0, col)

        self.color_widgets = {}
        plot_metrics = [
            ("cpm", "CPM"), 
            ("creds", "Credits"), 
            ("kpm", "KPM (Tab)"), 
            ("log_kpm", "KPM (Log)"), 
            ("live", "Live Enemies"), 
            ("fps", "FPS")
        ]

        for i, (key, label) in enumerate(plot_metrics):
            row = i + 1
            colors_layout.addWidget(QtWidgets.QLabel(label), row, 0)
            
            btn_line = self.create_color_button(self.plot_config["plots"][key]["line"])
            colors_layout.addWidget(btn_line, row, 1)
            
            btn_axis = self.create_color_button(self.plot_config["plots"][key]["axis"])
            colors_layout.addWidget(btn_axis, row, 2)
            
            self.color_widgets[key] = (btn_line, btn_axis)

        colors_group.setLayout(colors_layout)
        layout_appear.addWidget(colors_group)

        layout_appear.addStretch()
        self.tabs.addTab(tab_appearance, "Appearance")

        # ================= TAB 5: OVERLAY =================
        tab_overlay = QtWidgets.QWidget()
        tab_overlay.setObjectName("TabPage")
        layout_overlay = QtWidgets.QVBoxLayout(tab_overlay)
        
        # Number Overlay
        overlay_group = QtWidgets.QGroupBox("In-Game Overlay")
        overlay_layout = QtWidgets.QHBoxLayout()
        self.check_overlay = AnimatedToggle("Enable Number Overlay")
        self.check_overlay.setToolTip("Displays draggable, resizable numbers (CPM, KPM, etc.) over the game.")
        self.check_overlay.toggled.connect(lambda c: self.btn_conf_overlay.setEnabled(c))
        overlay_layout.addWidget(self.check_overlay)
        
        self.btn_conf_overlay = QtWidgets.QPushButton("Configure Colors/Metrics")
        self.btn_conf_overlay.setEnabled(False)
        self.btn_conf_overlay.clicked.connect(self.open_overlay_config)
        overlay_layout.addWidget(self.btn_conf_overlay)
        overlay_group.setLayout(overlay_layout)
        layout_overlay.addWidget(overlay_group)

        layout_overlay.addStretch()
        self.tabs.addTab(tab_overlay, "Overlay")

        # ================= TAB 6: ADVANCED =================
        tab_advanced = QtWidgets.QWidget()
        tab_advanced.setObjectName("TabPage")
        layout_adv = QtWidgets.QVBoxLayout(tab_advanced)

        # Scan Delay
        layout_adv.addWidget(QtWidgets.QLabel("Scan Delay (sec) [Wait after Tab]:"))
        self.spin_delay = QtWidgets.QDoubleSpinBox()
        self.spin_delay.setRange(0.1, 2.0)
        self.spin_delay.setSingleStep(0.1)
        self.spin_delay.setValue(0.3)
        self.spin_delay.setToolTip("How long to wait (in seconds) after you press TAB before taking a screenshot.<br>Increase if the UI takes longer to fade in.")
        layout_adv.addWidget(self.spin_delay)

        # Cooldown
        layout_adv.addWidget(QtWidgets.QLabel("Cooldown (sec) [Min time between scans]:"))
        self.spin_cooldown = QtWidgets.QDoubleSpinBox()
        self.spin_cooldown.setRange(0.5, 10.0)
        self.spin_cooldown.setSingleStep(0.5)
        self.spin_cooldown.setValue(3.0)
        self.spin_cooldown.setToolTip("The minimum time (in seconds) required between two consecutive TAB scans.<br>Prevents accidental double-scanning.")
        layout_adv.addWidget(self.spin_cooldown)
        
        # Data Recording Rate
        rec_row = QtWidgets.QWidget()
        rec_layout = QtWidgets.QHBoxLayout(rec_row)
        rec_layout.setContentsMargins(0, 0, 0, 0)
        rec_layout.addWidget(QtWidgets.QLabel("Data Recording Rate:"))
        self.combo_rec_rate = QtWidgets.QComboBox()
        self.combo_rec_rate.addItem("Ultra (25ms)", 25)
        self.combo_rec_rate.addItem("High Precision (100ms)", 100)
        self.combo_rec_rate.addItem("Balanced (500ms)", 500)
        self.combo_rec_rate.addItem("Low Resource (1000ms)", 1000)
        self.combo_rec_rate.setToolTip("How often to sample data from the log reader and save a row to the master CSV.<br>• <b>Ultra/High:</b> Smoother live graphs, larger CSV files, higher RAM usage.<br>• <b>Balanced/Low:</b> Less resource intensive, smaller files, but graphs may appear less smooth.<br><i>Note: This only affects data from 'Track Log Data' and 'Track FPS'. OCR data is only recorded on TAB press.</i>")
        rec_layout.addWidget(self.combo_rec_rate)
        layout_adv.addWidget(rec_row)
        
        # Log Update Rate Input
        self.log_rate_container = QtWidgets.QWidget()
        self.log_rate_container.setToolTip("Controls how frequently the live graphs are visually redrawn.<br>Lower values result in smoother-looking plots but use more CPU.<br>This is separate from the 'Data Recording Rate' which controls CSV data.")
        self.log_rate_layout = QtWidgets.QVBoxLayout(self.log_rate_container)
        self.log_rate_layout.setContentsMargins(0, 0, 0, 0)
        
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

        layout_adv.addWidget(self.log_rate_container)
        
        self.check_debug = AnimatedToggle("DEBUG MODE")
        self.check_debug.setChecked(False)
        self.check_debug.setToolTip("Enables detailed logging. Saves screenshots of OCR warnings/failures and a copy of the game's EE.log for the run inside a 'DEBUG_INFO' folder.<br>Useful for troubleshooting.<br><b>Requires 'Track Log Data' to be enabled.</b>")
        layout_adv.addWidget(self.check_debug)
        
        layout_adv.addStretch()
        self.tabs.addTab(tab_advanced, "Advanced")
        
        self.check_logs.toggled.connect(self.update_rate_state)
        self.check_kills.toggled.connect(self.update_rate_state)
        self.check_credits.toggled.connect(self.update_rate_state)
        self.update_rate_state()

        # --- Bottom Buttons ---
        bottom_layout = QtWidgets.QVBoxLayout()
        
        # Start Button
        self.btn_start = QtWidgets.QPushButton("Start Tracker")
        self.btn_start.clicked.connect(self.validate_and_accept)
        self.btn_start.setMinimumHeight(40)
        bottom_layout.addWidget(self.btn_start)
        
        # Add New Config Button
        self.btn_reconfig = QtWidgets.QPushButton("Refresh/Add New Bounding Box")
        self.btn_reconfig.setToolTip("Create a new configuration or edit the current one.")
        self.btn_reconfig.clicked.connect(self.handle_config_button)
        bottom_layout.addWidget(self.btn_reconfig)

        # Import Config Button
        self.btn_import = QtWidgets.QPushButton("Import Config from Previous Version")
        self.btn_import.setToolTip("Select the 'LECTA_SCRIPTS' folder of your previous version to import bounding boxes and settings.")
        self.btn_import.clicked.connect(self.import_old_config)
        bottom_layout.addWidget(self.btn_import)

        main_layout.addLayout(bottom_layout)
        self.setLayout(main_layout)
        
        # Start Update Check
        self.update_checker = UpdateChecker(self.version)
        self.update_checker.sig_update_found.connect(self.show_update_popup)
        self.update_checker.start()

    def create_color_button(self, color):
        btn = QtWidgets.QPushButton()
        btn.setStyleSheet(f"background-color: {color}; border: 1px solid #555;")
        btn.clicked.connect(lambda: self.pick_color(btn))
        return btn

    def pick_color(self, btn):
        color = QtWidgets.QColorDialog.getColor()
        if color.isValid():
            btn.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #555;")

    def show_update_popup(self, tag, title):
        QtWidgets.QMessageBox.information(self, "Update Available", 
                                          f"A new version <b>{tag}</b> is available!<br>"
                                          f"Title: {title}<br><br>"
                                          "Please check the GitHub Releases page.")

    def load_profiles_to_combo(self):
        self.combo_profiles.blockSignals(True)
        self.combo_profiles.clear()
        self.combo_profiles.addItem("Select a Profile...")
        if os.path.exists(self.profiles_file):
            try:
                with open(self.profiles_file, 'r') as f:
                    profiles = json.load(f)
                    self.combo_profiles.addItems(sorted(profiles.keys()))
            except: pass
        self.combo_profiles.blockSignals(False)

    def open_profile_manager(self):
        current = self.get_settings()
        dlg = ProfileManagerDialog(current, self.profiles_file, self)
        dlg.exec_()
        self.load_profiles_to_combo()

    def on_profile_changed(self):
        name = self.combo_profiles.currentText()
        if name == "Select a Profile...": return
        if os.path.exists(self.profiles_file):
            try:
                with open(self.profiles_file, 'r') as f:
                    profiles = json.load(f)
                    if name in profiles:
                        self.apply_settings(profiles[name])
            except Exception as e:
                print(f"Error loading profile: {e}")

    def save_current_profile(self):
        name = self.combo_profiles.currentText()
        if name == "Select a Profile...":
            self.open_profile_manager() # Or prompt for new name
            return
        
        # Confirm overwrite
        reply = QtWidgets.QMessageBox.question(self, "Save Profile", f"Overwrite profile '{name}' with current settings?", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if reply == QtWidgets.QMessageBox.Yes:
            current_settings = self.get_settings()
            try:
                profiles = {}
                if os.path.exists(self.profiles_file):
                    with open(self.profiles_file, 'r') as f:
                        profiles = json.load(f)
                
                profiles[name] = current_settings
                
                with open(self.profiles_file, 'w') as f:
                    json.dump(profiles, f, indent=4)
                
                QtWidgets.QMessageBox.information(self, "Success", f"Profile '{name}' updated.")
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "Error", f"Failed to save profile: {e}")

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

    def open_sound_config(self):
        dlg = SoundConfigDialog(self.sound_config, self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            self.sound_config = dlg.get_config()

    def import_old_config(self):
        src_dir = QtWidgets.QFileDialog.getExistingDirectory(self, "Select 'LECTA_SCRIPTS' Folder")
        if not src_dir:
            return

        # Smart Search: Check root, then check standard subfolders
        candidates = [
            src_dir,
            os.path.join(src_dir, "python_and_required_packages", "LECTA_SCRIPTS"),
            os.path.join(src_dir, "LECTA_SCRIPTS"),
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
                                           "Please make sure you selected the 'LECTA_SCRIPTS' folder containing your .json config files.")
             return

        files_to_copy = [
            "bbox_config_solo.json",
            "bbox_config_duo.json",
            "last_run_settings.json",
            "path_config.json",
            "setup_screenshot_solo.png",
            "setup_screenshot_duo.png",
            "profiles.json",
            "overlay_positions.json"
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
        self.check_add_log_kpm.setEnabled(log_tracking_enabled)
        self.check_debug.setEnabled(log_tracking_enabled)
        if not log_tracking_enabled:
            self.check_debug.setChecked(False)
            self.check_acolyte.setChecked(False)
            self.check_effigy.setChecked(False)
            self.check_add_log_kpm.setChecked(False)
        
        self.combo_cpm_mode.setEnabled(self.check_credits.isChecked())
        is_cpm_rolling = (self.combo_cpm_mode.currentIndex() == 1)
        self.spin_cpm_window.setVisible(is_cpm_rolling)
        self.spin_cpm_window.setEnabled(self.check_credits.isChecked() and is_cpm_rolling)
        
        self.combo_tab_kpm_mode.setEnabled(kills_enabled)
        is_tab_kpm_rolling = (self.combo_tab_kpm_mode.currentIndex() == 1)
        self.spin_tab_kpm_window.setVisible(is_tab_kpm_rolling)
        self.spin_tab_kpm_window.setEnabled(kills_enabled and is_tab_kpm_rolling)
        
        self.combo_kpm_mode.setEnabled(log_tracking_enabled)
        is_log_kpm_rolling = (self.combo_kpm_mode.currentIndex() == 1)
        self.spin_kpm_window.setVisible(is_log_kpm_rolling)
        self.spin_kpm_window.setEnabled(log_tracking_enabled and is_log_kpm_rolling)
        
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
        if not self.check_credits.isChecked() and not self.check_kills.isChecked() and not self.check_logs.isChecked():
            QtWidgets.QMessageBox.warning(self, "Invalid Settings", "You must track at least Credits, Kills, or Log Data.")
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
                    
                    # Check for batch file to preserve environment variables (Embedded version support)
                    bat_path = os.path.abspath("Start_Tracker.bat")
                    if os.path.exists(bat_path):
                        # Relaunch via batch file
                        ctypes.windll.shell32.ShellExecuteW(None, "runas", bat_path, None, os.getcwd(), 1)
                    else:
                        # Fallback for source code version
                        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{os.path.abspath(sys.modules["__main__"].__file__)}"', os.getcwd(), 1)
                    
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
        # Helper to extract color from button stylesheet
        def get_color(btn):
            style = btn.styleSheet()
            if "background-color:" in style:
                return style.split("background-color:")[1].split(";")[0].strip()
            return "#FFFFFF"

        # Update plot_config from UI
        self.plot_config["background_opacity"] = 0 if self.check_transparent_graphs.isChecked() else 100
        for key, (btn_line, btn_axis) in self.color_widgets.items():
            self.plot_config["plots"][key] = {
                "line": get_color(btn_line),
                "axis": get_color(btn_axis)
            }

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
            
            self.apply_settings(data)
        except Exception as e:
            print(f"[Settings] Error loading settings: {e}")

    def apply_settings(self, data):
        if data.get("mode") == "Solo":
            self.radio_solo.setChecked(True)
        else:
            self.radio_duo.setChecked(True)
            
        self.spin_delay.setValue(data.get("scan_delay", 0.3))
        self.spin_cooldown.setValue(data.get("cooldown", 3.0))
        self.check_credits.setChecked(data.get("track_credits", True))
        self.check_high_cpm.setChecked(data.get("show_high_cpm", False))
        self.check_high_cpm.setEnabled(self.check_credits.isChecked())
        self.combo_cpm_mode.setCurrentIndex(1 if data.get("cpm_rolling", False) else 0)
        self.spin_cpm_window.setValue(data.get("cpm_window", 300))
        
        self.check_kills.setChecked(data.get("track_kills", False))
        self.combo_tab_kpm_mode.setCurrentIndex(1 if data.get("tab_kpm_rolling", False) else 0)
        self.spin_tab_kpm_window.setValue(data.get("tab_kpm_window", 300))
        
        self.check_effigy.setChecked(data.get("effigy_warner_enabled", False))
        self.check_on_top.setChecked(data.get("always_on_top", True))
        self.check_sound.setChecked(data.get("use_sound", False))
        self.check_debug.setChecked(data.get("debug_mode", False))
        self.check_logs.setChecked(data.get("track_logs", False))
        
        # Load sound config or reset to defaults if missing (prevents settings leak from previous profile)
        self.sound_config = data.get("sound_config", {
            "scan_success": {"type": "Custom Beep", "freq": 1000, "dur": 150, "vol": 100},
            "scan_fail": {"type": "Custom Beep", "freq": 500, "dur": 200, "vol": 100},
            "acolyte": {"type": "Custom Beep", "freq": 1500, "dur": 100, "vol": 100},
            "effigy": {"type": "Custom Beep", "freq": 1500, "dur": 100, "vol": 100}
        })
        
        self.check_add_log_kpm.setChecked(data.get("add_log_kpm_plot", False))
        self.combo_kpm_mode.setCurrentIndex(1 if data.get("log_kpm_rolling", True) else 0)
        self.spin_kpm_window.setValue(data.get("log_kpm_window", 60))
        self.check_fps.setChecked(data.get("track_fps", False))
        self.check_overlay.setChecked(data.get("use_overlay", False))
        self.check_acolyte.setChecked(data.get("acolyte_warner_enabled", False))
        if "acolyte_config" in data:
            self.acolyte_config = data["acolyte_config"]
        if "effigy_config" in data:
            self.effigy_config = data["effigy_config"]

        if "plot_config" in data:
            self.plot_config = data["plot_config"]
            op = self.plot_config.get("background_opacity", 100)
            self.check_transparent_graphs.setChecked(op < 99)
            plots_cfg = self.plot_config.get("plots", {})
            for key, (btn_line, btn_axis) in self.color_widgets.items():
                if key in plots_cfg:
                    btn_line.setStyleSheet(f"background-color: {plots_cfg[key].get('line', '#FFFFFF')}; border: 1px solid #555;")
                    btn_axis.setStyleSheet(f"background-color: {plots_cfg[key].get('axis', '#FFFFFF')}; border: 1px solid #555;")

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
        
        self.update_rate_state()

    def get_settings(self):
        # Construct plot_config dynamically from UI elements
        current_plot_config = {
            "background_opacity": 0 if self.check_transparent_graphs.isChecked() else 100,
            "plots": {}
        }

        def get_btn_color(btn):
            style = btn.styleSheet()
            if "background-color:" in style:
                return style.split("background-color:")[1].split(";")[0].strip()
            return "#FFFFFF"

        for key, (btn_line, btn_axis) in self.color_widgets.items():
            current_plot_config["plots"][key] = {
                "line": get_btn_color(btn_line),
                "axis": get_btn_color(btn_axis)
            }

        return {
            "mode": "Solo" if self.radio_solo.isChecked() else "Duo",
            "scan_delay": self.spin_delay.value(),
            "cooldown": self.spin_cooldown.value(),
            "track_credits": self.check_credits.isChecked(),
            "show_high_cpm": self.check_high_cpm.isChecked(),
            "cpm_rolling": (self.combo_cpm_mode.currentIndex() == 1),
            "cpm_window": self.spin_cpm_window.value(),
            "track_kills": self.check_kills.isChecked(),
            "tab_kpm_rolling": (self.combo_tab_kpm_mode.currentIndex() == 1),
            "tab_kpm_window": self.spin_tab_kpm_window.value(),
            "effigy_warner_enabled": self.check_effigy.isChecked(),
            "always_on_top": self.check_on_top.isChecked(),
            "use_sound": self.check_sound.isChecked(),
            "debug_mode": self.check_debug.isChecked(),
            "sound_config": self.sound_config,
            "plot_config": current_plot_config,
            "track_logs": self.check_logs.isChecked(),
            "add_log_kpm_plot": self.check_add_log_kpm.isChecked(),
            "log_kpm_rolling": (self.combo_kpm_mode.currentIndex() == 1),
            "log_kpm_window": self.spin_kpm_window.value(),
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