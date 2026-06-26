#!/usr/bin/env python3
"""DNS-Check für E-Mail-Zustellbarkeit (SPF, DKIM, DMARC)."""

from __future__ import annotations

import subprocess
import sys


def dig_txt(name: str) -> list[str]:
    try:
        out = subprocess.check_output(["dig", "+short", "TXT", name], text=True, timeout=10)
        return [line.strip().strip('"') for line in out.splitlines() if line.strip()]
    except Exception:
        return []


def main() -> None:
    domain = "kaplan-solutions.de"
    print(f"=== DNS Zustellbarkeit: {domain} ===\n")

    root = dig_txt(domain)
    dmarc = dig_txt(f"_dmarc.{domain}")
    dkim = dig_txt(f"resend._domainkey.{domain}")
    send = dig_txt(f"send.{domain}")

    ok = True

    spf = [r for r in root + send if "v=spf1" in r.lower()]
    print("SPF:", "OK" if spf else "FEHLT")
    for r in spf:
        print(f"  {r[:120]}")

    print("\nDKIM (resend._domainkey):", "OK" if dkim else "FEHLT")
    for r in dkim:
        print(f"  {r[:80]}...")

    print("\nDMARC:", "OK" if dmarc else "FEHLT (empfohlen)")
    for r in dmarc:
        print(f"  {r}")

    if not spf or not dkim:
        ok = False
        print("\n→ Resend Dashboard → Domains → kaplan-solutions.de → DNS in Strato eintragen")
        print("  Anleitung: RESEND-SETUP.md")

    if ok:
        print("\nDNS technisch OK. Bei Spam trotzdem: Warm-up (40 Mails/Tag), neues Template aktiv.")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
