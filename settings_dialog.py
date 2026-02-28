import os
import json
import ctypes
import sys
import shutil
import subprocess
import time
import cv2 as cv
import mss
from screeninfo import get_monitors
from pyqtgraph.Qt import QtWidgets, QtCore, QtGui
from gui_components import AcolyteConfigDialog, EffigyConfigDialog, OverlayConfigDialog, SoundConfigDialog
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

class SettingsDialog(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tracker Settings")
        self.resize(300, 300)
        layout = QtWidgets.QVBoxLayout()

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
        # Default Sound Config
        self.sound_config = {
            "scan_success": {"type": "Custom Beep", "freq": 1000, "dur": 150, "vol": 100},
            "scan_fail": {"type": "Custom Beep", "freq": 500, "dur": 200, "vol": 100},
            "acolyte": {"type": "Custom Beep", "freq": 1500, "dur": 100, "vol": 100},
            "effigy": {"type": "Custom Beep", "freq": 1500, "dur": 100, "vol": 100}
        }

        # --- Profile Selection UI ---
        profile_group = QtWidgets.QGroupBox("Settings Profiles")
        profile_layout = QtWidgets.QHBoxLayout()
        
        self.combo_profiles = QtWidgets.QComboBox()
        self.load_profiles_to_combo()
        self.combo_profiles.currentIndexChanged.connect(self.on_profile_changed)
        profile_layout.addWidget(self.combo_profiles)
        
        self.btn_manage_profiles = QtWidgets.QPushButton("Manage Profiles")
        self.btn_manage_profiles.clicked.connect(self.open_profile_manager)
        profile_layout.addWidget(self.btn_manage_profiles)
        
        profile_group.setLayout(profile_layout)
        layout.addWidget(profile_group)

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

        sound_layout = QtWidgets.QHBoxLayout()
        self.check_sound = QtWidgets.QCheckBox("Sound Alert on Scan")
        self.check_sound.setChecked(False)
        self.check_sound.setToolTip("Plays a short 'beep' sound to confirm a successful scan has been processed.")
        sound_layout.addWidget(self.check_sound)
        self.btn_sound_config = QtWidgets.QPushButton("Configure Sounds...")
        self.btn_sound_config.clicked.connect(self.open_sound_config)
        sound_layout.addWidget(self.btn_sound_config)
        layout.addLayout(sound_layout)

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
        self.check_kills.setChecked(data.get("track_kills", False))
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
            "sound_config": self.sound_config,
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