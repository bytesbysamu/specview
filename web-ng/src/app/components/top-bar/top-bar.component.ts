import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-top-bar',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './top-bar.component.html',
  styleUrl: './top-bar.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TopBarComponent {
  readonly auth = inject(AuthService);
  showLoginForm = signal(false);
  loginError = signal<string | null>(null);
  loginLoading = signal(false);

  toggleLogin(): void {
    this.showLoginForm.update(v => !v);
    this.loginError.set(null);
  }

  async login(email: string, password: string): Promise<void> {
    if (!email || !password) return;
    this.loginLoading.set(true);
    this.loginError.set(null);
    try {
      await this.auth.login(email, password);
      this.showLoginForm.set(false);
    } catch (e: any) {
      this.loginError.set(e?.error?.error ?? 'Login failed');
    } finally {
      this.loginLoading.set(false);
    }
  }

  logout(): void {
    this.auth.signOut();
  }
}
