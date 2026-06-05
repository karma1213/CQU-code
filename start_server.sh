#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
export HOST="${HOST:-0.0.0.0}"
export PORT="${PORT:-8765}"

python3 -m pip install -r requirements.txt
python3 cqu_crawler.py
exec python3 notice_server.py
