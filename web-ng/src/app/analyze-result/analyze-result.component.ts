import {
  Component,
  OnInit,
  OnDestroy,
  inject,
  signal,
  computed,
} from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { marked } from 'marked';
import DOMPurify from 'dompurify';

import {
  LandingHandoffService,
  BootstrapFile,
  BootstrapJobStatus,
} from '../landing-handoff.service';

const FILE_LABELS: Record<string, string> = {
  'analysis.md': 'Analysis',
  'epic.md': 'Epic',
  'architecture.md': 'Solution Architecture',
  'timeline.md': 'Timeline',
  'spec-index.md': 'Spec Index',
  'README.md': 'README',
};

const CANONICAL_ORDER = [
  'spec-index.md',
  'analysis.md',
  'epic.md',
  'architecture.md',
  'timeline.md',
  'README.md',
];

const POLL_INTERVAL_MS = 3000;

const STEP_LABELS: Record<string, string> = {
  analysis: 'Analysing braindump...',
  epic: 'Writing epic...',
  architecture: 'Designing architecture...',
};

function sortFiles(files: BootstrapFile[]): BootstrapFile[] {
  return [...files].sort((a, b) => {
    const ia = CANONICAL_ORDER.indexOf(a.filename);
    const ib = CANONICAL_ORDER.indexOf(b.filename);
    return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
  });
}

/**
 * AnalyzeResultComponent — handles the `/analyze` route.
 *
 * On init the component decodes the base64url braindump from the URL hash
 * (via `LandingHandoffService`), fires `POST /api/ai/text/anonymous/bootstrap-project`,
 * and polls for progress. Partial files are rendered as each step completes so
 * the visitor sees progressive output. Both this component and `DemoResultComponent`
 * render with the same markup so the two paths converge on a single pipeline.
 */
@Component({
  selector: 'app-analyze-result',
  standalone: true,
  template: `
    <div class="result-shell" data-test="analyze-result-shell">
      @if (fatalError()) {
        <div class="result-error" data-test="analyze-result-error">
          <p>{{ fatalError() }}</p>
        </div>
      }

      @if (isRunning() && files().length === 0) {
        <div class="result-loading" data-test="analyze-result-loading">
          <div class="spinner" aria-hidden="true"></div>
          <p class="loading-label">{{ stepLabel() }}</p>
        </div>
      }

      @if (isRunning() && files().length > 0) {
        <div class="progress-banner" data-test="analyze-progress-banner">
          <div class="spinner spinner--sm" aria-hidden="true"></div>
          <span>{{ stepLabel() }}</span>
        </div>
      }

      @if (files().length > 0) {
        <div class="result-tabs" data-test="analyze-result-tabs">
          @for (f of files(); track f.filename) {
            <button
              class="tab-btn"
              [class.active]="activeFilename() === f.filename"
              (click)="selectFile(f.filename)"
              data-test="analyze-tab-btn"
            >
              {{ labelFor(f.filename) }}
            </button>
          }
        </div>

        <div class="result-content" data-test="analyze-result-content">
          @if (parsedContent()) {
            <div
              class="markdown-body"
              [innerHTML]="parsedContent()"
              data-test="analyze-markdown-body"
            ></div>
          }
        </div>

        @if (!isRunning()) {
          <div class="conversion-gate" data-test="analyze-conversion-gate">
            <p class="gate-prompt">
              Your spec is ready. Sign up to save it and create more — free.
            </p>
            <a href="/signup" class="gate-cta" data-test="analyze-signup-link">
              Save your spec
            </a>
          </div>
        }
      }
    </div>
  `,
  styles: [`
    .result-shell {
      display: flex;
      flex-direction: column;
      min-height: 100vh;
      max-width: 860px;
      margin: 0 auto;
      padding: 2rem 1.5rem;
      gap: 0;
    }

    .result-error {
      color: var(--color-error, #c0392b);
      padding: 1rem;
    }

    .result-loading {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 4rem 1rem;
      gap: 1rem;
    }

    .progress-banner {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.5rem 0;
      margin-bottom: 1rem;
      font-size: 0.875rem;
      color: var(--color-text-muted, #666);
    }

    .spinner {
      width: 32px;
      height: 32px;
      border: 3px solid var(--color-border, #e0e0e0);
      border-top-color: var(--color-accent, #1a73e8);
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }

    .spinner--sm {
      width: 16px;
      height: 16px;
      border-width: 2px;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    .loading-label {
      font-size: 0.9375rem;
      color: var(--color-text-muted, #666);
    }

    .result-tabs {
      display: flex;
      gap: 0.25rem;
      flex-wrap: wrap;
      border-bottom: 1px solid var(--color-border, #e0e0e0);
      margin-bottom: 1.5rem;
    }

    .tab-btn {
      padding: 0.5rem 1rem;
      border: none;
      background: none;
      cursor: pointer;
      font-size: 0.875rem;
      color: var(--color-text-muted, #666);
      border-bottom: 2px solid transparent;
      transition: color 0.15s, border-color 0.15s;
    }

    .tab-btn:hover {
      color: var(--color-text, #222);
    }

    .tab-btn.active {
      color: var(--color-accent, #1a73e8);
      border-bottom-color: var(--color-accent, #1a73e8);
      font-weight: 600;
    }

    .result-content {
      flex: 1;
    }

    .markdown-body {
      line-height: 1.7;
      font-size: 1rem;
      color: var(--color-text, #222);
    }

    .conversion-gate {
      margin-top: 3rem;
      padding: 2rem;
      background: var(--color-surface-alt, #f5f7fa);
      border-radius: 8px;
      text-align: center;
      border: 1px solid var(--color-border, #e0e0e0);
    }

    .gate-prompt {
      margin: 0 0 1rem;
      font-size: 1rem;
      color: var(--color-text, #222);
    }

    .gate-cta {
      display: inline-block;
      padding: 0.75rem 1.5rem;
      background: var(--color-accent, #1a73e8);
      color: #fff;
      border-radius: 6px;
      text-decoration: none;
      font-weight: 600;
      font-size: 0.9375rem;
      transition: opacity 0.15s;
    }

    .gate-cta:hover {
      opacity: 0.9;
    }
  `],
})
export class AnalyzeResultComponent implements OnInit, OnDestroy {
  private readonly handoffSvc = inject(LandingHandoffService);
  private readonly sanitizer = inject(DomSanitizer);

