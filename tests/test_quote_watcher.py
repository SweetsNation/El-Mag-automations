from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest
from zoneinfo import ZoneInfo

import quote_watcher as qw

ET = ZoneInfo("America/New_York")
FIXTURES = Path(__file__).resolve().parent / "fixtures"
CONFIG = qw.load_config(FIXTURES / "vendors.json")
MESSAGES = qw.load_messages_from_json(FIXTURES / "gmail_messages.json")

BEFORE_CUTOFF = datetime(2026, 11, 10, 9, 0, tzinfo=ET)
ON_CUTOFF = datetime(2026, 11, 13, 9, 0, tzinfo=ET)
AFTER_CUTOFF = datetime(2026, 11, 15, 19, 0, tzinfo=ET)


def test_load_messages_from_wrapped_and_list(tmp_path: Path):
    wrapped = FIXTURES / "gmail_messages.json"
    assert len(qw.load_messages_from_json(wrapped)) == 5
    only_list = tmp_path / "list.json"
    only_list.write_text(json.dumps(MESSAGES))
    assert len(qw.load_messages_from_json(only_list)) == 5


def test_match_vendor_by_email_and_domain():
    reply = next(m for m in MESSAGES if m["id"] == "msg-example-reply")
    vendor = qw.match_vendor(reply, CONFIG["vendors"])
    assert vendor is not None
    assert vendor["name"] == "Example Sign Co"

    domain_only = {
        "id": "x",
        "from": "someone@harbor-print.example",
        "subject": "Quote",
        "snippet": "Here you go",
        "date": "2026-10-31T12:00:00-04:00",
    }
    vendor = qw.match_vendor(domain_only, CONFIG["vendors"])
    assert vendor is not None
    assert vendor["name"] == "Harbor Print Shop"


def test_unrelated_and_too_early_messages_are_ignored():
    classified = qw.classify_messages(MESSAGES, CONFIG["vendors"])
    ids = {event["message"]["id"] for event in classified}
    assert "msg-unrelated" not in ids
    assert "msg-example-too-early" not in ids
    assert "msg-example-reply" in ids
    assert "msg-harbor-already-reported" in ids
    assert "msg-palm-bounce" in ids


def test_bounce_detected_from_flag_and_headers():
    bounce = next(m for m in MESSAGES if m["id"] == "msg-palm-bounce")
    assert qw.is_bounce(bounce)
    vendor = qw.match_vendor(bounce, CONFIG["vendors"])
    assert vendor is not None
    assert vendor["name"] == "Palm Board Works"

    inferred = {
        "from": "Mailer-Daemon@example-mail.com",
        "subject": "Undelivered Mail Returned to Sender",
        "snippet": "Could not deliver to sales@quiet-vinyl.example",
        "date": "2026-10-30T12:00:00-04:00",
        "is_bounce": False,
    }
    assert qw.is_bounce(inferred)
    assert qw.match_vendor(inferred, CONFIG["vendors"])["name"] == "Quiet Vinyl Co"


