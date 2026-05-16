import { Component, ChangeDetectionStrategy } from '@angular/core';

@Component({
  selector: 'app-pg-hero',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="hero">

      <!-- ── Tagline block ──────────────────────────────────────────────────── -->
      <div class="hero-tagline">
        <h1 class="hero-heading">Write messy. Ship clean.</h1>
        <p class="hero-deck">
          Paste a rough braindump. Get a complete spec suite — analysis, epic,
          architecture, implementation guide — in under a minute.
        </p>
      </div>

      <!-- ── Stat strip ─────────────────────────────────────────────────────── -->
      <div class="hero-stats">
        <div class="hero-stat">
          <span class="hero-stat__number">44.5s</span>
          <span class="hero-stat__label">avg generation</span>
        </div>
        <div class="hero-stat-sep"></div>
        <div class="hero-stat">
          <span class="hero-stat__number">5</span>
          <span class="hero-stat__label">files per run</span>
        </div>
        <div class="hero-stat-sep"></div>
        <div class="hero-stat">
          <span class="hero-stat__number">0</span>
          <span class="hero-stat__label">code required</span>
        </div>
        <div class="hero-stat-sep"></div>
        <div class="hero-stat">
          <span class="hero-stat__number">Free</span>
          <span class="hero-stat__label">tier available</span>
        </div>
      </div>

      <!-- ── Before / After lede ────────────────────────────────────────────── -->
      <div class="hero-lede">

        <!-- Left: messy braindump input -->
        <div class="hero-lede__main">
          <div class="hero-lede__overline">The Input</div>
          <div class="hero-braindump">
            <p class="hero-braindump__text">
              ok so i want to build this thing where users can paste like a big messy
              brain dump of their idea — doesnt matter how rough, just stream of
              consciousness — and then the system figures out what theyre actually
              trying to build and spits out like a full spec document set. analysis
              of the problem space first, then an epic with user stories, then a
              proper architecture doc with tech choices, and finally an impl guide
              that a dev could actually follow. it should work for any kind of
              software project, not just web apps. also need auth so people cant
              just spam it, maybe usage limits too. and it needs to be fast — nobody
              wants to wait 10 minutes, should be under a minute ideally...
            </p>
          </div>
        </div>

        <!-- Column rule -->
        <div class="hero-lede__divider"></div>

        <!-- Right: structured output cards + animated status bar -->
        <div class="hero-lede__aside">
          <div class="hero-lede__overline">The Output</div>

          <!-- Status bar demo (pure CSS animation) -->
          <div class="hero-status-bar">
            <div class="hero-status-track"></div>
            <div class="hero-status-content">
              <span class="hero-status-dot"></span>
              <span class="hero-status-project">my-project</span>
              <span class="hero-status-sep">&mdash;</span>
              <span class="hero-status-step">
                <span class="hero-file-name hero-file-name--1">analysis.md</span>
                <span class="hero-file-name hero-file-name--2">epic.md</span>
                <span class="hero-file-name hero-file-name--3">architecture.md</span>
                <span class="hero-file-name hero-file-name--4">implementation-guide.md</span>
                <span class="hero-file-name hero-file-name--5">braindump.md</span>
              </span>
            </div>
          </div>

          <!-- Document title cards -->
          <div class="hero-output-cards">
            <div class="hero-output-card hero-output-card--1">
              <span class="hero-output-card__name">analysis.md</span>
              <span class="hero-output-card__desc">Problem space, market context, constraints</span>
            </div>
            <div class="hero-output-card hero-output-card--2">
              <span class="hero-output-card__name">epic.md</span>
              <span class="hero-output-card__desc">User stories, acceptance criteria, scope</span>
            </div>
            <div class="hero-output-card hero-output-card--3">
              <span class="hero-output-card__name">architecture.md</span>
              <span class="hero-output-card__desc">Tech stack, system design, data model</span>
            </div>
            <div class="hero-output-card hero-output-card--4">
              <span class="hero-output-card__name">implementation-guide.md</span>
              <span class="hero-output-card__desc">Ordered tasks, estimates, code entry points</span>
            </div>
            <div class="hero-output-card hero-output-card--5">
              <span class="hero-output-card__name">braindump.md</span>
              <span class="hero-output-card__desc">Your original input, preserved verbatim</span>
            </div>
          </div>
        </div>

      </div>

      <!-- ── CTA ────────────────────────────────────────────────────────────── -->
      <div class="hero-cta-row">
        <button class="hero-cta">Try it free</button>
      </div>

    </div>
  `,
  styles: [`
    /* ── Wrapper ─────────────────────────────────────────────────────────────── */
    .hero {
      display: flex;
      flex-direction: column;
      gap: 40px;
    }

    /* ── Tagline block ───────────────────────────────────────────────────────── */
    .hero-heading {
      font-family: 'Playfair Display', Georgia, serif;
      font-size: 52px;
      font-weight: 700;
      line-height: 1.1;
      letter-spacing: -0.02em;
      color: var(--ink);
      margin-bottom: 16px;
    }

    .hero-deck {
      font-family: 'Source Serif 4', Georgia, serif;
      font-size: 18px;
      line-height: 1.65;
      color: var(--ink-light);
      max-width: 640px;
    }

    /* ── Stat strip ──────────────────────────────────────────────────────────── */
    .hero-stats {
      display: flex;
      align-items: center;
      gap: 0;
      padding: 24px 0;
      border-top: 1px solid var(--border);
      border-bottom: 1px solid var(--border);
    }

    .hero-stat {
      display: flex;
      flex-direction: column;
      gap: 4px;
      padding: 0 32px;
    }

    .hero-stat:first-child {
      padding-left: 0;
    }

    .hero-stat__number {
      font-family: 'Playfair Display', Georgia, serif;
      font-size: 36px;
      font-weight: 700;
      line-height: 1;
      color: var(--ink);
      letter-spacing: -0.01em;
    }

    .hero-stat__label {
      font-family: 'Source Sans 3', system-ui, sans-serif;
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--ink-muted);
    }

    .hero-stat-sep {
      width: 1px;
      height: 40px;
      background: var(--border);
      flex-shrink: 0;
    }

    /* ── Before / After lede ─────────────────────────────────────────────────── */
    .hero-lede {
      display: grid;
      grid-template-columns: 1fr auto 1fr;
      gap: 0;
      align-items: start;
    }

    .hero-lede__overline {
      font-family: 'Source Sans 3', system-ui, sans-serif;
      font-size: 9px;
      font-weight: 600;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--ink-muted);
      margin-bottom: 14px;
    }

    .hero-lede__divider {
      width: 1px;
      background: var(--border);
      margin: 0 32px;
      align-self: stretch;
    }

    /* Left column — braindump */
    .hero-braindump {
      border: 1px solid var(--border);
      padding: 20px;
      background: var(--code-bg);
    }

    .hero-braindump__text {
      font-family: 'Source Serif 4', Georgia, serif;
      font-size: 13px;
      line-height: 1.75;
      color: var(--ink-light);
      font-style: italic;
      white-space: pre-line;
    }

    /* Right column — output */

    /* ── CSS-animated status bar ─────────────────────────────────────────────── */
    .hero-status-bar {
      background: var(--status-active);
      color: #fff;
      font-family: 'Source Sans 3', system-ui, sans-serif;
      font-size: 12px;
      letter-spacing: 0.03em;
      overflow: hidden;
      margin-bottom: 12px;
    }

    .hero-status-track {
      height: 2px;
      background: linear-gradient(
        90deg,
        transparent 0%,
        rgba(255,255,255,0.5) 30%,
        rgba(255,255,255,0.9) 50%,
        rgba(255,255,255,0.5) 70%,
        transparent 100%
      );
      background-size: 200% 100%;
      animation: hero-shimmer 1.6s linear infinite;
    }

    @keyframes hero-shimmer {
      0%   { background-position: 200% 0; }
      100% { background-position: -200% 0; }
    }

    .hero-status-content {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 14px;
    }

    .hero-status-dot {
      width: 5px;
      height: 5px;
      border-radius: 50%;
      background: #fff;
      flex-shrink: 0;
      animation: hero-pulse 0.7s ease-out infinite alternate;
    }

    @keyframes hero-pulse {
      0%   { opacity: 0.6; }
      100% { opacity: 1; }
    }

    .hero-status-project {
      font-weight: 700;
      letter-spacing: 0.01em;
    }

    .hero-status-sep {
      opacity: 0.5;
      margin: 0 2px;
    }

    .hero-status-step {
      position: relative;
      min-width: 160px;
      height: 16px;
      overflow: hidden;
      display: inline-block;
    }

    /* Each file name cycles in and out via CSS keyframes */
    .hero-file-name {
      position: absolute;
      left: 0;
      top: 0;
      opacity: 0;
      white-space: nowrap;
      font-style: italic;
    }

    /* Total cycle: 5 files × 2s each = 10s loop */
    /* Each name is visible for 1.5s, fades for 0.25s either side */
    /* Percentages: visible window = 15% of 10s = 1.5s */

    .hero-file-name--1 {
      animation: hero-file-cycle 10s ease-in-out infinite 0s;
    }
    .hero-file-name--2 {
      animation: hero-file-cycle 10s ease-in-out infinite 2s;
    }
    .hero-file-name--3 {
      animation: hero-file-cycle 10s ease-in-out infinite 4s;
    }
    .hero-file-name--4 {
      animation: hero-file-cycle 10s ease-in-out infinite 6s;
    }
    .hero-file-name--5 {
      animation: hero-file-cycle 10s ease-in-out infinite 8s;
    }

    @keyframes hero-file-cycle {
      /*
       * At 0% the name starts invisible.
       * Fade in during first 5% (~0.5s), hold until 15% (~1.5s), fade out by 20%.
       * Invisible for the remaining 80% while the other 4 names take their turns.
       */
      0%   { opacity: 0; }
      5%   { opacity: 0.9; }
      15%  { opacity: 0.9; }
      20%  { opacity: 0; }
      100% { opacity: 0; }
    }

    /* ── Output document cards ───────────────────────────────────────────────── */
    .hero-output-cards {
      display: flex;
      flex-direction: column;
      gap: 0;
    }

    .hero-output-card {
      display: flex;
      flex-direction: column;
      gap: 3px;
      padding: 12px 0;
      border-bottom: 1px solid var(--border);
      animation: hero-card-appear 0.4s ease both;
    }

    .hero-output-card:last-child {
      border-bottom: none;
    }

    /* Stagger card appearance */
    .hero-output-card--1 { animation-delay: 0.1s; }
    .hero-output-card--2 { animation-delay: 0.3s; }
    .hero-output-card--3 { animation-delay: 0.5s; }
    .hero-output-card--4 { animation-delay: 0.7s; }
    .hero-output-card--5 { animation-delay: 0.9s; }

    @keyframes hero-card-appear {
      from { opacity: 0; transform: translateY(6px); }
      to   { opacity: 1; transform: translateY(0); }
    }

    .hero-output-card__name {
      font-family: 'Source Sans 3', system-ui, sans-serif;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.02em;
      color: var(--ink);
    }

    .hero-output-card__desc {
      font-family: 'Source Sans 3', system-ui, sans-serif;
      font-size: 11px;
      color: var(--ink-muted);
      letter-spacing: 0.01em;
    }

    /* ── CTA row ─────────────────────────────────────────────────────────────── */
    .hero-cta-row {
      display: flex;
      align-items: center;
    }

    .hero-cta {
      font-family: 'Source Sans 3', system-ui, sans-serif;
      font-size: 13px;
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      background: var(--ink);
      color: var(--bg);
      border: none;
      border-radius: 0;
      padding: 14px 36px;
      cursor: pointer;
      transition: opacity 0.15s;
    }

    .hero-cta:hover {
      opacity: 0.82;
    }
  `],
})
export class PgHeroComponent {}
