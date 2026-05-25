#!/bin/bash
set -e

# Initialize data directories
mkdir -p /data/profiles

# Kill stale processes from previous container runs
pkill -f 'Xvnc :[0-9]' 2>/dev/null || true
pkill -f '\.cache/invisible-playwright/.*/firefox' 2>/dev/null || true
pkill -f xclip 2>/dev/null || true

# Clean browser lock files left on the persistent volume
find /data/profiles -maxdepth 2 -name 'SingletonLock' -delete 2>/dev/null || true
find /data/profiles -maxdepth 2 -name 'SingletonCookie' -delete 2>/dev/null || true
find /data/profiles -maxdepth 2 -name 'SingletonSocket' -delete 2>/dev/null || true
find /data/profiles -maxdepth 2 -name '.parentlock' -delete 2>/dev/null || true
find /data/profiles -maxdepth 2 -name 'lock' -delete 2>/dev/null || true

# Remove X11 lock files from previous displays
rm -f /tmp/.X1*-lock 2>/dev/null || true

# Start FastAPI (serves built React + API)
cd /app
echo ""
echo "  Invisible Browser Manager running at http://localhost:8080"
echo ""
exec uvicorn backend.main:app --host 0.0.0.0 --port 8080 --log-level warning
