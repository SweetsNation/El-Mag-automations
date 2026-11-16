# Sign and vendor quote requests

Request and compare local vendor quotes by email for El-Mag Insurance jobs (for example a sign panel and a two-post stand), then track replies until a cutoff. Use this skill when Eric needs prices from South Florida shops and wants drafts he can send himself.

The [quote watcher](../../scripts/quote_watcher.py) script is the follow-up half of this playbook: it reports new Gmail replies or bounces and, after the cutoff, lists shops that never answered.

## Hard rules

- **Draft for approval only.** Never send an email, text, or form to a vendor unless Eric has approved that exact message and recipient.
- Prefer **local pickup in South Florida** (Broward and nearby) when freight is expensive. Ask for pickup city, lead time, and whether tax is included.
- Do not invent prices, lead times, or that a shop can do the job. If a quote is incomplete, draft a short follow-up.
- Keep a clean vendor list in `config/vendors.json` (copy `config/vendors.example.json`). Use real shop emails only in that private config and in Gmail — never commit real vendor threads or personal addresses to git if this repo is shared more widely than Eric's private copy.
- Gmail stays on Eric's account. The watcher reads mail; it does not send.

## Requesting quotes

1. Confirm the job specs with Eric before writing shops. Typical sign-job details to lock down:
   - What is being made (panel, stand, or both).
   - Size (for example 48" W × 24" H).
   - Material and finish (for example 3mm ACM, vinyl/PVC posts, color).
   - Single-sided vs double-sided.
   - Artwork status: final file, or a rebuild/proof needed.
   - Pickup vs shipping, and the preferred pickup area.
2. Build a vendor list of local shops. Record each shop's name, email (and domain), and the date the request will be sent. Set a cutoff date — enough time for a reply, not so long that the job stalls.
3. Draft one clear email per shop (or one shared template with the shop name filled in). Include the specs, ask for:
   - Price, and whether tax is included.
   - Lead time after approval (and after artwork proof, if needed).
   - Pickup location and hours.
   - Any extra cost to rebuild artwork or change a proof.
4. Show Eric the drafts. He sends them from his Gmail account (the address in the vendor-config `account` field, unless he says otherwise). After they go out, add the shops to `config/vendors.json` and set `cutoff_date` and each `date_sent`.

## Tracking replies

1. Run the quote watcher on a weekday schedule (hourly during work hours is enough):

   ```bash
   python scripts/quote_watcher.py --config config/vendors.json --state state/quote_watcher.json
   ```

2. The script prints a report only when there is something new: a reply or a bounce that has not been reported yet. Otherwise it stays quiet.
3. When a quote arrives, record price, tax, lead time, pickup city, and any caveats (artwork fees, single vs double sided, upgrades). Compare in a short table for Eric — do not pick a vendor for him unless he asks.
4. If a bounce arrives, draft a follow-up to a working address only if Eric wants one.
5. On the cutoff date the watcher lists shops that never replied (and notes if a bounce was received). Eric can choose to follow up, drop them, or extend the cutoff in the config. The "no reply" list is reported once unless state is cleared.
6. After Eric chooses a shop, draft the approval (proof request, pickup date, single vs double sided, and any artwork rebuild fee). He sends it. Then stop watching that job or trim the vendor list.

## Comparing quotes

For each complete quote, line up:

| Shop | Price (tax in?) | Lead time | Pickup | Notes |
| --- | --- | --- | --- | --- |
| … | … | … | … | … |

Call out missing pieces (frame size not confirmed, no lead time, freight vs pickup) before treating a quote as final. If two options exist (for example a standard stand vs one with decorative trim), show both and let Eric choose.

## After the cutoff

- Tell Eric which shops replied, which bounced, and which stayed silent.
- Do not nag a silent shop unless he asks for a follow-up draft.
- Turn the watcher off or update the config when the job is awarded or abandoned, so old threads are not re-reported.
