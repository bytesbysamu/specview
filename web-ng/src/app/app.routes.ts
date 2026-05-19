import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: 'login',
    loadComponent: () =>
      import('./components/login/login.component').then(m => m.LoginComponent),
  },
  {
    path: 'signup',
    loadComponent: () =>
      import('./pages/signup/signup.component').then(m => m.SignupComponent),
  },
  {
    path: 'playground',
    loadComponent: () =>
      import('./pg-scroll-shell.component').then(m => m.PgScrollShellComponent),
  },
  /**
   * Demo mode handoff: the landing page redirects here with ?demo=<slug>.
   * Uses a dedicated /demo path so we don't interfere with the bootstrap
   * AppComponent which renders the main app shell at the root path.
   */
  {
    path: 'demo',
    loadComponent: () =>
      import('./demo-result/demo-result.component').then(
        m => m.DemoResultComponent
      ),
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
