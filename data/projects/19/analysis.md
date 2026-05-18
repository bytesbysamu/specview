**1. Key Themes**

- **The playground is the Figma, the landing is the build.** This is the central inversion. Most teams treat component libraries as documentation *about* a design system; you're treating yours as the canonical artifact and the landing page as its first real application. The design work is already done — what remains is content placement, not visual decision-making.

- **Show, don't label.** The current landing narrates the design system ("here is the masthead"). The new landing performs it ("this *is* the masthead"). Removing the meta-layer is the entire shift. Every component goes from being its own demo to being itself.

- **Editorial as product positioning.** The newspaper metaphor isn't decoration — it's a claim about what Spec Doc produces. Pull quotes, overlines, ledes, mastheads all signal: this product makes documents that read like considered editorial work, not auto-generated AI sludge.

- **Constraint as quality gate.** No new CSS, no icon CDN, no inline styles, no code mockups. The discipline of refusing to add anything forces the design system to either be sufficient or be exposed as incomplete. Either outcome is useful.

- **Demo strip as recursive proof.** Embedding a miniaturized real spec inside the landing page means the landing *demonstrates the artifact by being adjacent to one*. The product's output and the product's marketing share a visual language because they are the same language.

**2. Hidden Connections**

- **The "no code blocks" rule and the editorial framing are the same rule.** Code mockups would break the metaphor — newspapers don't show source code. By banning `.step-code` you're not just simplifying; you're enforcing the fiction that this product belongs to the world of letters, not the world of dev tools. That positioning will affect who clicks.

- **The output-grid replacing `<ul>` is a thesis, not a styling choice.** A bulleted list says "here are some things." A card grid of artifacts says "here are the deliverables." The landing's refusal to use bullet lists is a refusal to be a feature page. It's a portfolio.

- **The relationship to the current landing mirrors the relationship to the playground.** Old landing → new landing is the same move as playground → landing: take something that documents/demonstrates and replace it with something that just *is*. The methodology you're applying to the marketing site is the methodology Spec Doc applies to specs.

- **"Design is done, content is next" is the spec-set methodology applied to the landing itself.** Braindump (this doc) → spec set (analysis/architecture pass) → implementation (content placement). The landing rebuild is itself an instance of the product it's selling.

**3. Open Questions**

- **Should `landing-v2.html` ever become `index.html`, or should it ship as a separate route that competes?**
  - Option A: Replace `index.html` once ready. Clean, decisive, one source of truth.
  - Option B: Run both at `/` and `/v2` for a window, A/B test on conversion or engagement.
  - Option C: Ship v2 immediately as `/`, archive old as `/classic` for reference.
  - **Recommended:** Option A. A/B testing a positioning shift this large produces noisy data; you'll learn more from committing and watching qualitative signal.

- **What is the "real spec excerpt" inside the demo strip?**
  - Option A: A spec for Spec Doc itself (recursive, on-brand, hard to read cold).
  - Option B: A spec for a relatable example product (todo app, auth flow) that visitors can scan in 10 seconds.
  - Option C: A spec for a famously hard problem (rate limiter, payment retry) that signals the tool handles real engineering.
  - **Recommended:** Option C. It demonstrates capability where skepticism lives — most visitors assume AI tools handle toy problems and break on real ones.

- **Does the hero CTA go to a signup, a live playground, or a generated example spec?**
  - Option A: Signup form (standard, measurable, low-commitment for you).
  - Option B: Live braindump input that produces a real spec inline (highest wow, highest build cost).
  - Option C: "View an example spec" link to a fully rendered artifact (medium effort, lets quality speak).
  - **Recommended:** Option C. The landing's whole argument is "the artifact is the proof" — the CTA should deliver an artifact, not a form.

- **How many overline sections before the page tips into being a brochure?**
  - Option A: Four sections as planned (What / How / See / Start).
  - Option B: Three — collapse "What it does" into the lede, since the output-grid already answers it.
  - Option C: Two — lede + demo strip + pricing, and let the artifact carry the argument.
  - **Recommended:** Option B. The output-grid in the lede already enumerates what it does; a separate "What it does" section duplicates work and weakens the editorial pacing.

- **Does the masthead's date/edition label stay static or update?**
  - Option A: Static date frozen at launch (intentional artifact, signals "this issue").
  - Option B: Auto-updating to today's date (live, but undermines the newspaper fiction since real newspapers don't change yesterday's edition).
  - Option C: Updates weekly with a real "edition" rhythm — Vol I, Issue 12 — tied to product changelog.
  - **Recommended:** Option C. It turns the masthead from decoration into an editorial calendar and gives you a reason to revisit the page.

- **What does the pull quote actually say, and who is it attributed to?**
  - Option A: A quote from a real user (requires having quotable users).
  - Option B: An unattributed editorial line about the methodology (safe, but feels like a tagline pretending to be a quote).
  - Option C: A self-attributed manifesto line — "Specs are how engineers think out loud. — Spec Doc."
  - **Recommended:** Option A if you have it, Option C if you don't. Avoid B — readers smell fake quotes.

**4. Ideas to Explore**

- **Build the demo strip first, before the rest of the page.** It's the highest-risk component (it has to feel like a real artifact, not a screenshot of one) and the rest of the page hangs off whether it works. If the embedded spec doesn't read as authentic, the whole editorial conceit collapses.

- **Write the hero deck paragraph as the lede of a real news article.** Not "AI-powered spec generation" — something like "Last Tuesday, a team of four engineers shipped a payment retry system in three days. The spec, written first, was forty pages." Story-as-positioning. Make the visitor curious, not informed.

- **Add a "corrections" or "masthead" footer block that lists what the page chose not to say.** A meta-editorial move: "This issue does not include: a feature comparison table, a logo wall, or the word 'powered.'" It's a flex. It tells design-conscious buyers exactly who you are.

- **Make the three steps describe a single real example end-to-end, not three abstract phases.** Step 1: "Sarah dumps three paragraphs about retries." Step 2: "Spec Doc returns a thirty-page spec with seven artifacts." Step 3: "The team ships in three days." Concrete beats abstract every time, and it lets the methodology breathe through narrative.

- **Run a typography audit before content goes in.** Open the playground and the new landing side by side at the same scroll position. If any element on the landing looks subtly different from its playground twin, the design system is leaking. Fix the leak in `style.css` (since you've banned new classes), or rework the landing to use the canonical pattern.

- **Treat the launch as an issue.** When `landing-v2.html` ships, publish a changelog post styled in the same newspaper format — "Vol I, Issue 1." The landing isn't a one-time rebuild; it's the start of an editorial rhythm where each product update is an issue. This turns the masthead from clever theming into a content strategy.

- **Steal one constraint from print: a fold.** Newspapers have above-the-fold logic — what survives on the rack at 6am. Decide what your page must accomplish before any scroll, and design the lede + first overline section to land that argument complete. Everything below is for the persuaded.