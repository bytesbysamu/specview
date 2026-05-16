import { ChangeDetectionStrategy, Component } from '@angular/core';

interface JourneyStage {
  number: string;
  name: string;
  description: string;
  painPoint: string;
}

const JOURNEY_STAGES: JourneyStage[] = [
  {
    number: '01',
    name: 'Braindump',
    description:
      'You open a blank text field and paste everything in your head: half-formed features, ' +
      'vague user flows, opinions about the database schema, and a few contradictions you ' +
      'haven\'t resolved yet. This is the only step that requires your unfiltered thinking — ' +
      'everything after this is structured for you.',
    painPoint:
      'This is where you realize the braindump was too vague. "Make it fast" is not a spec. ' +
      'The AI will surface the ambiguity — you\'ll have to decide what fast actually means.',
  },
  {
    number: '02',
    name: 'Generate',
    description:
      'You click Generate and wait roughly 45 seconds while the pipeline runs: analysis, ' +
      'epic, architecture, timeline, and implementation guide are produced in sequence. ' +
      'You watch the status bar advance through each step. When it finishes, five documents ' +
      'appear in the sidebar.',
    painPoint:
      'The first generation is rarely perfect. Expect one or two documents to miss the ' +
      'intent of a feature — especially if your braindump used domain jargon the model ' +
      'had no context for. That\'s what the next stage is for.',
  },
  {
    number: '03',
    name: 'Review',
    description:
      'You read each spec in the newspaper-style reader. The architecture document is the ' +
      'most load-bearing — it captures technology choices that flow into every other document. ' +
      'You check whether the data model matches your intent, whether the timeline is realistic, ' +
      'and whether the epic\'s acceptance criteria are testable.',
    painPoint:
      'This is where the architecture doc saves you from a bad database decision. A schema ' +
      'chosen in haste here will cost a migration later. Slow down at this step.',
  },
  {
    number: '04',
    name: 'Iterate',
    description:
      'You use inline text operations — Expand, Clarify, Rewrite, or a custom prompt — ' +
      'to refine individual sections. You can narrow a scope that ballooned, sharpen an ' +
      'acceptance criterion that was ambiguous, or reframe a paragraph that read as ' +
      'implementation rather than requirement. Iteration is section-level, not document-level.',
    painPoint:
      'The temptation is to iterate forever. Spec documents are not novels. Set a threshold: ' +
      'if a reviewer could build from it, it\'s done. Perfect specs are a form of procrastination.',
  },
  {
    number: '05',
    name: 'Ship',
    description:
      'You share the spec set via a public link or hand off the implementation guide to ' +
      'a developer agent. The documents are versioned in the project store. If requirements ' +
      'shift next week, you return to step one — the braindump — and regenerate. ' +
      'The cycle is designed to be fast enough to repeat.',
    painPoint:
      'Sharing is the moment of accountability. Once a stakeholder has read the epic, ' +
      '"we didn\'t know what we were building" is no longer a valid excuse. ' +
      'That\'s the whole point.',
  },
];

@Component({
  selector: 'app-pg-journey-v2',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [],
  template: `
    <div class="jv2-intro">
      <p class="jv2-overline">The Journey</p>
      <h2 class="jv2-headline">Five stages, honest friction</h2>
      <p class="jv2-deck">
        This is the human side of the pipeline — what you actually do at each stage,
        and where specview saves you from the mistakes most braindumps make.
      </p>
    </div>

    <div class="jv2-stages">
      @for (stage of stages; track stage.number) {
        <div class="jv2-stage">
          <div class="jv2-stage__header">
            <span class="jv2-stage__number">{{ stage.number }}</span>
            <h3 class="jv2-stage__name">{{ stage.name }}</h3>
          </div>
          <p class="jv2-stage__description">{{ stage.description }}</p>
          <p class="jv2-stage__pain-point">{{ stage.painPoint }}</p>
        </div>
      }
    </div>
  `,
  styles: [`
    /* ── Intro block ─────────────────────────────────────────────────────────── */
    .jv2-intro {
      margin-bottom: 48px;
    }

    .jv2-overline {
      font-family: var(--sans);
      font-size: 9px;
      font-weight: 600;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--red);
      margin-bottom: 14px;
    }

    .jv2-headline {
      font-family: var(--serif);
      font-size: 44px;
      font-weight: 700;
      line-height: 1.15;
      color: var(--ink);
      margin: 0 0 20px;
    }

    .jv2-deck {
      font-family: var(--body);
      font-size: 18px;
      line-height: 1.6;
      color: var(--ink);
      max-width: 680px;
      margin: 0;
    }

    /* ── Stage list ──────────────────────────────────────────────────────────── */
    .jv2-stages {
      display: flex;
      flex-direction: column;
      gap: 0;
    }

    /* ── Individual stage card ───────────────────────────────────────────────── */
    .jv2-stage {
      display: grid;
      grid-template-columns: 220px 1fr;
      grid-template-rows: auto 1fr;
      column-gap: 48px;
      padding: 32px 0;
      border-top: 1px solid var(--border);
    }

    .jv2-stage:last-child {
      border-bottom: 1px solid var(--border);
    }

    /* ── Stage header (number + name) ───────────────────────────────────────── */
    .jv2-stage__header {
      grid-column: 1;
      grid-row: 1 / 3;
      display: flex;
      flex-direction: column;
      gap: 8px;
      padding-right: 48px;
      border-right: 1px solid var(--border);
    }

    .jv2-stage__number {
      font-family: var(--sans);
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: var(--ink-muted);
    }

    .jv2-stage__name {
      font-family: var(--serif);
      font-size: 28px;
      font-weight: 700;
      color: var(--ink);
      margin: 0;
      line-height: 1.2;
    }

    /* ── Stage description ───────────────────────────────────────────────────── */
    .jv2-stage__description {
      grid-column: 2;
      grid-row: 1;
      font-family: var(--body);
      font-size: 15px;
      line-height: 1.7;
      color: var(--ink);
      margin: 0 0 20px;
    }

    /* ── Pain-point annotation ───────────────────────────────────────────────── */
    .jv2-stage__pain-point {
      grid-column: 2;
      grid-row: 2;
      font-family: var(--serif);
      font-size: 14px;
      font-style: italic;
      line-height: 1.6;
      color: var(--red);
      margin: 0;
      padding-top: 16px;
      border-top: 2px solid var(--red);
      align-self: start;
    }

    /* ── Mobile: single column stack ────────────────────────────────────────── */
    @media (max-width: 768px) {
      .jv2-stage {
        grid-template-columns: 1fr;
        grid-template-rows: auto auto auto;
        column-gap: 0;
        row-gap: 16px;
      }

      .jv2-stage__header {
        grid-column: 1;
        grid-row: 1;
        flex-direction: row;
        align-items: baseline;
        gap: 12px;
        padding-right: 0;
        border-right: none;
        border-bottom: 1px solid var(--border);
        padding-bottom: 12px;
      }

      .jv2-stage__description {
        grid-column: 1;
        grid-row: 2;
        margin-bottom: 0;
      }

      .jv2-stage__pain-point {
        grid-column: 1;
        grid-row: 3;
        padding-top: 12px;
      }

      .jv2-headline {
        font-size: 32px;
      }
    }
  `],
})
export class PgJourneyV2Component {
  readonly stages: JourneyStage[] = JOURNEY_STAGES;
}
