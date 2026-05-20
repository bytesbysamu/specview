import {
  Component,
  OnInit,
  OnDestroy,
  inject,
  signal,
} from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { marked } from 'marked';
import DOMPurify from 'dompurify';

import { ProjectsService } from '../services/projects.service';

const POLL_INTERVAL_MS = 2500;

/**
 * AnalyzeResultComponent — handles the `/analyze` route.
 *
 * Reads a `job` query parameter, polls `GET /api/public/analyze/<job_id>`
 * via `ProjectsService.pollPublicAnalysis`, and renders the analysis markdown.
 * No authentication required — this is a public endpoint.
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

      @if (isRunning() && !analysisHtml()) {
        <div class="result-loading" data-test="analyze-result-loading">
          <div class="spinner" aria-hidden="true"></div>
          <p class="loading-label">Analysing braindump...</p>
        </div>
      }

      @if (isRunning() && analysisHtml()) {
        <div class="progress-banner" data-test="analyze-progress-banner">
          <div class="spinner spinner--sm" aria-hidden="true"></div>
          <span>Analysis in progress...</span>
        </div>
      }

      @if (analysisHtml()) {
        <div class="result-content" data-test="analyze-result-content">
          <div
            class="markdown-body"
            [innerHTML]="analysisHtml()"
            data-test="analyze-markdown-body"
          ></div>
        </div>

        @if (braindumpContent()) {
          <details class="braindump-details" data-test="analyze-braindump-details">
            <summary class="braindump-summary">Your original braindump</summary>
            <pre class="braindump-pre">{{ braindumpContent() }}</pre>
          </details>
        }

        @if (!isRunning()) {
          <div class="conversion-gate" data-test="analyze-conversion-gate">
            <p class="gate-prompt">
              Your analysis is ready. Sign up to save it and create more — free.
            </p>
            <a href="/signup" class="gate-cta" data-test="analyze-signup-link">
              Save your analysis
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

    .result-content {
      flex: 1;
    }

    .markdown-body {
      line-height: 1.7;
      font-size: 1rem;
      color: var(--color-text, #222);
    }

    .braindump-details {
      margin-top: 2rem;
      border: 1px solid var(--color-border, #e0e0e0);
      border-radius: 6px;
      overflow: hidden;
    }

    .braindump-summary {
      padding: 0.75rem 1rem;
      cursor: pointer;
      font-size: 0.875rem;
      font-weight: 600;
      color: var(--color-text-muted, #666);
      background: var(--color-surface-alt, #f5f7fa);
      user-select: none;
    }

    .braindump-pre {
      margin: 0;
      padding: 1rem;
      font-size: 0.8125rem;
      line-height: 1.6;
      color: var(--color-text, #222);
      white-space: pre-wrap;
      word-break: break-word;
      background: transparent;
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
  private readonly route = inject(ActivatedRoute);
  private readonly projectsSvc = inject(ProjectsService);

  readonly isRunning = signal(false);
  readonly analysisHtml = signal<string | null>(null);
  readonly braindumpContent = signal<string | null>(null);
  readonly fatalError = signal<string | null>(null);
  readonly projectId = signal<string | null>(null);

  private pollInterval: ReturnType<typeof setInterval> | null = null;

  ngOnInit(): void {
    const jobId = this.route.snapshot.queryParamMap.get('job');
    if (!jobId) {
      this.fatalError.set('No job ID provided. Please return to the landing page and try again.');
      return;
    }
    this.isRunning.set(true);
    this._startPolling(jobId);
  }

  ngOnDestroy(): void {
    this._stopPolling();
  }

  private _startPolling(jobId: string): void {
    this.pollInterval = setInterval(async () => {
      try {
        const status = await this.projectsSvc.pollPublicAnalysis(jobId);

        if (status.done) {
          this._stopPolling();
          this.isRunning.set(false);
          if (status.error) {
            this.fatalError.set(status.error);
          } else {
            if (status.analysis) {
              const html = await marked.parse(status.analysis);
              this.analysisHtml.set(DOMPurify.sanitize(html));
            }
            if (status.braindump) {
              this.braindumpContent.set(status.braindump);
            }
            if (status.project_id) {
              this.projectId.set(status.project_id);
            }
          }
        }
      } catch (e: any) {
        const httpStatus = e?.status ?? 0;
        if (httpStatus === 404) {
          this._stopPolling();
          this.isRunning.set(false);
          this.fatalError.set('Analysis not found or expired.');
        }
        // Transient network errors: keep polling
      }
    }, POLL_INTERVAL_MS);
  }

  private _stopPolling(): void {
    if (this.pollInterval !== null) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }
  }
}
