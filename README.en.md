# Steam Screenshot Rebinder

> 🇷🇺 Русская версия: [README.md](README.md)

⚡ A lightweight desktop tool for re-uploading Steam screenshots.
It is used when the upload order in the Steam profile is broken or Steam blocks re-uploading files with the same names.

The project is distributed as a **ready-to-use portable Windows application** and does not require Python to be installed.

---

## 🎯 What the application can do

- 📂 Scans **OLD** (your original screenshots) and **NEW** (Steam `screenshots` folder).
- 🔄 Builds file pairs `(OLD → NEW)` without sorting — strictly in folder order.
- 🖼 Replaces the content of new screenshots with old ones while keeping Steam filenames.
- 🎛 Lightweight graphical interface built with PySide6.
- 📝 Detailed log (colors, statuses, timestamps).
- 🧪 Dry-run mode (testing without modifying files).
- ⚡ JPG / PNG support (or auto).
- ⌨️ Auto-screenshot mode (F12 key emulation):
  - configurable screenshot count and interval,
  - configurable start delay,
  - logging of each key press and final summary.

---

## 📘 How it works

1. Copy your **old screenshots** into the `OLD` folder.
2. Take **new screenshots in Steam** (using F12) — they are saved into the `NEW` folder.
3. The application builds pairs `(OLD → NEW)`.
4. The content of the new screenshots is replaced with the old images, while filenames remain unchanged.
5. The screenshots can now be uploaded again to your Steam profile 🚀

---

## ▶️ How to use (recommended)

### Ready-to-use application (portable)

1. Go to the **Releases** section on GitHub.
2. Download `SteamScreenshotRebinder-portable.zip`.
3. Extract the archive.
4. Run `SteamScreenshotRebinder.exe`.

Python and dependencies are **not required**.

---

## 🛠️ Run from source

### Requirements
- Windows 10 / 11
- Python **3.11+**

### Install runtime dependencies
```bash
pip install -r requirements.txt
```

### Run
```bash
python app.py
```

---

## 📦 Build portable application (PyInstaller)

### Install build dependencies
```bash
pip install -r requirements-dev.txt
```

### Build
```bash
pyinstaller SteamScreenshotRebinder.spec
```

The built application will appear in the `dist/` directory.

---

## 📁 Project structure

```
steam_screenshot_rebinder/
│
├── core/                   # Logic
├── ui/                     # PySide6 interface
├── tests/                  # pytest tests
│
├── app.py                  # GUI entry point
├── requirements.txt        # runtime dependencies
├── requirements-dev.txt    # build dependencies
├── SteamScreenshotRebinder.spec
├── .gitignore
└── README.md
```

---

## ▶️ How to use the application

1. Select the **OLD** folder with old screenshots.
2. Select the **NEW** folder (from Steam).
3. Click **Preview pairs**.
4. Click **Replace content**:
   - `Dry-run` enabled → only logs;
   - disabled → files are actually replaced.
5. Upload the screenshots to your Steam profile.

---

## ▶️ Auto-screenshot (F12)

1. Configure:
   - screenshot count,
   - interval,
   - start delay.
2. Click **Start F12**.
3. The log will display each key press.
4. The **Stop** button can interrupt the process at any moment.

---

## 🛟 Troubleshooting

- **No pairs found** → check folders and exclude `thumbnails/`.
- **Files are not replaced** → disable `Dry-run`.
- **Empty preview** → folders must contain image files.
- **Auto-screenshot does not work** → the game window must be active and Steam must accept F12.

---

## ⚠️ Notes

The application uses input automation (key emulation).
Some antivirus software may react to this — this is expected behavior.
