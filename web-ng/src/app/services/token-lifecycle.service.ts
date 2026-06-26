import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';

interface RefreshResponse { token: string; email: string; }

const TOKEN_KEY = 'specview_jwt';
const REFRESH_WINDOW_SECONDS = 3600; // 1 hour

@Injectable({ providedIn: 'root' })
export class TokenLifecycleService {
  /** Single source of truth for login state — AuthService reads this signal. */
  readonly isLoggedIn = signal(!!localStorage.getItem(TOKEN_KEY));

  /** In-flight refresh promise used as a mutex to prevent concurrent refresh calls. */
  private _refreshPromise: Promise<string | null> | null = null;

  constructor(private http: HttpClient, private router: Router) {}

  /** Store a token and update login state. Called by AuthService after login/register. */
  storeToken(token: string): void {
    localStorage.setItem(TOKEN_KEY, token);
    this.isLoggedIn.set(true);
  }

  /** Return the raw stored token without any refresh logic. */
  getRawToken(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  }

  /**
   * Return a valid token, proactively refreshing if within the refresh window.
   * Concurrent callers await the same in-flight refresh promise (mutex).
   */
  async getToken(): Promise<string | null> {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) return null;

    const exp = this._decodeExp(token);
    if (exp === null) return token;

    const secondsUntilExpiry = exp - Math.floor(Date.now() / 1000);

    if (secondsUntilExpiry <= 0) {
      // Token already expired — treat as terminal failure.
      await this.handleAuthFailure();
      return null;
    }

    if (secondsUntilExpiry > REFRESH_WINDOW_SECONDS) {
      // Token is fresh — return as-is.
      return token;
    }

    // Within refresh window — refresh, serialising concurrent callers.
    if (!this._refreshPromise) {
      this._refreshPromise = this._doRefresh().finally(() => {
        this._refreshPromise = null;
      });
    }
    return this._refreshPromise;
  }

  /** Clear state and navigate to login. Called on terminal 401 failures. */
  async handleAuthFailure(): Promise<void> {
    localStorage.removeItem(TOKEN_KEY);
    this.isLoggedIn.set(false);
    await this.router.navigate(['/login']);
  }

  // ---------------------------------------------------------------------------
  // Private helpers
  // ---------------------------------------------------------------------------

  private async _doRefresh(): Promise<string | null> {
    const current = localStorage.getItem(TOKEN_KEY);
    if (!current) {
      await this.handleAuthFailure();
      return null;
    }
    try {
      // /api/auth/refresh requires the (still-valid, near-expiry) bearer, but it
      // is a PUBLIC_PATH in the interceptor to avoid recursing through getToken().
      // So we attach the current token's bearer header explicitly here.
      const res = await firstValueFrom(
        this.http.post<RefreshResponse>('/api/auth/refresh', {}, {
          headers: { Authorization: `Bearer ${current}` },
        })
      );
      this.storeToken(res.token);
      return res.token;
    } catch {
      await this.handleAuthFailure();
      return null;
    }
  }

  /**
   * Decode the exp claim from a JWT payload segment without verifying the
   * signature (signature verification is the backend's responsibility).
   */
  private _decodeExp(token: string): number | null {
    try {
      const segments = token.split('.');
      if (segments.length !== 3) return null;
      const payload = JSON.parse(atob(segments[1].replace(/-/g, '+').replace(/_/g, '/')));
      return typeof payload['exp'] === 'number' ? payload['exp'] : null;
    } catch {
      return null;
    }
  }
}
