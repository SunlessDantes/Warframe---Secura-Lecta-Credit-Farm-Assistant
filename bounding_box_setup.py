import os
import sys
import time
import json
import cv2 as cv
import mss
import numpy as np
from screeninfo import get_monitors
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore, QtGui

class ConfigEditor(QtWidgets.QDialog):
    def __init__(self, images, config_data, monitor_offset, screenshot_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Config Editor - Drag/Resize Boxes")
        self.resize(1200, 800)
        self.image = images # Just one image now
        self.screenshot_path = screenshot_path
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
        
        self.img_item = pg.ImageItem()
        self.update_image_display()
        self.vb.addItem(self.img_item)
        
        self.rois = {}
        self.labels = []
        
        self.load_boxes()
        
        # Tools Layout
        tools_layout = QtWidgets.QHBoxLayout()

        self.btn_add = QtWidgets.QPushButton("Add Missing Item...")
        self.btn_add.clicked.connect(self.show_add_menu)
        tools_layout.addWidget(self.btn_add)
        
        self.btn_retake = QtWidgets.QPushButton("Retake Background Image")
        self.btn_retake.clicked.connect(self.retake_background)
        tools_layout.addWidget(self.btn_retake)
        self.layout.addLayout(tools_layout)

        self.btn_save = QtWidgets.QPushButton("Save Changes")
        self.btn_save.clicked.connect(self.save_and_close)
        self.layout.addWidget(self.btn_save)

    def update_image_display(self):
        img = self.image
        if img is None:
            self.img_item.clear()
            return
            
        if img.ndim == 2:
            img_rgb = cv.cvtColor(img, cv.COLOR_GRAY2RGB)
        elif img.shape[2] == 4:
            img_rgb = cv.cvtColor(img, cv.COLOR_BGRA2RGB)
        else:
            img_rgb = cv.cvtColor(img, cv.COLOR_BGR2RGB)
            
        img_t = np.transpose(img_rgb, (1, 0, 2))
        self.img_item.setImage(img_t)

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

    def load_boxes(self):
        if 'scan_area' in self.data:
            self.add_roi("Scan Area", self.data['scan_area'], 'g')
        if 'credit_positions' in self.data:
            for i, box in enumerate(self.data['credit_positions']):
                self.add_roi(f"Credit {i+1}", box, 'y')
        if self.data.get('scan_area_2'):
            self.add_roi("Scan Area 2", self.data['scan_area_2'], 'c')
        if self.data.get('credit_positions_2'):
            for i, box in enumerate(self.data['credit_positions_2']):
                self.add_roi(f"Credit 2-{i+1}", box, 'm')
        if self.data.get('track_kills') and 'kills' in self.data and self.data['kills']:
             self.add_roi("Kills", self.data['kills'], 'r')

    def show_add_menu(self):
        menu = QtWidgets.QMenu(self)
        
        # Check what is missing
        if "Kills" not in self.rois:
            menu.addAction("Kills Box", lambda: self.create_default_roi("Kills", 'r'))
            
        if "Scan Area 2" not in self.rois:
            menu.addAction("Scan Area 2 (Backup)", lambda: self.create_default_roi("Scan Area 2", 'c'))
            
        # Check for Credit sets
        has_creds_1 = any(f"Credit {i}" in self.rois for i in range(1, 6))
        if not has_creds_1:
            menu.addAction("Credit Positions (Primary - 5 boxes)", lambda: self.create_credit_set("", 'y'))
            
        has_creds_2 = any(f"Credit 2-{i}" in self.rois for i in range(1, 6))
        if not has_creds_2:
            menu.addAction("Credit Positions (Secondary - 5 boxes)", lambda: self.create_credit_set("2-", 'm'))

        if not menu.isEmpty():
            menu.exec_(QtGui.QCursor.pos())
        else:
            QtWidgets.QMessageBox.information(self, "Info", "All configurable items are already present.")

    def create_default_roi(self, name, color):
        # Place in center of view
        vr = self.vb.viewRect()
        cx = vr.center().x()
        cy = vr.center().y()
        w, h = 100, 50
        
        abs_l = int(cx + self.offset_x - w/2)
        abs_t = int(cy + self.offset_y - h/2)
        
        self.add_roi(name, [abs_l, abs_t, abs_l+w, abs_t+h], color)

    def create_credit_set(self, prefix, color):
        # Create 5 boxes horizontally distributed
        vr = self.vb.viewRect()
        start_x = vr.left() + 50
        y = vr.center().y()
        w, h = 40, 30
        gap = 10
        
        for i in range(1, 6):
            name = f"Credit {prefix}{i}"
            # Calculate absolute
            rel_x = start_x + (i-1)*(w+gap)
            abs_l = int(rel_x + self.offset_x)
            abs_t = int(y + self.offset_y)
            
            self.add_roi(name, [abs_l, abs_t, abs_l+w, abs_t+h], color)

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
        
        # Rebuild Credit Positions 1
        new_creds = []
        for i in range(1, 6):
            name = f"Credit {i}"
            if name in self.rois:
                new_creds.append(get_abs_coords(self.rois[name]))
        if new_creds:
            self.data['credit_positions'] = new_creds
        
        if "Scan Area 2" in self.rois:
            self.data['scan_area_2'] = get_abs_coords(self.rois["Scan Area 2"])
        
        # Rebuild Credit Positions 2
        new_creds_2 = []
        for i in range(1, 6):
            name = f"Credit 2-{i}"
            if name in self.rois:
                new_creds_2.append(get_abs_coords(self.rois[name]))
        if new_creds_2:
            self.data['credit_positions_2'] = new_creds_2

        if "Kills" in self.rois:
            self.data['kills'] = get_abs_coords(self.rois["Kills"])
        self.accept()

    def retake_background(self):
        original_text = self.btn_retake.text()
        
        # Countdown while visible
        for i in range(3, 0, -1):
            self.btn_retake.setText(f"Capturing in {i}...")
            for _ in range(10):
                QtWidgets.QApplication.processEvents()
                time.sleep(0.1)
                if not self.isVisible(): return

        self.btn_retake.setText("Capturing...")
        QtWidgets.QApplication.processEvents()
        
        # Hide briefly for the actual capture
        self.hide()
        QtWidgets.QApplication.processEvents()
        time.sleep(0.2)

        try:
            with mss.mss() as sct:
                # Try to find the monitor matching our offsets to get correct dimensions
                monitor = None
                for m in sct.monitors[1:]:
                    if m["left"] == self.offset_x and m["top"] == self.offset_y:
                        monitor = m
                        break
                
                if monitor is None:
                    w, h = 1920, 1080 # Fallback
                    if self.image is not None:
                        h, w = self.image.shape[:2]
                    monitor = {"left": self.offset_x, "top": self.offset_y, "width": w, "height": h}
                
                img_np = np.array(sct.grab(monitor))
                
                # Update internal image
                self.image = img_np
                self.update_image_display()
                
                if self.screenshot_path:
                    cv.imwrite(self.screenshot_path, img_np)
                    print(f"Screenshot updated: {self.screenshot_path}")
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Error", f"Failed to retake screenshot: {e}")
        
        self.show()
        self.btn_retake.setText(original_text)

    def keyPressEvent(self, event):
        if event.key() in (QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return):
            self.accept()
        elif event.key() == QtCore.Qt.Key_Escape:
            super().keyPressEvent(event)

def get_primary_monitor():
    primary_x, primary_y = 0, 0
    for m in get_monitors():
        if m.is_primary:
            primary_x, primary_y = m.x, m.y
            break
            
    monitor = mss.mss().monitors[1] # Fallback
    for m in mss.mss().monitors[1:]:
        if m["left"] == primary_x and m["top"] == primary_y:
            monitor = m
            break
    return monitor

def take_screenshot(monitor, save_path, message):
    print(f"\n{message}")
    print("Switch to Warframe now! Taking screenshot in 4 seconds...")
    time.sleep(4)
    
    with mss.mss() as sct:
        img = np.array(sct.grab(monitor))
        
    cv.imwrite(save_path, img)
    print(f"Screenshot saved: {save_path}")
    return img

def save_config(config_path, data):
    try:
        with open(config_path, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"Configuration saved to {config_path}")
    except Exception as e:
        print(f"Error saving config: {e}")

def main():
    app = QtWidgets.QApplication.instance()
    if app is None:
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
        app = QtWidgets.QApplication([])

    # Dark Theme for Editor
    pg.setConfigOption('background', '#191919')
    pg.setConfigOption('foreground', '#E6E6E6')

    monitor = get_primary_monitor()

    application_path = os.path.dirname(os.path.abspath(__file__))

    print("\n========================================")
    print("   Warframe Bounding Box Setup Wizard")
    print("========================================")
    print("This tool will help you define the screen areas the tracker needs to see.")
    print("We will take a screenshot, then open an editor for you to draw boxes.")
    print("========================================\n")
    
    setup_mode = "Solo"
    while True:
        mode_in = input("Is this for Solo or Duo setup? [s/d]: ").strip().lower()
        if mode_in in ['s', 'solo']:
            setup_mode = "Solo"
            break
        elif mode_in in ['d', 'duo']:
            setup_mode = "Duo"
            break
        print("Invalid input. Please enter 's' or 'd'.")

    # Set config filename based on mode
    config_filename = "bbox_config_solo.json" if setup_mode == "Solo" else "bbox_config_duo.json"
    config_path = os.path.join(application_path, config_filename)
    
    # Set screenshot filename based on mode
    screenshot_filename = "setup_screenshot_solo.png" if setup_mode == "Solo" else "setup_screenshot_duo.png"
    screenshot_path = os.path.join(application_path, screenshot_filename)

    # --- Step 1: Capture TAB Menu ---
    print("\n--- Step 1: Capture Mission Progress (TAB) ---")
    print("Open Warframe. Pause/Solo mode recommended.")
    print("Press and HOLD TAB (or open the menu) so the 'Credits' and numbers are visible.")
    input("Press Enter when ready to capture in 4 seconds...")
    img_tab = take_screenshot(monitor, screenshot_path, "Captured TAB menu.")

    # --- Step 3: Open Editor ---
    print("\nOpening Config Editor...")
    
    # Load existing config or create template
    data = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                data = json.load(f)
        except: pass
    
    if not data:
        data = {
        'setup_mode': setup_mode,
        'scan_area': [0, 0, 100, 100], # Dummy defaults
        'credit_positions': [],
        'track_kills': False
    }

    editor = ConfigEditor(img_tab, data, (monitor['left'], monitor['top']), screenshot_path)
    if editor.exec_() == QtWidgets.QDialog.Accepted:
        save_config(config_path, editor.data)
        print("Setup complete.")
    else:
        print("Setup cancelled.")

if __name__ == "__main__":
    main()
