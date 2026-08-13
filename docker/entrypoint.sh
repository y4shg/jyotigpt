#!/bin/sh
# JyotiGPT all-in-one entrypoint.
# Starts the FastAPI backend (uvicorn, :8000) and the Next.js web server
# (next start, :3001). The web runs as the primary process; when it exits the
# container exits. SIGTERM/SIGINT stops both servers cleanly.

set -eu

cd /app/api
python -m uvicorn jyoti_api.app:app --host 0.0.0.0 --port 8000 &
API_PID=$!

cd /app
npm run start &
WEB_PID=$!

shutdown() {
  kill "$API_PID" "$WEB_PID" 2>/dev/null || true
}
trap shutdown INT TERM

wait "$WEB_PID"
