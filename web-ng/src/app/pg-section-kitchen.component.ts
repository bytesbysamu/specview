/**
 * pg-section-kitchen.component.ts
 *
 * Playground V4 — Section 2 "Kitchen".
 *
 * EXTRACTION STATUS: Non-extractable
 * ────────────────────────────────────
 * This component is intentionally NOT extracted for landing page consumption.
 * It is tightly coupled to the scroll shell's narrative layout — the four-stage
 * pipeline grid is designed to be revealed progressively as the user scrolls
 * through the locked-gating sequence, and its content (pipeline stages) is
 * driven by PIPELINE_STAGES from playground-demo-data.ts via the scroll shell's
 * template binding.
 *
 * While the component accepts its data through an input signal (`stages`), the
 * editorial intent requires the scroll position context provided by
 * PgScrollShellComponent (IntersectionObserver reveal, locked-state teaser).
 * Rendering it outside that context produces an out-of-sequence narrative.
 *
 * If the landing page requires pipeline stage content, create a purpose-built
 * landing component that presents the four-stage story in a static layout.
 */
import { Component, ChangeDetectionStrategy, output } from '@angular/core';
import { PgPipelineComponent } from './pg-pipeline.component';

@Component({
  selector: 'app-pg-section-kitchen',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [PgPipelineComponent],
  styles: [`
    .kitchen {
      padding: 40px 0 32px;
      height: 100%;
      box-sizing: border-box;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }

    .kitchen__overline {
      font-family: var(--sans);
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      color: var(--ink-muted);
      margin-bottom: 32px;
      display: block;
    }

    .kitchen__headline {
      font-family: var(--serif);
      font-size: 48px;
      font-weight: 700;
      letter-spacing: -0.02em;
      line-height: 1.1;
      color: var(--ink);
      max-width: 640px;
      margin-bottom: 16px;
    }

    .kitchen__subhead {
      font-family: var(--body);
      font-size: 15px;
      line-height: 1.65;
      color: var(--ink-light);
      max-width: 480px;
      margin-bottom: 24px;
    }

    /* Pipeline grid — horizontal 4-across on desktop */
    .pipeline-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 0;
      border-top: 3px solid var(--ink);
    }

    .pipeline-stage {
      border-right: 1px solid var(--border);
      padding: 32px 28px 40px;
      display: flex;
      flex-direction: column;
      gap: 0;
    }

    .pipeline-stage:last-child {
      border-right: none;
    }

    .pipeline-stage__index {
      font-family: var(--sans);
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: var(--ink-muted);
      margin-bottom: 24px;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .pipeline-stage__index-num {
      font-family: var(--serif);
      font-size: 13px;
      color: var(--accent);
      font-weight: 700;
    }

    .pipeline-stage__title {
      font-family: var(--serif);
      font-size: 28px;
      font-weight: 700;
      letter-spacing: -0.01em;
      line-height: 1.15;
      color: var(--ink);
      margin-bottom: 12px;
    }

    .pipeline-stage__desc {
      font-family: var(--body);
      font-size: 13px;
      line-height: 1.6;
      color: var(--ink-light);
      margin-bottom: 28px;
      flex: 1;
    }

    /* Thumbnail snippet — styled as a mini spec document */
    .pipeline-stage__thumbnail {
      background: var(--code-bg);
      border: 1px solid var(--border);
      border-left: 3px solid var(--accent);
      padding: 14px 16px;
      font-family: var(--body);
      font-size: 11px;
      line-height: 1.55;
      color: var(--ink-light);
      overflow: hidden;
      max-height: 120px;
      position: relative;
    }

    .pipeline-stage__thumbnail::after {
      content: '';
      position: absolute;
      bottom: 0;
      left: 0;
      right: 0;
      height: 32px;
      background: linear-gradient(transparent, var(--code-bg));
    }

    .pipeline-stage__label {
      font-family: var(--sans);
      font-size: 10px;
      font-weight: 600;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--ink-muted);
      margin-bottom: 8px;
      display: block;
    }

    @media (max-width: 768px) {
      .kitchen {
        padding: 48px 0 80px;
      }

      .kitchen__headline {
        font-size: 32px;
        margin-bottom: 12px;
      }

      .kitchen__subhead {
        margin-bottom: 40px;
      }

      /* Vertical stack on mobile */
      .pipeline-grid {
        grid-template-columns: 1fr;
      }

      .pipeline-stage {
        border-right: none;
        border-bottom: 1px solid var(--border);
        padding: 28px 0 32px;
      }

      .pipeline-stage:last-child {
        border-bottom: none;
      }
    }
  `],
  template: `
    <div class="kitchen">
      <span class="kitchen__overline">The Kitchen</span>

      <h2 class="kitchen__headline">Four stages. One coherent spec.</h2>

      <p class="kitchen__subhead">
        The pipeline runs in sequence — each document builds on the last,
        narrowing from problem space to executable tasks.
      </p>

      <!-- Interactive pipeline progression -->
      <app-pg-pipeline (seeItLive)="onSeeItLive()" />
    </div>
  `,
})
export class PgSectionKitchenComponent {
  /** Bubbles the pipeline component's "See it live" event up to the scroll shell. */
  readonly seeItLive = output<void>();

  onSeeItLive(): void {
    this.seeItLive.emit();
  }
}
