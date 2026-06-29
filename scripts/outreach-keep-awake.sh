#!/bin/bash
# Hält den Mac werktags 8:55–18:05 wach (zusätzlich zum Daemon-caffeinate).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source <(grep -E '^(OUTREACH_HOUR_START|OUTREACH_HOUR_END|OUTREACH_WEEKDAYS_ONLY)=' "$ROOT/.env" 2>/dev/null || true)
  set +a
fi

HOUR_START="${OUTREACH_HOUR_START:-9}"
HOUR_END="${OUTREACH_HOUR_END:-18}"
WEEKDAYS_ONLY="${OUTREACH_WEEKDAYS_ONLY:-1}"

if [[ "$WEEKDAYS_ONLY" != "0" ]]; then
  DOW=$(date +%u)  # 1=Mo … 7=So
  if (( DOW >= 6 )); then
    exit 0
  fi
fi

NOW_HOUR=$(date +%H)
NOW_MIN=$(date +%M)
NOW_TOTAL=$((10#$NOW_HOUR * 60 + 10#$NOW_MIN))
START_TOTAL=$((HOUR_START * 60 - 5))   # 5 Min. Puffer vor Start
END_TOTAL=$((HOUR_END * 60 + 5))

if (( NOW_TOTAL < START_TOTAL || NOW_TOTAL >= END_TOTAL )); then
  exit 0
fi

SECONDS_LEFT=$(( (END_TOTAL - NOW_TOTAL) * 60 ))
exec /usr/bin/caffeinate -dimsu -t "$SECONDS_LEFT"
