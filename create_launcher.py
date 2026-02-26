import os

bat_content = r"""@echo off
setlocal

:: Start in the directory of this batch file
cd /d "%~dp0"

set "SUB_DIR=python_and_required_packages"

:: --- Logic to find Python and Scripts ---
:: 1. Check embeddable folder first (preferred if present)
if exist "%SUB_DIR%\python.exe" (
    set "PYTHON_EXE=.\%SUB_DIR%\python.exe"
    
    :: Check if scripts are in LECTA_SCRIPTS subfolder
    if exist "%SUB_DIR%\LECTA_SCRIPTS\CPM_OOP.py" (
        set "SCRIPT_DIR=.\%SUB_DIR%\LECTA_SCRIPTS"
    ) else (
        set "SCRIPT_DIR=.\%SUB_DIR%"
    )
) else if exist "..\%SUB_DIR%\python.exe" (
    :: 1b. Check parent folder (Development Environment)
    set "PYTHON_EXE=..\%SUB_DIR%\python.exe"
    set "SCRIPT_DIR=."
) else (
    :: 2. Check root folder
    if exist "python.exe" (
        set "PYTHON_EXE=.\python.exe"
        set "SCRIPT_DIR=."
    ) else (
        :: 3. Check System PATH (For Source Code Users)
        python --version >nul 2>&1
        if %ERRORLEVEL% EQU 0 (
            set "PYTHON_EXE=python"
            set "SCRIPT_DIR=."
        ) else (
            echo CRITICAL ERROR: Could not find python.exe!
            echo Expected in root, '%SUB_DIR%' folder, or System PATH.
            pause
            exit /b
        )
    )
)

:: --- Environment Setup ---
:: Configure EasyOCR to look for models locally in this folder
if not exist "easyocr_models" mkdir "easyocr_models"
set "EASYOCR_MODULE_PATH=%~dp0easyocr_models"

:: --- Launch Main Tracker ---
echo Launching Warframe Tracker...
"%PYTHON_EXE%" "%SCRIPT_DIR%\CPM_OOP.py"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo The tracker crashed or closed unexpectedly.
    pause
)
"""

file_path = "Start_Tracker.bat"

with open(file_path, "w") as f:
    f.write(bat_content)

print(f"Successfully created: {os.path.abspath(file_path)}")