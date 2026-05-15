import { Routes } from '@angular/router';
import { LoginComponent } from './components/login/login.component';
import { SignupComponent } from './pages/signup/signup.component';
import { UpgradeComponent } from './components/upgrade/upgrade.component';
import { PublicSpecComponent } from './pages/public-spec/public-spec.component';

export const routes: Routes = [
  { path: 'signup', component: SignupComponent },
  { path: 'upgrade', component: UpgradeComponent },
  { path: 's/:slug', component: PublicSpecComponent },
  { path: '', component: PublicSpecComponent, data: { isLanding: true, slug: 'LANDING' } },
  { path: '**', component: LoginComponent },
];
