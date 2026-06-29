#!/bin/bash
# Kaplan Solutions — Outreach-Daemon (LaunchAgent-Einstieg)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export PATH="/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin:${PATH:-}"

exec "$(command -v python3)" -m outreach.runner daemon
