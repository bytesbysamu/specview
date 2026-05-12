# Implementation Guide: SaaS Phase 1 — Security + Auth Completion

## Overview
This epic closes the gap between spec-doc's 70%-complete auth system and a launchable product by delivering user registration, automatic token lifecycle management, credential rotation, and transport security hardening. The four tasks execute sequentially: secrets rotation first (because a new JWT secret invalidates all sessions and must precede any new token issuance), then the signup endpoint and Angular registration page, followed by the token lifecycle service and refresh wiring, and finally CORS lockdown with security headers. Each task builds on the prior one's outputs, so parallel execution is not possible.

## Shared Pre-flight
- Confirm access to the Neon database console for password rotation and the Coolify dashboard for production environment variable configuration.
- Ensure the local development environment can start via docker-compose with the existing hardcoded credentials (baseline sanity check before any changes).
- Verify that the existing login flow works end-to-end locally: POST to /api/auth/login returns a JWT and the Angular app stores it in localStorage.
- Read the existing auth module files — api/modules/auth/routes.py, api/modules/auth/service.py, and web-ng/src/app/interceptors/auth.interceptor.ts — to understand current implementation details and line counts.
- Identify the app factory entry point (api/app.py or api/create_app.py) where Flask middleware and after_request handlers are registered.
- Confirm that .env is present in .gitignore so local credential files are never committed.
- Ensure Flask-CORS is listed as an existing dependency in requirements.txt or pyproject.toml.
- Review .pre-commit-config.yaml to understand the current hook configuration before adding a secrets-grep guard.

---

## Task 1: Secrets Rotation & Env-Var Migration  [Effort: 0.5 days]

### What
Extract DATABASE_URL and JWT_SECRET from docker-compose.yml into environment variables, rotate the Neon database password and JWT signing secret to values that have never existed in git history, and update all configuration surfaces (.env.example, docker-compose.yml, Coolify) to use variable substitution. This must happen first because the new JWT secret invalidates all existing sessions, and every subsequent task depends on a clean credential environment.

### Files
- **Modify**: docker-compose.yml — Replace hardcoded DATABASE_URL and JWT_SECRET string values with variable substitution syntax referencing .env values.
- **Modify**: .env.example — Add placeholder entries for DATABASE_URL, JWT_SECRET, and any other secrets, with non-functional example values and inline comments describing each variable.
- **Create**: .env — Add real local development credentials (local-safe JWT secret and Neon dev database URL). This file is gitignored and never committed.
- **Create**: .pre-commit-config.yaml — Add a grep-based hook that scans staged files for patterns matching known secret formats (Neon connection strings, long base64 JWT secrets) and rejects the commit if found.

### Steps
1. Open docker-compose.yml and locate every line where DATABASE_URL or JWT_SECRET appears as a plaintext string value. Record the exact current values so you can verify rotation later.
2. Generate a new JWT_SECRET using a cryptographically secure random generator — a 64-character hex string from /dev/urandom or equivalent. This value must never have appeared in any file tracked by git.
3. Log into the Neon console, navigate to the spec-doc project's connection settings, and rotate the database password. Copy the new connection string.
4. Create the local .env file with the new JWT_SECRET and the updated DATABASE_URL pointing to the Neon database with the rotated password.
5. Update docker-compose.yml to use variable substitution (dollar-brace syntax) for DATABASE_URL and JWT_SECRET, referencing the values that Docker Compose will load from .env.
6. Populate .env.example with placeholder values — a dummy connection string and a clearly-fake JWT secret — along with comments explaining each variable's purpose.
7. Add a pre-commit hook entry in .pre-commit-config.yaml that runs a grep scan against staged files for patterns like neon.tech connection strings and rejects the commit if any match.
8. Log into the Coolify dashboard and set DATABASE_URL and JWT_SECRET as production environment variables using the newly rotated values. Verify the production deployment restarts and serves traffic.

### Verify
- Run grep -r "JWT_SECRET\|DATABASE_URL" on the working tree excluding .env and .env.example and confirm zero matches with actual credential values in any committed file.
- Start the local docker-compose stack and confirm the Flask app boots without credential errors in the logs.
- Attempt to log in with a previously issued JWT token and confirm it is rejected (proving the old secret is no longer valid).
- Run git diff docker-compose.yml and confirm the file now contains variable substitution syntax, not plaintext secrets.

