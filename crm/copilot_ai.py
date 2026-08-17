"""OpenAI-Assistent für Kaplan Sales (Chat vom Handy)."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any

MODEL = os.getenv("COPILOT_MODEL", "gpt-4o-mini").strip()
_last_quota_exhausted = False


def configured() -> bool:
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


def quota_exhausted() -> bool:
    return _last_quota_exhausted


def _api_key() -> str:
    return os.getenv("OPENAI_API_KEY", "").strip()


def _tools() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": "get_status",
                "description": "Outreach-Zahlen, CRM-Leads, Posteingang-Übersicht",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "sync_inbox",
                "description": "Posteingang synchronisieren (Resend/IMAP)",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_inbox",
                "description": "Letzte Mails im Posteingang anzeigen",
                "parameters": {
                    "type": "object",
                    "properties": {"limit": {"type": "integer", "default": 5}},
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "send_email",
                "description": "E-Mail an Kontakt senden (Transaktional)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "to": {"type": "string"},
                        "subject": {"type": "string"},
                        "body": {"type": "string"},
                    },
                    "required": ["to", "body"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "send_test_email",
                "description": "Test-Mail an ADMIN_EMAIL (Gmail) senden",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_hot_leads",
                "description": "Leads mit Vertrag-Status oder hoher Priorität",
                "parameters": {
                    "type": "object",
                    "properties": {"limit": {"type": "integer", "default": 8}},
                },
            },
        },
    ]


def _run_tool(name: str, args: dict) -> str:
    from crm import copilot as cp

    if name == "get_status":
        return cp._auto_status()
    if name == "sync_inbox":
        from crm.mail_inbox import sync_inbox

        r = sync_inbox()
        return json.dumps(r, ensure_ascii=False)
    if name == "list_inbox":
        from crm.mail_inbox import list_messages, sync_inbox

        sync_inbox()
        lim = int(args.get("limit") or 5)
        m = list_messages(limit=lim)
        items = [
            {
                "from": x.get("from_email"),
                "subject": x.get("subject"),
                "unread": not x.get("is_read"),
                "preview": (x.get("body") or "")[:200],
                "analysis": x.get("analysis_summary"),
                "intent": x.get("analysis_intent"),
            }
            for x in m.get("messages") or []
        ]
        return json.dumps({"total": m.get("total"), "unread": m.get("unread"), "messages": items}, ensure_ascii=False)
    if name == "send_email":
        from crm.mail_inbox import send_reply

        r = send_reply(
            to_email=args.get("to", ""),
            subject=args.get("subject") or "Kaplan Solutions",
            body=args.get("body") or "",
        )
        return json.dumps(r, ensure_ascii=False)
    if name == "send_test_email":
        from crm.copilot import _send_test_mail

        return _send_test_mail()
    if name == "list_hot_leads":
        from sheet_client import crm_snapshot

        lim = int(args.get("limit") or 8)
        snap = crm_snapshot()
        leads = snap.get("leads") or []
        hot = [
            l
            for l in leads
            if "Vertrag" in (l.get("stage") or "") or l.get("priority") in ("hot", "heiss", "🔥")
        ][:lim]
        if not hot:
            hot = leads[:lim]
        return json.dumps(
            [
                {
                    "ref": l.get("ref"),
                    "name": l.get("name"),
                    "company": l.get("company"),
                    "stage": l.get("stage"),
                    "email": l.get("email"),
                }
                for l in hot
            ],
            ensure_ascii=False,
        )
    return json.dumps({"ok": False, "error": f"Unbekanntes Tool: {name}"})


def _openai_request(body: dict) -> dict:
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {_api_key()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.loads(resp.read())


def reply(user_text: str, history: list[dict]) -> str | None:
    global _last_quota_exhausted
    _last_quota_exhausted = False
    if not configured():
        return None

    system = """Du bist der Kaplan Sales Assistent für Kaplan Solutions (B2B Bauvermittlung).
Antworte auf Deutsch, konkret und handlungsorientiert — wie ChatGPT für Kaplan Solutions.
Du kannst: Status, Posteingang (immer erst syncen), E-Mails senden, Test-Mail an Gmail, Leads anzeigen.
Bei eingehenden Firmen-Mails: kurz zusammenfassen was zu tun ist.
Wenn der Nutzer eine Test-Mail will: send_test_email nutzen — nicht sagen „Posteingang leer“.
Projekt Duisburg: KS-2026-DU-01 (2 MFH, 14 WE)."""

    messages: list[dict[str, Any]] = [{"role": "system", "content": system}]
    for h in history[-10:]:
        role = h.get("role")
        if role in ("user", "assistant"):
            messages.append({"role": role, "content": h.get("text") or ""})
    messages.append({"role": "user", "content": user_text})

    body = {
        "model": MODEL,
        "messages": messages,
        "tools": _tools(),
        "tool_choice": "auto",
        "temperature": 0.4,
        "max_tokens": 1200,
    }

    try:
        for _ in range(4):
            data = _openai_request(body)
            choice = (data.get("choices") or [{}])[0]
            msg = choice.get("message") or {}
            tool_calls = msg.get("tool_calls") or []
            if tool_calls:
                messages.append(msg)
                for tc in tool_calls:
                    fn = tc.get("function") or {}
                    name = fn.get("name") or ""
                    try:
                        args = json.loads(fn.get("arguments") or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    result = _run_tool(name, args)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.get("id"),
                            "content": result,
                        }
                    )
                body["messages"] = messages
                continue
            text = (msg.get("content") or "").strip()
            if text:
                return re.sub(r"\*\*(.+?)\*\*", r"\1", text)
            return None
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode(errors="replace")
        try:
            detail = json.loads(raw).get("error") or {}
        except json.JSONDecodeError:
            detail = {}
        code = detail.get("code") or ""
        if exc.code == 429 and code == "insufficient_quota":
            _last_quota_exhausted = True
            return None  # → Smart-Fallback ohne irreführende „429“-Meldung
        if exc.code in (401, 403):
            return None
        print(f"[copilot-ai] OpenAI {exc.code}: {raw[:300]}", flush=True)
        return None
    except Exception as exc:
        print(f"[copilot-ai] {exc}", flush=True)
        return None
    return None
