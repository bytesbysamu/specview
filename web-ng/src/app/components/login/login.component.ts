import { Component, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [RouterLink],
  template: `
    <div class="login-wrap">
      <div class="login-card">
        <div class="login-title">Specview</div>
        <div class="login-sub">Sign in to continue</div>
        @if (error()) {
          <div class="login-error" data-test="login-error">{{ error() }}</div>
        }
        <form (submit)="submit($event)">
          <input #emailEl data-test="login-email" type="email" placeholder="Email" autocomplete="username" required />
          <input #passEl data-test="login-password" type="password" placeholder="Password" autocomplete="current-password" required />
          <button type="submit" data-test="login-submit" [disabled]="loading()">
            {{ loading() ? 'Signing in…' : 'Sign in' }}
          </button>
        </form>
        <div class="login-signup">Don't have an account? <a routerLink="/signup">Sign up</a></div>
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
    .login-signup {
      font-family: 'Source Sans 3', sans-serif;
      font-size: 13px;
      color: var(--ink-muted);
      text-align: center;
      margin-top: 20px;
    }
    .login-signup a {
      color: var(--ink);
      font-weight: 600;
      text-decoration: underline;
      text-underline-offset: 3px;
    }
    .login-signup a:hover { opacity: 0.7; }
  `]
})
export class LoginComponent {
  loading = signal(false);
  error = signal('');

  private auth = inject(AuthService);
  private router = inject(Router);

  async submit(e: Event) {
    e.preventDefault();
    const form = e.target as HTMLFormElement;
    const email = (form.elements[0] as HTMLInputElement).value;
    const password = (form.elements[1] as HTMLInputElement).value;

    this.loading.set(true);
    this.error.set('');
    try {
      await this.auth.login(email, password);
      this.router.navigate(['/']);
    } catch {
      this.error.set('Invalid email or password.');
    } finally {
      this.loading.set(false);
    }
  }
}