---

## Task 2: Signup Endpoint + Angular Registration Page  [Effort: 1 day]

### What
Add a POST /api/auth/register endpoint that accepts email and password, validates input, checks for duplicate accounts, hashes the password with bcrypt, inserts the user, and returns a JWT in the same response shape as /api/auth/login. Build a standalone Angular signup page component with its own route, wired to the existing auth service. Add IP-based rate limiting to the registration endpoint to mitigate abuse in the absence of email verification.

### Files
- **Modify**: api/modules/auth/routes.py — Add the /register route handler that validates the request body and delegates to the service layer.
- **Modify**: api/modules/auth/service.py — Add service functions for email normalization, password policy validation (minimum eight characters), duplicate-email detection via database query, user creation with bcrypt hashing, and JWT issuance for the new user.
- **Create**: api/modules/auth/rate_limit.py — Implement an IP-based rate-limiting decorator using an in-process dictionary with sliding-window timestamps, scoped to five requests per IP per hour.
- **Create**: web-ng/src/app/pages/signup/signup.component.ts — Standalone Angular component with a registration form containing email and password fields, client-side validation, error display, and a call to the auth service on submit.
- **Create**: web-ng/src/app/pages/signup/signup.component.html — Template for the signup form with validation messages and a link to the login page.
- **Create**: web-ng/src/app/pages/signup/signup.component.css — Styles for the signup page consistent with the existing login page appearance.
- **Modify**: web-ng/src/app/app.routes.ts — Add a /signup route pointing to the new SignupComponent.
- **Modify**: web-ng/src/app/services/auth.service.ts — Add a register method that POSTs email and password to /api/auth/register and processes the response identically to the existing login method (store token, update isLoggedIn signal).

### Steps
1. In api/modules/auth/service.py, add a function that normalizes an email address by lowercasing and trimming whitespace, and a function that enforces the password policy by rejecting passwords shorter than eight characters.
2. Add a service function that queries the database for an existing user with the given email and returns a boolean indicating whether the email is already registered.
3. Add a service function that creates a new user: hash the password with bcrypt, insert the user row into the database, and generate a JWT using the existing token-creation logic. Return the token and email.
4. Create api/modules/auth/rate_limit.py with a decorator that tracks request timestamps per IP in a module-level dictionary, enforces a sliding window of five requests per hour, and returns a 429 response with a Retry-After header when the limit is exceeded.
5. In api/modules/auth/routes.py, add the POST /register route handler. Apply the rate-limiting decorator. Parse and validate the request body for email and password fields. Call the service functions for normalization, policy check, duplicate detection, and user creation. Return the token and email as JSON with a 201 status, or return appropriate 400/409/429 error responses. Note: the existing /login route uses inline logic (validation + DB query + hashing in the route handler). Follow the same inline pattern for /register for consistency — the service-layer delegation described above applies to the new helper functions (normalize, validate), not to restructuring the route handler itself.
6. Create the Angular SignupComponent as a standalone component. The template should contain a reactive form with email and password fields, validation messages for required fields and minimum password length, a submit button, and a router link to the login page.
7. In the auth service, add a register method that sends a POST request to /api/auth/register with the email and password, then stores the returned token in localStorage and updates the isLoggedIn signal — reusing the same post-auth logic as the login method.
8. Register the /signup route in app.routes.ts pointing to SignupComponent, and optionally add Cloudflare Turnstile integration if time permits by adding the Turnstile script to index.html and validating the token server-side before executing the registration logic.

### Verify
- Send a POST request to /api/auth/register with a valid email and password and confirm a 201 response containing a token and email field.
- Send a duplicate registration request with the same email and confirm a 409 Conflict response.
- Send six registration requests from the same IP within one hour and confirm the sixth returns a 429 status.
- Navigate to /signup in the Angular app, fill in the form, submit, and confirm the app transitions to an authenticated state with the token stored in localStorage.

---

## Task 3: Token Lifecycle + Refresh  [Effort: 1 day]

