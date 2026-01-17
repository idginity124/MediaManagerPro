<div align="center">
  <img src="assets/app_icon.png" alt="Media Manager Pro Logo" width="120" height="120">

# 📁 Media Manager Pro
### The Ultimate File Organizer, Cleaner & Media Tool for Windows

  <p>
    <img src="https://img.shields.io/badge/VERSION-v1.0-2ea44f?style=for-the-badge">
    <img src="https://img.shields.io/badge/PYTHON-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white">
    <img src="https://img.shields.io/badge/PLATFORM-WINDOWS-0078D6?style=for-the-badge&logo=windows&logoColor=white">
    <img src="https://img.shields.io/badge/GUI-PySide6-41CD52?style=for-the-badge&logo=qt&logoColor=white">
    <img src="https://img.shields.io/badge/LICENSE-MIT-yellow?style=for-the-badge">
  </p>

  <p>
    <strong>Media Manager Pro</strong> is a powerful desktop utility that helps you clean up chaotic folders: organize by date, find duplicates, convert image formats, scrub metadata, and repair old photos.
    <br>
    Built for normal humans who would rather not spend their weekend renaming files.
  </p>

  <p>
    <a href="#-download">📥 Download</a> •
    <a href="#-features">✨ Features</a> •
    <a href="#-screenshots">📸 Screenshots</a> •
    <a href="#-developer-setup">🛠️ Developer Setup</a>
  </p>
</div>

---

## 🚀 Why Media Manager Pro?

Because “I’ll sort my photos later” is a lie we all tell ourselves.

- **Fast & Practical** (No wizardry, no 17-step configs)
- **Modern Desktop UI** (Dark/Light themes)
- **Safe File Handling** (Conflict modes: Copy/Overwrite/Skip)
- **Extensible System** (Add your own Plugins)

---

## ✨ Features

- **🗂️ Smart Organization**
  Sort mixed files into folders by **Day / Month / Year** automatically.

- **🧹 Duplicate Cleaner (Optimized)**
  Finds and separates identical files using size grouping + hash verification.

- **🧩 Plugin System (New!)**
  Extend functionality with custom Python scripts. Includes a **Plugin Manager**.

- **🔧 Photo Repair (New!)**
  Restore old or damaged photos using the **Telea Algorithm** (OpenCV).

- **🖼️ Image Converter**
  Convert between common formats (JPEG, PNG, WEBP, BMP, TIFF, HEIC).

- **🛡️ Privacy Mode**
  Strip sensitive metadata (EXIF, GPS, Camera info) from your photos.

- **🌍 Multi-Language**
  Fully localized interface (English + Turkish).

---

## 📥 Download

### Windows (Recommended)

1. Go to **[Releases](../../releases)** page.
2. Download the latest **MediaManagerPro_v1.0.zip**.
3. Extract the ZIP file and run **MediaManagerPro.exe**.

> **Note:** Please keep the `plugins` and `assets` folders next to the exe file for everything to work correctly.

> Windows SmartScreen may show a warning.
> Click **More info → Run anyway**.

---

## 📸 Screenshots

| Dashboard | Plugin Manager |
|:--:|:--:|
| <img src="docs/screenshot_dashboard.png" width="100%"> | <img src="docs/screenshot_organize.png" width="100%"> |

---

🧠 **The Training Arc**

This project is part of my ongoing training arc.
Built with discipline, refined through mistakes.

---

## 🛠️ Developer Setup

```bash
git clone <your-repo-url>
cd MediaManagerPro
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-full.txt
python main.py
