# Changelog# Changelog



All notable changes to KemonoDownloader will be documented in this file.All notable changes to KemonoDownloader will be documented in this file.



## [2.6.0] - 2024-10-02 - Cloud Auto 🌐## [2.4.0] - 2025-10-02 - Universal Support 🎯



### 🚀 REVOLUTIONARY FEATURE - AUTOMATIC CLOUD DOWNLOADING!### 🚀 REVOLUTIONARY UPDATE - UNIVERSAL FILE SUPPORT!



### ✨ Major New Features:### ✨ Added - MASSIVE expansion of supported file types:

- **🌐 AUTOMATIC CLOUD FILE DOWNLOADING** - Game-changing functionality!- **🎭 3D Models & Blender**: GLB, GLTF, BLEND, FBX, OBJ, DAE, 3DS, MAX, MA, MB (10 formats)

- **Google Drive** - Full automatic download with direct link extraction- **📄 Documents**: PDF, DOC, DOCX, TXT, RTF (5 formats)  

- **Dropbox** - Automatic URL conversion and file downloading  - **🎵 Audio**: MP3, WAV, FLAC, OGG, M4A, AAC (6 formats)

- **MediaFire** - Page parsing and direct file extraction- **🎮 Unity Resources**: UNITY, UNITYPACKAGE, PREFAB, ASSET (4 formats)

- **MEGA** - Support through mega.py library (optional: `pip install mega.py`)- **🎨 Textures & Materials**: DDS, HDR, EXR, MAT (4 formats)

- **📁 Smart Organization** - Cloud files saved to `cloud_files/` subdirectory- **📱 Applications**: EXE, MSI, DMG, APK, IPA (5 formats)

- **📋 Download Logging** - Success tracking in `cloud_downloads.log`- **📦 Extended Archives**: 7Z, TAR, GZ, BZ2, XZ (added to ZIP, RAR)

- **🔗 Link Management** - All cloud links saved to `cloud_links.txt`- **🖼️ Extended Images**: BMP, TIFF, TGA, PSD, WEBP, SVG (added to PNG, JPG, GIF)

- **🎬 Extended Video**: FLV, WMV, M4V, MPG, MPEG (added to MP4, MOV, AVI, MKV, WEBM)

### 🔧 Technical Improvements:

- Modular `CloudDownloader` class with extensible architecture### 🔧 Enhanced Features:

- Graceful degradation when cloud_downloader.py is missing- **Smart File Type Detection** - `get_file_type()` function identifies file categories

- Enhanced build system automatically includes cloud module- **Universal File Scanner** - `is_supported_file()` supports 61 file extensions

- Improved file deduplication preventing duplicates from API sections- **Improved Statistics** - Shows count by file type (e.g., "3D модель: 3, видео: 2")

- Progress tracking with visual indicators for large downloads- **Enhanced Logging** - Displays file types during download process

- Automatic retry mechanisms for failed cloud downloads- **Better HTML Parser** - Finds all file types in HTML fallback mode

- **Extended URL Patterns** - Searches for all supported extensions in content

### 🎯 Supported Cloud Services:

- 🟢 **Google Drive** - Full support with redirect handling### 🎯 GUI Improvements:

- 🟢 **Dropbox** - Complete automatic downloading- Added **"📋 Форматы файлов"** button showing all 61 supported formats

- 🟢 **MediaFire** - Page parsing and file extraction- Updated title to "v2.4 Universal"

- 🟡 **MEGA** - Requires optional mega.py library- Enhanced status display with file type breakdown

- 🟡 **OneDrive, Box, pCloud** - Basic public link support- Improved file listing with type indicators



## [2.5.0] - 2024-10-02 - Cloud Plus ☁️### 🖥️ Console Improvements:  

- Updated welcome message showing all supported categories

### ✨ Added:- Enhanced file discovery output with type classification

- **Cloud Link Detection** - Automatic recognition of 10+ cloud services- Better statistics and file type reporting

- **Universal File Support** - Extended to 61 total supported formats

- **Enhanced 3D Support** - GLB, GLTF, BLEND, FBX, OBJ, DAE formats### 📊 Technical Details:

- **Unity Assets** - UNITY, UNITYPACKAGE, PREFAB, ASSET support- **Total supported extensions**: 61 (up from ~10 in v2.3)

- **Advanced Textures** - DDS, HDR, EXR, MAT format support- **Categories supported**: 9 major file categories

- **Cloud Link Storage** - All found links saved to `cloud_links.txt`- **Backward compatibility**: All v2.3 features remain working

- **File Deduplication** - Prevention of duplicate downloads- **Performance**: Optimized file type detection algorithms



### 🔧 Improved:### 🧪 Tested:

