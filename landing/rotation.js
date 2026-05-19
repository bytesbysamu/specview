/**
 * rotation.js — Typewriter animation loop for the landing page braindump textarea.
 *
 * Cycles through DEMO_CONTENT entries, typing each braindump character-by-character
 * into the textarea at a natural reading pace.
 *
 * Exported state (read by redirect.js):
 *   window.rotationState.isEdited        — true once the visitor types anything
 *   window.rotationState.currentSlug     — slug of the currently displayed demo
 *   window.rotationState.currentContent  — live textarea value
 *
 * Behavior:
 *   - Types each character with a small random delay for a natural feel
 *   - Holds at the end of each demo for HOLD_MS before clearing and typing next
 *   - On first visitor keystroke (input event): stops animation, sets isEdited
 *   - On textarea focus: pauses animation, does not resume (visitor takes over)
 */

(function () {
  // ── Configuration ────────────────────────────────────────────────────────────

  /** Base typing delay in ms. Actual delay is randomised ±JITTER_MS. */
  var TYPE_DELAY_MS = 28;

  /** Jitter range added to base typing delay for a natural feel. */
  var JITTER_MS = 18;

  /** How long to hold at the end of a completed demo before clearing (ms). */
  var HOLD_MS = 3200;

  /** How long to pause after clearing before starting the next demo (ms). */
  var CLEAR_PAUSE_MS = 400;

  // ── State ────────────────────────────────────────────────────────────────────

  /** Shared state object read by redirect.js. */
  window.rotationState = {
    isEdited: false,
    currentSlug: '',
    currentContent: '',
  };

  /** Index into DEMO_CONTENT of the currently animating entry. */
  var currentIndex = 0;

  /** Whether the animation has been stopped (visitor focused or typed). */
  var stopped = false;

  /** setTimeout handle for the current scheduled tick. */
  var tickHandle = null;

  // ── Helpers ──────────────────────────────────────────────────────────────────

  function getTextarea() {
    return document.getElementById('braindump-textarea');
  }

  function schedule(fn, delay) {
    tickHandle = setTimeout(fn, delay);
  }

  function cancelTick() {
    if (tickHandle !== null) {
      clearTimeout(tickHandle);
      tickHandle = null;
    }
  }

  function randomDelay() {
    return TYPE_DELAY_MS + Math.round((Math.random() * 2 - 1) * JITTER_MS);
  }

  // ── Animation loop ───────────────────────────────────────────────────────────

  /**
   * Begin typing the demo at `index` into the textarea, starting at character
   * position `charPos`. When complete, hold then advance to the next demo.
   */
  function typeDemoFromPosition(index, charPos) {
    if (stopped) return;

    var demo = window.DEMO_CONTENT[index];
    var textarea = getTextarea();
    if (!textarea || !demo) return;

    // Update shared slug so redirect.js always knows which demo is showing.
    window.rotationState.currentSlug = demo.slug;

    if (charPos >= demo.text.length) {
      // Finished typing this demo — hold, then move to the next.
      schedule(function () {
        if (stopped) return;
        clearDemoAndAdvance(index);
      }, HOLD_MS);
      return;
    }

    // Type the next character.
    var nextText = demo.text.slice(0, charPos + 1);
    textarea.value = nextText;
    window.rotationState.currentContent = nextText;

    schedule(function () {
      typeDemoFromPosition(index, charPos + 1);
    }, randomDelay());
  }

  /**
   * Clear the textarea contents character-by-character is skipped in favour of
   * an instant clear to keep the total cycle time reasonable, then start the
   * next demo after a brief pause.
   */
  function clearDemoAndAdvance(completedIndex) {
    if (stopped) return;

    var textarea = getTextarea();
    if (textarea) {
      textarea.value = '';
      window.rotationState.currentContent = '';
    }

    var nextIndex = (completedIndex + 1) % window.DEMO_CONTENT.length;
    currentIndex = nextIndex;

    schedule(function () {
      typeDemoFromPosition(nextIndex, 0);
    }, CLEAR_PAUSE_MS);
  }

  // ── Visitor interaction handlers ─────────────────────────────────────────────

  /**
   * On first visitor keystroke: stop the rotation and mark the content as edited.
   * This is fired by the `input` event, which means the visitor actually changed
   * the textarea value (not just focused it).
   */
  function onVisitorInput() {
    if (!window.rotationState.isEdited) {
      window.rotationState.isEdited = true;
      cancelTick();
      stopped = true;
      // Keep the textarea's current value — the visitor owns it now.
      window.rotationState.currentContent = getTextarea()
        ? getTextarea().value
        : '';
    }
  }

  /**
   * On textarea focus: pause the animation. The visitor is about to interact.
   * We do not resume after focus — once they engage, the demo loop stops.
   */
  function onTextareaFocus() {
    if (!stopped) {
      cancelTick();
      stopped = true;
    }
  }

  // ── Init ─────────────────────────────────────────────────────────────────────

  /**
   * Start the rotation. Called from the DOMContentLoaded handler in index.html.
   * Requires window.DEMO_CONTENT to be loaded (from demo-content.js).
   */
  window.startRotation = function () {
    var textarea = getTextarea();
    if (!textarea) {
      console.warn('rotation.js: #braindump-textarea not found');
      return;
    }

    if (!window.DEMO_CONTENT || window.DEMO_CONTENT.length === 0) {
      console.warn('rotation.js: window.DEMO_CONTENT is empty or not loaded');
      return;
    }

    // Register interaction handlers.
    textarea.addEventListener('input', onVisitorInput);
    textarea.addEventListener('focus', onTextareaFocus);

    // Seed the first demo slug so the CTA has a valid slug even before typing starts.
    window.rotationState.currentSlug = window.DEMO_CONTENT[0].slug;

    // Begin typing the first demo.
    typeDemoFromPosition(0, 0);
  };
})();
