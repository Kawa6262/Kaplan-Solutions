"""KI-Assistent für Kaplan Sales — Google Gemini (kostenlos) oder OpenAI."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any

OPENAI_MODEL = os.getenv("COPILOT_MODEL", "gpt-4o-mini").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
GEMINI_MODEL_FALLBACKS = [
    m.strip()
    for m in os.getenv(
        "GEMINI_MODEL_FALLBACKS",
        "gemini-2.5-flash,gemini-2.0-flash,gemini-2.0-flash-lite",
    ).split(",")
    if m.strip()
]
_last_quota_exhausted = False
_last_error = ""

_SYSTEM = """Du bist der Kaplan Sales Assistent für Kaplan Solutions (B2B Bauvermittlung).
Antworte auf Deutsch, konkret und handlungsorientiert.
Du kannst: Status, Posteingang (immer erst syncen), E-Mails senden, Test-Mail an Gmail, Leads anzeigen.
Bei eingehenden Firmen-Mails: kurz zusammenfassen was zu tun ist.
Wenn der Nutzer eine Test-Mail will: send_test_email nutzen — nicht sagen „Posteingang leer“.
Projekt Duisburg: KS-2026-DU-01 (2 MFH, 14 WE)."""


def _gemini_key() -> str:
    for name in (
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "GOOGLE_AI_API_KEY",
        "GOOGLE_GENERATIVE_AI_KEY",
    ):
        val = os.getenv(name, "").strip()
        if val:
            return val
    return ""


def _provider() -> str:
    explicit = os.getenv("COPILOT_PROVIDER", "").strip().lower()
    has_gemini = bool(_gemini_key())
    has_openai = bool(os.getenv("OPENAI_API_KEY", "").strip())

    if explicit == "gemini":
        return "gemini" if has_gemini else ""
    if explicit == "openai":
        return "openai" if has_openai else ""
    if has_gemini:
        return "gemini"
    if has_openai:
        return "openai"
    return ""


def configured() -> bool:
    return bool(_provider())


def provider_name() -> str:
    return {"gemini": "Gemini", "openai": "OpenAI"}.get(_provider(), "")


def quota_exhausted() -> bool:
    return _last_quota_exhausted


def last_error() -> str:
    return _last_error


def diagnostics() -> dict:
    p = _provider()
    out: dict[str, Any] = {
        "ok": configured(),
        "provider": p,
        "provider_label": provider_name(),
        "gemini_key_set": bool(_gemini_key()),
        "openai_key_set": bool(os.getenv("OPENAI_API_KEY", "").strip()),
        "copilot_provider_env": os.getenv("COPILOT_PROVIDER", "").strip() or "auto",
        "model": GEMINI_MODEL if p == "gemini" else OPENAI_MODEL if p == "openai" else "",
        "last_error": _last_error,
    }
    if p == "gemini":
        discovered = _discover_gemini_model()
        out["discovered_model"] = discovered
        out["model"] = discovered or GEMINI_MODEL
        text = _gemini_text("Du antwortest nur mit einem Wort.", "Sage ok.", max_tokens=32, use_tools=False)
        out["ping_ok"] = bool(text)
        out["ping_reply"] = (text or "")[:80]
        if not text and _last_error:
            out["last_error"] = _last_error
    return out


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

        return json.dumps(sync_inbox(), ensure_ascii=False)
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

        return json.dumps(
            send_reply(
                to_email=args.get("to", ""),
                subject=args.get("subject") or "Kaplan Solutions",
                body=args.get("body") or "",
            ),
            ensure_ascii=False,
        )
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
        return _gemini_text(system, user, json_mode=json_mode, max_tokens=max_tokens, use_tools=False)
    if p == "openai":
        return _openai_text(system, user, json_mode=json_mode, max_tokens=max_tokens)
    return None


def _set_error(msg: str) -> None:
    global _last_error
    _last_error = msg[:400]


def _http_json(url: str, body: dict, headers: dict | None = None) -> dict:
    hdrs = {"Content-Type": "application/json", **(headers or {})}
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=hdrs, method="POST")
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.loads(resp.read())


_cached_gemini_model = ""


def _http_get_json(url: str) -> dict:
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def _discover_gemini_model() -> str:
    """Erstes verfügbares Flash-Modell von der Google API."""
    global _cached_gemini_model
    if _cached_gemini_model:
        return _cached_gemini_model
    key = _gemini_key()
    if not key:
        return GEMINI_MODEL
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
        data = _http_get_json(url)
        picks: list[str] = []
        for item in data.get("models") or []:
            name = (item.get("name") or "").replace("models/", "")
            methods = item.get("supportedGenerationMethods") or []
            if "generateContent" not in methods or not name:
                continue
            low = name.lower()
            if "flash" not in low:
                continue
            if any(x in low for x in ("preview", "-exp", "experimental", "thinking")):
                continue
            picks.append(name)
        for pref in ("2.5-flash", "2.0-flash", "2.0-flash-lite"):
            for name in picks:
                if pref in name:
                    _cached_gemini_model = name
                    return name
        if picks:
            _cached_gemini_model = picks[0]
            return picks[0]
    except Exception as exc:
        print(f"[copilot-ai] Gemini model discovery: {exc}", flush=True)
    return GEMINI_MODEL


def _gemini_models_to_try() -> list[str]:
    models: list[str] = []
    discovered = _discover_gemini_model()
    for m in [discovered, GEMINI_MODEL, *GEMINI_MODEL_FALLBACKS]:
        if m and m not in models:
            models.append(m)
    return models


def _gemini_request(body: dict, *, model: str | None = None) -> dict:
    key = _gemini_key()
    m = model or GEMINI_MODEL
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={key}"
    return _http_json(url, body)


def _parse_api_error(raw: str) -> str:
    try:
        detail = json.loads(raw)
        err = detail.get("error") or {}
        if isinstance(err, dict):
            return (err.get("message") or err.get("status") or raw[:200]).strip()
        return raw[:200]
    except json.JSONDecodeError:
        return raw[:200].strip()


def _read_http_error(exc: urllib.error.HTTPError) -> str:
    try:
        return exc.read().decode(errors="replace")
    except Exception:
        return str(exc)


def _gemini_request_resilient(body: dict) -> dict:
    global _cached_gemini_model
    last_msg = ""
    for model in _gemini_models_to_try():
        try:
            data = _gemini_request(body, model=model)
            _cached_gemini_model = model
            return data
        except urllib.error.HTTPError as exc:
            raw = _read_http_error(exc)
            last_msg = _parse_api_error(raw) or f"HTTP {exc.code}"
            _set_error(f"Gemini ({model}): {last_msg}")
            print(f"[copilot-ai] Gemini {model} {exc.code}: {raw[:250]}", flush=True)
            if exc.code in (400, 403, 404):
                continue
            raise RuntimeError(last_msg) from exc
    raise RuntimeError(last_msg or "Kein Gemini-Modell verfügbar")


def _extract_gemini_text(data: dict) -> str:
    candidate = (data.get("candidates") or [{}])[0]
    reason = candidate.get("finishReason") or ""
    if reason and reason not in ("STOP", "MAX_TOKENS"):
        _set_error(f"Gemini blockiert: {reason}")
    parts = (candidate.get("content") or {}).get("parts") or []
    for part in parts:
        text = (part.get("text") or "").strip()
        if text:
            return text
    prompt_feedback = data.get("promptFeedback") or {}
    if prompt_feedback.get("blockReason"):
        _set_error(f"Gemini blockiert: {prompt_feedback.get('blockReason')}")
    return ""


def _openai_request(body: dict) -> dict:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    return _http_json(
        "https://api.openai.com/v1/chat/completions",
        body,
        headers={"Authorization": f"Bearer {key}"},
    )


def _gemini_text(
    system: str,
    user: str,
    *,
    json_mode: bool = False,
    max_tokens: int = 1200,
    use_tools: bool = False,
) -> str | None:
    gen: dict[str, Any] = {"temperature": 0.2 if json_mode else 0.4, "maxOutputTokens": max_tokens}
    if json_mode:
        gen["responseMimeType"] = "application/json"
    body: dict[str, Any] = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": gen,
    }
    if use_tools:
        body["tools"] = _tools_gemini()
    try:
        data = _gemini_request_resilient(body)
        text = _extract_gemini_text(data)
        return text or None
    except RuntimeError as exc:
        _set_error(str(exc)[:400])
        print(f"[copilot-ai] Gemini: {exc}", flush=True)
    except urllib.error.HTTPError as exc:
        _handle_ai_error("gemini", exc)
    except Exception as exc:
        _set_error(str(exc)[:200])
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
        _set_error(str(exc)[:200])
        print(f"[copilot-ai] OpenAI: {exc}", flush=True)
    return None


def _handle_ai_error(provider: str, exc: urllib.error.HTTPError, raw: str = "") -> None:
    global _last_quota_exhausted
    if not raw:
        raw = _read_http_error(exc)
    msg = _parse_api_error(raw) or f"HTTP {exc.code}"
    _set_error(f"{provider}: {msg}")
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
        contents.append({"role": "user" if role == "user" else "model", "parts": [{"text": text}]})
    return contents


def _reply_gemini(user_text: str, history: list[dict]) -> str | None:
    contents = _history_to_gemini(history)
    contents.append({"role": "user", "parts": [{"text": user_text}]})
    body: dict[str, Any] = {
        "systemInstruction": {"parts": [{"text": _SYSTEM}]},
        "contents": contents,
        "tools": _tools_gemini(),
        "toolConfig": {"functionCallingConfig": {"mode": "AUTO"}},
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 1200},
    }

    for _ in range(4):
        try:
            data = _gemini_request_resilient(body)
        except RuntimeError:
            if body.get("tools"):
                text = _gemini_text(_SYSTEM, user_text, max_tokens=1200, use_tools=False)
                if text:
                    return re.sub(r"\*\*(.+?)\*\*", r"\1", text)
            return None
        except urllib.error.HTTPError as exc:
            if body.get("tools") and exc.code in (400, 404, 501):
                text = _gemini_text(_SYSTEM, user_text, max_tokens=1200, use_tools=False)
                if text:
                    return re.sub(r"\*\*(.+?)\*\*", r"\1", text)
            _handle_ai_error("gemini", exc)
            return None
        except Exception as exc:
            _set_error(str(exc)[:200])
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

        text = _extract_gemini_text(data)
        if text:
            return re.sub(r"\*\*(.+?)\*\*", r"\1", text)

    text = _gemini_text(_SYSTEM, user_text, max_tokens=1200, use_tools=False)
    if text:
        return re.sub(r"\*\*(.+?)\*\*", r"\1", text)
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
            _set_error(str(exc)[:200])
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
    global _last_quota_exhausted, _last_error
    _last_quota_exhausted = False
    _last_error = ""
    p = _provider()
    if p == "gemini":
        return _reply_gemini(user_text, history)
    if p == "openai":
        return _reply_openai(user_text, history)
    _set_error("Kein API-Key — GEMINI_API_KEY oder OPENAI_API_KEY auf Render setzen")
    return None
