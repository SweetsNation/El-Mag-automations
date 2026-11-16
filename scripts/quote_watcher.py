#!/usr/bin/env python3
"""Vendor quote-reply watcher.

Checks Gmail (or a JSON fixture) for replies and bounces from shops that
were emailed for quotes. Prints a plain-text report of new messages only.
After the cutoff date, also lists shops that never replied — once.

Prints nothing when there is nothing new. Never sends email.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date, datetime
from email.utils import parseaddr, parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

EASTERN = ZoneInfo("America/New_York")
GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"
DEFAULT_TOKEN_URI = "https://oauth2.googleapis.com/token"
BOUNCE_FROM_RE = re.compile(
    r"(mailer-daemon|postmaster|mail-daemon)@", re.IGNORECASE
)
BOUNCE_SUBJECT_RE = re.compile(
    r"(undeliverable|undelivered|delivery status|returned mail|"
    r"delivery failure|mail delivery failed|failure notice)",
    re.IGNORECASE,
)
EMAIL_RE = re.compile(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", re.IGNORECASE)


def eastern_now(now: datetime | None = None) -> datetime:
    if now is None:
        return datetime.now(EASTERN)
    if now.tzinfo is None:
        return now.replace(tzinfo=EASTERN)
    return now.astimezone(EASTERN)


def parse_iso_date(value: str) -> date:
    return date.fromisoformat(value)


def parse_message_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            dt = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=EASTERN)
    return dt.astimezone(EASTERN)


def format_et(dt: datetime) -> str:
    dt = eastern_now(dt)
    hour = dt.strftime("%I").lstrip("0") or "12"
    return f"{dt.strftime('%Y-%m-%d')} {hour}:{dt.strftime('%M %p')} ET"


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_config(path: Path) -> dict[str, Any]:
    config = load_json(path)
    if "vendors" not in config or "cutoff_date" not in config:
        raise ValueError("Config must include 'vendors' and 'cutoff_date'.")
    return config


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"reported_message_ids": [], "cutoff_reported_on": None}
    state = load_json(path)
    state.setdefault("reported_message_ids", [])
    state.setdefault("cutoff_reported_on", None)
    return state


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2)
        handle.write("\n")


def parse_from_header(value: str | None) -> tuple[str, str, str]:
    """Return (display_name, email, domain) from a From header."""
    display, email = parseaddr(value or "")
    email = (email or "").strip().lower()
    if not email and value:
        match = EMAIL_RE.search(value)
        email = match.group(0).lower() if match else ""
    domain = email.split("@", 1)[1] if "@" in email else ""
    return display, email, domain


def is_bounce(message: dict[str, Any]) -> bool:
    if message.get("is_bounce") is True:
        return True
    _, email, _ = parse_from_header(message.get("from") or "")
    subject = message.get("subject") or ""
    if email and BOUNCE_FROM_RE.search(email):
        return True
    if BOUNCE_SUBJECT_RE.search(subject):
        return True
    return False


def emails_and_domains_in_text(*parts: str | None) -> tuple[set[str], set[str]]:
    emails: set[str] = set()
    domains: set[str] = set()
    for part in parts:
        if not part:
            continue
        for match in EMAIL_RE.findall(part):
            address = match.lower()
            emails.add(address)
            domains.add(address.split("@", 1)[1])
    return emails, domains


def match_vendor(
    message: dict[str, Any], vendors: list[dict[str, Any]]
) -> dict[str, Any] | None:
    _, from_email, from_domain = parse_from_header(message.get("from") or "")
    found_emails, found_domains = emails_and_domains_in_text(
        message.get("from"),
        message.get("to"),
        message.get("original_to"),
        message.get("subject"),
        message.get("snippet"),
    )
    if from_email:
        found_emails.add(from_email)
    if from_domain:
        found_domains.add(from_domain)

    for vendor in vendors:
        vendor_email = (vendor.get("email") or "").strip().lower()
        vendor_domain = (vendor.get("domain") or "").strip().lower()
        if vendor_email and vendor_email in found_emails:
            return vendor
        if vendor_domain and vendor_domain in found_domains:
            return vendor
    return None


def message_datetime(message: dict[str, Any]) -> datetime | None:
    return parse_message_datetime(message.get("date"))


def is_after_date_sent(message: dict[str, Any], vendor: dict[str, Any]) -> bool:
    sent = vendor.get("date_sent")
    if not sent:
        return True
    dt = message_datetime(message)
    if dt is None:
        return True
    return dt.date() >= parse_iso_date(sent)


def classify_messages(
    messages: list[dict[str, Any]], vendors: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Attach vendor + bounce flag to messages that match a vendor after date_sent."""
    classified: list[dict[str, Any]] = []
    for message in messages:
        vendor = match_vendor(message, vendors)
        if vendor is None or not is_after_date_sent(message, vendor):
            continue
        classified.append(
            {
                "message": message,
                "vendor": vendor,
                "is_bounce": is_bounce(message),
            }
        )
    return classified


