/**
 * analyze.js — Inline analysis form submission for the landing page.
 *
 * Handles:
 *   - Form submission: POSTs braindump to /api/public/analyze
 *   - Polling loop: GETs /api/public/analyze/{job_id} every 2.5 seconds
 *   - Elapsed timer: counts seconds while analysis is in progress
 *   - Markdown rendering: uses marked.js to convert analysis to HTML
 *   - Error handling: 429 rate-limit messages, server errors, validation
 *
 * Depends on: marked.js (loaded from CDN in index.html)
 *
 * Exported: window.submitAnalysis() — called by redirect.js click handler
 */

(function () {
  var POLL_INTERVAL_MS = 2500;
  var MAX_CHARS = 10000;

  /** Active polling interval handle. */
  var pollHandle = null;

  /** Active elapsed timer interval handle. */
  var timerHandle = null;

  /** Seconds elapsed since analysis started. */
  var elapsedSeconds = 0;

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

  function getTimerEl() {
    return document.getElementById('analyze-timer');
  }

  function getResultEl() {
    return document.getElementById('analyze-result');
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

  function showResult(html) {
    var el = getResultEl();
    if (!el) return;
    el.innerHTML = html;
    el.hidden = false;
    // Scroll the result into view smoothly.
    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
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

  function hideResult() {
    var el = getResultEl();
    if (el) {
      el.innerHTML = '';
      el.hidden = true;
    }
  }

  function getConversionCta() {
    return document.getElementById('conversion-cta');
  }

  function showConversionCta() {
    var el = getConversionCta();
    if (!el) return;
    el.style.display = 'block';
    // Trigger reflow so the transition fires from opacity 0.
    void el.offsetWidth;
    el.classList.add('fade-in');
  }

  function hideConversionCta() {
    var el = getConversionCta();
    if (!el) return;
    el.classList.remove('fade-in');
    el.style.display = 'none';
  }

  // ── Timer ────────────────────────────────────────────────────────────────────

  function startTimer() {
    elapsedSeconds = 0;
    var timerEl = getTimerEl();
    if (timerEl) timerEl.textContent = '0s';
    timerHandle = setInterval(function () {
      elapsedSeconds += 1;
      var timerEl2 = getTimerEl();
      if (timerEl2) timerEl2.textContent = elapsedSeconds + 's';
    }, 1000);
  }

  function stopTimer() {
    if (timerHandle !== null) {
      clearInterval(timerHandle);
      timerHandle = null;
    }
  }

  // ── Polling ──────────────────────────────────────────────────────────────────

  function stopPolling() {
    if (pollHandle !== null) {
      clearInterval(pollHandle);
      pollHandle = null;
    }
  }

  /**
   * Poll GET /api/public/analyze/{jobId} every POLL_INTERVAL_MS.
   * Stops on done or error.
   */
  function pollAnalysis(jobId) {
    pollHandle = setInterval(function () {
      fetch('/api/public/analyze/' + jobId)
        .then(function (resp) {
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
          if (data.error) {
            stopPolling();
            stopTimer();
            hideLoading();
            showError('Analysis failed: ' + data.error);
            enableForm();
            return;
          }
          if (data.done) {
            stopPolling();
            stopTimer();
            hideLoading();
            // Render markdown to HTML using marked.js.
            var html = '';
            if (typeof window.marked !== 'undefined' && data.analysis) {
              html = DOMPurify.sanitize(window.marked.parse(data.analysis));
            } else if (data.analysis) {
              // Fallback: wrap raw text in a preformatted block.
              html = '<pre>' + escapeHtml(data.analysis) + '</pre>';
            } else {
              html = '<p>Analysis complete.</p>';
            }
            showResult(html);
            showConversionCta();
            enableForm();
          }
          // If not done yet, continue polling.
        })
        .catch(function (err) {
          stopPolling();
          stopTimer();
          hideLoading();
          showError(err.message || 'An error occurred while polling.');
          enableForm();
        });
    }, POLL_INTERVAL_MS);
  }

  // ── Helpers ──────────────────────────────────────────────────────────────────

  function escapeHtml(text) {
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

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
    hideResult();
    hideConversionCta();

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
    startTimer();

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
          stopTimer();
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
        if (!data.job_id) {
          throw new Error('No job_id returned from server.');
        }
        pollAnalysis(data.job_id);
      })
      .catch(function (err) {
        stopTimer();
        hideLoading();
        showError(err.message || 'Failed to start analysis. Please try again.');
        enableForm();
      });
  };
})();
