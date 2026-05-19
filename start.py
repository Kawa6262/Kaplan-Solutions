"""Render-Start: lädt server.py und aktiviert Resend (mailer.py)."""

import server
from mailer import install

install(server)

app = server.app
