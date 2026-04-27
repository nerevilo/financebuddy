#!/usr/bin/env bash
#
# FinanceBuddy one-shot installer.
#
#   bash setup.sh
#
# Idempotent. Re-run to repair venv or re-register the MCP server.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

VENV="$PROJECT_ROOT/.venv"
PY="$VENV/bin/python"
CERT="$PROJECT_ROOT/certificate.pem"
KEY="$PROJECT_ROOT/private_key.pem"

say()  { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m!! \033[0m %s\n' "$*"; }
die()  { printf '\033[1;31mxx \033[0m %s\n' "$*" >&2; exit 1; }

# 1. Python venv — needs 3.10+ for fastmcp
pick_python() {
  for cand in python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$cand" >/dev/null 2>&1; then
      ver=$("$cand" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || echo 0.0)
      major=${ver%%.*}; minor=${ver##*.}
      if [[ "$major" -ge 4 ]] || { [[ "$major" -eq 3 ]] && [[ "$minor" -ge 10 ]]; }; then
        echo "$cand"; return 0
      fi
    fi
  done
  return 1
}

if [[ ! -x "$PY" ]]; then
  PYBIN=$(pick_python) || die "Need Python ≥3.10 (try: brew install python@3.12)"
  say "Creating venv at .venv/ using $PYBIN ($("$PYBIN" --version))"
  "$PYBIN" -m venv "$VENV"
fi
say "Installing dependencies"
"$PY" -m pip install --quiet --upgrade pip
"$PY" -m pip install --quiet -r requirements.txt

# 2. Teller certs
if [[ ! -f "$CERT" || ! -f "$KEY" ]]; then
  cat <<EOF

$(warn "Teller mTLS certs not found.")

FinanceBuddy talks to your bank through Teller.io. Get your own free certs:

  1. Sign up at https://teller.io
  2. Create an application (development tier is free)
  3. Download the certificate (.pem) and private key (.pem)
  4. Place them at:
       $CERT
       $KEY
  5. Re-run: bash setup.sh

You'll also want to set TELLER_APP_ID + TELLER_ENV in a .env file
(see .env.example).

EOF
  exit 1
fi

# 3. .env scaffold
if [[ ! -f "$PROJECT_ROOT/.env" ]]; then
  say "Creating .env from .env.example"
  cp .env.example .env
  warn "Edit .env and set TELLER_APP_ID to your own Teller app id."
fi

# 4. Register MCP server with Claude Code
if ! command -v claude >/dev/null 2>&1; then
  warn "claude CLI not found on PATH — skipping MCP registration."
  warn "Install Claude Code, then re-run this script."
else
  say "Registering MCP server 'financebuddy' (user scope)"
  claude mcp remove financebuddy -s user >/dev/null 2>&1 || true
  claude mcp add -s user \
    -e "PYTHONPATH=$PROJECT_ROOT" \
    -- financebuddy "$PY" -m fb.mcp_server
fi

# 5. Link a bank (only if none yet)
HAS_BANK=$("$PY" - <<'PYEOF'
import sqlite3, os
from pathlib import Path
db = Path(os.environ.get("FB_DB_PATH", "financebuddy.db"))
if not db.exists():
    print("0"); raise SystemExit
conn = sqlite3.connect(db)
try:
    n = conn.execute("SELECT COUNT(*) FROM institutions").fetchone()[0]
    print(n)
except sqlite3.OperationalError:
    print("0")
PYEOF
)

if [[ "$HAS_BANK" == "0" ]]; then
  say "No banks linked yet. Launching Teller Connect at http://localhost:8787/"
  say "Complete the bank flow in your browser, then Ctrl-C this script."
  "$PY" -m fb.connect_server
else
  say "Found $HAS_BANK linked institution(s). Skipping Teller Connect."
  say "To add another: ./.venv/bin/python -m fb.connect_server"
fi

cat <<EOF

$(say "Done.")

Try it from Claude Code:

  /mcp                         # confirm 'financebuddy' is connected
  "what's my net worth?"       # asks the MCP server
  "sync my accounts"           # pulls fresh data from Teller

Manual sync from the shell:
  ./.venv/bin/python -m fb.sync

EOF
