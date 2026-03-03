import os
import shutil
import sys
import stat

def remove_readonly(func, path, excinfo):
    # Clear the readonly bit and reattempt the removal
    os.chmod(path, stat.S_IWRITE)
    func(path)

def build_full_release(source_dir, project_root):
    """Builds the full release package including the Python environment."""
    print("\n" + "="*30 + "\nBuilding FULL release package...\n" + "="*30)
    release_dir = os.path.join(project_root, "Release_Build")
    # The name of the embeddable python folder
    # Assuming it exists in the root directory as per previous setup
    embed_folder_name = "python_and_required_packages"
    embed_src = os.path.join(project_root, embed_folder_name)
    
    if not os.path.exists(embed_src):
        print(f"Error: Could not find embeddable python folder at: {embed_src}")
        print("Make sure you have the embedded python setup in the root folder.")
        sys.exit(1)

    # Clean previous build
    if os.path.exists(release_dir):
        print(f"Cleaning previous build at {release_dir}...")
        shutil.rmtree(release_dir, onerror=remove_readonly)
    
    os.makedirs(release_dir)
    print(f"Created release directory: {release_dir}")

    # 1. Copy Start_Tracker.bat and README.md from Source
    for file in ["Start_Tracker.bat", "README.md", "Log_Guide.md"]:
        src = os.path.join(source_dir, file)
        dst = os.path.join(release_dir, file)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            print(f"Copied {file}")
        else:
            print(f"Warning: {file} not found in Source!")

    # 2. Copy Embeddable Python Folder
    print("Copying Python environment (this may take a moment)...")
    embed_dst = os.path.join(release_dir, embed_folder_name)
    # Ignore LECTA_SCRIPTS if it exists in source python folder to avoid duplication
    shutil.copytree(embed_src, embed_dst, ignore=shutil.ignore_patterns("LECTA_SCRIPTS"))

    
    # 3. Create LECTA_SCRIPTS in the release root
    scripts_dst = os.path.join(release_dir, "LECTA_SCRIPTS")
    os.makedirs(scripts_dst, exist_ok=True)
    
    # 4. Copy Scripts and Binaries from Source to LECTA_SCRIPTS
    script_files = [
        "main.py", 
        "bounding_box_setup.py", 
        "fps_tracker.py", 
        "log_reader.py",
        "gui_components.py",
        "settings_dialog.py",
        "tracker.py",
        "gui_components.py",
        "PresentMon.exe",
        "requirements.txt",
        "Background.png", "Credits.png"
    ]
    script_files = sorted(list(set(script_files))) # Remove duplicates
    
    for file in script_files:
        src = os.path.join(source_dir, file)
        dst = os.path.join(scripts_dst, file)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            print(f"Copied {file} to scripts folder")
        else:
            print(f"Warning: {file} not found in Source! Make sure it is there.")

    # 5. Copy easyocr_models if they exist (Good for offline installers)
    # Check Source first, then Root
    models_src = os.path.join(source_dir, "easyocr_models")
    if not os.path.exists(models_src):
        models_src = os.path.join(project_root, "easyocr_models")

    if os.path.exists(models_src):
        print(f"Copying EasyOCR models from {models_src}...")
        shutil.copytree(models_src, os.path.join(release_dir, "easyocr_models"))

    # 6. Cleanup junk from the release python folder
    # Remove any existing .json configs or logs that might have been copied from your personal setup
    print("Cleaning up developer-specific config/log files from release build...")
    for item in os.listdir(scripts_dst):
        if item.endswith(".json") or item.endswith(".png") or item == "OUTPUT":
            path_to_remove = os.path.join(scripts_dst, item)
            print(f"  - Removing: {item}")
            if os.path.isfile(path_to_remove):
                os.remove(path_to_remove)
            elif os.path.isdir(path_to_remove):
                shutil.rmtree(path_to_remove, onerror=remove_readonly)

    print("\nBuild Complete!")
    print(f"Release is ready at: {release_dir}")
    print("Action: Zip the CONTENTS of 'Release_Build' and upload to GitHub Releases.")

