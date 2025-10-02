#!/bin/bash

echo "🦊 KemonoDownloader v2.7 Multithread - Build Script"
echo "===================================================="
echo

echo "🔍 Checking dependencies..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python not found! Please install Python 3."
    exit 1
fi

# Check PyInstaller
if ! command -v pyinstaller &> /dev/null; then
    echo "💡 Installing PyInstaller..."
    pip install pyinstaller
fi

echo "✅ Dependencies OK"
echo

echo "🧹 Cleaning old files..."
rm -rf build/
rm -f *.spec

echo "🚀 Building GUI version..."
pyinstaller --onefile --windowed --add-data "assets:assets" --add-data "cloud_downloader.py:." --icon="assets/icons/KemonoDownloader.ico" --name="KemonoDownloader_GUI_v2.7_Multithread" kemono_gui_static.py

echo "🚀 Building Console version..."
pyinstaller --onefile --console --add-data "assets:assets" --add-data "cloud_downloader.py:." --icon="assets/icons/KemonoDownloader.ico" --name="KemonoDownloader_Console_v2.7_Multithread" downloader_static.py

echo
echo "📋 Build Results:"
echo "================="

if [ -f "dist/KemonoDownloader_GUI_v2.7_Multithread" ]; then
    echo "✅ GUI version: KemonoDownloader_GUI_v2.7_Multithread"
else
    echo "❌ GUI version: FAILED!"
fi

if [ -f "dist/KemonoDownloader_Console_v2.7_Multithread" ]; then
    echo "✅ Console version: KemonoDownloader_Console_v2.7_Multithread"
else
    echo "❌ Console version: FAILED!"
fi

echo
echo "✅ Build complete!"
echo "📁 Files are in: dist/"
read -p "Press Enter to continue..."