def new_events(
    classified: list[dict[str, Any]], reported_ids: set[str]
) -> list[dict[str, Any]]:
    fresh = []
    for event in classified:
        msg_id = str(event["message"].get("id") or "")
        if not msg_id or msg_id in reported_ids:
            continue
        fresh.append(event)
    fresh.sort(key=lambda event: message_datetime(event["message"]) or datetime.min.replace(tzinfo=EASTERN))
    return fresh


def vendors_without_reply(
    vendors: list[dict[str, Any]], classified: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    replied: set[str] = set()
    bounced: set[str] = set()
    for event in classified:
        key = event["vendor"].get("email") or event["vendor"].get("name")
        if event["is_bounce"]:
            bounced.add(key)
        else:
            replied.add(key)
    silent = []
    for vendor in vendors:
        key = vendor.get("email") or vendor.get("name")
        if key in replied:
            continue
        row = dict(vendor)
        row["had_bounce"] = key in bounced
        silent.append(row)
    return silent


def build_report(
    new: list[dict[str, Any]],
    silent: list[dict[str, Any]] | None,
    cutoff: date,
    now: datetime,
) -> str:
    if not new and not silent:
        return ""

    lines = [f"Vendor quote replies — {eastern_now(now).strftime('%Y-%m-%d')} (America/New_York)", ""]

    replies = [event for event in new if not event["is_bounce"]]
    bounces = [event for event in new if event["is_bounce"]]

    if replies:
        lines.append(f"New replies ({len(replies)}):")
        for event in replies:
            lines.extend(_event_lines(event))
        lines.append("")

    if bounces:
        lines.append(f"New bounces ({len(bounces)}):")
        for event in bounces:
            lines.extend(_event_lines(event, bounce=True))
        lines.append("")

    if silent is not None:
        if silent:
            lines.append(f"Shops with no reply as of cutoff {cutoff.isoformat()}:")
            for vendor in silent:
                bounce_note = " (bounce received)" if vendor.get("had_bounce") else ""
                email = vendor.get("email") or vendor.get("domain") or ""
                lines.append(f"- {vendor.get('name', 'Unknown')} ({email}){bounce_note}")
        else:
            lines.append(f"All shops replied as of cutoff {cutoff.isoformat()}.")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _event_lines(event: dict[str, Any], bounce: bool = False) -> list[str]:
    message = event["message"]
    vendor = event["vendor"]
    dt = message_datetime(message)
    when = format_et(dt) if dt else "unknown time"
    verb = "bounced" if bounce else ""
    timing = f"{verb} {when}".strip() if bounce else when
    email = vendor.get("email") or ""
    subject = (message.get("subject") or "").strip()
    snippet = " ".join((message.get("snippet") or "").split())
    if len(snippet) > 200:
        snippet = snippet[:197] + "..."
    lines = [f"- {vendor.get('name', 'Unknown')} <{email}> — {timing}"]
    if subject:
        lines.append(f"  Subject: {subject}")
    if snippet:
        lines.append(f"  {snippet}")
    return lines


def should_include_cutoff(
    now: datetime, cutoff: date, cutoff_reported_on: str | None
) -> bool:
    if eastern_now(now).date() < cutoff:
        return False
    return cutoff_reported_on is None


def run_watch(
    config: dict[str, Any],
    state: dict[str, Any],
    messages: list[dict[str, Any]],
    now: datetime | None = None,
) -> tuple[str, dict[str, Any]]:
    now = eastern_now(now)
    cutoff = parse_iso_date(config["cutoff_date"])
    vendors = config["vendors"]
    reported_ids = set(state.get("reported_message_ids") or [])

    classified = classify_messages(messages, vendors)
    fresh = new_events(classified, reported_ids)
    include_cutoff = should_include_cutoff(now, cutoff, state.get("cutoff_reported_on"))
    silent = vendors_without_reply(vendors, classified) if include_cutoff else None

    report = build_report(fresh, silent, cutoff, now)

    new_state = {
        "reported_message_ids": sorted(reported_ids | {str(e["message"]["id"]) for e in fresh if e["message"].get("id")}),
        "cutoff_reported_on": cutoff.isoformat() if include_cutoff else state.get("cutoff_reported_on"),
    }
    return report, new_state


# --- Gmail (optional live path) ------------------------------------------------

def _http_json(
    url: str,
    headers: dict[str, str] | None = None,
    data: bytes | None = None,
    method: str | None = None,
) -> dict[str, Any]:
    request = Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} for {url}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Request failed for {url}: {exc}") from exc
    return json.loads(body) if body else {}


def refresh_access_token(token: dict[str, Any]) -> dict[str, Any]:
    token_uri = token.get("token_uri") or DEFAULT_TOKEN_URI
    payload = urlencode(
        {
            "grant_type": "refresh_token",
            "refresh_token": token["refresh_token"],
            "client_id": token["client_id"],
            "client_secret": token["client_secret"],
        }
    ).encode("utf-8")
    refreshed = _http_json(
        token_uri,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data=payload,
        method="POST",
    )
    token = dict(token)
    token["access_token"] = refreshed["access_token"]
    if refreshed.get("refresh_token"):
        token["refresh_token"] = refreshed["refresh_token"]
    return token


