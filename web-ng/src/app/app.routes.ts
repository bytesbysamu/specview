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
   * Angular Router does not match on query parameters; the empty-string path
   * catches the root URL and LandingHandoffService reads the ?demo param.
   * When a ?demo param is present, DemoResultComponent renders the pre-computed
   * JSON. Otherwise the standard AppComponent is shown.
   */
  {
    path: '',
    loadComponent: () => {
      // Angular Router cannot branch on query params, so we inspect the URL
      // here at load time. When ?demo=<slug> is present, load the demo viewer;
      // otherwise fall through to the main app shell.
      const params = new URLSearchParams(
        typeof window !== 'undefined' ? window.location.search : ''
      );
      if (params.has('demo') && params.get('demo')!.trim().length > 0) {
        return import('./demo-result/demo-result.component').then(
          m => m.DemoResultComponent
        );
      }
      return import('./app.component').then(m => m.AppComponent);
    },
    pathMatch: 'full',
  },
  /**
   * Real mode handoff: the landing page redirects here with the braindump
   * content base64url-encoded in the URL hash fragment (#<encoded>).
   * LandingHandoffService reads and decodes window.location.hash on this path.
   * AnalyzeResultComponent calls the anonymous bootstrap API and polls for
   * progressive results.
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
