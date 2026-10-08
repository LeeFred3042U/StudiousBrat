#!/usr/bin/env bash
# Analogy Tutor - one-shot setup and launcher.
#
# Works in WSL, Git Bash (Windows), Linux and macOS.
#
# Usage:
#   ./setup.sh              install everything, migrate the database, start both servers
#   ./setup.sh --setup-only install and migrate, but do not start the servers
#   ./setup.sh --start-only skip installs/migration, just start the servers
#   ./setup.sh --help       show this help
#
# What it does:
#   1. Checks Python (3.10+), Node (18+) and npm
#   2. Creates backend/.env (asks for DATABASE_URL and LLM_API_KEY if missing)
#   3. Creates a Python virtualenv in backend/.venv and installs requirements
#   4. Runs npm install in frontend/ and creates frontend/.env
#   5. Applies migrations/001_init.sql to Neon (skipped if already applied)
#   6. Verifies the database connection
#   7. Starts the backend (http://localhost:8000) and frontend (http://localhost:5173)

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

MODE="all"
case "${1:-}" in
  --setup-only) MODE="setup" ;;
  --start-only) MODE="start" ;;
  -h|--help)
    sed -n '2,20p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
    exit 0
    ;;
  "") ;;
  *) echo "Unknown option: $1 (try --help)"; exit 1 ;;
esac

