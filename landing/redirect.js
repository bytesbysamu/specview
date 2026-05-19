/**
 * redirect.js — Landing-to-App redirect URL builder and CTA wiring.
 *
 * Constructs the correct redirect URL based on mode:
 *   - Demo mode:  app origin + ?demo=<slug>
 *   - Real mode:  app origin + /analyze#<base64url-encoded braindump>
 *
 * No dependencies. Works across different origins (landing vs app can be on
 * different ports or domains). No sessionStorage used — URL only.
 *
 * Also wires the CTA button click handler. Call window.initCtaButton() after
 * the DOM is ready (done in index.html DOMContentLoaded).
 */

/**
 * The set of known demo braindump slugs. These match pre-computed fixture
 * projects in the Angular app's DemoAwareProjectsService / demo-fixtures.ts.
 * The landing page cycles through these as the rotating textarea content.
 */
window.DEMO_SLUGS = [
  'mobile-app',
  'saas-feature',
  'side-project',
  'refactoring-task',
];

/**
 * Encode a UTF-8 string as a base64url string (no padding, URL-safe alphabet).
 *
 * Uses TextEncoder to convert the string to bytes first, so all Unicode
 * content (emoji, accented characters, CJK) survives the round-trip.
 *
 * @param {string} text — The UTF-8 string to encode.
 * @returns {string} The base64url-encoded string.
 */
function encodeBase64Url(text) {
  var bytes = new TextEncoder().encode(text);
  var binary = '';
  for (var i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  // Convert to standard base64, then make URL-safe by replacing + → -, / → _
  // and stripping trailing = padding characters.
  return btoa(binary)
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
}
window.encodeBase64Url = encodeBase64Url;

/**
 * Build the redirect URL for the Angular app.
 *
 * @param {boolean} isEdited — True when the visitor modified the textarea
 *   content (real mode). False when the demo text is unchanged (demo mode).
 * @param {string} content — Demo mode: a slug from DEMO_SLUGS.
 *   Real mode: the raw braindump text typed by the visitor.
 * @param {string} [appOrigin] — The Angular app's origin. Defaults to the
 *   value of window.APP_ORIGIN if set, otherwise falls back to the current
 *   origin (useful when landing and app share a host).
 * @returns {string} The fully qualified redirect URL.
 */
function buildRedirectUrl(isEdited, content, appOrigin) {
  // Resolve the app origin: explicit argument > window.APP_ORIGIN > current origin.
  var origin =
    appOrigin ||
    (window.APP_ORIGIN || '') ||
    window.location.origin;

  // Just open the app — it has demo data for unauthenticated users.
  return origin + '/';
}
window.buildRedirectUrl = buildRedirectUrl;

/**
 * Wire the CTA button click handler.
 *
 * Reads window.rotationState (set by rotation.js) to determine whether the
 * visitor edited the textarea (real mode) or left the demo text (demo mode).
 * Builds the redirect URL and assigns it to window.location.href.
 *
 * Call this function after the DOM is ready.
 */
window.initCtaButton = function () {
  var btn = document.getElementById('cta-button');
  if (!btn) {
    console.warn('redirect.js: #cta-button not found');
    return;
  }

  btn.addEventListener('click', function () {
    window.location.href = buildRedirectUrl(false, '');
  });
};
