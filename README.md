# Aladin Movie Splitter

*Developed by Aladin.*

A Windows desktop app that splits large movie/video files into parts of a length you choose.
Built with **Python 3.11+**, **PySide6** and **FFmpeg / FFprobe**.

* Fast, lossless splitting by default (FFmpeg stream copy, no re-encoding)
* Optional **Accurate mode** (re-encode) for parts of *exactly* the requested length
* Automatic output folder and numbering: `D:\Split Movies\Avatar\Avatar_Part_001.mkv`, `..._002.mkv`, ...
* Dashboard UI with dark/light themes, drag and drop, live progress, ETA, cancel, history

---------------------------------------------------------------------

## 1. Install

### Step 1 - Python
Install Python 3.11 or newer from <https://www.python.org/downloads/> and tick **Add python.exe to PATH**.

### Step 2 - FFmpeg (required)
Easiest (Windows 10/11), in Command Prompt:

```
winget install Gyan.FFmpeg
```

Then restart the app. Manual install: download a release build from <https://www.gyan.dev/ffmpeg/builds/>,
extract to `C:\ffmpeg` and add `C:\ffmpeg\bin` to PATH.

**How FFmpeg is detected** (first match wins): the paths set in *Settings*, next to the app / in an `ffmpeg\` or `bin\`
folder beside it, PATH, then common locations (`C:\ffmpeg\bin`, Program Files, WinGet, Chocolatey, Scoop).
If nothing is found the app stays open, shows a banner, and the *Setup help* dialog lets you pick `ffmpeg.exe` manually.

### Step 3 - Run
Double-click **`run.bat`**. On first launch it creates a virtual environment and installs PySide6.

Or manually:

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## 2. Using the app

1. **Select a video**: drag it into the window, press `Ctrl+O`, or use *Browse*. Filename, size, format, resolution,
   duration, codecs and a thumbnail appear (read with FFprobe).
2. **Split Settings**: enter hours / minutes / seconds, or click 5 min, 10 min, 15 min, 30 min, 1 hour.
   The estimate shows the expected number of parts, e.g. a 02:10:00 movie split every 00:15:00 gives **9 parts**,
   and the last part holds the remaining 00:10:00.
3. Choose the output location (the movie's own sub-folder is created automatically) and press **Start Splitting**.
4. Watch progress (percent, current part / total, elapsed, remaining, speed). **Cancel** removes partial files.
5. The success screen appears only after **every part has been verified** with FFprobe (exists, non-empty, readable,
   playable duration).

### Output naming
* Folder: `<output location>\<movie name without extension>\`
* Files: `<movie name>_Part_001.<original extension>`: at least 3 digits, growing past 999 (`_Part_1000`).
* Existing part files are **never overwritten silently**: you can overwrite, use a new folder (`Avatar (2)`), or cancel.
* Characters Windows does not allow in names are replaced with `_`.

### Keyboard shortcuts
| Keys | Action |
|---|---|
| Ctrl+O | Open a video |
| Ctrl+1 ... Ctrl+6 | Dashboard, Video, Split Settings, Processing, Completed, Settings |
| Ctrl+Enter | Start splitting (on the Split Settings page) |
| Esc | Cancel the running split (asks for confirmation) |
| Ctrl+T | Toggle dark / light theme |
| Ctrl+R | Reset (clear video and split settings) |
| Ctrl+Shift+C / Ctrl+Shift+O | Copy / open the output folder |

## 3. Fast mode vs Accurate mode (important)

| | **Fast (stream copy)** - default | **Accurate (re-encode)** |
|---|---|---|
| Speed | Very fast (disk speed) | Slow (depends on CPU) |
| Quality | Identical to the original | Re-encoded (H.264 CRF 18; VP9 for WebM) |
| Part length | Cuts happen on **keyframes**, so a part can be a few seconds longer or shorter than requested | Exactly the requested length (keyframes are forced at each cut point) |
| Part count | Can differ slightly from the estimate | Matches the estimate |
| Disk space | About the size of the original | Can be larger or smaller than the original |

Both modes use FFmpeg's *segment muxer* in a single pass, so parts never overlap and nothing is skipped.

### Audio, subtitles and container limitations
* Fast mode copies all video and audio streams. Accurate mode keeps video re-encoded and audio copied for MKV, AAC for MP4/MOV/M4V/TS/FLV/WMV/MPG, MP3 for AVI and Opus for WebM.
* **MKV**: all subtitle tracks are kept. **MP4/MOV/M4V**: text subtitles are converted to `mov_text`; picture subtitles (PGS/VobSub) cannot be stored and are skipped. **WebM**: text subtitles become WebVTT. **AVI** and other formats: subtitles are not copied.
* Cover art, attachments, data streams and whole-movie chapters are not copied into the parts (chapters would be wrong inside each part). The processing log lists anything skipped.
* If the source extension cannot be written (for example `.m2ts`), parts are saved as `.mkv`.
* Some old codecs cannot be stream-copied into every container (for example certain AVI/WMV audio). The app explains this and suggests Accurate mode.
* Accurate mode needs an FFmpeg build with `libx264` (and `libvpx-vp9`/`libopus` for WebM); the Gyan.dev builds include them.

## 4. Build a standalone EXE

Double-click **`build_exe.bat`**. It creates `dist\AladinMovieSplitter.exe` (single file, no console window).
To bundle FFmpeg so users need nothing else, put `ffmpeg.exe` and `ffprobe.exe` into a folder named `ffmpeg\` next to
`build_exe.bat` before building. Mind the FFmpeg licence if you redistribute it.

## 5. Project layout

```
movie_splitter_pro/
  main.py               entry point (logging, crash handler, app start-up)
  requirements.txt / requirements-dev.txt
  run.bat / build_exe.bat
  core/                 no Qt: FFmpeg detection, ffprobe, planning, naming, command builder, split engine
  workers/              QThread wrappers (split job, probe + thumbnail)
  ui/                   theme (design tokens), icons, widgets, state, dialogs, main window, pages/
  utils/                settings (JSON), logging, time/size formatting, disk space, OS helpers
  assets/               app icon
  tests/                pytest suite
