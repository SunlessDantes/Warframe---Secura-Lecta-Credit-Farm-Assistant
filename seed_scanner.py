import os
import re
import sys
import csv
from datetime import datetime, timezone


YOUR_NAME = "SilberKomet"

def get_ee_log_path():
    # Standard location for Warframe EE.log
    return os.path.expandvars(r"%LOCALAPPDATA%\Warframe\EE.log")

def scan_and_save_seed():
    log_path = get_ee_log_path()
    
    # Setup output directory and file
    base_dir = os.path.dirname(os.path.abspath(__file__))
    seeds_dir = os.path.join(base_dir, "MAP_SEEDS")
    os.makedirs(seeds_dir, exist_ok=True)
    seeds_file = os.path.join(seeds_dir, "seeds.csv")

    if not os.path.exists(log_path):
        print(f"Error: EE.log not found at {log_path}")
        return

    # Regex Patterns
    seed_pattern = re.compile(r"/Lotus/Levels/Proc/.*/(?P<seed>[^/]+)\.lp")
    
    # 54.920 Script [Info]: ThemedSquadOverlay.lua: Mission name: Titan (Saturn) - THE STEEL PATH
    mission_name_overlay_pattern = re.compile(r"Script \[Info\]: ThemedSquadOverlay\.lua: Mission name: (?P<name>.*)")
    
    # 31.819 Script [Info]: MapRedux.lua: MapRedux::NodeRollOver SolNode96 - TITAN
    mission_name_rollover_pattern = re.compile(r"Script \[Info\]: MapRedux\.lua: MapRedux::NodeRollOver .* - (?P<name>.*)")
    
    # missionType=MT_SURVIVAL
    mission_type_pattern = re.compile(r"missionType=(?P<type>MT_[A-Z0-9_]+)")
    
    last_seed = None
    last_mission_name = "Unknown"
    last_is_sp = False
    last_mission_type = "Unknown"

    try:
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                # Check for Seed
                seed_match = seed_pattern.search(line)
                if seed_match:
                    last_seed = seed_match.group("seed")
                
                # Check for Mission Name (Overlay - Preferred)
                overlay_match = mission_name_overlay_pattern.search(line)
                if overlay_match:
                    raw_name = overlay_match.group("name").strip()
                    if " - THE STEEL PATH" in raw_name:
                        last_mission_name = raw_name.replace(" - THE STEEL PATH", "").strip()
                        last_is_sp = True
                    else:
                        last_mission_name = raw_name
                        last_is_sp = False
                
                # Check for Mission Name (Rollover - Fallback/Non-SP)
                # Only use if we haven't seen an overlay line more recently? 
                # Actually, since we read top-to-bottom, we just update. 
                # However, Overlay usually happens AFTER Rollover (during load), so it will overwrite correctly.
                rollover_match = mission_name_rollover_pattern.search(line)
                if rollover_match:
                    # Rollover doesn't indicate SP, so assume False or keep previous? 
                    # Usually rollover implies we are in nav, so reset SP to False.
                    last_mission_name = rollover_match.group("name").strip()
                    last_is_sp = False

                # Check for Mission Type
                type_match = mission_type_pattern.search(line)
                if type_match:
                    last_mission_type = type_match.group("type")

    except Exception as e:
        print(f"Error reading log: {e}")
        return

    if last_seed:
        print(f"Found seed: {last_seed}")
        print(f"Mission: {last_mission_name} | SP: {last_is_sp} | Type: {last_mission_type}")
        
        try:
            file_exists = os.path.exists(seeds_file)
            with open(seeds_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["Mission Name", "Steel Path", "Mission Type", "Seed", "Timestamp (UTC)", "Added By"])
                
                current_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                writer.writerow([last_mission_name, last_is_sp, last_mission_type, last_seed, current_time, YOUR_NAME])
                
            print(f"Seed appended to {seeds_file}")
        except Exception as e:
            print(f"Error writing to file: {e}")
    else:
        print("No map seed found in EE.log.")

def main():
    print("--- Warframe Map Seed Scanner ---")
    while True:
        scan_and_save_seed()
        
        while True:
            user_input = input("scan again [y/n]: ").strip().lower()
            if user_input == 'y':
                break
            elif user_input == 'n':
                sys.exit()
            # If invalid input, loop asks again

if __name__ == "__main__":
    main()