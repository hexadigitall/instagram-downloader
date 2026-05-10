# Instagram Archive Studio

A local-first Instagram media archiving tool for creators, marketers, researchers, and everyday users who need to save content they own or have permission to download.

This project is intentionally positioned as a rights-respecting archive assistant, not a stealth scraper. The app asks users to confirm that they own the content, have permission, or are otherwise allowed to save it before a job can run.

## What It Does

- Downloads public Instagram post, Reel, and video URLs through `instaloader`.
- Queues batches of Instagram URLs from the web UI or CLI.
- Detects duplicates by shortcode after a completed archive exists.
- Supports owner profile archives with a local Instaloader session file.
- Provides a clean local web interface for paste-link workflows.
- Provides a CLI for batchable creator and power-user workflows.
- Stores downloads in per-job folders with status, metadata, logs, and optional ZIP archives.
- Exports job history as CSV or JSON.
- Keeps a local job history so users can recover prior results.
- Avoids collecting Instagram credentials in the web UI.

## Quick Start

Install Python 3.11 or newer, then run from WSL Ubuntu:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m instagram_archive_studio.server
```

Open:

```text
http://127.0.0.1:8080
```

CLI usage:

```bash
python -m instagram_archive_studio.cli "https://www.instagram.com/p/SHORTCODE/" --yes-i-have-rights
python -m instagram_archive_studio.cli "https://www.instagram.com/reel/SHORTCODE/" --yes-i-have-rights --no-zip
python -m instagram_archive_studio.cli --batch-file urls.txt --yes-i-have-rights
python -m instagram_archive_studio.cli --profile yourbrand --session-file ~/.config/instaloader/session-yourbrand --yes-i-have-rights
python -m instagram_archive_studio.cli --export-csv exports/jobs.csv
```

## WSL Installer

```bash
bash scripts/install_wsl.sh
```

## Product Boundaries

Use this tool only for content you own, content you have permission to save, or content you are legally allowed to archive. Instagram and Meta policies restrict automated collection without permission, so this app is designed for narrow, user-directed archiving rather than bulk scraping.

## Project Layout

```text
instagram_archive_studio/
  cli.py             Command-line entry point
  downloader.py      Instaloader integration and job lifecycle
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

## Known Runtime Requirement

The current workspace did not have Python available during project creation. Install Python before running the app.
