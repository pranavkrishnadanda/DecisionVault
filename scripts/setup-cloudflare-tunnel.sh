#!/bin/bash
set -euo pipefail

PORT="${1:-8000}"

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "cloudflared not found. Installing..."
  if command -v brew >/dev/null 2>&1; then
    brew install cloudflared
  else
    echo "Homebrew is required for auto-install. Install manually: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
    exit 1
  fi
fi

echo "Starting Cloudflare quick tunnel on port ${PORT}..."
echo "Use the generated https://*.trycloudflare.com URL as SLACK_REDIRECT_BASE_URL"
cloudflared tunnel --url "http://localhost:${PORT}"