def test_new_reply_is_reported(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    state_path = tmp_path / "state.json"
    empty_state = {"reported_message_ids": ["msg-harbor-already-reported"], "cutoff_reported_on": None}
    state_path.write_text(json.dumps(empty_state))

    exit_code = qw.main(
        [
            "--config",
            str(FIXTURES / "vendors.json"),
            "--state",
            str(state_path),
            "--from-json",
            str(FIXTURES / "gmail_messages.json"),
            "--now",
            "2026-11-10T09:00:00-05:00",
        ]
    )
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "New replies (1):" in out
    assert "Example Sign Co" in out
    assert "$200 plus tax" in out
    assert "New bounces (1):" in out
    assert "Palm Board Works" in out
    assert "Quiet Vinyl Co" not in out  # cutoff not reached
    assert "Harbor Print Shop" not in out  # already reported

    saved = json.loads(state_path.read_text())
    assert "msg-example-reply" in saved["reported_message_ids"]
    assert "msg-palm-bounce" in saved["reported_message_ids"]
    assert saved["cutoff_reported_on"] is None


def test_already_reported_messages_yield_empty_output_before_cutoff(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    state_path = tmp_path / "state.json"
    state_path.write_text(
        json.dumps(
            {
                "reported_message_ids": [
                    "msg-example-reply",
                    "msg-harbor-already-reported",
                    "msg-palm-bounce",
                ],
                "cutoff_reported_on": None,
            }
        )
    )
    exit_code = qw.main(
        [
            "--config",
            str(FIXTURES / "vendors.json"),
            "--state",
            str(state_path),
            "--from-json",
            str(FIXTURES / "gmail_messages.json"),
            "--now",
            "2026-11-10",
        ]
    )
    assert exit_code == 0
    assert capsys.readouterr().out == ""


def test_cutoff_lists_shops_that_never_replied():
    state = {
        "reported_message_ids": [
            "msg-example-reply",
            "msg-harbor-already-reported",
            "msg-palm-bounce",
        ],
        "cutoff_reported_on": None,
    }
    report, new_state = qw.run_watch(CONFIG, state, MESSAGES, now=ON_CUTOFF)
    assert "Shops with no reply as of cutoff 2026-11-13:" in report
    assert "Quiet Vinyl Co (sales@quiet-vinyl.example)" in report
    assert "Palm Board Works (info@palm-board.example) (bounce received)" in report
    assert "Example Sign Co" not in report.split("Shops with no reply")[1]
    assert "Harbor Print Shop" not in report.split("Shops with no reply")[1]
    assert new_state["cutoff_reported_on"] == "2026-11-13"
    # No new message section when everything was already reported
    assert "New replies" not in report


def test_cutoff_already_reported_stays_quiet():
    state = {
        "reported_message_ids": [
            "msg-example-reply",
            "msg-harbor-already-reported",
            "msg-palm-bounce",
        ],
        "cutoff_reported_on": "2026-11-13",
    }
    report, new_state = qw.run_watch(CONFIG, state, MESSAGES, now=AFTER_CUTOFF)
    assert report == ""
    assert new_state["cutoff_reported_on"] == "2026-11-13"


def test_new_reply_after_cutoff_already_reported_does_not_repeat_silent_list():
    extra = {
        "id": "msg-quiet-late",
        "from": "sales@quiet-vinyl.example",
        "subject": "Re: Quote",
        "date": "2026-11-14T10:00:00-05:00",
        "snippet": "Sorry for the delay. We can do the stand for $450 including tax.",
    }
    state = {
        "reported_message_ids": [
            "msg-example-reply",
            "msg-harbor-already-reported",
            "msg-palm-bounce",
        ],
        "cutoff_reported_on": "2026-11-13",
    }
    report, new_state = qw.run_watch(CONFIG, state, MESSAGES + [extra], now=AFTER_CUTOFF)
    assert "Quiet Vinyl Co" in report
    assert "$450 including tax" in report
    assert "Shops with no reply" not in report
    assert "msg-quiet-late" in new_state["reported_message_ids"]


def test_dry_run_does_not_write_state(tmp_path: Path):
    state_path = tmp_path / "state.json"
    qw.main(
        [
            "--config",
            str(FIXTURES / "vendors.json"),
            "--state",
            str(state_path),
            "--from-json",
            str(FIXTURES / "gmail_messages.json"),
            "--now",
            "2026-11-10T09:00:00-05:00",
            "--dry-run",
        ]
    )
    assert not state_path.exists()


def test_missing_gmail_token_exits_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("GMAIL_TOKEN_FILE", raising=False)
    with pytest.raises(SystemExit) as exc:
        # argparse won't SystemExit if we call main(); main returns 2
        raise SystemExit(
            qw.main(
                [
                    "--config",
                    str(FIXTURES / "vendors.json"),
                    "--state",
                    str(tmp_path / "state.json"),
                ]
            )
        )
    assert exc.value.code == 2


def test_format_et_uses_eastern():
    dt = datetime(2026, 10, 30, 18, 22, tzinfo=ZoneInfo("UTC"))
    # 18:22 UTC in late October 2026 is EDT (UTC-4) → 2:22 PM ET
    assert qw.format_et(dt) == "2026-10-30 2:22 PM ET"


def test_vendor_query_includes_after_clause():
    query = qw._vendor_query(CONFIG)
    assert "from:quotes@example-signs.com" in query
    assert "from:mailer-daemon" in query
    assert "after:2026/10/27" in query


def test_normalize_gmail_message():
    raw = {
        "id": "abc",
        "snippet": "Hello",
        "labelIds": ["INBOX"],
        "payload": {
            "headers": [
                {"name": "From", "value": "Quotes <quotes@example-signs.com>"},
                {"name": "To", "value": "agent@example.com"},
                {"name": "Subject", "value": "Re: Quote"},
                {"name": "Date", "value": "Fri, 30 Oct 2026 14:22:00 -0400"},
            ]
        },
    }
    normalized = qw.normalize_gmail_message(raw)
    assert normalized["id"] == "abc"
    assert "quotes@example-signs.com" in normalized["from"]
    assert normalized["subject"] == "Re: Quote"
    assert qw.match_vendor(normalized, CONFIG["vendors"])["name"] == "Example Sign Co"
