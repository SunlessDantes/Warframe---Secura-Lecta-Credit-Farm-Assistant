import time
import re
import os
import threading

ACOLYTE_MAP = {
    "Duellist": {"name": "Violence", "duration": 5.1},
    "Rogue":    {"name": "Mania",    "duration": 5.1},
    "Control":  {"name": "Torment",  "duration": 5.1},
    "Heavy":    {"name": "Malice",   "duration": 5.1},
}
SCREAM_ACOLYTE_NAME = "Acolyte" # Generic for Misery/Angst
SCREAM_DURATION = 11.5

class LogReader:
    def __init__(self, log_path):
        self.log_path = log_path
        self.live_enemies = 0
        self.total_spawned = 0
        self.ally_live = 0
        self.running = False
        self.thread = None
        self.triggered_acolytes = [] # Changed from bool to list
        self.general_events = [] # Queue for other events (Death, etc.)
        self.lock = threading.Lock() # For thread-safe list access
        self.last_acolyte_warning_time = 0
        
        # Regex to capture numbers after 'Live' and 'Spawned'
        # Example: OnAgentCreated /Npc/Lancer Live 31 Spawned 53 Ticking 31
        self.live_pattern = re.compile(r"Live\s+(\d+)")
        self.spawned_pattern = re.compile(r"Spawned\s+(\d+)")
        self.ally_live_pattern = re.compile(r"AllyLive\s+(\d+)")

        self.acolyte_taunt_pattern = re.compile(r"/Lotus/Sounds/Dialog/Taunts/Acolytes/(?P<tag>Duellist|Rogue|Control|Heavy)AcolyteTaunt")
        self.acolyte_scream_pattern = re.compile(r"ScreamDebuffAttachProj")
        self.acolyte_defeat_pattern = re.compile(r"/Lotus/Sounds/Dialog/Taunts/Acolytes/(?P<tag>Duellist|Rogue|Control|Heavy)AcolyteDefeat")
    def start(self):
        """Starts the monitoring thread."""
        if self.thread is not None and self.thread.is_alive():
            return
        
        self.running = True # Corrected from False to True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """Stops the monitoring thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)

    def _monitor_loop(self):
        if not os.path.exists(self.log_path):
            print(f"Log file not found: {self.log_path}")
            self.running = False
            return

        print(f"[LogReader] Monitoring started: {self.log_path}")
        try:
            with open(self.log_path, 'r', encoding='utf-8', errors='ignore') as f:
                # Read the last 20KB to get the current state if the game is already running
                f.seek(0, os.SEEK_END)
                file_size = f.tell()
                f.seek(max(0, file_size - 20480)) # Go back 20KB
                
                while self.running:
                    current_pos = f.tell()
                    line = f.readline()
                    if not line:
                        time.sleep(0.05)
                        continue
                    
                    # Ensure we have a complete line (ends with newline)
                    # This prevents reading a line mid-write and failing the regex
                    if not line.endswith('\n'):
                        f.seek(current_pos)
                        time.sleep(0.05)
                        continue
                    
                    self._process_line(line)
        except Exception as e:
            print(f"Error in LogReader: {e}")
            self.running = False

    def _process_line(self, line):
        # Acolyte Checks first
        taunt_match = self.acolyte_taunt_pattern.search(line)
        if taunt_match:
            tag = taunt_match.group("tag")
            if tag in ACOLYTE_MAP:
                now = time.time()
                if now - self.last_acolyte_warning_time < 180: # 3 minute cooldown
                    return
                self.last_acolyte_warning_time = now
                
                acolyte = ACOLYTE_MAP[tag]
                print(f"[LogReader] ACOLYTE WARNING DETECTED: {acolyte['name']}")
                with self.lock:
                    self.triggered_acolytes.append((acolyte['name'], acolyte['duration']))
                return # Don't process other things on this line

        if self.acolyte_scream_pattern.search(line):
            now = time.time()
            if now - self.last_acolyte_warning_time < 180:
                return
            self.last_acolyte_warning_time = now
            print(f"[LogReader] ACOLYTE WARNING DETECTED: {SCREAM_ACOLYTE_NAME} (Scream)")
            with self.lock:
                self.triggered_acolytes.append((SCREAM_ACOLYTE_NAME, SCREAM_DURATION))
            return

        # Acolyte Death (Defeat)
        defeat_match = self.acolyte_defeat_pattern.search(line)
        if defeat_match:
            tag = defeat_match.group("tag")
            if tag in ACOLYTE_MAP:
                name = ACOLYTE_MAP[tag]['name']
                with self.lock:
                    self.general_events.append(f"{name} Dead")

        if "OnAgentCreated" in line:
            live_match = self.live_pattern.search(line)
            if live_match:
                self.live_enemies = int(live_match.group(1))
            
            spawned_match = self.spawned_pattern.search(line)
            if spawned_match:
                self.total_spawned = int(spawned_match.group(1))
            
            ally_match = self.ally_live_pattern.search(line)
            if ally_match:
                self.ally_live = int(ally_match.group(1))

    def get_stats(self):
        """Returns a tuple (live_enemies, total_spawned, ally_live)."""
        return self.live_enemies, self.total_spawned, self.ally_live
    
    def check_and_clear_acolyte_warning(self):
        """Pops one acolyte warning from the queue if available."""
        with self.lock:
            if self.triggered_acolytes:
                return self.triggered_acolytes.pop(0)
        return None

    def check_and_clear_general_events(self):
        """Pops one general event from the queue if available."""
        with self.lock:
            if self.general_events:
                return self.general_events.pop(0)
        return None
