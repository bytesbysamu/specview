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
  { path: '**', redirectTo: '', pathMatch: 'full' },
];
