import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: 'login',
    loadComponent: () =>
      import('./components/login/login.component').then(m => m.LoginComponent),
  },
  {
    // Passwordless: "sign up" and "sign in" are the same magic-link flow
    // (/api/auth/verify find-or-creates the user). Kept as a route so existing
    // "Sign up free" links resolve.
    path: 'signup',
    loadComponent: () =>
      import('./components/login/login.component').then(m => m.LoginComponent),
  },
  {
    // Magic-link landing target: FRONTEND_URL/auth/verify?token=...
    path: 'auth/verify',
    loadComponent: () =>
      import('./components/verify/verify.component').then(m => m.VerifyComponent),
  },
  {
    // Stripe Checkout return target: FRONTEND_URL/upgrade?session_id=...
    // (backend success_url / cancel_url both point here). Reads ?session_id,
    // verifies the session, and shows success / pending / cancelled state.
    path: 'upgrade',
    loadComponent: () =>
      import('./components/upgrade/upgrade.component').then(m => m.UpgradeComponent),
  },
  {
    path: 'playground',
    loadComponent: () =>
      import('./pg-scroll-shell.component').then(m => m.PgScrollShellComponent),
  },
  /**
   * Real mode handoff: the landing page redirects here with the braindump
   * content base64url-encoded in the URL hash fragment (#<encoded>).
   * LandingHandoffService reads and decodes window.location.hash on this path.
   */
  {
    path: 'analyze',
    loadComponent: () =>
      import('./analyze-result/analyze-result.component').then(
        m => m.AnalyzeResultComponent
      ),
  },
  { path: '**', redirectTo: '', pathMatch: 'full' },
];
