#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

cat <<'MSG'
Instagram Archive Studio is installed.

Run:
  . .venv/bin/activate
  python -m instagram_archive_studio.server

Then open:
  http://127.0.0.1:8080
MSG
