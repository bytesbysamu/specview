import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { TokenLifecycleService } from './token-lifecycle.service';

interface MagicLinkResponse { sent: boolean; }
interface VerifyResponse { token: string; email: string; }

/**
 * Passwordless, magic-link auth against oll-core.
 *
 *   requestMagicLink(email) → POST /api/auth/magic-link  (emails a sign-in link)
 *   verifyToken(token)      → POST /api/auth/verify       (exchanges link token for a JWT)
 *
 * There are no passwords and no separate register step: /api/auth/verify
 * find-or-creates the user by email, so "sign up" and "sign in" are one flow.
 */
@Injectable({ providedIn: 'root' })
export class AuthService {
  /** Exposed for components and guards — backed by TokenLifecycleService. */
  get isLoggedIn() { return this.lifecycle.isLoggedIn; }

  constructor(private http: HttpClient, private lifecycle: TokenLifecycleService) {}

  /**
   * Request a single-use sign-in link by email. Always resolves on a 200
   * (the backend returns {sent:true} even for unknown addresses to prevent
   * account enumeration); the caller shows a "check your email" confirmation.
   */
  async requestMagicLink(email: string): Promise<void> {
    await firstValueFrom(
      this.http.post<MagicLinkResponse>('/api/auth/magic-link', { email })
    );
  }

  /**
   * Exchange the token from an emailed sign-in link for a JWT and persist it.
   * Throws on an invalid/expired/used token (HTTP 401).
   */
  async verifyToken(token: string): Promise<string> {
    const res = await firstValueFrom(
      this.http.post<VerifyResponse>('/api/auth/verify', { token })
    );
    this.lifecycle.storeToken(res.token);
    return res.email;
  }

  signOut(): void {
    this.lifecycle.handleAuthFailure();
  }

  /** Returns the raw stored JWT. Used by the interceptor for non-refresh paths. */
  getStoredJwt(): string | null {
    return this.lifecycle.getRawToken();
  }
}
