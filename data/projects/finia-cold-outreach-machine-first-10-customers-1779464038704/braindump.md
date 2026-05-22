# FINIA Cold Outreach Machine — First 10 Paying Customers

## The opportunity sitting on the table

I did the research in April. The FINIA compliance wedge is real:
- 1,486 licensed portfolio managers + 152 trustees in Switzerland
- New regulatory regime (FINIA 2020, mandatory since 2023) with painful workflows no SaaS addresses
- Workflows: suitability checks (Geeignetheitsprüfung), conflict of interest register, KYC/AML, FINMA audit trails
- Competitors: Aviolo (consultancy only), SwissComply (firm-level ICS, not client-level) — the wedge is OPEN
- Pricing: CHF 299-999/mo is normal for Swiss B2B finance tools
- My reach: 970 firms (65% of market) via German + French fluency
- I work in finance. I speak the language. I know the pain.

And I've done nothing with it for 2 months.

## What I need

Not a SaaS product. Not yet. First I need to validate that people will pay. The Marc Lou pre-sell playbook: 5-sentence cold emails, 30-min calls, verbal commitments. If 3 out of 30 say "tell me more" and 1 says "I'd pay for that", I build it. If not, I don't.

An autonomous outreach agent that:

- Scrapes the FINMA public register (finma.ch) to build a target list of licensed portfolio managers and trustees with contact info
- Cross-references with company websites (many list email addresses) and LinkedIn (for names/titles)
- Generates hyper-personalized 5-sentence cold emails in German (Zurich/Bern firms) and French (Geneva/Lausanne firms)
- Each email references something specific about the firm — their license type, location, or a recent regulatory change
- Sends via himalaya after my approval (confirm-before-execute, always)
- Tracks responses: sent, opened (if possible), replied, meeting booked, declined
- Follow-up sequence: if no reply in 5 days, one follow-up. If no reply after follow-up, mark cold.
- Weekly report: emails sent, response rate, meetings booked, pipeline status

## The email template direction

Not selling software. Selling a conversation about a pain point.

German version:
"Guten Tag [Name], ich arbeite im Finanzbereich in Zürich und sehe, dass viele FINIA-lizenzierte Vermögensverwalter die Geeignetheitsprüfungen noch manuell in Excel durchführen. Wir entwickeln ein Tool, das diesen Workflow automatisiert. Hätten Sie 20 Minuten für ein kurzes Gespräch dazu?"

French version:
"Bonjour [Nom], je travaille dans le secteur financier à Zurich et je constate que de nombreux gérants de fortune sous FINIA effectuent encore les vérifications d'adéquation manuellement. Nous développons un outil qui automatise ce processus. Auriez-vous 20 minutes pour en discuter?"

The agent personalizes each email. I approve before sending.

## What exists

- FINMA register is public and downloadable from finma.ch
- infinity.swiss has a Treuhandverzeichnis (scrapeable)
- VAPA and TreuhandSuisse are trade associations with member directories
- OpenClaw has himalaya for email, apple-reminders for follow-ups
- I have German + French fluency for authentic outreach

## Success criteria

- 30 cold emails sent in the first 2 weeks
- 3+ "tell me more" replies (10% response rate)
- 1+ verbal commitment to pay for the tool
- If yes: build MVP. If no: pivot the pitch, try 30 more. If still no: kill it.

## Constraints

- I'm employed — outreach happens on evenings/weekends, but the agent prepares everything during the day
- Every email requires my approval before sending — no autonomous outreach
- Start with Zurich (German) firms since that's my home market
- Don't build ANY software until validation is complete — this is pre-sell only
- Budget: CHF 0 for tools. Use free data sources and existing OpenClaw infrastructure