/**
 * analyze.js — Inline analysis form submission for the landing page.
 *
 * Handles:
 *   - Form submission: POSTs braindump to /api/public/analyze
 *   - On 202 success: redirects browser to the Angular app with ?job=<id>
 *   - Error handling: 429 rate-limit messages, server errors, validation
 *
 * Exported: window.submitAnalysis() — called by redirect.js click handler
 */

(function () {
  var APP_ORIGIN = window.APP_ORIGIN || (window.location.hostname === 'localhost' ? 'http://localhost:8095' : 'https://app.specview.dev');

  var MAX_CHARS = 10000;

  // ── DOM helpers ──────────────────────────────────────────────────────────────

  function getTextarea() {
    return document.getElementById('braindump-textarea');
  }

  function getCtaButton() {
    return document.getElementById('cta-button');
  }

  function getLoadingEl() {
    return document.getElementById('analyze-loading');
  }

  function getErrorEl() {
    return document.getElementById('analyze-error');
  }

  // ── State helpers ────────────────────────────────────────────────────────────

  function disableForm() {
    var textarea = getTextarea();
    var btn = getCtaButton();
    if (textarea) textarea.disabled = true;
    if (btn) {
      btn.disabled = true;
      btn.textContent = 'Analysing…';
    }
  }

  function enableForm() {
    var textarea = getTextarea();
    var btn = getCtaButton();
    if (textarea) textarea.disabled = false;
    if (btn) {
      btn.disabled = false;
      btn.textContent = 'Generate specs';
    }
  }

  function showLoading() {
    var el = getLoadingEl();
    if (el) el.hidden = false;
  }

  function hideLoading() {
    var el = getLoadingEl();
    if (el) el.hidden = true;
  }

  function showError(message) {
    var el = getErrorEl();
    if (!el) return;
    el.textContent = message;
    el.hidden = false;
  }

  function clearError() {
    var el = getErrorEl();
    if (el) {
      el.textContent = '';
      el.hidden = true;
    }
  }

  // ── Helpers ──────────────────────────────────────────────────────────────────

  /**
   * Parse a Retry-After header value (seconds or HTTP-date) and return hours
   * as a rounded integer, or null if unparseable.
   */
  function parseRetryAfterHours(headerValue) {
    if (!headerValue) return null;
    var seconds = parseInt(headerValue, 10);
    if (!isNaN(seconds)) {
      return Math.ceil(seconds / 3600);
    }
    // HTTP-date format fallback.
    var date = new Date(headerValue);
    if (!isNaN(date.getTime())) {
      var diffMs = date.getTime() - Date.now();
      if (diffMs > 0) return Math.ceil(diffMs / 3600000);
    }
    return null;
  }

  // ── Main entry point ─────────────────────────────────────────────────────────

  /**
   * Submit the braindump textarea content for analysis.
   * Called by the CTA button click handler in redirect.js.
   */
  window.submitAnalysis = function () {
    clearError();

    var textarea = getTextarea();
    var text = textarea ? textarea.value.trim() : '';

    if (!text) {
      showError('Please enter a braindump before submitting.');
      return;
    }

    if (text.length > MAX_CHARS) {
      showError(
        'Your braindump is ' + text.length + ' characters. Please keep it under ' +
        MAX_CHARS.toLocaleString() + ' characters.'
      );
      return;
    }

    disableForm();
    showLoading();

    fetch('/api/public/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ braindump: text }),
    })
      .then(function (resp) {
        if (resp.status === 429) {
          var retryAfter = resp.headers.get('Retry-After');
          var hours = parseRetryAfterHours(retryAfter);
          var msg = "You've reached the daily limit.";
          if (hours !== null && hours > 0) {
            msg += ' Try again in ' + hours + ' hour' + (hours === 1 ? '' : 's') + '.';
          } else {
            msg += ' Please try again later.';
          }
          hideLoading();
          showError(msg);
          enableForm();
          return null;
        }
        if (!resp.ok) {
          return resp.json().catch(function () {
            return { error: 'Server error (' + resp.status + ')' };
          }).then(function (body) {
            throw new Error(body.error || 'Server error (' + resp.status + ')');
          });
        }
        return resp.json();
      })
      .then(function (data) {
        if (!data) return; // handled above (e.g. 429)
        if (!data.share_slug && !data.job_id) {
          throw new Error('No share_slug returned from server.');
        }
        window.location.href = APP_ORIGIN + '/?share=' + encodeURIComponent(data.share_slug || data.job_id);
      })
      .catch(function (err) {
        hideLoading();
        showError(err.message || 'Failed to start analysis. Please try again.');
        enableForm();
      });
  };
})();
