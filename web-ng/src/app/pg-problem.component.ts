import { Component, ChangeDetectionStrategy } from '@angular/core';

@Component({
  selector: 'app-pg-problem',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="nw-intro">
      <p class="nw-overline">The Problem</p>
      <h2 class="nw-headline">Specs are critical.<br>Nobody writes them.</h2>
      <p class="nw-deck">
        Every engineering project begins with intent. Most of that intent never makes it to
        paper. The gap between "we talked about this" and "we documented this" costs teams
        weeks of rework, misaligned architecture, and painful handoffs — on every single
        project, every single time.
      </p>
    </div>

    <!-- Pain point 1: Ambiguous requirements -->
    <div class="pain-block">
      <h3 class="section-heading">Ambiguous requirements compound into rework</h3>
      <p class="body-text">
        When requirements live in a Slack thread and a half-remembered standup, every engineer
        builds a slightly different mental model. The divergence is invisible until integration —
        at which point the cost is no longer an hour of clarification but a week of teardown and
        rebuild. Without a written spec, "we agreed on this" becomes the most dangerous phrase in
        software development.
      </p>
    </div>

    <!-- Pain point 2: Architecture decisions without documentation -->
    <div class="pain-block">
      <h3 class="section-heading">Architecture decisions made without documentation cause drift</h3>
      <p class="body-text">
        Architectural choices compound over time. The decision to use a queue instead of a direct
        call, to normalize or denormalize a schema, to split a service or keep it monolithic —
        each of these shapes everything that follows. When those decisions are undocumented, the
        team that made them moves on and the team that inherits the system has no map. Drift is
        not a failure of discipline; it is the predictable outcome of absent documentation.
      </p>
    </div>

    <!-- Pullquote row between pain point 2 and 3 -->
    <div class="nw-pullquote-row">
      <div class="nw-pullquote">
        <p class="nw-pullquote-mark">"</p>
        <p class="nw-pullquote-text">
          The most expensive code is the code you write twice because no one wrote down
          what it was supposed to do the first time.
        </p>
        <p class="nw-pullquote-attr">On the cost of ambiguity</p>
      </div>
      <div class="nw-pullquote-divider"></div>
      <div class="nw-pullquote">
        <p class="nw-pullquote-mark">"</p>
        <p class="nw-pullquote-text">
          Architecture is a conversation. Documentation is the transcript. Without it,
          every new engineer starts the conversation from scratch.
        </p>
        <p class="nw-pullquote-attr">On knowledge decay</p>
      </div>
    </div>

    <!-- Pain point 3: Handoff friction -->
    <div class="pain-block">
      <h3 class="section-heading">Handoff friction stalls execution before it starts</h3>
      <p class="body-text">
        The distance between a product decision and a working implementation passes through
        people. Each handoff — from founder to product manager, from PM to engineer, from
        senior to junior — is a lossy translation. Context compresses. Nuance drops out.
        By the time a developer opens their editor, the original intent may be unrecognizable.
        The spec is the interface that makes handoffs lossless.
      </p>
    </div>

    <!-- Closing argument -->
    <div class="closing-block">
      <p class="body-text body-text--closing">
        Specview does not ask teams to become better writers or to find more time. It takes a
        braindump — the raw, unpolished thinking that already exists in someone's head — and
        generates the documentation layer that the team was never going to write by hand.
        The pipeline produces a problem analysis, product epic, architecture guide, timeline,
        and implementation roadmap in minutes. Not because writing specs is easy, but because
        it no longer has to be manual.
      </p>
    </div>
  `,
  styles: [`
    .nw-intro {
      margin-bottom: 48px;
    }

    .nw-overline {
      font-family: var(--sans);
      font-size: 9px;
      font-weight: 600;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--red);
      margin-bottom: 14px;
    }

    .nw-headline {
      font-family: 'Playfair Display', Georgia, serif;
      font-size: 44px;
      font-weight: 700;
      line-height: 1.15;
      color: var(--ink);
      margin: 0 0 20px;
    }

    .nw-deck {
      font-family: 'Source Serif 4', 'Source Serif Pro', Georgia, serif;
      font-size: 18px;
      line-height: 1.6;
      color: var(--ink);
      max-width: 680px;
      margin: 0;
    }

    .pain-block {
      margin-bottom: 48px;
    }

    .section-heading {
      font-family: var(--sans);
      font-size: 20px;
      font-weight: 700;
      color: var(--ink);
      margin: 0 0 16px;
      padding-bottom: 10px;
      border-bottom: 1px solid var(--border);
    }

    .body-text {
      font-family: 'Source Serif 4', 'Source Serif Pro', Georgia, serif;
      font-size: 17px;
      line-height: 1.7;
      color: var(--ink);
      max-width: 720px;
      margin: 0;
    }

    .nw-pullquote-row {
      display: grid;
      grid-template-columns: 1fr 1px 1fr;
      border-top: 1px solid var(--border);
      border-bottom: 1px solid var(--border);
      margin-bottom: 48px;
    }

    .nw-pullquote {
      padding: 36px 40px;
    }

    .nw-pullquote-divider {
      background: var(--border);
    }

    .nw-pullquote-mark {
      font-family: var(--serif);
      font-size: 56px;
      font-weight: 700;
      color: var(--border);
      line-height: 0.8;
      margin-bottom: 8px;
    }

    .nw-pullquote-text {
      font-family: var(--serif);
      font-size: 22px;
      font-style: italic;
      line-height: 1.45;
      color: var(--ink);
      margin-bottom: 16px;
    }

    .nw-pullquote-attr {
      font-family: var(--sans);
      font-size: 11px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--ink-muted);
      margin: 0;
    }

    .closing-block {
      margin-top: 8px;
      padding: 32px 40px;
      background: var(--surface, #f9fafb);
      border-left: 3px solid var(--accent, #6366f1);
    }

    .body-text--closing {
      max-width: 100%;
    }
  `],
})
export class PgProblemComponent {}