### What
Introduce a dedicated Angular token-lifecycle service that owns token storage, expiry detection, proactive refresh orchestration with a mutex to prevent concurrent refresh requests, and failure-mode routing. Refactor the existing HTTP interceptor to delegate all token and auth-failure decisions to this service. Add a POST /api/auth/refresh backend endpoint that issues a fresh JWT for authenticated users, and extend the /api/auth/me response to include token_expires_at.

### Files
- **Create**: web-ng/src/app/services/token-lifecycle.service.ts — Angular injectable service that manages token storage in localStorage, decodes JWT expiry, triggers proactive refresh when within one hour of expiry, serializes concurrent refresh attempts behind a mutex promise, and handles terminal auth failure by clearing state and navigating to login.
- **Modify**: web-ng/src/app/interceptors/auth.interceptor.ts — Refactor to delegate token retrieval and 401 handling to the token-lifecycle service. Add /api/auth/register and /api/auth/refresh to the PUBLIC_PATHS array. Remove direct signOut calls in favor of service-mediated disposition.
- **Modify**: api/modules/auth/routes.py — Add the POST /refresh route handler, protected by @require_auth, that delegates to the service layer for fresh token issuance.
- **Modify**: api/modules/auth/service.py — Add a service function that accepts a verified user identity (from the current token's claims) and issues a new JWT with a fresh 72-hour expiry window. Extend the /me response data to include a token_expires_at ISO timestamp.
- **Modify**: web-ng/src/app/services/auth.service.ts — Coordinate with the token-lifecycle service for token storage so that login and register flows store tokens through the lifecycle service rather than directly in localStorage.

### Steps
1. In api/modules/auth/service.py, add a function that takes a user ID (extracted from the current JWT by the @require_auth decorator), looks up the user, and generates a new JWT with a 72-hour expiry. Also modify the existing user-info retrieval function to include a token_expires_at field as an ISO 8601 timestamp computed from the current token's exp claim.
2. In api/modules/auth/routes.py, add the POST /refresh endpoint decorated with @require_auth. The handler extracts the authenticated user's identity from the request context, calls the service function to generate a fresh token, and returns the token and email in the standard response shape. Note: when SKIP_AUTH is active, `g.current_user` is None (see decorators.py:25). Add an early guard — if `g.current_user is None`, return 401. This prevents crashes if a developer calls /refresh with SKIP_AUTH enabled locally.
3. Create web-ng/src/app/services/token-lifecycle.service.ts. Implement a getToken method that reads the token from localStorage, decodes the exp claim from the JWT payload (base64 decode of the second segment), and compares it to the current time. If the token is more than one hour from expiry, return it directly. If within the refresh window, call the refresh endpoint, store the new token, and return it. Use a private promise field as a mutex so that concurrent calls to getToken await the same in-flight refresh rather than issuing parallel requests.
4. Add a handleAuthFailure method to the token-lifecycle service that clears the token from localStorage, resets the isLoggedIn signal to false via the auth service, and navigates to the login route using the Angular Router.
5. Refactor auth.interceptor.ts to inject the token-lifecycle service. Replace the direct localStorage read with a call to getToken (which may trigger a proactive refresh). Replace the direct signOut call in the 401 handler with a call to handleAuthFailure on the lifecycle service. Add /api/auth/register and /api/auth/refresh to the PUBLIC_PATHS array.
6. Update auth.service.ts so that the login and register methods store the returned token through the token-lifecycle service's storage method rather than writing to localStorage directly, ensuring a single source of truth for token state.
7. Test the full lifecycle by logging in, waiting for the token to approach its refresh window (or manually adjusting the token's exp for testing), issuing an API request, and confirming that the interceptor transparently refreshes the token without user-visible interruption.

### Verify
- Send a POST request to /api/auth/refresh with a valid Bearer token and confirm a 200 response containing a new token with a later expiry than the original.
- Send a POST request to /api/auth/refresh with no token or an expired token and confirm a 401 response.
- In the Angular app, confirm that after login the token-lifecycle service returns the stored token via getToken without triggering a refresh when expiry is more than one hour away.
- Confirm that the /api/auth/me endpoint response now includes a token_expires_at field with a valid ISO 8601 timestamp.

---

## Task 4: CORS Lockdown, Security Headers & SKIP_AUTH Gating  [Effort: 0.5 days]

### What
Restrict CORS to an environment-driven allowlist (specview.app in production, localhost in development), add X-Content-Type-Options, X-Frame-Options, Strict-Transport-Security, and X-Request-ID headers to all responses, and gate the SKIP_AUTH development bypass behind a FLASK_ENV=development check so it cannot activate in production. Add a /api/health/security canary endpoint that returns 503 if any dev-bypass flag is active, suitable for deployment pipeline validation.

### Files
- **Modify**: api/create_app.py — Update the existing `_parse_cors_origins()` function to fail closed (default to empty string instead of `http://localhost:4201`). Register an after_request handler that sets X-Content-Type-Options, X-Frame-Options, Strict-Transport-Security, and X-Request-ID headers on every response.
- **Modify**: api/create_app.py — Add the GET /api/health/security canary endpoint alongside the existing /api/health endpoint, checking whether SKIP_AUTH is active in a non-development environment and returning 503 if so, or 200 if clean.
- **Modify**: api/modules/auth/decorators.py (or wherever @require_auth is defined) — Add a FLASK_ENV check at the top of the SKIP_AUTH branch: only honor the bypass when FLASK_ENV equals development. In all other environments, ignore the SKIP_AUTH variable entirely.
- **Modify**: docker-compose.yml — Add CORS_ORIGINS using variable substitution syntax (${CORS_ORIGINS}).
- **Modify**: docker-compose.override.yml — Add CORS_ORIGINS with local development origins (http://localhost:4200,http://localhost:8095) alongside the existing dev env vars.
- **Modify**: .env.example — Add CORS_ORIGINS with example localhost values and a comment explaining the production value.

### Steps
1. Locate the @require_auth decorator definition. Find the conditional branch that checks for SKIP_AUTH. Wrap that branch in an additional check that FLASK_ENV equals development. If FLASK_ENV is anything other than development (including unset), the SKIP_AUTH variable is ignored and authentication proceeds normally.
2. In api/create_app.py, modify the existing `_parse_cors_origins()` function (line 32) to change the default from `"http://localhost:4201"` to `""` so it fails closed when CORS_ORIGINS is unset. The function already splits on commas and strips whitespace — no other changes needed.
3. In the same file, register a Flask after_request handler (after the `CORS(app, ...)` call) that adds four headers to every response: X-Content-Type-Options set to nosniff, X-Frame-Options set to DENY, Strict-Transport-Security set to max-age=31536000 with includeSubDomains, and X-Request-ID set to a freshly generated UUID4 string.
4. Add CORS_ORIGINS to docker-compose.yml under the api service's environment section using variable substitution (${CORS_ORIGINS}). Add the actual dev value to docker-compose.override.yml alongside the existing dev env vars (CHAIN_PROVIDER, SPEC_DOC_DIR, etc.): `CORS_ORIGINS: "http://localhost:4200,http://localhost:8095"`.
5. Add CORS_ORIGINS to .env.example with placeholder localhost values and a descriptive comment noting that production should use https://specview.app,https://www.specview.app.
6. Add the GET /api/health/security endpoint in api/create_app.py alongside the existing `/api/health` endpoint (line 90). This endpoint checks whether SKIP_AUTH is set and FLASK_ENV is not development. If the bypass would be active in a non-dev environment, return a 503 with a JSON body describing the misconfiguration. Otherwise return a 200 confirming the security posture is clean.
7. In the Coolify production dashboard, set CORS_ORIGINS to https://specview.app,https://www.specview.app. Confirm that FLASK_ENV is either set to production or not set at all (both result in the SKIP_AUTH gate blocking the bypass).

### Verify
- Start the local stack and make a cross-origin request from an origin not in CORS_ORIGINS — confirm the browser rejects it with a CORS error.
- Inspect any API response's headers and confirm X-Content-Type-Options, X-Frame-Options, Strict-Transport-Security, and X-Request-ID are all present with the expected values.
- Set SKIP_AUTH=true and FLASK_ENV=production locally, restart the Flask app, and send a request to a protected endpoint — confirm the request is rejected with a 401, proving the bypass is gated.
- Send a GET request to /api/health/security with FLASK_ENV=production and SKIP_AUTH=true and confirm a 503 response. Repeat with FLASK_ENV=development and confirm a 200 response.