- Enhanced API parsing for better file detection- ✅ All 61 file extensions properly detected and categorized

- Improved HTML fallback mechanism when API fails- ✅ 3D models (GLB, BLEND) download successfully  

- Better cloud service URL recognition patterns- ✅ Unity packages (UNITYPACKAGE) supported

- Multi-domain file serving (n1-n6.kemono.cr) with automatic failover- ✅ All archive formats work correctly

- ✅ Documents and audio files detected properly

## [2.4.0] - 2024-10-02 - Universal Support 🎯

### 📁 Build Files:

### 🚀 UNIVERSAL FILE SUPPORT - 61 FORMATS!- `KemonoDownloader_GUI_v2.4_Universal.exe` - GUI version with universal support

- `KemonoDownloader_Console_v2.4_Universal.exe` - Console version with universal support

### ✨ Added - Massive file type expansion:

- **🎭 3D Models**: GLB, GLTF, BLEND, FBX, OBJ, DAE, 3DS, MAX, MA, MB (10 formats)## [2.3.0] - 2025-09-30 - Images Fixed 🖼️

- **📄 Documents**: PDF, DOC, DOCX, TXT, RTF, ODT (6 formats)  

- **🎵 Audio**: MP3, WAV, FLAC, OGG, M4A, AAC (6 formats)### ✅ Fixed

- **🎮 Unity**: UNITY, UNITYPACKAGE, PREFAB, ASSET (4 formats)- **PNG/JPG images now download correctly** - Fixed parsing of `post.file` and `previews` API sections

- **🎨 Textures**: DDS, HDR, EXR, MAT, TGA (5 formats)- **Complete media support** - All image formats now supported alongside videos

- **📱 Applications**: EXE, MSI, DMG, APK, IPA (5 formats)- **API structure parsing** - Enhanced parsing of kemono.cr API response structure

- **📦 Archives**: ZIP, RAR, 7Z, TAR, GZ, BZ2, XZ (7 formats)

- **🖼️ Images**: PNG, JPG, GIF, BMP, TIFF, TGA, PSD, WEBP, SVG (9 formats)### ✨ Added

- **🎬 Video**: MP4, MOV, AVI, MKV, WEBM, FLV, WMV, M4V, MPG (9 formats)- Support for `post.file` section (main post files)

- Support for `previews` section (preview images)  

### 🔧 Enhanced:- Enhanced API debugging and logging

- Intelligent file type detection and categorization- Comprehensive media type detection

- Cross-platform build scripts (Windows/Linux)

- PyInstaller optimization for smaller executables### 🧪 Tested

- Enhanced console interface with file statistics- ✅ PNG images: 6-7MB files downloaded successfully

- Improved error handling and user feedback- ✅ MP4 videos: 178MB files continue to work

- ✅ MOV videos: 181MB files downloaded successfully

### 🛠️ Technical:- ✅ Multi-domain support: n1-n6.kemono.cr all working

- Automatic build system with `build.bat` and `build.sh`

- Comprehensive file extension mapping### 📁 Files

- Better memory management for large files- `KemonoDownloader_GUI_v2.3_Final.exe` (42.6 MB) - GUI version

- Enhanced download stability- `KemonoDownloader_Console_v2.3_Final.exe` (15.3 MB) - Console version



## [2.3.0] - 2024-10-01 - Build System## [2.2.0] - 2025-09-30 - MP4 Fixed 🎬



### ✨ Added:### ✅ Fixed  

- Automated build scripts for Windows and Linux- **MP4 videos now download correctly** - Fixed multi-domain support

- PyInstaller configuration optimization- **Domain discovery** - Auto-search across n1-n6.kemono.cr domains

- Cross-platform executable generation- **Large file handling** - Improved download for 100MB+ files



### 🔧 Improved:### ✨ Added

- Download resume functionality- Multi-domain HEAD request validation

- Error handling and recovery- Enhanced download retry logic

- File integrity verification- Improved error handling for large files



---### 🔧 Changed

- Removed fake-useragent dependency for exe stability

Based on the original project by [VoxDroid/KemonoDownloader](https://github.com/VoxDroid/KemonoDownloader)- Static User-Agent for consistent behavior
- Enhanced API response parsing

## [2.1.0] - 2025-09-30 - Stable Base

### ✨ Added
- Initial GUI application with PyQt6
- Console version for automation
- Basic kemono.cr API integration
- Support for images and archives
- Progress tracking and themes

### 🎯 Features
- Creator post downloading
- Folder organization
- Light/dark themes
- Real-time progress bars

---

## Legend
- 🖼️ Image support improvements  
- 🎬 Video support improvements
- ✨ New features
- ✅ Bug fixes
- 🔧 Technical improvements
- 🧪 Testing and validation