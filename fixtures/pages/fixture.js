// fixture.js — state machine and test API for the razbiram synthetic fixture page.
// Vanilla JS, no dependencies, works with file:// URLs.
// Exposes window.reveal / window.reshuffle / window.rerender / window.reset / window.navigate.

(function () {
  'use strict';

  // ── Internal helpers ──────────────────────────────────────────────────

  function getContainer(id) {
    var el = document.getElementById(id);
    if (!el) throw new Error('fixture: no container with id "' + id + '"');
    return el;
  }

  function setDataState(container, state) {
    container.dataset.state = state;
    // Update the visible badge if present
    var badge = container.querySelector('.state-badge');
    if (badge) badge.textContent = state;
  }

  // ── Per-family reveal logic ───────────────────────────────────────────

  function revealRadioGroup(container) {
    var items = container.querySelectorAll('[data-option-id]');
    items.forEach(function (item) {
      var input = item.querySelector('input[type="radio"]');
      var labelSpan = item.querySelector('.option-label');
      if (input) {
        input.disabled = true;
      }
      if (item.dataset.correct === 'true') {
        item.dataset.feedback = 'correct';
        // Prepend ✓ to visibleText. cleanText (data-clean-text) stays unchanged.
        // This exercises IDENTITY_ALGORITHMS.md feedback-stripping rule (G-feedback).
        if (labelSpan) {
          labelSpan.textContent = '✓ ' + labelSpan.dataset.cleanText;
        }
        // Native inputs own their checked state; ARIA in HTML prohibits aria-checked here.
        if (input) input.checked = true;
      } else {
        item.dataset.feedback = 'incorrect';
      }
    });
    setDataState(container, 'reveal');
  }

  function revealCheckboxGroup(container) {
    var items = container.querySelectorAll('[data-option-id]');
    items.forEach(function (item) {
      var input = item.querySelector('input[type="checkbox"]');
      if (input) input.disabled = true;
      if (item.dataset.correct === 'true') {
        item.dataset.feedback = 'correct';
        // Native inputs own their checked state; ARIA in HTML prohibits aria-checked here.
        if (input) input.checked = true;
      } else {
        item.dataset.feedback = 'incorrect';
      }
    });
    setDataState(container, 'reveal');
  }

  function revealFlashcard(container) {
    var front = container.querySelector('.flashcard-front');
    var back  = container.querySelector('.flashcard-back');
    var btn   = container.querySelector('[data-action="reveal"]');
    if (front) { front.hidden = true; front.setAttribute('aria-hidden', 'true'); }
    if (back)  { back.hidden = false; back.removeAttribute('aria-hidden'); }
    if (btn)   { btn.hidden = true; }
    setDataState(container, 'reveal');
  }

  function revealOcclusion(container) {
    container.querySelectorAll('.occlusion-region').forEach(function (r) {
      r.dataset.revealed = 'true';
      var alt = r.dataset.altText || 'Revealed';
      r.setAttribute('aria-label', alt);
      r.textContent = alt;
    });
    setDataState(container, 'reveal');
  }

  // ── window.reveal(id) ─────────────────────────────────────────────────

  window.reveal = function (id) {
    var c = getContainer(id);
    if (c.dataset.state === 'reveal') return; // idempotent
    switch (c.dataset.family) {
      case 'single-choice':
      case 'true-false':
        revealRadioGroup(c);
        break;
      case 'multiple-select':
        revealCheckboxGroup(c);
        break;
      case 'flashcard':
        revealFlashcard(c);
        break;
      case 'image-occlusion':
        revealOcclusion(c);
        break;
      default:
        setDataState(c, 'reveal');
    }
  };

  // ── window.reshuffle(id) — G13 ────────────────────────────────────────
  // Shuffles the DOM order of option items inside a radio/checkbox group.
  // questionFingerprint is unaffected because IDENTITY_ALGORITHMS.md sorts
  // option cleanTexts before hashing.

  window.reshuffle = function (id) {
    var c = getContainer(id);
    var list = c.querySelector('.options-list');
    if (!list) return;
    var items = Array.from(list.querySelectorAll('[data-option-id]'));
    // Fisher-Yates shuffle
    for (var i = items.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      // Swap DOM positions
      var nodeI = items[i];
      var nodeJ = items[j];
      var afterI = nodeI.nextSibling;
      var afterJ = nodeJ.nextSibling;
      if (afterI === nodeJ) {
        list.insertBefore(nodeJ, nodeI);
      } else if (afterJ === nodeI) {
        list.insertBefore(nodeI, nodeJ);
      } else {
        list.insertBefore(nodeJ, afterI);
        list.insertBefore(nodeI, afterJ);
      }
      // Update local array
      var tmp = items[i]; items[i] = items[j]; items[j] = tmp;
    }
  };

  // ── window.rerender(id) — G14 ────────────────────────────────────────
  // Replaces the container's DOM nodes with fresh clones, changing HTML id
  // attributes on child elements (simulating React key/reconcile churn) while
  // preserving all data-* semantic attributes. stateFingerprint must be
  // identical before and after because semantic content is unchanged.

  var _rerenderCount = 0;

  window.rerender = function (id) {
    var c = getContainer(id);
    var parent = c.parentNode;
    if (!parent) return;
    _rerenderCount++;
    var suffix = '-rr' + _rerenderCount;
    // Deep clone preserves all attributes and text
    var clone = c.cloneNode(true);
    // Re-key internal HTML ids to simulate node replacement without semantic change
    clone.querySelectorAll('[id]').forEach(function (el) {
      if (el === clone) return; // keep the container id stable
      el.id = el.id + suffix;
    });
    // Update aria-labelledby references to match new ids
    clone.querySelectorAll('[aria-labelledby]').forEach(function (el) {
      var refs = el.getAttribute('aria-labelledby').split(/\s+/);
      el.setAttribute('aria-labelledby', refs.map(function (r) {
        // Only rewrite if the target was inside the container
        return clone.querySelector('#' + r + suffix) ? r + suffix : r;
      }).join(' '));
    });
    parent.replaceChild(clone, c);
    initContainer(clone);
  };

  // ── window.reset() ───────────────────────────────────────────────────

  window.reset = function () {
    document.querySelectorAll('[data-question-id]').forEach(resetContainer);
  };

  // ── window.navigate(id) — G15 ────────────────────────────────────────
  // Scrolls to and focuses a question container. Use in tests to simulate
  // navigating away and back: navigate(idA), navigate(idB), navigate(idA).

  window.navigate = function (id) {
    var el = document.getElementById(id);
    if (!el) return;
    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    el.focus({ preventScroll: true });
  };

  // ── Reset a single container ──────────────────────────────────────────

  function resetContainer(container) {
    setDataState(container, 'question');

    // Re-enable and uncheck all inputs
    container.querySelectorAll('input[type="radio"], input[type="checkbox"]').forEach(function (inp) {
      inp.checked = false;
      inp.disabled = false;
    });

    // Clear feedback data attributes
    container.querySelectorAll('[data-feedback]').forEach(function (el) {
      delete el.dataset.feedback;
    });

    // Restore option labels to cleanText (remove ✓/✗ prefix)
    container.querySelectorAll('.option-label[data-clean-text]').forEach(function (span) {
      span.textContent = span.dataset.cleanText;
    });

    // Flashcard: show front, hide back, show reveal button
    var front = container.querySelector('.flashcard-front');
    var back  = container.querySelector('.flashcard-back');
    var btn   = container.querySelector('[data-action="reveal"]');
    if (front) { front.hidden = false; front.removeAttribute('aria-hidden'); }
    if (back)  { back.hidden = true; back.setAttribute('aria-hidden', 'true'); }
    if (btn)   { btn.hidden = false; }

    // Image-occlusion: restore masks
    container.querySelectorAll('.occlusion-region').forEach(function (r) {
      r.dataset.revealed = 'false';
      r.setAttribute('aria-label', 'Occluded region — press Enter or click to reveal');
      r.textContent = '?';
    });
  }

  // ── Event delegation per container ───────────────────────────────────

  function initContainer(container) {
    container.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-action]');
      if (!btn) return;
      var action   = btn.dataset.action;
      var targetId = btn.dataset.target || container.id;
      if (action === 'reveal')    { window.reveal(targetId); }
      else if (action === 'reshuffle') { window.reshuffle(targetId); }
      else if (action === 'rerender')  { window.rerender(targetId); }
      else if (action === 'reset')     { resetContainer(container); }
    });

    // Keyboard activation for occlusion mask buttons
    container.querySelectorAll('.occlusion-region').forEach(function (r) {
      r.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          window.reveal(container.id);
        }
      });
    });
  }

  // ── Bootstrap ────────────────────────────────────────────────────────

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-question-id]').forEach(initContainer);
  });

})();
