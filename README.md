# Eric automations

Small, tested scripts and playbooks for repetitive work at El-Mag Insurance (ACA / Healthcare Marketplace, Broward County, Florida). Timezone is America/New_York.

Scripts use Python 3 and the standard library only. Skills are markdown playbooks a person or assistant should follow. Nothing in this repo sends email or SMS; Gmail and GoHighLevel access is read-only.

Do not put real client names, phone numbers, emails, or API tokens in this repo. Copy the example config, keep tokens and state files out of git, and use `--from-json` fixtures for tests.

## What's in here

| Item | Type | Job |
| --- | --- | --- |
| `scripts/quote_watcher.py` | Script | Watch Gmail for new vendor quote replies or bounces; after a cutoff, list shops that never answered. Stays quiet when nothing is new. |
| `scripts/client_text_triage.py` | Script | List unread inbound SMS in DFY CRM / GoHighLevel, sort by unread count then age, and categorize the last message. Read-only. |
| `skills/client-reply-drafting/SKILL.md` | Skill | Draft short SMS replies to common Marketplace questions. Never send without approval; never guess a client's plan or subsidy. |
| `skills/sign-vendor-quotes/SKILL.md` | Skill | Request and compare local vendor quotes by email (draft-for-approval), then track replies until a cutoff. |

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`requirements.txt` only lists `pytest` (for tests). The scripts themselves need no third-party packages.

### Environment variables

Copy `config/vendors.example.json` to `config/vendors.json` and fill in the real shop list. That live config can stay untracked.

**Quote watcher (Gmail)**

- `GMAIL_TOKEN_FILE` — path to a Google OAuth token JSON file with `access_token`, `refresh_token`, `client_id`, `client_secret`, and optional `token_uri`. The script refreshes the access token when those fields are present. The token file is gitignored; never commit it.

**Client text triage (GoHighLevel / DFY CRM)**

- `GHL_TOKEN` — bearer token for the HighLevel API v2.
- `GHL_LOCATION_ID` — the DFY CRM location id.

The triage script calls `GET https://services.leadconnectorhq.com/conversations/search` with headers `Authorization: Bearer …` and `Version: 2021-04-15`, plus `locationId` as a query parameter.

## How to run

From the repo root:

```bash
# Vendor quote replies, live Gmail
python scripts/quote_watcher.py \
  --config config/vendors.json \
  --state state/quote_watcher.json

# Same check, offline, against a fixture
python scripts/quote_watcher.py \
  --config tests/fixtures/vendors.json \
  --state /tmp/quote_watcher_state.json \
  --from-json tests/fixtures/gmail_messages.json \
  --now 2026-11-15T19:00:00-05:00

# Client SMS triage, live HighLevel (read-only)
python scripts/client_text_triage.py

# Same report, offline
python scripts/client_text_triage.py \
  --from-json tests/fixtures/ghl_conversations.json \
  --now 2026-11-15T19:00:00-05:00
```

Useful quote-watcher flags:

- `--dry-run` — print the report but do not update the state file.
- `--now` — ISO date or datetime, for testing the cutoff.
- `--from-json` — a list of messages, or an object with a `messages` array. Each message needs `id`, `from`, `subject`, `date`, and `snippet`. Optional: `to`, `original_to`, `is_bounce`.

The watcher writes already-reported Gmail message ids to the state file. After the `cutoff_date` in the config, it also lists shops with no (non-bounce) reply, once. Later runs stay silent unless a new reply or bounce arrives.

The triage report does not include phone numbers. Categories, in match order, are: upset/complaint, document upload, payment help, Marketplace application update, general question, and other.

## Tests

```bash
python -m pytest -q
```

Tests use only the fake fixtures under `tests/fixtures/`. They do not call Gmail or HighLevel.

## Layout

```
config/vendors.example.json      Example vendor list (fake addresses)
scripts/quote_watcher.py
scripts/client_text_triage.py
skills/client-reply-drafting/SKILL.md
skills/sign-vendor-quotes/SKILL.md
state/                           Runtime state; JSON files are gitignored
tests/fixtures/                  Fake Gmail and HighLevel payloads
```
