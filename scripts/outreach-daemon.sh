#!/bin/bash
# Kaplan Solutions — Outreach-Daemon (LaunchAgent-Einstieg)
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export PATH="/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin:${PATH:-}"

if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env" 2>/dev/null || true
  set +a
fi

exec "$(command -v python3)" -m outreach.runner daemon