def build_update_package(source_dir, project_root):
    """Builds a lightweight update package with scripts only."""
    print("\n" + "="*30 + "\nBuilding UPDATE package...\n" + "="*30)

    update_dir = os.path.join(project_root, "Update_Build")

    # Clean previous build
    if os.path.exists(update_dir):
        print(f"Cleaning previous update build at {update_dir}...")
        shutil.rmtree(update_dir, onerror=remove_readonly)
    
    os.makedirs(update_dir)
    print(f"Created update directory: {update_dir}")

    # 1. Create LECTA_SCRIPTS inside the update folder
    scripts_dst = os.path.join(update_dir, "LECTA_SCRIPTS")
    os.makedirs(scripts_dst, exist_ok=True)

    # 2. Copy Scripts and Binaries from Source to LECTA_SCRIPTS
    script_files = [
        "main.py", "bounding_box_setup.py", "fps_tracker.py", "log_reader.py",
        "gui_components.py", "settings_dialog.py", "tracker.py",
        "PresentMon.exe", "requirements.txt",
        "Background.png", "Credits.png"
    ]
    script_files = sorted(list(set(script_files)))

    for file in script_files:
        src = os.path.join(source_dir, file)
        dst = os.path.join(scripts_dst, file)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            print(f"Copied {file} to update scripts folder")
        else:
            print(f"Warning: {file} not found in Source!")

    # 3. Create and add the apply_update.bat script
    apply_update_bat_content = r"""@echo off
setlocal

echo =================================================================
echo = Warframe Lecta Tracker - Update Script
echo =================================================================
echo.
echo This script will copy the new application files into your existing
echo installation directory. Your configuration files (.json, .png) 
echo will NOT be deleted.
echo.
echo IMPORTANT: Please close the Lecta Tracker application before proceeding.
echo.

:get_path
set "INSTALL_PATH="
set /p "INSTALL_PATH=Please drag and drop your main Lecta Tracker folder here and press Enter: "

rem Clean up quotes if user drags and drops a folder
set "INSTALL_PATH=%INSTALL_PATH:"=%"

if not defined INSTALL_PATH (
    echo You must provide a path.
    goto get_path
)

set "TARGET_DIR=%INSTALL_PATH%\LECTA_SCRIPTS"

if not exist "%TARGET_DIR%" (
    echo.
    echo ERROR: Could not find the 'LECTA_SCRIPTS' folder inside the path
    echo you provided: %INSTALL_PATH%
    echo.
    echo Please make sure you are selecting the correct main installation folder
    echo (the one that contains 'Start_Tracker.bat').
    echo.
    goto get_path
)

set "SOURCE_DIR=%~dp0LECTA_SCRIPTS"

echo.
echo The following directory will be updated: %TARGET_DIR%
echo.
choice /C YN /M "Do you want to proceed with the update?"
if errorlevel 2 (
    echo Update cancelled.
    goto end
)

echo.
echo Copying new files...
xcopy "%SOURCE_DIR%" "%TARGET_DIR%\" /Y /E /I /R

if %errorlevel% neq 0 (
    echo.
    echo An error occurred during file copy. Please make sure the tracker is not running
    echo and that you have permissions to write to the directory.
    goto end
)

echo.
echo =================================================================
echo = Update Complete!
echo =================================================================
echo.
echo You can now start the tracker using the Start_Tracker.bat in your
echo main installation folder.
echo.

:end
pause
"""
    with open(os.path.join(update_dir, "apply_update.bat"), "w", newline='\r\n') as f:
        f.write(apply_update_bat_content)
    print("Created apply_update.bat")

    # 4. Create an instructions file
    instructions_content = """How to apply this update:

1. Make sure you have a previous version of the Lecta Tracker already installed.
   This update package does NOT contain the full Python environment and will not work on its own.

2. Close the Lecta Tracker application if it is running.

3. Run the `apply_update.bat` script.

4. When prompted, drag and drop your main Lecta Tracker installation folder
   (the one that contains `Start_Tracker.bat`) into the command window and press Enter.

5. Confirm the update. The script will copy the new files.

6. That's it! Your tracker is now updated, and your settings have been preserved.
"""
    with open(os.path.join(update_dir, "Update_Instructions.txt"), "w") as f:
        f.write(instructions_content)
    print("Created Update_Instructions.txt")

    print("\nUpdate Build Complete!")
    print(f"Update package is ready at: {update_dir}")
    print("Action: Zip the CONTENTS of 'Update_Build' and upload to GitHub Releases as a smaller update package.")

def main():
    # Define paths
    source_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(source_dir)

    if '--update' in sys.argv:
        build_update_package(source_dir, project_root)
    elif '--full' in sys.argv or len(sys.argv) == 1:
        build_full_release(source_dir, project_root)
    else:
        print("Usage: build_release.py [--full | --update]")
        print("  --full    (default) Builds the complete package with embedded Python.")
        print("  --update  Builds a lightweight update package with scripts only.")

if __name__ == "__main__":
    main()