```

## 6. Tests

```
pip install -r requirements-dev.txt
python -m pytest -q
```

Covers duration formatting, split planning (including the 02:10:00 / 15 min = 9 parts example and the remainder
part), naming and numbering, FFmpeg command building, error translation, and, when FFmpeg is installed,
end-to-end splitting, exact lengths in Accurate mode, the no-overwrite rule and cancellation clean-up.

## 7. Troubleshooting

| Problem | Fix |
|---|---|
| "FFmpeg was not found" banner | `winget install Gyan.FFmpeg`, restart the app, or choose `ffmpeg.exe` in *Settings*. |
| "This file could not be read as a video" | The file is damaged, still downloading, or not a video. Try playing it in VLC. |
| Parts are a few seconds longer/shorter than requested | Normal in Fast mode (keyframes). Use Accurate mode. |
| Fewer/more parts than estimated | Same cause. The success screen tells you the real count. |
| "Permission denied" | Choose an output folder you can write to; check antivirus / Controlled Folder Access. |
| "Not enough free disk space" warning | Free space or pick another drive. Fast mode needs about the source size. |
| MP4 result lacks some subtitles | Picture subtitles cannot go into MP4. Use MKV output (rename not needed: split an MKV) or accept the loss. |
| Window stays empty / crashes on start | Update graphics drivers; run `python main.py` in a terminal to see errors. |
| Need technical details | *Processing log* (on the Processing page, with a Copy button) and `%APPDATA%\AladinMovieSplitter\logs\movie_splitter.log` (Settings > Open log folder). |

Settings, history and logs live in `%APPDATA%\AladinMovieSplitter`.

## 8. Known limitations
* Only one video is processed at a time.
* In Fast mode the first part of some files may start slightly after 0 s if the source does not begin on a keyframe; Accurate mode avoids this.
* Disk-space warnings are exact for Fast mode and only an estimate for Accurate mode.
