import os
import sys

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame
pygame.init() # Initialize all imported pygame modules

# Ensure local modules in the same directory are found
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import easyocr

import pyqtgraph as pg #pip install pyqtgraph and pip install pyQt5
from pyqtgraph.Qt import QtWidgets, QtCore, QtGui
from settings_dialog import SettingsDialog
from tracker import WarframeTracker

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
    
    # Modern Dark Stylesheet
    app.setStyleSheet("""
        QMainWindow, QDialog, QWidget {
            background-color: #1e1e1e;
            color: #f0f0f0;
            font-family: "Segoe UI", "Arial", sans-serif;
            font-size: 10pt;
        }
        QTabWidget::pane {
            border: 1px solid #333333;
            background: #252526;
            border-radius: 5px;
            margin-top: -1px;
        }
        QTabBar::tab {
            background: #1e1e1e;
            color: #888888;
            padding: 8px 20px;
            border-top-left-radius: 5px;
            border-top-right-radius: 5px;
            border: 1px solid transparent;
        }
        QTabBar::tab:selected {
            background: #252526;
            color: #ffffff;
            border-bottom: 2px solid #2ea043;
        }
        QTabBar::tab:hover {
            background: #2d2d2d;
            color: #cccccc;
        }
        QPushButton {
            background-color: #2ea043;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
        }
        QPushButton:hover { background-color: #3fb950; }
        QPushButton:pressed { background-color: #238636; }
        QPushButton:disabled { background-color: #333333; color: #888888; }
        QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
            background-color: #333333; border: 1px solid #444444; border-radius: 4px; color: white; padding: 5px;
        }
        QGroupBox {
            border: 1px solid #444444; border-radius: 5px; margin-top: 20px; font-weight: bold;
        }
        QGroupBox::title {
            subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; color: #2ea043;
        }
        QListWidget { background-color: #252526; border: 1px solid #333333; border-radius: 4px; color: white; }
        QScrollArea { border: none; background: transparent; }
    """)
    
    pg.setConfigOption('background', '#191919')
    pg.setConfigOption('foreground', '#E6E6E6')

    APP_VERSION = "v1.5.1"
    # Show Settings Dialog
    dialog = SettingsDialog(version=APP_VERSION)
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