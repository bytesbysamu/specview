import { Component, ChangeDetectionStrategy, signal, output } from '@angular/core';
import {
  PAYMENT_GATEWAY_BRAINDUMP,
  PIPELINE_ANALYSIS_PREVIEW,
  PIPELINE_EPIC_PREVIEW,
  PIPELINE_ARCHITECTURE_PREVIEW,
} from './playground-demo-data';

interface PipelineStage {
  index: number;
  label: string;
  description: string;
  content: string;
  isStructured: boolean;
}

@Component({
  selector: 'app-pg-pipeline',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <!-- ── 4-stage horizontal tab bar ────────────────────────────────────────── -->
    <div class="pipeline-tabs" role="tablist">
      @for (stage of stages; track stage.label; let i = $index) {
        <button
          class="pipeline-tab"
          [class.pipeline-tab--active]="activeStage() === i"
          role="tab"
          [attr.aria-selected]="activeStage() === i"
          [attr.data-test]="'pipeline-tab-' + i"
          (click)="setStage(i)"
        >
          <span class="pipeline-tab__num">0{{ i + 1 }}</span>
          <span class="pipeline-tab__label">{{ stage.label }}</span>
        </button>
      }
    </div>

    <!-- ── Content reader area ───────────────────────────────────────────────── -->
    <div class="pipeline-reader" [attr.data-test]="'pipeline-reader'">
      <div class="pipeline-reader__header">
        <span class="pipeline-reader__stage-label">
          {{ stages[activeStage()].label }}
        </span>
        <span class="pipeline-reader__project-name">Payment Gateway Redesign</span>
      </div>

      @if (stages[activeStage()].isStructured) {
        <!-- Structured content: analysis / epic / architecture -->
        <div class="pipeline-reader__body pipeline-reader__body--structured">
          {{ stages[activeStage()].content }}
        </div>
      } @else {
        <!-- Plain-text braindump -->
        <div class="pipeline-reader__body pipeline-reader__body--raw">
          {{ stages[activeStage()].content }}
        </div>
      }

      <!-- "See it live" affordance — only visible on Architecture tab (index 3) -->
      @if (activeStage() === 3) {
        <div class="pipeline-reader__cta-row">
          <button
            class="pipeline-reader__see-it-live"
            (click)="onSeeItLive()"
            data-test="pipeline-see-it-live"
          >
            See it live &rarr;
          </button>
        </div>
      }
    </div>
  `,
  styles: [`
    :host {
      display: flex;
      flex-direction: column;
      flex: 1;
      overflow: hidden;
    }

    /* ── Tab bar ─────────────────────────────────────────────────────────────── */
    .pipeline-tabs {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      border-top: 3px solid var(--ink);
    }

    .pipeline-tab {
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: 6px;
      padding: 20px 24px;
      border: none;
      border-right: 1px solid var(--border);
      border-bottom: 3px solid transparent;
      background: var(--surface);
      cursor: pointer;
      transition: background 0.15s, border-bottom-color 0.15s;
      text-align: left;
    }

    .pipeline-tab:last-child {
      border-right: none;
    }

    .pipeline-tab:hover {
      background: var(--surface-raised, rgba(0, 0, 0, 0.02));
    }

    .pipeline-tab--active {
      background: var(--surface-raised, rgba(0, 0, 0, 0.03));
      border-bottom-color: var(--ink);
    }

    .pipeline-tab__num {
      font-family: var(--serif, 'Source Serif 4', Georgia, serif);
      font-size: 11px;
      font-weight: 700;
      color: var(--accent, var(--ink-muted));
    }

    .pipeline-tab__label {
      font-family: var(--sans, 'Source Sans 3', system-ui, sans-serif);
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: var(--ink);
    }

    /* ── Reader panel ────────────────────────────────────────────────────────── */
    .pipeline-reader {
      border-top: 1px solid var(--border);
      border-bottom: 1px solid var(--border);
      padding: 20px 0 24px;
      flex: 1;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }

    .pipeline-reader__header {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      margin-bottom: 20px;
    }

    .pipeline-reader__stage-label {
      font-family: var(--sans, 'Source Sans 3', system-ui, sans-serif);
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: var(--ink-muted);
    }

    .pipeline-reader__project-name {
      font-family: var(--sans, 'Source Sans 3', system-ui, sans-serif);
      font-size: 10px;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--ink-muted);
    }

    .pipeline-reader__body {
      font-family: var(--body, 'Source Serif 4', Georgia, serif);
      font-size: 13px;
      line-height: 1.65;
      color: var(--ink-light, var(--ink));
      flex: 1;
      overflow: hidden;
    }

    .pipeline-reader__body--structured {
      white-space: pre-line;
      column-count: 2;
      column-rule: 1px solid var(--border);
      column-gap: 32px;
    }

    .pipeline-reader__body--raw {
      white-space: pre-line;
      font-family: var(--body, 'Source Serif 4', Georgia, serif);
      font-style: italic;
      color: var(--ink-light, var(--ink));
      border-left: 3px solid var(--border);
      padding-left: 20px;
    }

    /* ── "See it live" CTA ───────────────────────────────────────────────────── */
    .pipeline-reader__cta-row {
      margin-top: 32px;
      padding-top: 20px;
      border-top: 1px solid var(--border);
    }

    .pipeline-reader__see-it-live {
      font-family: var(--sans, 'Source Sans 3', system-ui, sans-serif);
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--ink);
      background: transparent;
      border: 2px solid var(--ink);
      padding: 10px 20px;
      cursor: pointer;
      transition: background 0.15s, color 0.15s;
    }

    .pipeline-reader__see-it-live:hover {
      background: var(--ink);
      color: var(--surface);
    }

    @media (max-width: 768px) {
      .pipeline-tabs {
        grid-template-columns: repeat(2, 1fr);
      }

      .pipeline-reader__body--structured {
        column-count: 1;
      }
    }
  `],
})
export class PgPipelineComponent {
  /** Fires when the visitor clicks "See it live" on the Architecture tab. */
  readonly seeItLive = output<void>();

  readonly stages: PipelineStage[] = [
    {
      index: 0,
      label: 'Braindump',
      description: 'Raw input — any format, any length, any roughness.',
      content: PAYMENT_GATEWAY_BRAINDUMP,
      isStructured: false,
    },
    {
      index: 1,
      label: 'Analysis',
      description: 'Problem space, constraints, and root causes surfaced.',
      content: PIPELINE_ANALYSIS_PREVIEW,
      isStructured: true,
    },
    {
      index: 2,
      label: 'Epic',
      description: 'Success criteria, scope boundaries, and milestones defined.',
      content: PIPELINE_EPIC_PREVIEW,
      isStructured: true,
    },
    {
      index: 3,
      label: 'Architecture',
      description: 'Tech decisions, system design, and data flow documented.',
      content: PIPELINE_ARCHITECTURE_PREVIEW,
      isStructured: true,
    },
  ];

  /** Active stage index (0 = Braindump). */
  readonly activeStage = signal<number>(0);

  setStage(index: number): void {
    this.activeStage.set(index);
  }

  onSeeItLive(): void {
    this.seeItLive.emit();
  }
}