say()  { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
ok()   { printf '\033[1;32m  ok\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m  !!\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31mERROR:\033[0m %s\n' "$*" >&2; exit 1; }

# --------------------------------------------------------------------------
# 1. Prerequisites
# --------------------------------------------------------------------------
find_python() {
  for c in python3 python py; do
    if command -v "$c" >/dev/null 2>&1 \
       && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then
      echo "$c"
      return 0
    fi
  done
  return 1
}

if [ "$MODE" != "start" ]; then
  say "Checking prerequisites"
  PYTHON="$(find_python)" || die "Python 3.10+ not found. Install it from https://www.python.org/downloads/ (tick 'Add to PATH' on Windows) and re-run."
  ok "Python: $("$PYTHON" --version 2>&1)"

  command -v node >/dev/null 2>&1 || die "Node.js not found. Install Node 18+ from https://nodejs.org/ and re-run."
  NODE_MAJOR="$(node -p 'process.versions.node.split(".")[0]')"
  [ "$NODE_MAJOR" -ge 18 ] || die "Node 18+ required (found $(node -v))."
  ok "Node: $(node -v)"

  command -v npm >/dev/null 2>&1 || die "npm not found (it ships with Node.js)."
  ok "npm: $(npm -v)"
fi

# --------------------------------------------------------------------------
# 2. backend/.env
# --------------------------------------------------------------------------
if [ "$MODE" != "start" ]; then
  say "Configuring backend/.env"
  if [ -f "$BACKEND/.env" ]; then
    ok "backend/.env already exists - leaving it alone"
  else
    [ -f "$ROOT/.env.example" ] || die ".env.example is missing."
    cp "$ROOT/.env.example" "$BACKEND/.env"
    echo "backend/.env not found. I need two secrets (they are saved only to backend/.env)."
    echo
    read -r -p "Neon POOLED DATABASE_URL (host contains '-pooler'): " DB_URL
    [ -n "$DB_URL" ] || die "DATABASE_URL cannot be empty."
    read -r -p "Gemini API key (from https://aistudio.google.com/apikey): " API_KEY
    [ -n "$API_KEY" ] || die "LLM_API_KEY cannot be empty."
    # Use python for the replacement so special characters (&, /, |) are safe.
    DB_URL="$DB_URL" API_KEY="$API_KEY" ENV_FILE="$BACKEND/.env" "$PYTHON" - <<'PY'
import os, re
path = os.environ["ENV_FILE"]
text = open(path, encoding="utf-8").read()
text = re.sub(r"(?m)^DATABASE_URL=.*$", lambda m: "DATABASE_URL=" + os.environ["DB_URL"], text)
text = re.sub(r"(?m)^LLM_API_KEY=.*$", lambda m: "LLM_API_KEY=" + os.environ["API_KEY"], text)
open(path, "w", encoding="utf-8").write(text)
PY
    ok "wrote backend/.env"
  fi
fi

# --------------------------------------------------------------------------
# 3. Backend: virtualenv + dependencies
# --------------------------------------------------------------------------
VENV="$BACKEND/.venv"
if [ -x "$VENV/Scripts/python.exe" ]; then
  VENV_PY="$VENV/Scripts/python.exe"      # Windows (Git Bash)
else
  VENV_PY="$VENV/bin/python"              # Linux / macOS / WSL
fi

if [ "$MODE" != "start" ]; then
  say "Installing backend dependencies"
  if [ ! -d "$VENV" ]; then
    "$PYTHON" -m venv "$VENV" || die "Could not create the virtualenv. On Debian/Ubuntu/WSL run: sudo apt install python3-venv"
  fi
  if [ -x "$VENV/Scripts/python.exe" ]; then
    VENV_PY="$VENV/Scripts/python.exe"
  else
    VENV_PY="$VENV/bin/python"
  fi
  "$VENV_PY" -m pip install --quiet --upgrade pip
  "$VENV_PY" -m pip install --quiet -r "$BACKEND/requirements.txt"
  ok "backend packages installed in backend/.venv"
fi

# --------------------------------------------------------------------------
# 4. Frontend: npm install + .env
# --------------------------------------------------------------------------
if [ "$MODE" != "start" ]; then
  say "Installing frontend dependencies"
  if [ ! -f "$FRONTEND/.env" ] && [ -f "$FRONTEND/.env.example" ]; then
    cp "$FRONTEND/.env.example" "$FRONTEND/.env"
    ok "created frontend/.env"
  fi
  (cd "$FRONTEND" && npm install --no-audit --no-fund)
  ok "frontend packages installed"
fi

# --------------------------------------------------------------------------
# 5 + 6. Database migration and connection check
# --------------------------------------------------------------------------
if [ "$MODE" != "start" ]; then
  say "Applying database migration"
  (cd "$BACKEND" && "$VENV_PY" migrate.py) \
    || die "Migration failed. Check DATABASE_URL in backend/.env (it must be the pooled Neon string)."

  say "Verifying database connection"
  (cd "$BACKEND" && "$VENV_PY" verify_db.py) \
    || die "Database verification failed."

  warn "PDF export needs the Pango/GTK libraries. On Windows they are not bundled; chat works without them."
fi

if [ "$MODE" = "setup" ]; then
  say "Setup complete"
  echo "Start the app any time with:  ./setup.sh --start-only"
  exit 0
fi

# --------------------------------------------------------------------------
# 7. Start both servers
# --------------------------------------------------------------------------
[ -f "$VENV_PY" ] || [ -x "$VENV_PY" ] || die "Backend virtualenv not found. Run ./setup.sh first."
[ -d "$FRONTEND/node_modules" ] || die "Frontend packages not installed. Run ./setup.sh first."

# uvicorn --reload spawns a child worker process that actually binds the
# port; the parent PID bash captures with $! is just the reload supervisor.
# If a previous run was killed uncleanly (closed terminal, OS sleep, etc.)
# that child can be orphaned and keep holding the port, which is why
# "Address already in use" can show up even right after Ctrl+C. Free the
# ports first, best-effort, before trying to bind them again.
free_port() {
  local port="$1" pids=""
  # Every branch below must never return non-zero when the port is free
  # (the normal, expected case) - under `set -e`/`pipefail` that would kill
  # the whole script right here, silently, before the servers ever start.
  if command -v lsof >/dev/null 2>&1; then
    pids="$(lsof -ti ":$port" 2>/dev/null || true)"
  elif command -v fuser >/dev/null 2>&1; then
    pids="$(fuser "$port"/tcp 2>/dev/null | tr -s ' ' || true)"
  elif command -v netstat >/dev/null 2>&1; then
    # Git Bash on Windows: parse `netstat -ano` output.
    pids="$(netstat -ano 2>/dev/null | grep "LISTENING" | grep ":$port " | awk '{print $NF}' | sort -u || true)"
  fi
  if [ -n "$pids" ]; then
    warn "Port $port is already in use (PID(s): $(echo "$pids" | tr '\n' ' ')) - killing the leftover process from a previous run."
    for p in $pids; do kill -9 "$p" >/dev/null 2>&1 || true; done
    sleep 1
  fi
}

say "Starting servers"
free_port 8000
free_port 5173
BACK_PID=""
FRONT_PID=""

cleanup() {
  echo
  echo "Stopping servers..."
  [ -n "$BACK_PID" ]  && kill "$BACK_PID"  >/dev/null 2>&1 || true
  [ -n "$FRONT_PID" ] && kill "$FRONT_PID" >/dev/null 2>&1 || true
  sleep 0.5
  # Belt-and-suspenders: uvicorn --reload's worker child can survive the
  # parent being killed, so sweep by command line too.
  pkill -9 -f "uvicorn app.api:app" >/dev/null 2>&1 || true
  wait >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

(cd "$BACKEND" && exec "$VENV_PY" -m uvicorn app.api:app --reload --port 8000) &
BACK_PID=$!

(cd "$FRONTEND" && exec npm run dev -- --host 127.0.0.1) &
FRONT_PID=$!

echo
echo "  Backend : http://localhost:8000   (health: /health)"
echo "  Frontend: http://localhost:5173   <- open this in your browser"
echo
echo "Press Ctrl+C to stop both."

# Exit as soon as either server dies.
while kill -0 "$BACK_PID" 2>/dev/null && kill -0 "$FRONT_PID" 2>/dev/null; do
  sleep 1
done
warn "One of the servers stopped - shutting down."