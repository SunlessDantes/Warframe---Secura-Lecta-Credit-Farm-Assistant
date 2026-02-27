import os
import shutil
from datetime import datetime

def main():
    # Define paths
    source_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(source_dir)
    
    # Create a timestamped output folder in the project root
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    patch_dir_name = f"Branch_Patch_{timestamp}"
    output_dir = os.path.join(project_root, patch_dir_name)
    
    # The structure inside the patch
    lecta_scripts_dest = os.path.join(output_dir, "LECTA_SCRIPTS")
    
    # Create directories
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(lecta_scripts_dest)
    
    print(f"Creating Branch Patch in: {output_dir}")

    # 1. Copy Start_Tracker.bat (if modified)
    bat_file = "Start_Tracker.bat"
    src_bat = os.path.join(source_dir, bat_file)
    if os.path.exists(src_bat):
        shutil.copy2(src_bat, os.path.join(output_dir, bat_file))
        print(f"Copied {bat_file}")
    else:
        print(f"Warning: {bat_file} not found in Source. Make sure to run create_launcher.py if missing.")

    # 2. Files to copy to LECTA_SCRIPTS
    # Core Code
    core_files = [
        "CPM_OOP.py",
        "bounding_box_setup.py",
        "fps_tracker.py",
        "log_reader.py",
        "PresentMon.exe",
        "requirements.txt"
    ]
    
    # Configs (User specific, but requested to be included)
    config_files = [
        "bbox_config_solo.json",
        "bbox_config_duo.json",
        "setup_screenshot_solo.png",
        "setup_screenshot_duo.png",
        "overlay_positions.json",
        "path_config.json"
    ]

    all_files = core_files + config_files

    for filename in all_files:
        src = os.path.join(source_dir, filename)
        dst = os.path.join(lecta_scripts_dest, filename)
        
        if os.path.exists(src):
            shutil.copy2(src, dst)
            print(f"Copied {filename}")
        else:
            # Only warn for core files, configs might not exist
            if filename in core_files:
                print(f"Warning: Core file {filename} missing in Source!")

    print("\n=======================================================")
    print(f"Patch created successfully: {patch_dir_name}")
    print("=======================================================")
    print("Instructions for Testers:")
    print("1. Copy 'Start_Tracker.bat' to their main folder (overwrite existing).")
    print("2. Copy the CONTENTS of the 'LECTA_SCRIPTS' folder into:")
    print("   'python_and_required_packages/LECTA_SCRIPTS' (overwrite existing).")
    print("=======================================================")

if __name__ == "__main__":
    main()