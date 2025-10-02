# 🌐 KemonoDownloader v2.6 Cloud Auto - Revolutionary Release!

## 🚀 GAME-CHANGING FEATURE: Automatic Cloud File Downloading!

This release introduces **AUTOMATIC CLOUD FILE DOWNLOADING** - a revolutionary feature that automatically downloads files from cloud storage services without any manual intervention!

## ✨ What's New in v2.6 Cloud Auto

### 🌐 Automatic Cloud Downloads
- **Google Drive** - Full automatic download with direct link extraction
- **Dropbox** - Automatic URL conversion and file downloading  
- **MediaFire** - Page parsing and direct file extraction
- **MEGA** - Support through mega.py library (optional: `pip install mega.py`)

### 📁 Smart File Organization
- Cloud files automatically saved to `cloud_files/` subdirectory
- Download progress tracking with visual indicators
- Success logging in `cloud_downloads.log`
- All cloud links catalogued in `cloud_links.txt`

### 🎯 Supported Cloud Services
| Service | Status | Description |
|---------|--------|-------------|
| 🟢 **Google Drive** | Full Support | Automatic direct link extraction with redirect handling |
| 🟢 **Dropbox** | Full Support | Complete automatic downloading |
| 🟢 **MediaFire** | Full Support | Page parsing and file extraction |
| 🟡 **MEGA** | Optional | Requires `pip install mega.py` |
| 🟡 **OneDrive, Box, pCloud** | Basic | Public link support |

## 📦 Ready-to-Use Applications

### Windows Executables (Ready to Download!)
- **`KemonoDownloader_GUI_v2.6_CloudAuto.exe`** (42.67 MB) - User-friendly interface
- **`KemonoDownloader_Console_v2.6_CloudAuto.exe`** (15.33 MB) - Command-line version

### Universal File Support (61 Formats!)
- **3D Models**: GLB, GLTF, BLEND, FBX, OBJ, DAE, 3DS, MAX
- **Unity Assets**: UNITY, UNITYPACKAGE, PREFAB, ASSET
- **Archives**: ZIP, RAR, 7Z, TAR, GZ, BZ2, XZ
- **Media Files**: MP4, PNG, JPG, MP3, WAV and many more!

## 🔧 Technical Improvements

### Enhanced Architecture
- Modular `CloudDownloader` class with extensible design
- Graceful degradation when cloud modules are missing
- Improved file deduplication preventing duplicate downloads
- Enhanced error handling and retry mechanisms

### Build System
- Cross-platform build scripts (Windows `build.bat` + Linux `build.sh`)
- Automatic dependency checking and installation
- Clean project structure with removed test files

## 💻 How to Use

### Quick Start (Recommended)
1. Download the appropriate `.exe` file from the release assets
2. Double-click to run - no installation required!
3. Enter kemono.cr or coomer.cr URLs
4. Watch as files download automatically, including from cloud services!

### From Source Code
```bash
git clone https://github.com/Steam2208/Kemono_downloader_alpha.git
cd Kemono_downloader_alpha
pip install -r requirements.txt
python downloader_static.py
```

### For Full MEGA Support (Optional)
```bash
pip install mega.py
```

## 🌟 Example Usage

```
🦊 KemonoDownloader v2.6 Cloud Auto

🔗 Enter URL: https://kemono.cr/gumroad/user/123/post/456

📄 Processing post...
  🔍 Found 3 regular files
  ☁️ Found 2 cloud links:
      ☁️ Google Drive: 1
      ☁️ Dropbox: 1

🌐 Auto-downloading cloud files: 2
[1/2] Google Drive: Downloading textures.zip...
✅ Downloaded: textures.zip (15.2 MB)

[2/2] Dropbox: Downloading animations.fbx...  
✅ Downloaded: animations.fbx (8.1 MB)

✅ Download complete!
📁 Files saved to: ./downloads/gumroad_user_123/post_456/
  📄 model.blend (5.2 MB)
  📂 cloud_files/
    📄 textures.zip (15.2 MB)
    📄 animations.fbx (8.1 MB)
```

## 🔄 Automatic Resume
The program automatically creates `.kemono_progress.json` to track download progress. If interrupted, just restart - it continues where it left off!

## 📋 Release Assets

Download the ready-to-use executables below:

- **KemonoDownloader_GUI_v2.6_CloudAuto.exe** - Full-featured GUI version
- **KemonoDownloader_Console_v2.6_CloudAuto.exe** - Lightweight console version

Both include automatic cloud downloading capabilities!

## 🙏 Credits

Based on the original project by [VoxDroid/KemonoDownloader](https://github.com/VoxDroid/KemonoDownloader)

---

**This is a game-changing release that revolutionizes how you download content from kemono.cr!** 🎉