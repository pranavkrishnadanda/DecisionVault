#!/bin/bash
set -euo pipefail

PORT="${1:-3000}"
FRONTEND_ENV_FILE="frontend/.env.local"
BACKEND_ENV_FILE="backend/.env"

if ! command -v ngrok >/dev/null 2>&1; then
  echo "ngrok not found. Installing..."
  if command -v brew >/dev/null 2>&1; then
    brew install ngrok/ngrok/ngrok
  else
    echo "Homebrew is required for auto-install. Install ngrok manually: https://ngrok.com/download"
    exit 1
  fi
fi

if pgrep -x ngrok >/dev/null 2>&1; then
  echo "Stopping existing ngrok process..."
  pkill -x ngrok || true
  sleep 1
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

FRONTEND_CALLBACK_URL="${URL}/oauth/slack/callback"
NGROK_HOST=$(python3 - "$URL" <<'PY'
from urllib.parse import urlparse
import sys
print(urlparse(sys.argv[1]).hostname or "")
PY
)

update_env_key() {
  local file="$1"
  local key="$2"
  local value="$3"

  if [ ! -f "$file" ]; then
    touch "$file"
  fi

  python3 - "$file" "$key" "$value" <<'PY'
from pathlib import Path
import re
import sys

file_path, key, value = sys.argv[1], sys.argv[2], sys.argv[3]
path = Path(file_path)
content = path.read_text() if path.exists() else ""
pattern = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)
line = f"{key}={value}"

if pattern.search(content):
    content = pattern.sub(line, content)
else:
    if content and not content.endswith("\n"):
        content += "\n"
    content += f"{line}\n"

path.write_text(content)
PY
}

update_env_key "$FRONTEND_ENV_FILE" "NEXT_PUBLIC_SLACK_REDIRECT_URI" "$FRONTEND_CALLBACK_URL"
update_env_key "$BACKEND_ENV_FILE" "SLACK_REDIRECT_BASE_URL" "$URL"

python3 - "$BACKEND_ENV_FILE" "$NGROK_HOST" <<'PY'
from pathlib import Path
import re
import sys

env_file, host = sys.argv[1], sys.argv[2].strip()
if not host:
    raise SystemExit(0)

path = Path(env_file)
content = path.read_text() if path.exists() else ""
m = re.search(r"^ALLOWED_HOSTS=(.*)$", content, re.MULTILINE)

if m:
    parts = [v.strip() for v in m.group(1).split(",") if v.strip()]
    if host not in parts:
        parts.append(host)
    line = "ALLOWED_HOSTS=" + ",".join(parts)
    content = re.sub(r"^ALLOWED_HOSTS=.*$", line, content, flags=re.MULTILINE)
else:
    if content and not content.endswith("\n"):
        content += "\n"
    content += f"ALLOWED_HOSTS=localhost,127.0.0.1,{host}\n"

path.write_text(content)
PY

echo ""
echo "ngrok HTTPS URL: $URL"
echo "Updated files:"
echo "  $FRONTEND_ENV_FILE -> NEXT_PUBLIC_SLACK_REDIRECT_URI=$FRONTEND_CALLBACK_URL"
echo "  $BACKEND_ENV_FILE -> SLACK_REDIRECT_BASE_URL=$URL"
echo "  $BACKEND_ENV_FILE -> ALLOWED_HOSTS now includes $NGROK_HOST"
echo ""
echo "Set this exact Slack OAuth redirect URL in Slack App config:"
echo "  $FRONTEND_CALLBACK_URL"
echo ""
echo "Note: free ngrok URLs change when the tunnel restarts."
echo "ngrok process PID: $NGROK_PID"
