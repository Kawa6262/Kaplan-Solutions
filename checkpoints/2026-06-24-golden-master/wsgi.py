"""Einstieg für Render (Resend) — Dateiname wsgi.py vermeidet Konflikte mit start.sh."""

import sys

print("[wsgi] Lade Anwendung …", flush=True)

try:
    import server
    from mailer import install

    install(server)
    app = server.app
    print("[wsgi] OK — bereit.", flush=True)
except Exception as exc:
    print(f"[wsgi] FEHLER beim Start: {exc!r}", flush=True)
    raise
