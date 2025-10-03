@echo off
chcp 65001 >nul
echo.
echo 🦊 KemonoDownloader v2.8.2 Progress - Build Script
echo ====================================================
echo.

echo 🔍 Checking dependencies...
where python >nul 2>nul
if errorlevel 1 (
    echo ❌ Python not found! Please install Python.
    pause
    exit /b 1
)

where pyinstaller >nul 2>nul
if errorlevel 1 (
    echo 💡 Installing PyInstaller...
    pip install pyinstaller
)

echo ✅ Dependencies OK
echo.

echo 🧹 Cleaning old files...
if exist "build" rmdir /s /q "build" >nul 2>nul
if exist "*.spec" del /q "*.spec" >nul 2>nul

echo 🚀 Building GUI version...
pyinstaller --onefile --windowed --add-data "assets;assets" --add-data "cloud_downloader.py;." --icon="assets/icons/KemonoDownloader.ico" --name="KemonoDownloader_GUI_v2.8.2_Progress" kemono_gui_static.py

echo 🚀 Building Console version...
pyinstaller --onefile --console --add-data "assets;assets" --add-data "cloud_downloader.py;." --icon="assets/icons/KemonoDownloader.ico" --name="KemonoDownloader_Console_v2.8.2_Progress" downloader_static.py

echo.
echo 📋 Build Results:
echo ================
if exist "dist\KemonoDownloader_GUI_v2.8.2_Progress.exe" (
    echo ✅ GUI version: KemonoDownloader_GUI_v2.8.2_Progress.exe
) else (
    echo ❌ GUI version: FAILED!
)

if exist "dist\KemonoDownloader_Console_v2.8.2_Progress.exe" (
    echo ✅ Console version: KemonoDownloader_Console_v2.8.2_Progress.exe
) else (
    echo ❌ Console version: FAILED!
)

echo.
echo ✅ Build complete!
echo 📁 Files are in: dist/
pause