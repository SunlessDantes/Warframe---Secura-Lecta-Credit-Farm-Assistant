# Warframe Lecta Tracker (CPM/KPM/OCR)

A Python-based overlay and tracker for Warframe that monitors Credits Per Minute (CPM), Kills Per Minute (KPM), Enemy Data  using Optical Character Recognition and EE.log reading.

## Safety Disclaimer

This project is strictly a Quality of Life (QoL) and analytics tool.

* **No Code Interference**: It does not modify, inject into, or interfere with Warframe's memory or internal code in any way. (EE.log is strictly read-only).
* **No Automation**: This tool does not use any macros, automated keystrokes, or botting to play the game or complete tasks for you.
* **No Unfair Advantage**: It simply uses standard OCR (Optical Character Recognition) to read the screen and parses local log files to plot statistics, allowing players to analyze and improve their own performance.

## Features
- **Live Overlay:** Draggable stats (Credits,CPM, current ammount of alive enemies, KPM, FPS) over the game.
- **Real-time Graphs:** Visualizes your farming efficiency.
- **OCR Tracking:** Reads credits/kills from the Mission Progress screen (Tab).
- **Log Analysis (Real-time):** Reads `EE.log` to track:
    *   Live Enemy Count
    *   Live KPM (as alternative to log reading)
    *   Total Enemies Spawned
    *   Ally/Effigy Status
- **FPS Tracker:** Uses PresentMon for an FPS plot.
- **Live PB comparing:** Upload a run that will plot live along your data to see how much better/worse you perform.
- **Acolyte Warner:** Flashes a warning on-screen when an Acolyte is about to spawn, showing its name and a countdown.
- **Effigy Replace Warner** When Effigy dissapeares (dead or no energy) a warning will be flashed to replace it.
- **Sound Alerts:** Customizable sounds (Beeps or MP3/WAV) for successful scans, failures, and warnings.
- **Flexible Metrics:** Choose between **Cumulative** (Run Average) or **Rolling** (Current Pace) calculations for CPM and KPM.
---

## Example
<a href="https://www.youtube.com/watch?v=" target="_blank">
  <img src="https://img.youtube.com/vi//maxresdefault.jpg" alt="Warframe Lecta Tracker Demo" width="100%" />
</a>

*Click the image above to watch the demo video.*



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
   *(Or run `python main.py` directly)*

## Loading your Configurations into a new Version
**Recommended Method:**
1. Launch the new version of the tracker.
2. In the Settings menu, click the **"Import Config from Previous Version"** button (at the bottom).
3. Select the **Main Folder** of your previous version (the folder containing `Start_Tracker.bat`).
4. The tracker will automatically find and copy your bounding boxes, settings, and screenshots.

**Manual Method:**
Copy all `.json` and `.png` files from your old `python_and_required_packages\LECTA_SCRIPTS` folder and paste them into the same location in the new version.

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
3. Follow the on-screen instructions to draw boxes around the "Credits" text and the 5 possible credit values in the Mission Progress screen.

* Example Bounding boxes:
<img src="Bbox_example.png" alt="Bounding Box Example" width="100%" />

## Cumulative vs. Rolling Average
In the settings, you can choose how **CPM**, **Tab KPM**, and **Log KPM** are calculated.

*   **Cumulative Average (Default):** Calculates the average over the *entire* run so far.
    *   *Why use it?* It provides a stable, smooth line that represents your overall session performance. It is less affected by short pauses (like looting or Acolyte fights).
    *   *Downside:* Late in a long run (e.g., 40+ mins), it becomes very slow to react. If your efficiency drops significantly at minute 45, the cumulative average will barely move because it is "weighted down" by the previous 45 minutes of good data.

*   **Rolling Average:** Calculates the average over a specific time window (e.g., "Last 5 Minutes").
    *   *Why use it?* It shows your *current* pace. If you stop killing for 1 minute, the graph will drop immediately. This is excellent for testing new strategies mid-run or spotting immediate efficiency drops.
    *   *Downside:* The graph can be "jumpy" or volatile. For CPM/Tab KPM, if you don't scan frequently enough within the window, the data might be less accurate.



## Understanding the Logs
For a detailed explanation of the CSV data, runtime logs, and debug files, please read **Log_Guide.md** included in the release folder.

## Requirements
- Warframe must be running on the **Primary Monitor**.
- Interface Scale in Warframe should be consistent (default 100 recommended).
- **PresentMon.exe** must be in the ``LECTA_SCRIPTS`` for FPS tracking.
  - *Note:* This project uses **PresentMon v1.6.0** (Legacy). Newer versions of Intel PresentMon have changed their output format and command-line arguments, which are not compatible with this tracker's parsing logic. The correct version is included in the release.


## General Notes and Feature explenation
* `EE.log` is only read from, no injection is happening. You can uncheck that box and the script will not read the data. The log features will only work if you are the host. ``EE.log`` is different for Client.
* The Acolyte Warner relies on reading `EE.log` to detect specific pre-spawn log entries. It can identify Violence, Mania, Torment, and Malice by name. For Misery and Angst, identification happens via the Scream. (Therefore the warning for Misery and Angst happens earlier than for the other Acolytes)
* Tracking the FPS requires `PresentMon.exe` to be run as Administrator hence you will be asked to rerun as Administrator.
* ``EE.log`` based KPM works best in faster paced enviroments, so no earth non SP capture e.g. is recommended. Though this is for Secura LEcta Credit farm, where enemies spawn constantly. 
* You can load already recorded runs (`master_run_log.csv`) from yourself or others into the tracker, this will add plots when you start so you can compare yourself to another Run (e.g. your own PB). You have the option to either let the PB run plot itself along with your data (recommended for readability and visability) or you can plot the entire PB plot and just have your current run plot live. Either way the `run_plots.png` and `enemy_plots.png` will include both runs across your recorded time window.


