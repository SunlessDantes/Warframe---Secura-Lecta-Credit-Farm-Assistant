import os
import shutil
import sys
import stat

def remove_readonly(func, path, excinfo):
    # Clear the readonly bit and reattempt the removal
    os.chmod(path, stat.S_IWRITE)
    func(path)

def main():
    # Define paths
    source_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(source_dir)
    release_dir = os.path.join(project_root, "Release_Build")
    
    # The name of the embeddable python folder
    # Assuming it exists in the root directory as per previous setup
    embed_folder_name = "python_and_required_packages"
    embed_src = os.path.join(project_root, embed_folder_name)
    
    if not os.path.exists(embed_src):
        print(f"Error: Could not find embeddable python folder at: {embed_src}")
        print("Make sure you have the embedded python setup in the root folder.")
        return

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
    shutil.copytree(embed_src, embed_dst)

    
    # 3. Create LECTA_SCRIPTS inside the python folder
    # This keeps the scripts separate from the python binaries
    scripts_dst = os.path.join(embed_dst, "LECTA_SCRIPTS")
    os.makedirs(scripts_dst, exist_ok=True)
    
    # 4. Copy Scripts and Binaries from Source to LECTA_SCRIPTS
    script_files = [
        "CPM_OOP.py", 
        "bounding_box_setup.py", 
        "fps_tracker.py", 
        "log_reader.py",
        "PresentMon.exe",
        "requirements.txt"
    ]
    
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
    # (Only check for config files, not folders like easyocr_models)
    for item in os.listdir(release_dir):
        if item.endswith(".json") or item.endswith(".png") or item == "OUTPUT":
             path = os.path.join(scripts_dst, item)
             if os.path.isfile(path):
                 os.remove(path)
             elif os.path.isdir(path):
                 shutil.rmtree(path)

    print("\nBuild Complete!")
    print(f"Release is ready at: {release_dir}")
    print("Action: Zip the CONTENTS of 'Release_Build' and upload to GitHub Releases.")

if __name__ == "__main__":
    main()
