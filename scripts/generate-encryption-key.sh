#!/bin/bash
set -euo pipefail

BACKEND_ENV_FILE="backend/.env"

KEY=$(python3 - <<'PY'
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
PY
)

if [ ! -f "$BACKEND_ENV_FILE" ]; then
  touch "$BACKEND_ENV_FILE"
fi

python3 - "$BACKEND_ENV_FILE" "$KEY" <<'PY'
from pathlib import Path
import re
import sys

file_path, key = sys.argv[1], sys.argv[2]
path = Path(file_path)
content = path.read_text() if path.exists() else ""
pattern = re.compile(r"^TOKEN_ENCRYPTION_KEY=.*$", re.MULTILINE)
line = f"TOKEN_ENCRYPTION_KEY={key}"

if pattern.search(content):
    content = pattern.sub(line, content)
else:
    if content and not content.endswith("\n"):
        content += "\n"
    content += f"{line}\n"

path.write_text(content)
PY

echo "Generated and saved TOKEN_ENCRYPTION_KEY in $BACKEND_ENV_FILE"
echo "$KEY"
