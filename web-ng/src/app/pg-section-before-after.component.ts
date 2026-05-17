/**
 * pg-section-before-after.component.ts
 *
 * Playground V4 — Before/After Transformation Section.
 *
 * Renders a two-column editorial layout that shows the "aha" moment:
 * the same Payment Gateway Redesign content as raw braindump text on the
 * left and structured AI-generated analysis on the right.
 *
 * Reveal behaviour (Task 4):
 *   The right column starts hidden (opacity 0, translateY 20px) via a global
 *   CSS rule in styles.css (.before-after__right). When the scroll shell's
 *   unified IntersectionObserver adds the `revealed` class to the parent
 *   section wrapper, the CSS rule .pg-section.revealed .before-after__right
 *   triggers the delayed right-column animation (160ms transition-delay).
 *   No IntersectionObserver or signal state is needed in this component.
 *
 * No external service dependencies — all content is sourced from
 * playground-demo-data.ts constants.
 *
 * Extraction status: Non-extractable
 * Tightly coupled to the scroll shell narrative — the before/after moment
 * is meaningful only in the progressive reveal context of the playground.
 */

import {
  ChangeDetectionStrategy,
  Component,
} from '@angular/core';
import { ANALYSIS_CONTENT, PAYMENT_GATEWAY_BRAINDUMP } from './playground-demo-data';

@Component({
  selector: 'app-pg-section-before-after',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  styles: [`
    .before-after {
      padding: 48px 0 40px;
      height: 100%;
      box-sizing: border-box;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }

    /* ── Header ────────────────────────────────────── */

    .before-after__overline {
      font-family: var(--sans);
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      color: var(--ink-muted);
      margin-bottom: 12px;
      display: block;
    }

    .before-after__headline {
      font-family: var(--serif);
      font-size: 36px;
      font-weight: 700;
      letter-spacing: -0.02em;
      line-height: 1.1;
      color: var(--ink);
      max-width: 720px;
      margin-bottom: 24px;
    }

    /* ── Two-column grid ───────────────────────────── */
    /*
     * 12-column editorial grid: left occupies 5 cols, right occupies 7 cols.
     * Uses the same gap rhythm as the rest of the newspaper layout.
     */

    .before-after__grid {
      display: grid;
      grid-template-columns: 5fr 7fr;
      gap: 0;
      border-top: 3px solid var(--ink);
      flex: 1;
      overflow: hidden;
    }

    /* ── Left column: raw braindump ─────────────────── */

    .before-after__left {
      border-right: 1px solid var(--border);
      padding: 24px 32px 32px 0;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }

    .before-after__col-label {
      font-family: var(--sans);
      font-size: 9px;
      font-weight: 700;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      color: var(--ink-muted);
      margin-bottom: 20px;
      display: block;
    }

    .before-after__braindump {
      font-family: 'SF Mono', Consolas, monospace;
      font-size: 11px;
      line-height: 1.6;
      color: var(--ink-light);
      white-space: pre-wrap;
      word-break: break-word;
      background: var(--code-bg);
      border: 1px solid var(--border);
      border-left: 3px solid var(--border-dark);
      padding: 16px 20px;
      overflow: hidden;
    }

    /* ── Right column: structured analysis ──────────── */
    /*
     * Reveal animation is handled globally by styles.css:
     *   .before-after__right            — initial hidden state
     *   .pg-section.revealed .before-after__right — revealed with 160ms delay
     */

    .before-after__right {
      padding: 24px 0 32px 32px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }

    /* Analysis typography — mirrors the existing newspaper reader panel */

    .before-after__analysis {
      font-family: var(--body);
      font-size: 13px;
      line-height: 1.65;
      color: var(--ink);
      overflow: hidden;
    }

    .before-after__analysis h1 {
      font-family: var(--serif);
      font-size: 22px;
      font-weight: 700;
      margin: 0 0 16px;
      padding-bottom: 8px;
      border-bottom: 1px solid var(--border);
      line-height: 1.2;
      color: var(--ink);
    }

    .before-after__analysis h2 {
      font-family: var(--serif);
      font-size: 16px;
      font-weight: 700;
      margin: 24px 0 8px;
      color: var(--ink);
    }

    .before-after__analysis p {
      margin: 10px 0;
      color: var(--ink-light);
    }

    .before-after__analysis ul,
    .before-after__analysis ol {
      margin: 10px 0;
      padding-left: 22px;
    }

    .before-after__analysis li {
      margin: 4px 0;
      color: var(--ink-light);
    }

    .before-after__analysis strong {
      font-weight: 600;
      color: var(--ink);
    }

    /* ── Mobile: stack columns ──────────────────────── */

    @media (max-width: 768px) {
      .before-after {
        padding: 48px 0 80px;
      }

      .before-after__headline {
        font-size: 28px;
        margin-bottom: 32px;
      }

      .before-after__grid {
        grid-template-columns: 1fr;
      }

      .before-after__left {
        border-right: none;
        border-bottom: 1px solid var(--border);
        padding: 28px 0 32px;
      }

      .before-after__right {
        padding: 28px 0 32px;
      }
    }
  `],
  template: `
    <div class="before-after">
      <span class="before-after__overline">The Transformation</span>

      <h2 class="before-after__headline">
        Same idea. Before and after.
      </h2>

      <div class="before-after__grid">

        <!-- Left: raw braindump input -->
        <div class="before-after__left">
          <span class="before-after__col-label">Input — Raw Braindump</span>
          <pre class="before-after__braindump">{{ braindump }}</pre>
        </div>

        <!-- Right: structured analysis output (revealed via CSS cascade) -->
        <div class="before-after__right">
          <span class="before-after__col-label">Output — AI Analysis</span>
          <div class="before-after__analysis" [innerHTML]="analysisHtml"></div>
        </div>

      </div>
    </div>
  `,
})
export class PgSectionBeforeAfterComponent {

