import { Component, inject, signal, OnInit } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { AuthService } from '../../services/auth.service';

/**
 * Landing target for emailed magic links: FRONTEND_URL/auth/verify?token=...
 * Reads ?token=, exchanges it for a JWT via AuthService.verifyToken(), then
 * redirects to the logged-in app root. Shows an error with a retry link if the
 * token is missing, expired, or already used.
 */
@Component({
  selector: 'app-verify',
  standalone: true,
  imports: [RouterLink],
  template: `
    <div class="verify-wrap">
      <div class="verify-card">
        <div class="verify-title">Specview</div>
        @if (error()) {
          <p class="verify-msg verify-err" data-test="verify-error">{{ error() }}</p>
          <a class="verify-link" routerLink="/login" data-test="verify-retry">Request a new link</a>
        } @else {
          <p class="verify-msg" data-test="verify-pending">Signing you in…</p>
        }
      </div>
    </div>
  `,
  styles: [`
    .verify-wrap {
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      background: var(--bg);
    }
    .verify-card {
      width: 320px;
      border: 1px solid var(--border);
      padding: 40px 32px;
      text-align: center;
    }
    .verify-title {
      font-family: 'Playfair Display', serif;
      font-size: 32px;
      font-weight: 700;
      margin-bottom: 20px;
    }
    .verify-msg {
      font-family: 'Source Sans 3', sans-serif;
      font-size: 14px;
      color: var(--ink);
      margin: 0 0 16px;
    }
    .verify-err { color: var(--red); }
    .verify-link {
      font-family: 'Source Sans 3', sans-serif;
      font-size: 13px;
      font-weight: 600;
      color: var(--ink);
      text-decoration: underline;
      text-underline-offset: 3px;
    }
  `]
})
export class VerifyComponent implements OnInit {
  error = signal('');

  private auth = inject(AuthService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);

  async ngOnInit() {
    const token = this.route.snapshot.queryParamMap.get('token');
    if (!token) {
      this.error.set('This sign-in link is missing its token.');
      return;
    }
    try {
      await this.auth.verifyToken(token);
      await this.router.navigateByUrl('/');
    } catch {
      this.error.set('This sign-in link is invalid or has expired.');
    }
  }
}
