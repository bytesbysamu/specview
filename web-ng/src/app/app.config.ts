import { ApplicationConfig, provideZoneChangeDetection } from '@angular/core';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideAnimations } from '@angular/platform-browser/animations';
import { provideRouter } from '@angular/router';
import { authInterceptor } from './interceptors/auth.interceptor';
import { billingInterceptor } from './interceptors/billing.interceptor';
import { baseUrlInterceptor } from './interceptors/base-url.interceptor';
import { provideApiConfiguration } from './api/api-configuration';
import { environment } from '../environments/environment';
import { routes } from './app.routes';

export const appConfig: ApplicationConfig = {
  providers: [
    provideZoneChangeDetection({ eventCoalescing: true }),
    // baseUrlInterceptor runs LAST so auth/billing still match root-relative
    // paths; it then prefixes environment.apiBaseUrl (empty on web, absolute on
    // a Capacitor native build).
    provideHttpClient(withInterceptors([authInterceptor, billingInterceptor, baseUrlInterceptor])),
    // Keep the generated API client's rootUrl aligned with the same base.
    provideApiConfiguration(environment.apiBaseUrl),
    provideAnimations(),
    provideRouter(routes),
  ]
};
