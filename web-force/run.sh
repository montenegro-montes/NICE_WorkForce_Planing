#!/bin/sh
set -eu
APP_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$APP_DIR"
exec "$APP_DIR/.venv/bin/python" -m streamlit run "$APP_DIR/app.py" --server.address 127.0.0.1 --server.port 8503 "$@"
