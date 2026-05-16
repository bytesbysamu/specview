import { Component, ChangeDetectionStrategy, signal } from '@angular/core';
import {
  PIPELINE_BRAINDUMP_PREVIEW,
  PIPELINE_ANALYSIS_PREVIEW,
  PIPELINE_EPIC_PREVIEW,
  PIPELINE_ARCHITECTURE_PREVIEW,
  PIPELINE_GUIDE_PREVIEW,
} from './playground-demo-data';

interface PipelineStep {
  number: string;
  label: string;
  description: string;
  content: string;
}

@Component({
  selector: 'app-pg-pipeline',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <!-- ── 5-column step grid ────────────────────────────────────────────────── -->
    <div class="pipeline-grid">
      @for (step of steps; track step.label; let i = $index) {
        <div
          class="pipeline-col"
          [class.pipeline-col--active]="selectedStep() === i"
          (click)="selectStep(i)"
          role="button"
          [attr.aria-pressed]="selectedStep() === i"
          [attr.data-test]="'pipeline-step-' + i"
        >
          <span class="pipeline-col__number">{{ step.number }}</span>
          <span class="pipeline-col__label">{{ step.label }}</span>
          <span class="pipeline-col__desc">{{ step.description }}</span>
        </div>
      }
    </div>

    <!-- ── Expanded preview panel ────────────────────────────────────────────── -->
    @if (selectedStep() !== null) {
      <div class="pipeline-panel" [attr.data-test]="'pipeline-panel'">
        <div class="pipeline-panel__header">
          <span class="pipeline-panel__step-label">
            {{ steps[selectedStep()!].label }}
          </span>
          <button class="pipeline-panel__close" (click)="selectStep(selectedStep()!)">
            Close
          </button>
        </div>
        <div class="pipeline-panel__body">
          {{ steps[selectedStep()!].content }}
        </div>
      </div>
    }
  `,
  styles: [`
    /* ── Grid ───────────────────────────────────────────────────────────────── */
    .pipeline-grid {
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      border-top: 1px solid var(--border);
      border-bottom: 1px solid var(--border);
    }

    .pipeline-col {
      display: flex;
      flex-direction: column;
      gap: 10px;
      padding: 28px 24px;
      border-right: 1px solid var(--border);
      cursor: pointer;
      transition: background 0.15s;
    }

    .pipeline-col:last-child {
      border-right: none;
    }

    .pipeline-col:hover {
      background: var(--surface-raised, rgba(0, 0, 0, 0.02));
    }

    .pipeline-col--active {
      background: var(--surface-raised, rgba(0, 0, 0, 0.03));
    }

    /* ── Step number ─────────────────────────────────────────────────────────── */
    .pipeline-col__number {
      font-family: 'Playfair Display', Georgia, serif;
      font-size: 64px;
      font-weight: 700;
      line-height: 1;
      color: var(--border);
      letter-spacing: -0.02em;
      user-select: none;
    }

    /* ── Step label ──────────────────────────────────────────────────────────── */
    .pipeline-col__label {
      font-family: 'Source Sans 3', system-ui, sans-serif;
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: var(--ink);
    }

    /* ── Step description ────────────────────────────────────────────────────── */
    .pipeline-col__desc {
      font-family: 'Source Serif 4', Georgia, serif;
      font-size: 13px;
      line-height: 1.55;
      color: var(--ink-muted);
    }

    /* ── Preview panel ───────────────────────────────────────────────────────── */
    .pipeline-panel {
      border-top: 3px solid var(--ink);
      border-bottom: 1px solid var(--border);
      padding: 32px 0;
    }

    .pipeline-panel__header {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      margin-bottom: 24px;
    }

    .pipeline-panel__step-label {
      font-family: 'Source Sans 3', system-ui, sans-serif;
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: var(--ink-muted);
    }

    .pipeline-panel__close {
      font-family: 'Source Sans 3', system-ui, sans-serif;
      font-size: 10px;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--ink-muted);
      background: transparent;
      border: none;
      cursor: pointer;
      padding: 0;
      transition: color 0.12s;
    }

    .pipeline-panel__close:hover {
      color: var(--ink);
    }

    .pipeline-panel__body {
      font-family: 'Source Serif 4', Georgia, serif;
      font-size: 14px;
      line-height: 1.75;
      color: var(--ink-light, var(--ink));
      white-space: pre-line;
      column-count: 2;
      column-rule: 1px solid var(--border);
      column-gap: 32px;
    }
  `],
})
export class PgPipelineComponent {
  readonly steps: PipelineStep[] = [
    {
      number: '01',
      label: 'Braindump',
      description: 'Raw input — any format, any length, any roughness.',
      content: PIPELINE_BRAINDUMP_PREVIEW,
    },
    {
      number: '02',
      label: 'Analysis',
      description: 'Problem space, constraints, and root causes surfaced.',
      content: PIPELINE_ANALYSIS_PREVIEW,
    },
    {
      number: '03',
      label: 'Epic',
      description: 'Success criteria, scope boundaries, and milestones defined.',
      content: PIPELINE_EPIC_PREVIEW,
    },
    {
      number: '04',
      label: 'Architecture',
      description: 'Tech decisions, system design, and data flow documented.',
      content: PIPELINE_ARCHITECTURE_PREVIEW,
    },
    {
      number: '05',
      label: 'Guide',
      description: 'Ordered implementation tasks a developer can execute.',
      content: PIPELINE_GUIDE_PREVIEW,
    },
  ];

  selectedStep = signal<number | null>(null);

  selectStep(index: number): void {
    if (this.selectedStep() === index) {
      this.selectedStep.set(null);
    } else {
      this.selectedStep.set(index);
    }
  }
}
