#!/usr/bin/env bash
#
# Launch the razbiram-screen-to-learn studio — a standalone local app. The API and the
# UI are served from one loopback origin, so there is no proxy, no account and no
# razbiram.com shell around it. Captured content never leaves the machine.
#
#   ./start.sh              build the UI if needed, serve it, open the browser
#   ./start.sh --rebuild    rebuild the UI first (after changing apps/studio)
#   ./start.sh --no-open    don't open a browser
#   ./start.sh --free-port  stop whatever holds the port first (opt-in)
#   ./start.sh -h|--help    show this help
#
# Ctrl-C stops the server.  Override the port with PORT=… ./start.sh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${PORT:-8765}"
VENV="$ROOT_DIR/.venv"
UI_DIR="$ROOT_DIR/apps/studio"
OPEN=1
FREE_PORT=0
REBUILD=0

for arg in "$@"; do
  case "$arg" in
    --rebuild) REBUILD=1 ;;
    --no-open) OPEN=0 ;;
    --free-port) FREE_PORT=1 ;;
    -h|--help) sed -n '3,13p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Unknown option: $arg" >&2; exit 1 ;;
  esac
done

cd "$ROOT_DIR"

ensure_port_free() {
  local port="$1"
  local pids=()
  command -v lsof >/dev/null 2>&1 || return 0
  while IFS= read -r pid; do
    [ -n "$pid" ] && pids+=("$pid")
  done < <(lsof -ti tcp:"$port" 2>/dev/null || true)
  [ "${#pids[@]}" -eq 0 ] && return 0
  if [ "$FREE_PORT" = 1 ]; then
    echo "Freeing port $port (PID(s): ${pids[*]}) — you passed --free-port."
    kill "${pids[@]}" 2>/dev/null || true
    sleep 1
    return 0
  fi
  { echo "Port $port is in use by PID(s): ${pids[*]}."
    echo "Stop it, re-run with --free-port, or set PORT."; } >&2
  exit 1
}

# --- Python side: the venv owns extraction, validation and export ---
# python3.11+ is required (pyproject: requires-python >=3.11); a 3.10 default is common.
if [ ! -x "$VENV/bin/python" ]; then
  PY=""
  for cand in python3.13 python3.12 python3.11; do
    command -v "$cand" >/dev/null 2>&1 && { PY="$cand"; break; }
  done
  [ -n "$PY" ] || { echo "Python 3.11+ is required (see https://python.org)." >&2; exit 1; }
  echo "Creating .venv with $PY…"
  "$PY" -m venv "$VENV"
fi

if [ ! -x "$VENV/bin/razbiram-screen-to-learn" ]; then
  echo "Installing the package into .venv…"
  # A uv-created venv has no pip, so prefer uv and fall back to pip where it exists.
  if command -v uv >/dev/null 2>&1; then
    uv pip install --python "$VENV/bin/python" -q -e "$ROOT_DIR"
  elif [ -x "$VENV/bin/pip" ]; then
    "$VENV/bin/pip" install -q -e "$ROOT_DIR"
  else
    "$VENV/bin/python" -m ensurepip --upgrade >/dev/null 2>&1 || {
      echo "Neither uv nor pip is available in $VENV." >&2; exit 1; }
    "$VENV/bin/python" -m pip install -q -e "$ROOT_DIR"
  fi
fi

# --- UI side: the studio is served from apps/studio/dist ---
if [ "$REBUILD" = 1 ] || [ ! -f "$UI_DIR/dist/index.html" ]; then
  command -v node >/dev/null 2>&1 || { echo "Node.js is required to build the UI (see https://nodejs.org)." >&2; exit 1; }
  [ -d "$UI_DIR/node_modules" ] || { echo "Installing UI dependencies…"; (cd "$UI_DIR" && npm ci); }
  echo "Building the studio UI…"
  (cd "$UI_DIR" && npm run build)
fi

ensure_port_free "$PORT"

# Images need the tesseract binary. Say so now rather than letting the first dropped screenshot
# fail with a server error the user cannot act on. Not fatal: text and HTML work without it.
if ! command -v tesseract >/dev/null 2>&1; then
  { echo
    echo "Note: 'tesseract' is not installed, so images cannot be read."
    echo "      Text and HTML files still work."
    echo "      macOS:  brew install tesseract tesseract-lang"
    echo "      Debian: sudo apt install tesseract-ocr tesseract-ocr-bul"
    echo; } >&2
fi

echo "razbiram-screen-to-learn studio → http://127.0.0.1:$PORT"
if [ "$OPEN" = 1 ]; then
  exec "$VENV/bin/razbiram-screen-to-learn" studio --port "$PORT"
fi
exec "$VENV/bin/razbiram-screen-to-learn" studio --port "$PORT" --no-open
