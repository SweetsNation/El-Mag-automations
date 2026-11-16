# Client reply drafting

Draft short, warm, plain-English SMS replies to common Healthcare Marketplace questions for Eric Salinas (El-Mag Insurance, Broward County, Florida). Use this skill when a client texts a question about coverage, deadlines, documents, payments, or their application.

The [client text triage](../../scripts/client_text_triage.py) script can list unread inbound SMS and categorize them. This skill is for writing the reply. It does not send anything.

## Hard rules

- **Never send without Eric's approval.** Draft the text, then stop. Eric sends it himself from DFY CRM, or explicitly asks for a send after reviewing the draft.
- **Never guess about a specific client's plan, subsidy, eligibility, premium, or enrollment status.** If the answer depends on that client's application, say you will look it up and get back to them, and flag it for Eric.
- **Never log into HealthCare.gov as the client. Never take or process a payment.** Point the client to their own Marketplace account or insurer payment page, or tell them Eric will walk them through it.
- **Keep client data private.** Do not paste names, phone numbers, dates of birth, SSNs, income, or case details into other chats, tickets, or public tools. Do not put real client data in fixtures, logs, or git.
- Stay in Eric's voice: short sentences, warm, no jargon, no exclamation-point piles, no baby talk.
- If the latest message is an upset or complaint, acknowledge the frustration first, then say what Eric will do next. Do not get defensive.
- Official links below are for Eric and, when helpful, to share with a client. Prefer one link over a stack of them.

## How to draft

1. Read the full thread, not just the last text.
2. Categorize the ask (application update, document upload, payment help, general question, complaint, other).
3. If it is a general Marketplace question, draft from the FAQ below and official pages.
4. If it is about that client's plan, documents already on file, subsidy, or a payment that already posted, draft a holding reply and flag it for Eric. Do not invent a status.
5. Keep the draft to a few short sentences, in English, at a 6th-to-8th-grade reading level. Offer a call if the topic is easier to talk through.
6. Show Eric the draft and wait.

## FAQ template

