import { Routes } from '@angular/router';
import { LandingComponent } from './pages/landing/landing.component';

export const routes: Routes = [
  {
    path: '',
    component: LandingComponent,
  },
  {
    path: 'app',
    loadComponent: () =>
      import('./pages/app-page/app-page.component').then(
        m => m.AppPageComponent
      ),
  },
  {
    path: 'playground',
    loadComponent: () =>
      import('./pg-scroll-shell.component').then(m => m.PgScrollShellComponent),
  },
  { path: '**', redirectTo: '', pathMatch: 'full' },
];
