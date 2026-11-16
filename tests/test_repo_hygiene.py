from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Real account and vendor details from prior work must not land in this repo.
FORBIDDEN = re.compile(
    r"("
    r"esal9843|"
    r"@gmail\.com|"
    r"print-it\.com|"
    r"scott@|"
    r"Carol Bailey|"
    r"863.658|"
    r"561-444|"
    r"GHL_TOKEN\s*=\s*\S+"
    r")",
    re.IGNORECASE,
)

ALLOWED_SUFFIXES = {".py", ".md", ".json", ".txt", ".gitignore"}
SKIP_PARTS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache"}


def iter_text_files():
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        if path.name == "test_repo_hygiene.py":
            continue
        if path.suffix.lower() not in ALLOWED_SUFFIXES and path.name != ".gitignore":
            continue
        yield path


def test_no_real_client_or_secret_material():
    offenders = []
    for path in iter_text_files():
        text = path.read_text(encoding="utf-8")
        # README may mention the Gmail account in setup docs — check that case below.
        if path.name == "README.md" or path.name == "SKILL.md":
            # Skills/README can name Eric's Gmail as the account to connect,
            # but must not include token values or unrelated personal numbers.
            if re.search(r"(Carol Bailey|863.658|561-444|GHL_TOKEN\s*=\s*\S+)", text, re.I):
                offenders.append(str(path.relative_to(ROOT)))
            continue
        if FORBIDDEN.search(text):
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []


def test_gitignore_covers_tokens_and_state():
    text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "state/*.json" in text
    assert "*token*.json" in text
    assert ".env" in text


def test_skill_files_exist_and_state_the_rules():
    reply = (ROOT / "skills/client-reply-drafting/SKILL.md").read_text(encoding="utf-8")
    assert "Never send without Eric's approval" in reply
    assert "Never guess about a specific client's plan" in reply
    assert "Never log into HealthCare.gov" in reply
    assert "Keep client data private" in reply
    assert "https://www.healthcare.gov/" in reply

    quotes = (ROOT / "skills/sign-vendor-quotes/SKILL.md").read_text(encoding="utf-8")
    assert "Draft for approval only" in quotes
    assert "quote_watcher.py" in quotes
    assert "cutoff" in quotes.lower()
