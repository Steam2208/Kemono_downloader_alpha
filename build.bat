@echo off
chcp 65001 >nul
echo.
echo 🦊 KemonoDownloader v2.6 Cloud Auto - Build Script
echo ==================================================
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
pyinstaller --onefile --windowed --add-data "assets;assets" --add-data "cloud_downloader.py;." --icon="assets/icons/KemonoDownloader.ico" --name="KemonoDownloader_GUI_v2.6_CloudAuto" kemono_gui_static.py

echo 🚀 Building Console version...
pyinstaller --onefile --console --add-data "assets;assets" --add-data "cloud_downloader.py;." --icon="assets/icons/KemonoDownloader.ico" --name="KemonoDownloader_Console_v2.6_CloudAuto" downloader_static.py

echo.
echo 📋 Build Results:
echo ================
if exist "dist\KemonoDownloader_GUI_v2.6_CloudAuto.exe" (
    echo ✅ GUI version: KemonoDownloader_GUI_v2.6_CloudAuto.exe
) else (
    echo ❌ GUI version: FAILED!
)

if exist "dist\KemonoDownloader_Console_v2.6_CloudAuto.exe" (
    echo ✅ Console version: KemonoDownloader_Console_v2.6_CloudAuto.exe
) else (
    echo ❌ Console version: FAILED!
)

echo.
echo ✅ Build complete!
echo 📁 Files are in: dist/
pause