import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { TokenLifecycleService } from './token-lifecycle.service';

interface AuthResponse { token: string; email: string; }

@Injectable({ providedIn: 'root' })
export class AuthService {
  /** Exposed for components and guards — backed by TokenLifecycleService. */
  get isLoggedIn() { return this.lifecycle.isLoggedIn; }

  constructor(private http: HttpClient, private lifecycle: TokenLifecycleService) {}

  async login(email: string, password: string): Promise<void> {
    const res = await firstValueFrom(
      this.http.post<AuthResponse>('/api/auth/login', { email, password })
    );
    this.lifecycle.storeToken(res.token);
  }

  async register(email: string, password: string): Promise<void> {
    const res = await firstValueFrom(
      this.http.post<AuthResponse>('/api/auth/register', { email, password })
    );
    this.lifecycle.storeToken(res.token);
  }

  signOut(): void {
    this.lifecycle.handleAuthFailure();
  }

  /** Returns the raw stored JWT. Used by the interceptor for non-refresh paths. */
  getStoredJwt(): string | null {
    return this.lifecycle.getRawToken();
  }
}
