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

    APP_VERSION = "v1.5"
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