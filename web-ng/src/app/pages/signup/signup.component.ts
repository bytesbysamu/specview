import { Component, signal, inject } from '@angular/core';
import { RouterLink, Router, ActivatedRoute } from '@angular/router';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-signup',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './signup.component.html',
  styleUrl: './signup.component.css',
})
export class SignupComponent {
  loading = signal(false);
  error = signal('');

  private auth = inject(AuthService);
  private router = inject(Router);
  private route = inject(ActivatedRoute);

  async submit(e: Event) {
    e.preventDefault();
    const form = e.target as HTMLFormElement;
    const email = (form.elements[0] as HTMLInputElement).value.trim();
    const password = (form.elements[1] as HTMLInputElement).value;

    if (!email || !password) {
      this.error.set('Email and password are required.');
      return;
    }

    if (password.length < 8) {
      this.error.set('Password must be at least 8 characters.');
      return;
    }

    this.loading.set(true);
    this.error.set('');
    try {
      await this.auth.register(email, password);
      const shareParam = this.route.snapshot.queryParamMap.get('share');
      if (shareParam) {
        await this.router.navigate(['/'], { queryParams: { share: shareParam } });
      } else {
        await this.router.navigate(['/']);
      }
    } catch (err: any) {
      const status = err?.status;
      if (status === 409) {
        this.error.set('An account with this email already exists.');
      } else if (status === 429) {
        this.error.set('Too many attempts — please wait before trying again.');
      } else {
        this.error.set('Registration failed. Please try again.');
      }
    } finally {
      this.loading.set(false);
    }
  }
}
