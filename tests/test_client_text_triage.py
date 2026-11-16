from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest
from zoneinfo import ZoneInfo

import client_text_triage as triage

ET = ZoneInfo("America/New_York")
FIXTURES = Path(__file__).resolve().parent / "fixtures"
NOW = datetime(2026, 11, 15, 19, 0, tzinfo=ET)


def load_conversations() -> list[dict]:
    return triage.conversations_from_payload(
        json.loads((FIXTURES / "ghl_conversations.json").read_text())
    )


def test_categorize_all_six_labels():
    assert triage.categorize("I'm frustrated that nobody has told me what the next step is.") == "upset/complaint"
    assert triage.categorize("Can you help me upload my proof of income?") == "document upload"
    assert triage.categorize("My premium payment was declined. How do I pay?") == "payment help"
    assert triage.categorize("I need to update my application because I changed my income.") == "Marketplace application update"
    assert triage.categorize("What is a deductible?") == "general question"
    assert triage.categorize("Please call me when you can.") == "other"


def test_pay_stub_is_document_not_payment():
    assert triage.categorize("I took a photo of my pay stub for the upload.") == "document upload"


def test_epoch_ms_converts_to_eastern():
    # 2026-11-11 06:20 AM America/New_York (EST, UTC-5)
    dt = triage.epoch_ms_to_eastern(1794396000000)
    assert dt is not None
    assert dt.tzinfo is not None
    assert dt.astimezone(ET).isoformat() == "2026-11-11T06:20:00-05:00"
    assert triage.format_et(dt) == "2026-11-11 6:20 AM ET"


def test_epoch_seconds_are_accepted():
    dt = triage.epoch_ms_to_eastern(1794396000)
    assert dt is not None
    assert triage.format_et(dt) == "2026-11-11 6:20 AM ET"


def test_triage_filters_and_sorts():
    rows = triage.triage(load_conversations(), now=NOW)
    names = [row["contact_name"] for row in rows]
    # Unread inbound SMS only; email, already-read, and outbound dropped.
    assert names == [
        "Jordan Lee",    # 5 unread, oldest
        "Riley Chen",    # 3 unread, older than Sam
        "Sam Patel",     # 3 unread
        "Morgan Diaz",   # 2 unread
        "Casey Nguyen",  # 1 unread, older than Avery
        "Avery Brooks",  # 1 unread
    ]
    assert "Taylor Kim" not in names
    assert "Quinn Walsh" not in names
    assert "Jamie Ortiz" not in names

    by_name = {row["contact_name"]: row for row in rows}
    assert by_name["Jordan Lee"]["category"] == "upset/complaint"
    assert by_name["Sam Patel"]["category"] == "document upload"
    assert by_name["Riley Chen"]["category"] == "payment help"
    assert by_name["Morgan Diaz"]["category"] == "Marketplace application update"
    assert by_name["Avery Brooks"]["category"] == "general question"
    assert by_name["Casey Nguyen"]["category"] == "other"
    assert by_name["Jordan Lee"]["last_message_et"] == "2026-11-11 6:20 AM ET"
    assert by_name["Jordan Lee"]["unread_count"] == 5


def test_report_and_cli(capsys: pytest.CaptureFixture[str]):
    exit_code = triage.main(
        [
            "--from-json",
            str(FIXTURES / "ghl_conversations.json"),
            "--now",
            "2026-11-15T19:00:00-05:00",
        ]
    )
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "6 unread inbound SMS conversations." in out
    assert "Jordan Lee [conv-001]" in out
    assert "Category: upset/complaint" in out
    assert "Category: document upload" in out
    assert "Category: payment help" in out
    assert "Category: Marketplace application update" in out
    assert "Category: general question" in out
    assert "Category: other" in out
    assert "6:20 AM ET" in out
    # Privacy: fixtures have no phones, and the report should not invent any.
    assert "+1" not in out
    assert "555" not in out
    # Sort: Riley (older, 3 unread) appears before Sam (newer, 3 unread)
    assert out.index("Riley Chen") < out.index("Sam Patel")


def test_empty_conversations_message(capsys: pytest.CaptureFixture[str]):
    exit_code = triage.main(["--from-json", str(FIXTURES / "ghl_conversations_empty.json")])
    assert exit_code == 0
    assert capsys.readouterr().out == "No unread inbound SMS conversations.\n"


def test_missing_env_exits_2(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("GHL_TOKEN", raising=False)
    monkeypatch.delenv("GHL_LOCATION_ID", raising=False)
    assert triage.main([]) == 2


def test_conversations_from_payload_shapes():
    rows = [{"id": "a", "unreadCount": 1}]
    assert triage.conversations_from_payload(rows) == rows
    assert triage.conversations_from_payload({"conversations": rows}) == rows
    assert triage.conversations_from_payload({"data": rows}) == rows
    with pytest.raises(ValueError):
        triage.conversations_from_payload({"unexpected": True})
