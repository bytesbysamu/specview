import { Routes } from '@angular/router';
import { LoginComponent } from './components/login/login.component';
import { SignupComponent } from './pages/signup/signup.component';
import { UpgradeComponent } from './components/upgrade/upgrade.component';
import { PublicSpecComponent } from './pages/public-spec/public-spec.component';
import { AppComponent } from './app.component';

export const routes: Routes = [
  { path: 'signup', component: SignupComponent },
  { path: 'upgrade', component: UpgradeComponent },
  { path: 's/:slug', component: PublicSpecComponent },
  { path: 'playground', loadComponent: () => import('./pg-scroll-shell.component').then(m => m.PgScrollShellComponent) },
  { path: 'v1', component: AppComponent },
  { path: 'v2', redirectTo: '', pathMatch: 'full' },
  { path: 'v3', redirectTo: '', pathMatch: 'full' },
  { path: '', loadComponent: () => import('./app-v3.component').then(m => m.AppV3Component) },
  { path: '**', component: LoginComponent },
];
