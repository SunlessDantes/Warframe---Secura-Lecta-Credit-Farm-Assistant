# Warframe Lecta Tracker (CPM/KPM/OCR)

A Python-based overlay and tracker for Warframe that monitors Credits Per Minute (CPM), Kills Per Minute (KPM), Enemy Data  using Optical Character Recognition and EE.log reading.

## Features
- **Live Overlay:** Draggable stats (Credits,CPM, current ammount of alive enemies, KPM, FPS) over the game.
- **Real-time Graphs:** Visualizes your farming efficiency.
- **OCR Tracking:** Reads credits/kills from the Mission Progress screen (Tab).
- **Log Tracking:** Optionally reads `EE.log` for 100% accurate kill counts and spawn rates.
- **FPS Tracker:** Uses PresentMon for accurate FPS analysis.
- **Live PB comparing** uploading a run that will plot live along your data to see how much better/worse you perform.

---

## Example
[![Watch the video](https://img.youtube.com/vi/7BJbUHTeVs8/hqdefault.jpg)](https://www.youtube.com/embed/<VIDEO_ID>)
https://www.youtube.com/watch?v=7BJbUHTeVs8
[<img src="https://img.youtube.com/vi/7BJbUHTeVs8/hqdefault.jpg" width="600" height="300"
/>](https://www.youtube.com/embed/7BJbUHTeVs8)



## How to Download & Run

### Option 1: Embeddable folder for easy use
**Python and packages are embedded within**
1. Go to the Releases page.
2. Download the latest `.zip` file.
3. Extract it anywhere.
4. Run `Start_Tracker.bat`.

### Option 2: Source Code
If you have Python installed and want to run the raw scripts/edit the code yourself:

1. Clone this repository or download the Source Code zip.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the launcher:
   ```bash
   Start_Tracker.bat
   ```
   *(Or run `python CPM_OOP.py` directly)*

---

## Controls
| Key | Action |
| :--- | :--- |
| **F8** | Start Run Timer |
| **TAB** | Scan Credits (Open Mission Progress) |
| **F9** | Toggle Bounding Box Overlay |
| **F10** | Save Data & End Run |

## First Time Setup
1. When you first launch the tracker, it will ask you to select a folder to save your run data. In that Folder you will find data of the run `master_run_log.csv` and plots
2. It will then launch the **Bounding Box Setup**.
3. Follow the on-screen instructions to draw boxes around the "Credits" text and the 5 possible credit values in the Mission Progress screen. (You can draw bad bbox's since there is a bbox editor which is more user friendly)

## Requirements
- Warframe must be running on the **Primary Monitor**.
- Interface Scale in Warframe should be consistent (default 100 recommended).
- **PresentMon.exe** must be in the folder for FPS tracking.
  - *Note:* This project uses **PresentMon v1.6.0** (Legacy). Newer versions of Intel PresentMon have changed their output format and command-line arguments, which are not compatible with this tracker's parsing logic. The correct version is included in the release.


## General Notes
* `EE.log` is only read from, no injection is happening. You can uncheck that box and the script will not read the data.
* Tracking the FPS requires `PresentMon.exe` to be run as Administrator hence you will be asked to rerun as Administrator.