def load_gmail_token(path: Path) -> dict[str, Any]:
    token = load_json(path)
    if not token.get("access_token") and not token.get("refresh_token"):
        raise ValueError(f"No access_token or refresh_token in {path}")
    if token.get("refresh_token") and token.get("client_id") and token.get("client_secret"):
        # Always refresh so a stale access token does not fail the run.
        token = refresh_access_token(token)
    return token


def _gmail_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}


def _header_map(gmail_message: dict[str, Any]) -> dict[str, str]:
    headers = {}
    payload = gmail_message.get("payload") or {}
    for item in payload.get("headers") or []:
        name = (item.get("name") or "").lower()
        if name:
            headers[name] = item.get("value") or ""
    return headers


def normalize_gmail_message(gmail_message: dict[str, Any]) -> dict[str, Any]:
    headers = _header_map(gmail_message)
    return {
        "id": gmail_message.get("id"),
        "from": headers.get("from", ""),
        "to": headers.get("to", ""),
        "subject": headers.get("subject", ""),
        "date": headers.get("date", ""),
        "snippet": gmail_message.get("snippet") or "",
        "labels": gmail_message.get("labelIds") or [],
        "is_bounce": False,
    }


def _vendor_query(config: dict[str, Any]) -> str:
    from datetime import timedelta

    clauses = []
    earliest: date | None = None
    for vendor in config["vendors"]:
        email = (vendor.get("email") or "").strip()
        domain = (vendor.get("domain") or "").strip()
        if email:
            clauses.append(f"from:{email}")
        email_domain = email.split("@")[-1] if email else ""
        if domain and domain != email_domain:
            clauses.append(f"from:{domain}")
        if vendor.get("date_sent"):
            sent = parse_iso_date(vendor["date_sent"])
            earliest = sent if earliest is None else min(earliest, sent)
    clauses.append("from:mailer-daemon")
    clauses.append("from:postmaster")
    query = " OR ".join(clauses)
    if earliest:
        # Gmail "after:" is exclusive; include the day before the earliest send.
        after = (earliest - timedelta(days=1)).isoformat().replace("-", "/")
        query = f"({query}) after:{after}"
    return query


def fetch_gmail_messages(token: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
    access_token = token["access_token"]
    query = _vendor_query(config)
    messages: list[dict[str, Any]] = []
    page_token = None
    while True:
        params = {"q": query, "maxResults": "100"}
        if page_token:
            params["pageToken"] = page_token
        listing = _http_json(
            f"{GMAIL_API}/messages?{urlencode(params)}",
            headers=_gmail_headers(access_token),
        )
        for stub in listing.get("messages") or []:
            raw = _http_json(
                f"{GMAIL_API}/messages/{stub['id']}?format=metadata"
                "&metadataHeaders=From&metadataHeaders=To"
                "&metadataHeaders=Subject&metadataHeaders=Date",
                headers=_gmail_headers(access_token),
            )
            messages.append(normalize_gmail_message(raw))
        page_token = listing.get("nextPageToken")
        if not page_token:
            break
    return messages


def load_messages_from_json(path: Path) -> list[dict[str, Any]]:
    payload = load_json(path)
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and "messages" in payload:
        return payload["messages"]
    raise ValueError("JSON input must be a list of messages or an object with 'messages'.")


def parse_now_arg(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return parse_message_datetime(value) or eastern_now(
            datetime.combine(parse_iso_date(value), datetime.min.time())
        )
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid --now value: {value}") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/vendors.json"),
        help="Vendor list and cutoff date (JSON).",
    )
    parser.add_argument(
        "--state",
        type=Path,
        default=Path("state/quote_watcher.json"),
        help="State file of already-reported message ids.",
    )
    parser.add_argument(
        "--from-json",
        dest="from_json",
        type=Path,
        help="Read messages from a JSON fixture instead of the Gmail API.",
    )
    parser.add_argument(
        "--now",
        type=str,
        default=None,
        help="Override current time (ISO date or datetime) for cutoff tests.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the report but do not update the state file.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config(args.config)
    state = load_state(args.state)
    now = parse_now_arg(args.now)

    if args.from_json:
        messages = load_messages_from_json(args.from_json)
    else:
        token_path = os.environ.get("GMAIL_TOKEN_FILE")
        if not token_path:
            print(
                "Set GMAIL_TOKEN_FILE to an OAuth token JSON path, or pass --from-json.",
                file=sys.stderr,
            )
            return 2
        token = load_gmail_token(Path(token_path))
        messages = fetch_gmail_messages(token, config)

    report, new_state = run_watch(config, state, messages, now=now)
    if report:
        sys.stdout.write(report)
    if not args.dry_run:
        save_state(args.state, new_state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
