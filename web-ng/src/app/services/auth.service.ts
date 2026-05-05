import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';

interface LoginResponse { token: string; email: string; }

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly TOKEN_KEY = 'specview_jwt';
  readonly isLoggedIn = signal(!!this.getStoredJwt());

  constructor(private http: HttpClient) {}

  async login(email: string, password: string): Promise<void> {
    const res = await firstValueFrom(
      this.http.post<LoginResponse>('/api/auth/login', { email, password })
    );
    localStorage.setItem(this.TOKEN_KEY, res.token);
    this.isLoggedIn.set(true);
  }

  signOut(): void {
    localStorage.removeItem(this.TOKEN_KEY);
    this.isLoggedIn.set(false);
  }

  getStoredJwt(): string | null {
    return localStorage.getItem(this.TOKEN_KEY);
  }
}
