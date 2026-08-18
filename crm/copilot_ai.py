"""KI-Assistent für Kaplan Sales — Google Gemini (kostenlos) oder OpenAI."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any

OPENAI_MODEL = os.getenv("COPILOT_MODEL", "gpt-4o-mini").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip()
_last_quota_exhausted = False

_SYSTEM = """Du bist der Kaplan Sales Assistent für Kaplan Solutions (B2B Bauvermittlung).
Antworte auf Deutsch, konkret und handlungsorientiert.
Du kannst: Status, Posteingang (immer erst syncen), E-Mails senden, Test-Mail an Gmail, Leads anzeigen.
Bei eingehenden Firmen-Mails: kurz zusammenfassen was zu tun ist.
Wenn der Nutzer eine Test-Mail will: send_test_email nutzen — nicht sagen „Posteingang leer“.
Projekt Duisburg: KS-2026-DU-01 (2 MFH, 14 WE)."""


def _provider() -> str:
    explicit = os.getenv("COPILOT_PROVIDER", "").strip().lower()
    if explicit in ("gemini", "openai"):
        if explicit == "gemini" and os.getenv("GEMINI_API_KEY", "").strip():
            return "gemini"
        if explicit == "openai" and os.getenv("OPENAI_API_KEY", "").strip():
            return "openai"
    if os.getenv("GEMINI_API_KEY", "").strip():
        return "gemini"
    if os.getenv("OPENAI_API_KEY", "").strip():
        return "openai"
    return ""


def configured() -> bool:
    return bool(_provider())


def provider_name() -> str:
    p = _provider()
    return {"gemini": "Gemini", "openai": "OpenAI"}.get(p, "")


def quota_exhausted() -> bool:
    return _last_quota_exhausted


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


def _tools_gemini() -> list[dict]:
    decls = []
    for tool in _tools():
        fn = tool["function"]
        decls.append(
            {
                "name": fn["name"],
                "description": fn["description"],
                "parameters": fn.get("parameters") or {"type": "object", "properties": {}},
            }
        )
    return [{"functionDeclarations": decls}]


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


def complete_json(*, system: str, user: str, max_tokens: int = 500) -> dict | None:
    """JSON-Antwort für Mail-Analyse o.ä."""
    if not configured():
        return None
    raw = _complete_text(system=system, user=user, json_mode=True, max_tokens=max_tokens)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
    return None


def _complete_text(*, system: str, user: str, json_mode: bool = False, max_tokens: int = 1200) -> str | None:
    p = _provider()
    if p == "gemini":
        return _gemini_text(system, user, json_mode=json_mode, max_tokens=max_tokens)
    if p == "openai":
        return _openai_text(system, user, json_mode=json_mode, max_tokens=max_tokens)
    return None


def _http_json(url: str, body: dict, headers: dict | None = None) -> dict:
    hdrs = {"Content-Type": "application/json", **(headers or {})}
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=hdrs, method="POST")
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.loads(resp.read())


def _gemini_request(body: dict) -> dict:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={key}"
    return _http_json(url, body)


def _openai_request(body: dict) -> dict:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    return _http_json(
        "https://api.openai.com/v1/chat/completions",
        body,
        headers={"Authorization": f"Bearer {key}"},
    )


def _gemini_text(system: str, user: str, *, json_mode: bool = False, max_tokens: int = 1200) -> str | None:
    gen: dict[str, Any] = {"temperature": 0.2 if json_mode else 0.4, "maxOutputTokens": max_tokens}
    if json_mode:
        gen["responseMimeType"] = "application/json"
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": gen,
    }
    try:
        data = _gemini_request(body)
        parts = (((data.get("candidates") or [{}])[0].get("content") or {}).get("parts") or [])
        for part in parts:
            if part.get("text"):
                return part["text"].strip()
    except urllib.error.HTTPError as exc:
        _handle_ai_error("gemini", exc)
    except Exception as exc:
        print(f"[copilot-ai] Gemini: {exc}", flush=True)
    return None


def _openai_text(system: str, user: str, *, json_mode: bool = False, max_tokens: int = 1200) -> str | None:
    body: dict[str, Any] = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2 if json_mode else 0.4,
        "max_tokens": max_tokens,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    try:
        data = _openai_request(body)
        return (((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip() or None
    except urllib.error.HTTPError as exc:
        _handle_ai_error("openai", exc)
    except Exception as exc:
        print(f"[copilot-ai] OpenAI: {exc}", flush=True)
    return None


def _handle_ai_error(provider: str, exc: urllib.error.HTTPError) -> None:
    global _last_quota_exhausted
    raw = exc.read().decode(errors="replace")
    print(f"[copilot-ai] {provider} {exc.code}: {raw[:300]}", flush=True)
    if exc.code == 429:
        _last_quota_exhausted = True


def _history_to_gemini(history: list[dict]) -> list[dict]:
    contents: list[dict] = []
    for h in history[-10:]:
        role = h.get("role")
        text = (h.get("text") or "").strip()
        if not text or role not in ("user", "assistant"):
            continue
        contents.append(
            {
                "role": "user" if role == "user" else "model",
                "parts": [{"text": text}],
            }
        )
    return contents


def _reply_gemini(user_text: str, history: list[dict]) -> str | None:
    contents = _history_to_gemini(history)
    contents.append({"role": "user", "parts": [{"text": user_text}]})

    body: dict[str, Any] = {
        "systemInstruction": {"parts": [{"text": _SYSTEM}]},
        "contents": contents,
        "tools": _tools_gemini(),
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 1200},
    }

    for _ in range(4):
        try:
            data = _gemini_request(body)
        except urllib.error.HTTPError as exc:
            _handle_ai_error("gemini", exc)
            return None
        except Exception as exc:
            print(f"[copilot-ai] Gemini: {exc}", flush=True)
            return None

        candidate = (data.get("candidates") or [{}])[0]
        parts = (candidate.get("content") or {}).get("parts") or []
        fn_calls = [p.get("functionCall") for p in parts if p.get("functionCall")]
        if fn_calls:
            for fc in fn_calls:
                name = fc.get("name") or ""
                args = fc.get("args") or {}
                if not isinstance(args, dict):
                    args = {}
                result = _run_tool(name, args)
                contents.append({"role": "model", "parts": [{"functionCall": fc}]})
                try:
                    parsed = json.loads(result)
                except json.JSONDecodeError:
                    parsed = {"result": result}
                contents.append(
                    {
                        "role": "function",
                        "parts": [{"functionResponse": {"name": name, "response": parsed}}],
                    }
                )
            body["contents"] = contents
            continue

        for part in parts:
            text = (part.get("text") or "").strip()
            if text:
                return re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        return None
    return None


def _reply_openai(user_text: str, history: list[dict]) -> str | None:
    messages: list[dict[str, Any]] = [{"role": "system", "content": _SYSTEM}]
    for h in history[-10:]:
        role = h.get("role")
        if role in ("user", "assistant"):
            messages.append({"role": role, "content": h.get("text") or ""})
    messages.append({"role": "user", "content": user_text})

    body = {
        "model": OPENAI_MODEL,
        "messages": messages,
        "tools": _tools(),
        "tool_choice": "auto",
        "temperature": 0.4,
        "max_tokens": 1200,
    }

    for _ in range(4):
        try:
            data = _openai_request(body)
        except urllib.error.HTTPError as exc:
            _handle_ai_error("openai", exc)
            return None
        except Exception as exc:
            print(f"[copilot-ai] OpenAI: {exc}", flush=True)
            return None

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
                messages.append({"role": "tool", "tool_call_id": tc.get("id"), "content": result})
            body["messages"] = messages
            continue
        text = (msg.get("content") or "").strip()
        if text:
            return re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        return None
    return None


def reply(user_text: str, history: list[dict]) -> str | None:
    global _last_quota_exhausted
    _last_quota_exhausted = False
    p = _provider()
    if p == "gemini":
        return _reply_gemini(user_text, history)
    if p == "openai":
        return _reply_openai(user_text, history)
    return None