  readonly files = signal<BootstrapFile[]>([]);
  readonly activeFilename = signal<string | null>(null);
  readonly isRunning = signal(false);
  readonly currentStep = signal<string | null>(null);
  readonly fatalError = signal<string | null>(null);

  readonly stepLabel = computed(() => {
    const step = this.currentStep();
    return step ? (STEP_LABELS[step] ?? `Running ${step}...`) : 'Starting analysis...';
  });

  readonly parsedContent = computed<SafeHtml>(() => {
    const name = this.activeFilename();
    const f = this.files().find(x => x.filename === name);
    if (!f?.content) return '';
    const html = marked.parse(f.content) as string;
    return this.sanitizer.bypassSecurityTrustHtml(DOMPurify.sanitize(html));
  });

  private pollInterval: ReturnType<typeof setInterval> | null = null;

  ngOnInit(): void {
    const handoff = this.handoffSvc.handoff;
    if (handoff.mode !== 'real') {
      this.fatalError.set('No braindump found. Please return to the landing page and try again.');
      return;
    }
    this._startBootstrap(handoff.braindump);
  }

  ngOnDestroy(): void {
    this._stopPolling();
  }

  selectFile(filename: string): void {
    this.activeFilename.set(filename);
  }

  labelFor(filename: string): string {
    return FILE_LABELS[filename] ?? filename.replace(/\.md$/i, '');
  }

  private async _startBootstrap(braindump: string): Promise<void> {
    this.isRunning.set(true);
    this.fatalError.set(null);

    const projectName = this._deriveProjectName(braindump);

    let jobId: string;
    try {
      const resp = await this.handoffSvc.startAnonymousBootstrap(braindump, projectName);
      jobId = resp.job_id;
    } catch (e: any) {
      const msg = e?.error?.message ?? e?.error?.error ?? e?.message ?? 'Failed to start analysis.';
      this.fatalError.set(msg);
      this.isRunning.set(false);
      return;
    }

    this._startPolling(jobId);
  }

  private _startPolling(jobId: string): void {
    this.pollInterval = setInterval(async () => {
      try {
        const status: BootstrapJobStatus = await this.handoffSvc.pollAnonymousBootstrap(jobId);
        this.currentStep.set(status.current_step ?? null);
        this._applyPartialFiles(status.partial_files ?? []);

        if (status.done) {
          this._stopPolling();
          this.isRunning.set(false);
          if (status.error) {
            this.fatalError.set(status.error);
          } else {
            this._applyFinalFiles(status.files ?? status.partial_files ?? []);
          }
        }
      } catch (e: any) {
        // Don't stop polling on a transient network error — only on explicit failure
        const status = e?.status ?? 0;
        if (status === 404) {
          // Job evicted — treat as completion failure
          this._stopPolling();
          this.isRunning.set(false);
          if (this.files().length === 0) {
            this.fatalError.set('Analysis job not found. It may have expired.');
          }
        }
      }
    }, POLL_INTERVAL_MS);
  }

  private _stopPolling(): void {
    if (this.pollInterval !== null) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }
  }

  /**
   * Merge partial files into the current file list without clobbering files
   * that already arrived from a later step. We keep the latest content per filename.
   */
  private _applyPartialFiles(incoming: BootstrapFile[]): void {
    if (incoming.length === 0) return;
    const current = new Map(this.files().map(f => [f.filename, f]));
    for (const f of incoming) {
      current.set(f.filename, f);
    }
    const sorted = sortFiles(Array.from(current.values()));
    this.files.set(sorted);
    // Auto-select first file if none is selected yet
    if (!this.activeFilename() && sorted.length > 0) {
      this.activeFilename.set(sorted[0].filename);
    }
  }

  private _applyFinalFiles(files: BootstrapFile[]): void {
    const sorted = sortFiles(files);
    this.files.set(sorted);
    if (!this.activeFilename() && sorted.length > 0) {
      this.activeFilename.set(sorted[0].filename);
    }
  }

  /** Derive a readable project name from the first line of the braindump. */
  private _deriveProjectName(braindump: string): string {
    const firstLine = braindump.split('\n').find(l => l.trim().length > 0) ?? '';
    const trimmed = firstLine.trim().replace(/^#+\s*/, '').slice(0, 60);
    return trimmed || 'My Project';
  }
}
