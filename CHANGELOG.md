# Changelog

All notable changes to KemonoDownloader will be documented in this file.

## [2.3.0] - 2025-09-30 - Images Fixed 🖼️

### ✅ Fixed
- **PNG/JPG images now download correctly** - Fixed parsing of `post.file` and `previews` API sections
- **Complete media support** - All image formats now supported alongside videos
- **API structure parsing** - Enhanced parsing of kemono.cr API response structure

### ✨ Added
- Support for `post.file` section (main post files)
- Support for `previews` section (preview images)  
- Enhanced API debugging and logging
- Comprehensive media type detection

### 🧪 Tested
- ✅ PNG images: 6-7MB files downloaded successfully
- ✅ MP4 videos: 178MB files continue to work
- ✅ MOV videos: 181MB files downloaded successfully
- ✅ Multi-domain support: n1-n6.kemono.cr all working

### 📁 Files
- `KemonoDownloader_GUI_v2.3_Final.exe` (42.6 MB) - GUI version
- `KemonoDownloader_Console_v2.3_Final.exe` (15.3 MB) - Console version

## [2.2.0] - 2025-09-30 - MP4 Fixed 🎬

### ✅ Fixed  
- **MP4 videos now download correctly** - Fixed multi-domain support
- **Domain discovery** - Auto-search across n1-n6.kemono.cr domains
- **Large file handling** - Improved download for 100MB+ files

### ✨ Added
- Multi-domain HEAD request validation
- Enhanced download retry logic
- Improved error handling for large files

### 🔧 Changed
- Removed fake-useragent dependency for exe stability
- Static User-Agent for consistent behavior
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