# Social Archive Studio

A local-first social media archiving tool for creators, marketers, researchers, and everyday users who need to save content they own or have permission to download.

This project is intentionally positioned as a rights-respecting archive assistant, not a stealth scraper. The app asks users to confirm that they own the content, have permission, or are otherwise allowed to save it before a job can run.


## What It Does

- Downloads supported Instagram, Twitter/X, TikTok, Snapchat, Pinterest, Facebook, and YouTube URLs.
- Previews title, uploader, duration, and thumbnail before download when the platform exposes metadata.
- **YouTube: Choose video quality before download** (e.g., 240p, 360p, 720p) to save data or storage. The web UI will show a quality dropdown after previewing a YouTube link.
- Uses `instaloader` for Instagram post/profile archive workflows.
- Uses `yt-dlp` for Twitter/X, TikTok, Snapchat, Pinterest, Facebook, and YouTube media URLs.
- Queues batches of supported social media URLs from the web UI or CLI.
- Detects duplicates by shortcode after a completed archive exists.
- Supports owner profile archives with a local Instaloader session file.
- Provides a clean local web interface for paste-link workflows.
- Provides a CLI for batchable creator and power-user workflows.
- Stores downloads in per-job folders with status, metadata, logs, and optional ZIP archives.
- Exports job history as CSV or JSON.
- Offers browser-save links for completed files and ZIP archives, using the user's browser download folder settings.
- Keeps a local job history so users can recover prior results.
- Avoids collecting Instagram credentials in the web UI.
- **Shows a download progress bar** for each job in the web UI.
- **Clear Jobs View**: Hide all jobs from the browser view (without deleting them) to start a new set of jobs with a clean slate.

## Quick Start


Install Python 3.11 or newer, then run from WSL Ubuntu:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m instagram_archive_studio.server
```

Open:

```text
http://127.0.0.1:8080
```

CLI usage:

```bash
python3 -m instagram_archive_studio.cli "https://www.instagram.com/p/SHORTCODE/" --yes-i-have-rights
python3 -m instagram_archive_studio.cli "https://www.youtube.com/watch?v=VIDEO_ID" --yes-i-have-rights
python3 -m instagram_archive_studio.cli "https://www.tiktok.com/@user/video/VIDEO_ID" --yes-i-have-rights --no-zip
python3 -m instagram_archive_studio.cli --batch-file urls.txt --yes-i-have-rights
python3 -m instagram_archive_studio.cli --profile yourbrand --session-file ~/.config/instaloader/session-yourbrand --yes-i-have-rights
python3 -m instagram_archive_studio.cli --export-csv exports/jobs.csv
```

## WSL Installer

```bash
bash scripts/install_wsl.sh
```

## Product Boundaries

Use this tool only for content you own, content you have permission to save, or content you are legally allowed to archive. Social platforms often restrict automated collection without permission, so this app is designed for narrow, user-directed archiving rather than bulk scraping.

## Project Layout

```text
instagram_archive_studio/
  cli.py             Command-line entry point
  downloader.py      Instaloader/yt-dlp integration and job lifecycle
  server.py          Standard-library local web server and API
  static/
    index.html       App shell
    app.js           Frontend behavior
    styles.css       Interface styling
    legal/           Launch-ready legal placeholders
docs/
  AUDIT_AND_STRATEGY.md
scripts/
  install_wsl.sh
tests/
  test_downloader.py
downloads/          Created at runtime
```

## Known Runtime Requirements

- Python 3.11 or newer must be installed and available as `python3` in your environment (WSL/Ubuntu recommended).
- `ffmpeg` must be installed and available in your system PATH for video/audio downloads (install via `sudo apt install ffmpeg`).
- All Python dependencies must be installed using `python3 -m pip install -r requirements.txt` inside your virtual environment.
- For best results, use a virtual environment (`python3 -m venv .venv`).
