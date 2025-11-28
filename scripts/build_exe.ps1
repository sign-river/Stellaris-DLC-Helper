# Build script for Windows (PowerShell)
# Usage: run in the repository root in PowerShell: .\scripts\build_exe.ps1

# Make sure pyinstaller is installed in your current environment
# pip install pyinstaller

# Build a directory-mode (onedir) executable that includes assets and patches
pyinstaller --onedir --windowed --icon=assets\icon.ico --add-data "assets;assets" --add-data "patches;patches" --add-data "Stellaris_DLC_Cache;Stellaris_DLC_Cache" -n stellaris_dlc_helper main.py

Write-Host "Build finished. See dist\stellaris_dlc_helper\"