#!/usr/bin/env python3
"""Render Deploy Hook auslösen (nach git push)."""

from __future__ import annotations

import os
import sys
import urllib.request

ROOT = __import__("pathlib").Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

HOOK = os.getenv("RENDER_DEPLOY_HOOK", "").strip()
if not HOOK:
    print("RENDER_DEPLOY_HOOK fehlt — in Render: Service → Settings → Deploy Hook URL kopieren")
    sys.exit(1)

req = urllib.request.Request(HOOK, data=b"", method="POST")
with urllib.request.urlopen(req, timeout=60) as resp:
    print(f"Deploy ausgelöst (HTTP {resp.status})")
