#!/bin/bash
set -euo pipefail

PORT="${1:-8000}"

if ! command -v ngrok >/dev/null 2>&1; then
  echo "ngrok not found. Installing..."
  if command -v brew >/dev/null 2>&1; then
    brew install ngrok/ngrok/ngrok
  else
    echo "Homebrew is required for auto-install. Install ngrok manually: https://ngrok.com/download"
    exit 1
  fi
fi

echo "Starting ngrok tunnel on port ${PORT}..."
ngrok http "$PORT" --log=stdout > /tmp/decisionvault-ngrok.log 2>&1 &
NGROK_PID=$!

sleep 3

URL=$(curl -s http://127.0.0.1:4040/api/tunnels | python3 -c 'import sys, json; data=json.load(sys.stdin); print(next((t["public_url"] for t in data.get("tunnels", []) if t.get("public_url", "").startswith("https://")), ""))')

if [ -z "$URL" ]; then
  echo "Failed to detect ngrok HTTPS URL. Check /tmp/decisionvault-ngrok.log"
  kill "$NGROK_PID" || true
  exit 1
fi

echo ""
echo "ngrok HTTPS URL: $URL"
echo "Set this in backend/.env:"
echo "  SLACK_REDIRECT_BASE_URL=$URL"
echo ""
echo "Update Slack app redirect URL to:"
echo "  $URL/api/slack/callback"
echo ""
echo "Note: free ngrok URLs change when the tunnel restarts."
echo "ngrok process PID: $NGROK_PID"
