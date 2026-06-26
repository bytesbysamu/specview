import { Component, inject, signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { AuthService, PENDING_SHARE_KEY } from '../../services/auth.service';

/**
 * Passwordless sign-in: collect an email, request a magic link, then show a
 * "check your email" confirmation. The actual JWT is minted on /auth/verify
 * after the user clicks the emailed link. No password field exists.
 */
@Component({
  selector: 'app-login',
  standalone: true,
  imports: [],
  template: `
    <div class="login-wrap">
      <div class="login-card">
        <div class="login-title">Specview</div>

        @if (sent()) {
          <div class="login-sub">Check your email</div>
          <p class="login-msg" data-test="login-sent">
            We sent a sign-in link to <strong>{{ sentTo() }}</strong>.
            Open it on this device to continue.
          </p>
          <button type="button" class="ghost" data-test="login-again" (click)="reset()">
            Use a different email
          </button>
        } @else {
          <div class="login-sub">Sign in with your email — no password.</div>
          @if (error()) {
            <div class="login-error" data-test="login-error">{{ error() }}</div>
          }
          <form (submit)="submit($event)">
            <input #emailEl data-test="login-email" type="email" placeholder="Email"
                   autocomplete="email" required />
            <button type="submit" data-test="login-submit" [disabled]="loading()">
              {{ loading() ? 'Sending…' : 'Send sign-in link' }}
            </button>
          </form>
        }
      </div>
    </div>
  `,
  styles: [`
    .login-wrap {
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      background: var(--bg);
    }
    .login-card {
      width: 320px;
      border: 1px solid var(--border);
      padding: 40px 32px;
    }
    .login-title {
      font-family: 'Playfair Display', serif;
      font-size: 32px;
      font-weight: 700;
      margin-bottom: 4px;
    }
    .login-sub {
      font-family: 'Source Sans 3', sans-serif;
      font-size: 13px;
      color: var(--ink-muted);
      margin-bottom: 28px;
    }
    .login-msg {
      font-family: 'Source Sans 3', sans-serif;
      font-size: 14px;
      line-height: 1.5;
      color: var(--ink);
      margin: 0 0 20px;
    }
    .login-error {
      font-family: 'Source Sans 3', sans-serif;
      font-size: 12px;
      color: var(--red);
      margin-bottom: 16px;
      padding: 8px 12px;
      border: 1px solid var(--red);
    }
    form { display: flex; flex-direction: column; gap: 12px; }
    input {
      font-family: 'Source Sans 3', sans-serif;
      font-size: 14px;
      background: none;
      border: 1px solid var(--border);
      color: var(--ink);
      padding: 10px 12px;
      outline: none;
      transition: border-color 0.15s;
      width: 100%;
    }
    input:focus { border-color: var(--ink); }
    button {
      font-family: 'Source Sans 3', sans-serif;
      font-size: 13px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      background: var(--ink);
      color: var(--bg);
      border: none;
      padding: 12px;
      cursor: pointer;
      transition: opacity 0.15s;
      margin-top: 4px;
    }
    button:disabled { opacity: 0.5; cursor: not-allowed; }
    button.ghost {
      background: none;
      color: var(--ink-muted);
      border: 1px solid var(--border);
    }
  `]
})
export class LoginComponent {
  loading = signal(false);
  error = signal('');
  sent = signal(false);
  sentTo = signal('');

  private auth = inject(AuthService);
  private route = inject(ActivatedRoute);

  async submit(e: Event) {
    e.preventDefault();
    const form = e.target as HTMLFormElement;
    const email = (form.elements[0] as HTMLInputElement).value.trim();
    if (!email) {
      this.error.set('Please enter your email.');
      return;
    }

    // Preserve a ?share=slug across the magic-link email round-trip: the emailed
    // /auth/verify link carries no query params, so stash the slug now and let
    // VerifyComponent restore it after sign-in. Same-device assumption matches
    // the "Open it on this device" copy below.
    const share = this.route.snapshot.queryParamMap.get('share');
    if (share) {
      localStorage.setItem(PENDING_SHARE_KEY, share);
    }

    this.loading.set(true);
    this.error.set('');
    try {
      await this.auth.requestMagicLink(email);
      this.sentTo.set(email);
      this.sent.set(true);
    } catch {
      this.error.set('Could not send the link. Please try again.');
    } finally {
      this.loading.set(false);
    }
  }

  reset() {
    this.sent.set(false);
    this.sentTo.set('');
    this.error.set('');
  }
}
