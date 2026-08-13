"""Täglicher 8:30-Check — Bugs finden, beheben, Bestätigung per Mail."""

from __future__ import annotations

import os
import subprocess
import sys
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from outreach import config
from outreach import health
from outreach import storage

try:
    from mailer import email_configured, send_email
except ImportError:
    email_configured = lambda: False  # type: ignore
    send_email = None  # type: ignore

TZ = ZoneInfo("Europe/Berlin")
REPORT_EMAIL = os.getenv(
    "OUTREACH_HEALTH_EMAIL", os.getenv("ADMIN_EMAIL", "")
).strip()
DAEMON_LABEL = "com.kaplansolutions.outreach"
ROOT = Path(__file__).resolve().parent.parent


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str
    fixed: bool = False
    fix_note: str = ""


@dataclass
class HealthReport:
    checks: list[CheckResult] = field(default_factory=list)
    had_issues: bool = False
    all_fixed: bool = True
    cycle_ok: bool = False
    cycle_note: str = ""

    def add(self, result: CheckResult) -> None:
        self.checks.append(result)
        if not result.ok:
            self.had_issues = True
            if not result.fixed:
                self.all_fixed = False


def _launchctl_list() -> tuple[bool, str]:
    uid = os.getuid()
    for target in (f"gui/{uid}/{DAEMON_LABEL}", DAEMON_LABEL):
        r = subprocess.run(
            ["launchctl", "list", target.split("/")[-1]],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if r.returncode != 0:
            continue
        parts = r.stdout.strip().split()
        if len(parts) < 3:
            continue
        pid, status = parts[0], parts[1]
        if pid not in ("-", "0"):
            return True, f"Daemon aktiv (PID {pid})"
        return False, f"Daemon geladen, aber inaktiv (Exit {status})"
    return False, "Daemon nicht in launchctl geladen"


def _restart_daemon() -> tuple[bool, str]:
    uid = os.getuid()
    label = f"gui/{uid}/{DAEMON_LABEL}"
    r = subprocess.run(
        ["launchctl", "kickstart", "-k", label],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if r.returncode == 0:
        return True, "Daemon neu gestartet (kickstart)"
    setup = ROOT / "scripts" / "setup-outreach-daemon.sh"
    if setup.is_file():
        sr = subprocess.run(
            ["bash", str(setup)],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(ROOT),
        )
        if sr.returncode == 0:
            return True, "Daemon neu installiert (setup-outreach-daemon.sh)"
        return False, (sr.stderr or sr.stdout or "Setup fehlgeschlagen")[:200]
    return False, (r.stderr or r.stdout or "kickstart fehlgeschlagen")[:200]


def _recent_cycle_errors(within_minutes: int = 120) -> list[str]:
    log_path = config.LOG_PATH
    if not log_path.is_file():
        return []
    cutoff = datetime.now(TZ) - timedelta(minutes=within_minutes)
    errors: list[str] = []
    try:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    for line in lines[-300:]:
        if "Zyklus-Fehler" not in line:
            continue
        try:
            ts = datetime.strptime(line[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=TZ)
        except ValueError:
            errors.append(line)
            continue
        if ts >= cutoff:
            errors.append(line)
    return errors


def _check_imports() -> CheckResult:
    try:
        from outreach import bounce_sync  # noqa: F401
        from outreach import discover  # noqa: F401
        from outreach import enrich  # noqa: F401
        from outreach import reminder  # noqa: F401
        from outreach import sender  # noqa: F401
        from outreach import sheet_sync  # noqa: F401
        from outreach.runner import run_cycle  # noqa: F401
        return CheckResult("Module & Code", True, "Alle Outreach-Module laden fehlerfrei")
    except Exception as exc:
        return CheckResult("Module & Code", False, str(exc))


def _check_database() -> CheckResult:
    try:
        storage.init_db()
        n = storage.stats_summary()["queued"]
        return CheckResult("Datenbank", True, f"OK — {n} Mails in Warteschlange")
    except Exception as exc:
        if health.is_sqlite_io_error(exc):
            health.recover_db()
            try:
                storage.init_db()
                return CheckResult(
                    "Datenbank",
                    True,
                    "Wiederhergestellt nach I/O-Fehler",
                    fixed=True,
                    fix_note="DB-Recovery ausgeführt",
                )
            except Exception as exc2:
                return CheckResult("Datenbank", False, str(exc2))
        return CheckResult("Datenbank", False, str(exc))


def _check_email() -> CheckResult:
    if not email_configured():
        return CheckResult(
            "E-Mail (Resend)",
            False,
            "RESEND_API_KEY oder ADMIN_EMAIL fehlt",
        )
    if not os.getenv("RESEND_API_KEY", "").strip():
        return CheckResult("E-Mail (Resend)", False, "RESEND_API_KEY fehlt")
    return CheckResult("E-Mail (Resend)", True, "Konfiguration OK")


def _check_daemon(report: HealthReport) -> CheckResult:
    ok, detail = _launchctl_list()
    if ok:
        return CheckResult("Outreach-Daemon", True, detail)
    fixed, note = _restart_daemon()
    result = CheckResult("Outreach-Daemon", False, detail, fixed=fixed, fix_note=note)
    if fixed:
        ok2, detail2 = _launchctl_list()
        result.ok = ok2
        result.detail = detail2 if ok2 else f"{detail} → {note}, aber noch inaktiv"
    return result


def _check_log_errors(report: HealthReport) -> CheckResult | None:
    errors = _recent_cycle_errors(within_minutes=180)
    if not errors:
        return CheckResult("Fehler-Log", True, "Keine Zyklus-Fehler in den letzten 3 Stunden")
    last = errors[-1]
    msg = last.split("Zyklus-Fehler:", 1)[-1].strip() if "Zyklus-Fehler:" in last else last
    fixed, note = _restart_daemon()
    return CheckResult(
        "Fehler-Log",
        False,
        f"{len(errors)} Fehler — zuletzt: {msg[:120]}",
        fixed=fixed,
        fix_note=note if fixed else "Neustart fehlgeschlagen",
    )


def _check_yesterday_sends() -> CheckResult:
    """War gestern Werktag und wurden genug Mails versendet?"""
    yesterday = (datetime.now(TZ) - timedelta(days=1)).date().isoformat()
    wd = (datetime.now(TZ) - timedelta(days=1)).weekday()
    if wd >= 5:
        return CheckResult("Versand gestern", True, "Wochenende — kein Versand erwartet")
    c = storage.get_daily_counters(yesterday)
    total = (
        int(c.get("sent", 0))
        + int(c.get("referral_sent", 0))
        + int(c.get("bauherr_sent", 0))
    )
    if total >= 20:
        return CheckResult("Versand gestern", True, f"{total} Mails versendet")
    return CheckResult(
        "Versand gestern",
        False,
        f"Nur {total} Mails — Mac war vermutlich im Sleep oder Outreach hing",
    )


def _run_test_cycle() -> tuple[bool, str]:
    try:
        from outreach.runner import run_cycle
        from outreach import system_state

        before = (
            storage.get_counter("sent", "partner")
            + storage.get_counter("sent", "referral")
            + storage.get_counter("sent", "bauherr")
        )
        run_cycle()
        system_state.record_cycle_ok()
        after = (
            storage.get_counter("sent", "partner")
            + storage.get_counter("sent", "referral")
            + storage.get_counter("sent", "bauherr")
        )
        if after > before:
            return True, f"Test-Zyklus OK — +{after - before} Mails gesendet"
        return True, "Test-Zyklus OK — Outreach bereit"
    except Exception as exc:
        return False, f"{exc}\n{traceback.format_exc()[-400:]}"


def _build_email(report: HealthReport) -> tuple[str, str, str]:
    now = datetime.now(TZ)
    date_label = now.strftime("%d.%m.%Y %H:%M")
    s = storage.stats_summary()
    today = storage.get_daily_counters(now.date().isoformat())
    partner_sent = today.get("sent", 0)
    ref_sent = today.get("referral_sent", 0)
    bh_sent = today.get("bauherr_sent", 0)
    daily_total = (
        config.DAILY_SEND_LIMIT
        + (config.REFERRAL_DAILY_SEND_LIMIT if config.REFERRAL_ENABLED else 0)
        + (config.BAUHERR_DAILY_SEND_LIMIT if config.BAUHERR_ENABLED else 0)
    )
    sent_today = partner_sent + ref_sent + bh_sent

    if not report.had_issues and report.cycle_ok:
        subject = f"✓ Outreach Check 8:30 — Alles OK ({now.strftime('%d.%m.')})"
        status_line = "Alles in Ordnung — Outreach läuft normal."
    elif report.all_fixed and report.cycle_ok:
        subject = f"⚠ Outreach Check 8:30 — Bug behoben ({now.strftime('%d.%m.')})"
        status_line = "Es gab ein Problem — automatisch behoben. Outreach läuft wieder."
    else:
        subject = f"✗ Outreach Check 8:30 — Achtung ({now.strftime('%d.%m.')})"
        status_line = "Es gibt noch ein Problem — bitte manuell prüfen."

    lines = [
        f"Outreach Health-Check — {date_label}",
        "",
        status_line,
        "",
        "── Prüfungen ──",
    ]
    for c in report.checks:
        icon = "✓" if c.ok else ("↻" if c.fixed else "✗")
        lines.append(f"{icon} {c.name}: {c.detail}")
        if c.fix_note:
            lines.append(f"   → {c.fix_note}")

    lines.extend(
        [
            "",
            f"Test-Zyklus: {'✓ ' + report.cycle_note if report.cycle_ok else '✗ ' + report.cycle_note}",
            "",
            "── Heute ──",
            f"Versendet:     {sent_today} / {daily_total}",
            f"Warteschlange: {s['queued']}",
            f"Fenster:       {config.SEND_HOUR_START}:00–{config.SEND_HOUR_END}:00 Uhr",
            "",
            "Kaplan Solutions · Automatischer Morgen-Check",
        ]
    )
    text = "\n".join(lines)

    fix_rows = "".join(
        f"<li><strong>{c.name}</strong>: {c.detail}"
        + (f"<br><em>→ {c.fix_note}</em>" if c.fix_note else "")
        + "</li>"
        for c in report.checks
    )
    status_color = "#0b3d2e" if report.cycle_ok and (not report.had_issues or report.all_fixed) else "#b87333"
    html = f"""<!DOCTYPE html><html><body style="font-family:Arial,sans-serif;color:#1a1a1a;line-height:1.7;max-width:560px;padding:24px">
<h2 style="color:{status_color};margin:0 0 12px">{status_line}</h2>
<p style="color:#666;font-size:13px">Health-Check · {date_label}</p>
<ul style="line-height:1.9">{fix_rows}</ul>
<p><strong>Test-Zyklus:</strong> {'✓' if report.cycle_ok else '✗'} {report.cycle_note}</p>
<hr style="border:none;border-top:1px solid #ddd;margin:20px 0">
<p>Versendet heute: <strong>{sent_today}/{daily_total}</strong> · Warteschlange: <strong>{s['queued']}</strong></p>
<p style="color:#888;font-size:12px">Kaplan Solutions · Automatischer Morgen-Check 8:30</p>
</body></html>"""
    return subject, text, html


def run_daily_health_check(*, force: bool = False) -> bool:
    """Hauptfunktion — Checks, Auto-Fix, Test-Zyklus, Bestätigungs-Mail."""
    now = datetime.now(TZ)
    today = now.date().isoformat()

    if not force and storage.health_check_was_sent(today):
        print(f"[healthcheck] Bereits gesendet heute ({today})", flush=True)
        return True

    if now.weekday() >= 5 and not force:  # Sa/So
        print("[healthcheck] Wochenende — übersprungen", flush=True)
        return True

    report = HealthReport()

    report.add(_check_imports())
    report.add(_check_email())
    report.add(_check_database())
    report.add(_check_yesterday_sends())

    import_result = report.checks[0] if report.checks else None
    if import_result and import_result.ok:
        report.add(_check_daemon(report))
        log_check = _check_log_errors(report)
        if log_check:
            report.add(log_check)
            if not log_check.ok and log_check.fixed:
                report.add(_check_daemon(report))

    cycle_ok, cycle_note = _run_test_cycle() if (import_result and import_result.ok) else (False, "Import-Fehler — kein Zyklus")
    report.cycle_ok = cycle_ok
    report.cycle_note = cycle_note
    if not cycle_ok:
        report.had_issues = True
        report.all_fixed = False

    if email_configured() and REPORT_EMAIL and send_email:
        subject, text, html = _build_email(report)
        try:
            send_email(REPORT_EMAIL, subject, text, html)  # type: ignore
            storage.mark_health_check_sent(today)
            print(f"[healthcheck] Mail → {REPORT_EMAIL}: {subject}", flush=True)
        except Exception as exc:
            print(f"[healthcheck] Mail fehlgeschlagen: {exc}", flush=True)
            return False
    else:
        print("[healthcheck] Keine E-Mail konfiguriert", flush=True)

    line = (
        f"[healthcheck] {'OK' if report.cycle_ok and not report.had_issues else 'FIXED' if report.all_fixed else 'WARN'}"
        f" — cycle={'ok' if report.cycle_ok else 'fail'}"
    )
    try:
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        with config.LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(f"{now.strftime('%Y-%m-%d %H:%M:%S')} {line}\n")
    except OSError:
        pass

    return report.cycle_ok and (not report.had_issues or report.all_fixed)