Use these answers as a starting point. Confirm dates each open-enrollment season; do not hard-code a year if you have not checked [HealthCare.gov dates and deadlines](https://www.healthcare.gov/quick-guide/dates-and-deadlines/).

### When can I enroll or change a plan?

Open enrollment is the yearly window to apply or change Marketplace coverage. Outside that window, a client usually needs a qualifying life event for a Special Enrollment Period (for example, losing other coverage, moving, marriage, or a new child). Point Eric to official dates before naming one.

- [Open enrollment period](https://www.healthcare.gov/glossary/open-enrollment-period/)
- [Special enrollment period](https://www.healthcare.gov/glossary/special-enrollment-period/)
- [Dates and deadlines](https://www.healthcare.gov/quick-guide/dates-and-deadlines/)
- [Coverage outside open enrollment](https://www.healthcare.gov/coverage-outside-open-enrollment/)

Draft shape: "You can apply or change plans during open enrollment. Outside that window you usually need a qualifying life event. I'll confirm the current dates and what applies to you."

### When does coverage start?

Start dates depend on when the client enrolls and whether it is open enrollment or a special enrollment. Do not invent an effective date.

- [Dates and deadlines](https://www.healthcare.gov/quick-guide/dates-and-deadlines/)
- [Get coverage](https://www.healthcare.gov/get-coverage/)

Draft shape: "Coverage does not always start the same day you apply. I'll check the deadline that applies to you and tell you the start date."

### What is a deductible, copay, coinsurance, or out-of-pocket max?

These are standard plan cost terms. Give the official definition, then offer to walk through that client's plan if Eric has it in front of him.

- [Deductible](https://www.healthcare.gov/glossary/deductible/)
- [Copayment (copay)](https://www.healthcare.gov/glossary/co-payment/)
- [Coinsurance](https://www.healthcare.gov/glossary/co-insurance/)
- [Out-of-pocket maximum](https://www.healthcare.gov/glossary/out-of-pocket-maximum-limit/)
- [What Marketplace plans cover](https://www.healthcare.gov/coverage/what-marketplace-plans-cover/)

Draft shape: "A deductible is what you pay for covered services before the plan starts paying. A copay is a set amount for a visit or prescription. Coinsurance is a percentage you pay after the deductible. The out-of-pocket max is the most you'd pay in a year for covered services. I can walk you through your plan if you want."

### How do subsidies / premium tax credits work? What income counts?

Eligibility for a premium tax credit depends on household size and expected yearly income (modified adjusted gross income). Never tell a client they do or do not qualify unless Eric has reviewed their application.

- [Premium tax credit](https://www.healthcare.gov/glossary/premium-tax-credit/)
- [Modified adjusted gross income (MAGI)](https://www.healthcare.gov/glossary/modified-adjusted-gross-income-magi/)
- [Income and household information](https://www.healthcare.gov/income-and-household-information/)

Draft shape: "The tax credit is based on your household size and the income you expect this year. I don't want to guess on yours — I'll review it and explain what it means for your premium."

### I need to update my application (income, address, household).

Clients should report changes promptly; they can affect the tax credit and plan cost.

- [Reporting changes](https://www.healthcare.gov/reporting-changes/)

Draft shape: "Yes, we should update that on your Marketplace application. Tell me what changed and when, and I'll take care of the update with you."

### The Marketplace asked me for documents.

HealthCare.gov may ask a client to verify income, citizenship or immigration status, or other information. Collect the list they were asked for; Eric uploads it in the agent portal or walks the client through their account. Do not log in as the client.

- [Verify information](https://www.healthcare.gov/verify-information/)

Draft shape: "If they asked for proof, send me a photo of the letter or the exact list, plus clear photos of each document. I'll tell you if anything is missing and upload them for you."

### How do I pay my premium? I think I missed a payment.

Payment is made to the insurance company, not to Eric, and not through a bot. Do not take a card number over text.

- [Using Marketplace coverage](https://www.healthcare.gov/using-marketplace-coverage/)
- [Help Center](https://www.healthcare.gov/help/)

Draft shape: "Your premium is paid to the insurance company, not to me. I can send you the insurer's payment link or walk you through it on a call. Don't text card numbers."

### Immigration or citizenship questions.

Point to official immigrant eligibility pages and flag the thread for Eric. Do not interpret a client's status.

- [Immigrants and the Marketplace](https://www.healthcare.gov/immigrants/)
- [Immigration status](https://www.healthcare.gov/immigrants/immigration-status/)
- [Lawfully present immigrants](https://www.healthcare.gov/immigrants/lawfully-present-immigrants/)

Draft shape: "Eligibility can depend on immigration status, and I want to get that right. I'll review your application and follow up."

### Medicaid or CHIP.

Some clients will qualify for Medicaid or CHIP instead of (or in addition to) a Marketplace plan. Florida rules can differ from the federal Marketplace. Flag for Eric; do not declare the client eligible.

- [Medicaid & CHIP](https://www.healthcare.gov/medicaid-chip/)
- [Getting Medicaid or CHIP](https://www.healthcare.gov/medicaid-chip/getting-medicaid-chip/)

### How do I apply or compare plans?

- [Quick guide](https://www.healthcare.gov/quick-guide/)
- [Get coverage](https://www.healthcare.gov/get-coverage/)
- [See plans](https://www.healthcare.gov/see-plans/)
- [Choose a plan](https://www.healthcare.gov/choose-a-plan/)
- [Screener](https://www.healthcare.gov/screener/)
- [Marketplace in your state](https://www.healthcare.gov/marketplace-in-your-state/)

Draft shape: "I can help you apply and compare plans. Share a good time to talk, or start a Marketplace account and I'll walk you through the next step."

### Tax forms (1095-A).

- [Taxes and HealthCare.gov](https://www.healthcare.gov/taxes/)

Draft shape: "If you had Marketplace coverage last year you should get a Form 1095-A for your taxes. I'll help you find it or request a copy if you don't have yours."

## After drafting

- Put the draft in front of Eric, plus a one-line reason and any official link you used.
- Mark anything that needs his portal review (plan, subsidy, payment posted, document already uploaded).
- Do not mark the CRM conversation as read in a way that hides work he still needs to do, unless he asks.
