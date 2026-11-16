#!/usr/bin/env python3
"""Client text triage report for DFY CRM / GoHighLevel.

Lists conversations with unread inbound SMS, sorted by unread count then
age (oldest first). Categorizes the last message by keyword and prints
timestamps in America/New_York. Read-only: never sends a message.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

EASTERN = ZoneInfo("America/New_York")
GHL_SEARCH_URL = "https://services.leadconnectorhq.com/conversations/search"
GHL_VERSION = "2021-04-15"

# Categories are checked in this order; the first match wins.
# "pay stub" is treated as a document, not a payment, by checking documents first
# after complaints.
CATEGORY_RULES: list[tuple[str, re.Pattern[str]]] = [
    (
        "upset/complaint",
        re.compile(
            r"\b("
            r"leave me alone|angry|upset|frustrated|furious|terrible|horrible|"
            r"worst|complaint|complain|lawyer|attorney|better business bureau|"
            r"ignored|unprofessional|ridiculous|do nothing|not helping|"
            r"fed up|waste of time|no help|don't care|dont care"
            r")\b",
            re.IGNORECASE,
        ),
    ),
    (
        "document upload",
        re.compile(
            r"\b("
            r"documents?|upload|uploaded|proof of|verification|verify|"
            r"pay\s*stubs?|tax returns?|w-?2|citizenship|green card|"
            r"driver'?s license|social security card|birth certificate|"
            r"paperwork|attachment"
            r")\b",
            re.IGNORECASE,
        ),
    ),
    (
        "payment help",
        re.compile(
            r"\b("
            r"payments?|pay(ing)?|premiums?|invoice|billed|billing|"
            r"past due|overdue|declined|card declined|make a payment|"
            r"can't pay|cant pay|how (do I|to) pay"
            r")\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Marketplace application update",
        re.compile(
            r"\b("
            r"application|marketplace app|update my (application|info|income|address)|"
            r"income change|change(d)? my income|address change|moved|"
            r"report a change|household|add(ed)? my (spouse|husband|wife|kid|child|dependent)|"
            r"healthcare\.gov application"
            r")\b",
            re.IGNORECASE,
        ),
    ),
    (
        "general question",
        re.compile(
            r"(\?|\b("
            r"what is|how do|how does|when does|when do|which plan|"
            r"deductible|coverage starts?|copay|co-?pay|coinsurance|"
            r"out[- ]of[- ]pocket|question"
            r")\b)",
            re.IGNORECASE,
        ),
    ),
]

SMS_TYPES = {
    "sms",
    "type_sms",
    "campaign_sms",
    "custom_sms",
}


def eastern_now(now: datetime | None = None) -> datetime:
    if now is None:
        return datetime.now(EASTERN)
    if now.tzinfo is None:
        return now.replace(tzinfo=EASTERN)
    return now.astimezone(EASTERN)


def epoch_ms_to_eastern(value: int | float | str | None) -> datetime | None:
    if value is None or value == "":
        return None
    try:
        ms = float(value)
    except (TypeError, ValueError):
        return None
    # Allow accidental seconds-scale timestamps.
    if ms < 1e12:
        ms *= 1000
    return datetime.fromtimestamp(ms / 1000.0, tz=EASTERN)


def format_et(dt: datetime | None) -> str:
    if dt is None:
        return "unknown time"
    hour = dt.strftime("%I").lstrip("0") or "12"
    return f"{dt.strftime('%Y-%m-%d')} {hour}:{dt.strftime('%M %p')} ET"


def categorize(text: str | None) -> str:
    body = text or ""
    for label, pattern in CATEGORY_RULES:
        if pattern.search(body):
            return label
    return "other"


def message_type_is_sms(value: str | None) -> bool:
    if not value:
        return False
    return value.strip().lower() in SMS_TYPES or "sms" in value.strip().lower()


def is_inbound(value: str | None) -> bool:
    if not value:
        return False
    return value.strip().lower() in {"inbound", "in", "incoming"}


def unread_inbound_sms(conversation: dict[str, Any]) -> bool:
    unread = int(conversation.get("unreadCount") or 0)
    if unread <= 0:
        return False
    if not message_type_is_sms(conversation.get("lastMessageType")):
        return False
    # Unread SMS threads whose latest message is inbound. If the last
    # message is outbound but unreadCount is still set, include it only
    # when direction is missing (treat as inbound) or inbound.
    direction = conversation.get("lastMessageDirection")
    if direction and not is_inbound(direction):
        return False
    return True


def age_seconds(last_dt: datetime | None, now: datetime) -> float:
    if last_dt is None:
        return 0.0
    return max(0.0, (eastern_now(now) - last_dt).total_seconds())


def normalize_conversation(raw: dict[str, Any], now: datetime) -> dict[str, Any]:
    last_dt = epoch_ms_to_eastern(raw.get("lastMessageDate"))
    return {
        "id": raw.get("id") or raw.get("conversationId") or "",
        "contact_name": raw.get("contactName") or raw.get("fullName") or "Unknown",
        "last_message": (raw.get("lastMessageBody") or raw.get("lastMessage") or "").strip(),
        "last_message_dt": last_dt,
        "last_message_et": format_et(last_dt),
        "last_message_type": raw.get("lastMessageType") or "",
        "last_message_direction": raw.get("lastMessageDirection") or "",
        "unread_count": int(raw.get("unreadCount") or 0),
        "category": categorize(raw.get("lastMessageBody") or raw.get("lastMessage") or ""),
        "age_seconds": age_seconds(last_dt, now),
    }


def triage(
    conversations: list[dict[str, Any]], now: datetime | None = None
) -> list[dict[str, Any]]:
    now = eastern_now(now)
    rows = [
        normalize_conversation(conv, now)
        for conv in conversations
        if unread_inbound_sms(conv)
    ]
    rows.sort(key=lambda row: (-row["unread_count"], -row["age_seconds"], row["contact_name"]))
    return rows


def build_report(rows: list[dict[str, Any]], now: datetime | None = None) -> str:
    now = eastern_now(now)
    if not rows:
        return "No unread inbound SMS conversations.\n"

    lines = [
        f"Client text triage — {now.strftime('%Y-%m-%d')} (America/New_York)",
        f"{len(rows)} unread inbound SMS conversation{'s' if len(rows) != 1 else ''}.",
        "Sorted by unread count, then age (oldest first).",
        "",
    ]
    for row in rows:
        unread = row["unread_count"]
        unread_label = f"{unread} unread"
        lines.append(
            f"- {row['contact_name']} [{row['id']}] — {unread_label}, last {row['last_message_et']}"
        )
        lines.append(f"  Category: {row['category']}")
        body = " ".join(row["last_message"].split())
        if len(body) > 220:
            body = body[:217] + "..."
        if body:
            lines.append(f"  {body}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def conversations_from_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        if "conversations" in payload:
            return payload["conversations"]
        if "data" in payload and isinstance(payload["data"], list):
            return payload["data"]
    raise ValueError(
        "JSON input must be a list of conversations or an object with 'conversations'."
    )


def _http_json(url: str, headers: dict[str, str]) -> dict[str, Any]:
    request = Request(url, headers=headers, method="GET")
    try:
        with urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} for {url}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Request failed for {url}: {exc}") from exc
    return json.loads(body) if body else {}


def fetch_ghl_conversations(token: str, location_id: str) -> list[dict[str, Any]]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Version": GHL_VERSION,
        "Accept": "application/json",
    }
    conversations: list[dict[str, Any]] = []
    start_after_id = None
    start_after_date = None
    while True:
        params = {
            "locationId": location_id,
            "status": "unread",
            "limit": "100",
        }
        if start_after_id:
            params["startAfterId"] = start_after_id
        if start_after_date:
            params["startAfterDate"] = start_after_date
        payload = _http_json(f"{GHL_SEARCH_URL}?{urlencode(params)}", headers)
        batch = conversations_from_payload(payload) if payload else []
        if not batch:
            break
        conversations.extend(batch)
        # Stop if the API did not give a paging cursor or returned a short page.
        next_id = payload.get("startAfterId") or payload.get("nextPageId")
        next_date = payload.get("startAfterDate")
        if not next_id and not next_date:
            if len(batch) < 100:
                break
            last = batch[-1]
            next_id = last.get("id")
            next_date = last.get("lastMessageDate")
            if not next_id:
                break
        if next_id == start_after_id and next_date == start_after_date:
            break
        start_after_id = str(next_id) if next_id else None
        start_after_date = str(next_date) if next_date else None
        if len(conversations) > 5000:
            break
    return conversations


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--from-json",
        dest="from_json",
        type=Path,
        help="Read conversations from a JSON fixture instead of the GHL API.",
    )
    parser.add_argument(
        "--now",
        type=str,
        default=None,
        help="Override current time (ISO datetime) when computing age.",
    )
    return parser


def parse_now_arg(value: str | None) -> datetime | None:
    if not value:
        return None
    raw = value.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid --now value: {value}") from exc
    return eastern_now(dt)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    now = parse_now_arg(args.now)

    if args.from_json:
        conversations = conversations_from_payload(load_json(args.from_json))
    else:
        token = os.environ.get("GHL_TOKEN")
        location_id = os.environ.get("GHL_LOCATION_ID")
        if not token or not location_id:
            print(
                "Set GHL_TOKEN and GHL_LOCATION_ID, or pass --from-json.",
                file=sys.stderr,
            )
            return 2
        conversations = fetch_ghl_conversations(token, location_id)

    rows = triage(conversations, now=now)
    sys.stdout.write(build_report(rows, now=now))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
