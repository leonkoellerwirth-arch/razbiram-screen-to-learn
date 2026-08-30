#!/usr/bin/env bash
#
# Launch the razbiram-screen-to-learn studio — a standalone local app. The API and the
# UI are served from one loopback origin, so there is no proxy, no account and no
# razbiram.com shell around it. Captured content never leaves the machine.
#
# THIS SCRIPT IS THE ONLY SUPPORTED WAY TO START THE APP — people and agents alike.
# Starting uvicorn, vite or `npm run dev` by hand gives a half-wired app; starting the
# razbiram.com dev server gives a different product that happens to share a logo.
# After changing apps/studio, re-run with --rebuild: the UI is served from dist/.
#
#   ./start.sh              build the UI if needed, pick a free port, serve it, open the browser
#   ./start.sh --rebuild    rebuild the UI first (after changing apps/studio)
#   ./start.sh --no-open    don't open a browser
#   ./start.sh --free-port  stop whatever holds the port first (opt-in)
#   ./start.sh --stop       stop the running instance recorded in .dev-port
#   ./start.sh -h|--help    show this help
#
# Ctrl-C stops the server. Override the dynamic port with PORT=… ./start.sh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT_FILE="$ROOT_DIR/.dev-port"
VENV="$ROOT_DIR/.venv"
UI_DIR="$ROOT_DIR/apps/studio"
OPEN=1
FREE_PORT=0
REBUILD=0
STOP=0

for arg in "$@"; do
  case "$arg" in
    --rebuild) REBUILD=1 ;;
    --no-open) OPEN=0 ;;
    --free-port) FREE_PORT=1 ;;
    --stop) STOP=1 ;;
    -h|--help) sed -n '3,18p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Unknown option: $arg" >&2; exit 1 ;;
  esac
done

cd "$ROOT_DIR"

open_url() {
  [ "$OPEN" = 1 ] && command -v open >/dev/null 2>&1 && open "$1" || true
}

is_studio_app() {
  local port="$1"
  curl -fsS "http://127.0.0.1:${port}/health" 2>/dev/null \
    | grep -Fq '"status":"ok"'
}

running_port() {
  [ -f "$PORT_FILE" ] || return 1
  local port
  port="$(<"$PORT_FILE")"
  [ -n "$port" ] || return 1
  is_studio_app "$port" || return 1
  echo "$port"
}

is_our_pid() {
  local pid="$1"
  ps -p "$pid" -o command= 2>/dev/null | grep -Fq "$ROOT_DIR"
}

port_free() {
  if command -v lsof >/dev/null 2>&1; then
    ! lsof -ti tcp:"$1" >/dev/null 2>&1
  else
    ! curl -fsS "http://127.0.0.1:$1/" -o /dev/null 2>/dev/null
  fi
}

pick_port() {
  local port
  if port_free 8765; then
    echo 8765
    return 0
  fi
  for _ in $(seq 1 80); do
    port=$(( (RANDOM % 700) + 8766 ))
    if port_free "$port"; then
      echo "$port"
      return 0
    fi
  done
  echo "No free port found in 8765–9465." >&2
  return 1
}

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

install_editable() {
  local path="$1"
  if command -v uv >/dev/null 2>&1; then
    uv pip install --python "$VENV/bin/python" -q -e "$path"
  elif [ -x "$VENV/bin/pip" ]; then
    "$VENV/bin/pip" install -q -e "$path"
  else
    "$VENV/bin/python" -m ensurepip --upgrade >/dev/null 2>&1 || {
      echo "Neither uv nor pip is available in $VENV." >&2; exit 1; }
    "$VENV/bin/python" -m pip install -q -e "$path"
  fi
}

if [ "$STOP" = 1 ]; then
  stopped=0
  port=""
  [ -f "$PORT_FILE" ] && port="$(<"$PORT_FILE")"

  if [ -n "$port" ] && command -v lsof >/dev/null 2>&1; then
    for pid in $(lsof -ti tcp:"$port" 2>/dev/null || true); do
      if is_our_pid "$pid"; then
        kill "$pid" 2>/dev/null || true
        echo "razbiram-screen-to-learn stopped (port $port, PID $pid)."
        stopped=1
      fi
    done
  fi

  if [ "$stopped" = 0 ]; then
    echo "No running razbiram-screen-to-learn instance found."
  fi

  rm -f "$PORT_FILE"
  exit 0
fi

if port="$(running_port)"; then
  url="http://127.0.0.1:${port}"
  echo "razbiram-screen-to-learn is already running: $url"
  open_url "$url"
  exit 0
fi

rm -f "$PORT_FILE"

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
  install_editable "$ROOT_DIR"
fi

if ! "$VENV/bin/python" -c 'import scrapling.fetchers' >/dev/null 2>&1; then
  SCRAPLING_DIR="$ROOT_DIR/../Scrapling"
  if [ -d "$SCRAPLING_DIR/scrapling" ]; then
    echo "Installing local Scrapling for the Quizlet importer…"
    install_editable "${SCRAPLING_DIR}[fetchers]"
  else
    echo "Note: Scrapling is not installed; the Quizlet URL tab will report this until installed." >&2
  fi
fi

# --- UI side: the studio is served from apps/studio/dist ---
if [ "$REBUILD" = 1 ] || [ ! -f "$UI_DIR/dist/index.html" ]; then
  command -v node >/dev/null 2>&1 || { echo "Node.js is required to build the UI (see https://nodejs.org)." >&2; exit 1; }
  [ -d "$UI_DIR/node_modules" ] || { echo "Installing UI dependencies…"; (cd "$UI_DIR" && npm ci); }
  echo "Building the studio UI…"
  (cd "$UI_DIR" && npm run build)
fi

PORT="${PORT:-$(pick_port)}"
if ! [[ "$PORT" =~ ^[0-9]+$ ]] || [ "$PORT" -lt 1024 ] || [ "$PORT" -gt 65535 ]; then
  echo "Invalid port: $PORT" >&2
  exit 1
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

echo "$PORT" > "$PORT_FILE"
cleanup() { rm -f "$PORT_FILE"; }
trap cleanup EXIT INT TERM

echo "razbiram-screen-to-learn studio → http://127.0.0.1:$PORT"
if [ "$OPEN" = 1 ]; then
  "$VENV/bin/razbiram-screen-to-learn" studio --port "$PORT"
else
  "$VENV/bin/razbiram-screen-to-learn" studio --port "$PORT" --no-open
fi
