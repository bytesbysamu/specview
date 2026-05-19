import { DOCUMENT } from '@angular/common';
import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';

/** Shape of a single generated file returned by the bootstrap API. */
export interface BootstrapFile {
  filename: string;
  content: string;
}

/**
 * The static demo JSON shape stored in `public/demo/{slug}.json`.
 * Mirrors the terminal `BootstrapJobStatus` response (`done=true`) so that
 * `DemoResultComponent` and `AnalyzeResultComponent` share a single rendering
 * pipeline — both receive the same object shape.
 */
export interface DemoResult {
  done: true;
  running: false;
  files: BootstrapFile[];
  partial_files?: BootstrapFile[];
  latencyMs?: number;
}

/** Live bootstrap job status returned by the polling endpoint. */
export interface BootstrapJobStatus {
  running: boolean;
  done: boolean;
  status?: string;
  current_step?: string | null;
  partial_files?: BootstrapFile[];
  files?: BootstrapFile[];
  error?: string;
  latencyMs?: number;
}

/**
 * The three possible handoff states arriving from the landing page.
 *
 * - `none`  — The app was opened directly; no landing-page data present.
 * - `demo`  — Visitor clicked "Analyze" on an unedited demo braindump.
 *             `slug` identifies which pre-computed fixture to display.
 * - `real`  — Visitor edited the textarea and clicked "Analyze".
 *             `braindump` contains the decoded UTF-8 text they typed.
 */
export type LandingHandoff =
  | { mode: 'none' }
  | { mode: 'demo'; slug: string }
  | { mode: 'real'; braindump: string };

/**
 * Decode a base64url string back to a UTF-8 string.
 *
 * Mirrors the encoding in `landing/redirect.js`:
 *   - Restores the standard base64 alphabet (- → +, _ → /)
 *   - Re-pads the string to a multiple of 4 characters
 *   - Decodes via atob + TextDecoder to correctly reconstruct multi-byte Unicode
 *
 * @param encoded — The base64url string from the URL hash.
 * @returns The original UTF-8 string, or null if decoding fails.
 */
function decodeBase64Url(encoded: string): string | null {
  try {
    // Restore standard base64 alphabet and padding.
    const base64 = encoded
      .replace(/-/g, '+')
      .replace(/_/g, '/')
      .padEnd(encoded.length + ((4 - (encoded.length % 4)) % 4), '=');

    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    return new TextDecoder('utf-8').decode(bytes);
  } catch {
    return null;
  }
}

/**
 * LandingHandoffService — reads landing-page redirect parameters on construction
 * and exposes a typed handoff descriptor to consuming components.
 *
 * Read priority:
 *   1. `?demo=<slug>` query parameter   → demo mode
 *   2. `/analyze` path + `#<base64url>` hash fragment → real mode
 *   3. Neither present                  → no handoff
 *
 * The service is read-once at construction time. No polling, no subscriptions.
 * Consuming components read `handoff` once and act on it — they do not need to
 * react to changes because the handoff is a one-shot bootstrap event.
 */
@Injectable({ providedIn: 'root' })
export class LandingHandoffService {
  /**
   * The resolved handoff descriptor. Available synchronously after construction.
   */
  readonly handoff: LandingHandoff;

  private readonly http = inject(HttpClient);
  private readonly doc = inject(DOCUMENT);

  constructor() {
    this.handoff = this._resolve();
  }

  // ── Public API ─────────────────────────────────────────────────────────────

  /**
   * Fetch the pre-computed demo JSON for `slug` from `public/demo-data/{slug}.json`.
   * Used by `DemoResultComponent` to render results without an API call.
   */
  fetchDemoResult(slug: string): Promise<DemoResult> {
    return firstValueFrom(
      this.http.get<DemoResult>(`/demo-data/${slug}.json`)
    );
  }

  /**
   * Start an anonymous bootstrap job for a visitor-supplied braindump.
   * Returns a `job_id` that the caller should poll with `pollAnonymousBootstrap`.
   */
  startAnonymousBootstrap(braindump: string, projectName: string): Promise<{ job_id: string }> {
    return firstValueFrom(
      this.http.post<{ job_id: string }>(
        '/api/ai/text/anonymous/bootstrap-project',
        { project_name: projectName, braindump }
      )
    );
  }

  /**
   * Poll an anonymous bootstrap job by `job_id`.
   * Mirrors `ProjectsService.pollBootstrap` but hits the anonymous endpoint.
   */
  pollAnonymousBootstrap(jobId: string): Promise<BootstrapJobStatus> {
    return firstValueFrom(
      this.http.get<BootstrapJobStatus>(
        `/api/ai/text/anonymous/bootstrap-project/status/${jobId}`
      )
    );
  }

  // ── Private ────────────────────────────────────────────────────────────────

  private _resolve(): LandingHandoff {
    const loc = this.doc?.location;
    if (!loc) {
      return { mode: 'none' };
    }

    const params = new URLSearchParams(loc.search);
    const demoSlug = params.get('demo');

    if (demoSlug !== null && demoSlug.trim().length > 0) {
      return { mode: 'demo', slug: demoSlug.trim() };
    }

    const hash = loc.hash;
    if (loc.pathname === '/analyze' && hash.length > 1) {
      const encoded = hash.slice(1);
      const decoded = decodeBase64Url(encoded);
      if (decoded !== null && decoded.trim().length > 0) {
        return { mode: 'real', braindump: decoded };
      }
    }

    return { mode: 'none' };
  }
}
