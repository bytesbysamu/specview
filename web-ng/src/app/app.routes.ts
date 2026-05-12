import { Routes } from '@angular/router';
import { LoginComponent } from './components/login/login.component';
import { SignupComponent } from './pages/signup/signup.component';

export const routes: Routes = [
  { path: 'signup', component: SignupComponent },
  { path: '**', component: LoginComponent },
];
