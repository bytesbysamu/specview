import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: 'playground',
    loadComponent: () =>
      import('./pg-scroll-shell.component').then(m => m.PgScrollShellComponent),
  },
  { path: '**', redirectTo: '', pathMatch: 'full' },
];
