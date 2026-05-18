import { routes } from './app.routes';

describe('app.routes', () => {
  it('defines a route for "login"', () => {
    const route = routes.find(r => r.path === 'login');
    expect(route).toBeTruthy();
  });

  it('defines a route for "signup"', () => {
    const route = routes.find(r => r.path === 'signup');
    expect(route).toBeTruthy();
  });

  it('defines a route for "playground"', () => {
    const route = routes.find(r => r.path === 'playground');
    expect(route).toBeTruthy();
  });

  it('defines a wildcard "**" catch-all route', () => {
    const route = routes.find(r => r.path === '**');
    expect(route).toBeTruthy();
  });

  it('does NOT define a route for "upgrade"', () => {
    const route = routes.find(r => r.path === 'upgrade');
    expect(route).toBeUndefined();
  });

  it('wildcard route redirects to ""', () => {
    const wildcard = routes.find(r => r.path === '**');
    expect(wildcard?.redirectTo).toBe('');
  });

  it('wildcard route uses pathMatch "full"', () => {
    const wildcard = routes.find(r => r.path === '**');
    expect(wildcard?.pathMatch).toBe('full');
  });
});
