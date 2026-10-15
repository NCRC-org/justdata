/**
 * Long option lists in the controls (spec 04 A2): a step that can show more
 * than about eight options keeps them in a <details class="app-choices">,
 * closed by default. Its summary is one line saying what is selected, with
 * "Change →", and opening it expands the list in place.
 *
 *   <details class="app-choices" data-noun="counties">
 *     <summary><span class="app-choices-text"></span><span class="app-choices-change"></span></summary>
 *     <div class="app-choices-body">…checkboxes…</div>
 *   </details>
 *
 * data-noun: the summary counts ticked boxes, "84 counties selected" or
 *   "83 of 84 counties selected"; data-suffix is added after it ("in 21 areas").
 * data-summary="labels": the summary lists the ticked labels, one group per
 *   fieldset, "Originations · Owner-occupied · 1 unit, 2 units".
 *
 *   AppChoices.update(el)  after changing a list's contents or data-suffix
 *   AppChoices.close(el)   collapse again (Reset)
 * AppRun.setInvalid opens the list holding an invalid field.
 */
(function (root) {
  'use strict';

  function boxes(scope) {
    return Array.prototype.slice.call(scope.querySelectorAll('input[type="checkbox"]'));
  }

  /** Label text without the HMDA code the option shows in brackets. */
  function labelText(box) {
    var label = box.closest('label');
    return (label ? label.textContent : box.value).replace(/\s*\(\d+\)\s*$/, '').trim();
  }

  function countText(el) {
    var all = boxes(el.querySelector('.app-choices-body'));
    var ticked = all.filter(function (b) { return b.checked; }).length;
    var noun = el.dataset.noun || 'options';
    var text = !ticked ? 'No ' + noun + ' selected'
      : (ticked === all.length ? ticked : ticked + ' of ' + all.length) + ' ' + noun + ' selected';
    return el.dataset.suffix ? text + ' ' + el.dataset.suffix : text;
  }

  function labelsText(el) {
    var groups = el.querySelectorAll('.app-choices-body fieldset');
    return Array.prototype.map.call(groups, function (g) {
      var ticked = boxes(g).filter(function (b) { return b.checked; }).map(labelText);
      return ticked.length ? ticked.join(', ') : 'none';
    }).join(' · ');
  }

  function update(el) {
    var text = el.querySelector('.app-choices-text');
    var change = el.querySelector('.app-choices-change');
    if (text) text.textContent = el.dataset.summary === 'labels' ? labelsText(el) : countText(el);
    if (change) change.textContent = el.open ? 'Done ↑' : 'Change →';
  }

  function close(el) {
    el.open = false;
    update(el);
  }

  function all() {
    return Array.prototype.slice.call(document.querySelectorAll('details.app-choices'));
  }

  document.addEventListener('change', function (e) {
    var el = e.target.closest && e.target.closest('details.app-choices');
    if (el) update(el);
  });
  all().forEach(function (el) {
    el.addEventListener('toggle', function () { update(el); });
    update(el);
  });

  root.AppChoices = { update: update, close: close, all: all };
})(window);