  // ── Content ──────────────────────────────────────────────────────────────────

  readonly braindump = PAYMENT_GATEWAY_BRAINDUMP;

  /**
   * Convert ANALYSIS_CONTENT markdown to HTML for the right column.
   * Uses a minimal hand-rolled renderer scoped to the content shape
   * (h1, h2, paragraphs, lists) — no external library dependency.
   */
  readonly analysisHtml: string = renderMinimalMarkdown(ANALYSIS_CONTENT);
}

// ── Minimal markdown renderer ─────────────────────────────────────────────────

/**
 * Converts a limited subset of markdown (h1, h2, paragraphs, bold, bullet
 * lists) to HTML. Used only for the demo analysis content — not a general
 * markdown renderer.
 *
 * This keeps the component free of marked/DOMPurify dependency while
 * still rendering the structured analysis content correctly.
 */
function renderMinimalMarkdown(md: string): string {
  const lines = md.split('\n');
  const out: string[] = [];
  let inList = false;

  for (const raw of lines) {
    const line = raw.trimEnd();

    if (line.startsWith('## ')) {
      if (inList) { out.push('</ul>'); inList = false; }
      out.push(`<h2>${escapeHtml(line.slice(3))}</h2>`);
    } else if (line.startsWith('# ')) {
      if (inList) { out.push('</ul>'); inList = false; }
      out.push(`<h1>${escapeHtml(line.slice(2))}</h1>`);
    } else if (line.startsWith('- ')) {
      if (!inList) { out.push('<ul>'); inList = true; }
      out.push(`<li>${inlineMd(line.slice(2))}</li>`);
    } else if (line.trim() === '') {
      if (inList) { out.push('</ul>'); inList = false; }
    } else {
      if (inList) { out.push('</ul>'); inList = false; }
      out.push(`<p>${inlineMd(line)}</p>`);
    }
  }

  if (inList) out.push('</ul>');
  return out.join('\n');
}

function inlineMd(text: string): string {
  return escapeHtml(text).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
