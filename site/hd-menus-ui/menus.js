// Display crops of the nine owner-approved hosted comparison images.
// Both halves use the same source image, without recoloring or regenerated pixels.
(function () {
  'use strict';
  document.querySelectorAll('[data-comparison]').forEach(function (figure) {
    var stage = figure.querySelector('.comparison__stage');
    var range = figure.querySelector('.comparison__range');
    var beforeTag = figure.querySelector('.comparison__tag--before');
    var afterTag = figure.querySelector('.comparison__tag--after');
    var buttons = figure.querySelectorAll('[data-position]');
    function update() {
      var value = Number(range.value);
      stage.style.setProperty('--position', value + '%');
      range.setAttribute('aria-valuetext', value + '% original, ' + (100 - value) + '% restored');
      beforeTag.hidden = value === 0;
      afterTag.hidden = value === 100;
      buttons.forEach(function (button) {
        button.setAttribute('aria-pressed', String(Number(button.dataset.position) === value));
      });
    }
    range.addEventListener('input', update);
    buttons.forEach(function (button) {
      button.addEventListener('click', function () {
        range.value = button.dataset.position;
        update();
      });
    });
    // Direct positioning keeps the divider under the pointer, including on mobile.
    function point(event) {
      var bounds = stage.getBoundingClientRect();
      range.value = String(Math.round(Math.max(0, Math.min(1,
        (event.clientX - bounds.left) / bounds.width)) * 100));
      update();
    }
    range.addEventListener('pointerdown', function (event) {
      if (event.button !== 0) return;
      range.focus({preventScroll: true});
      range.setPointerCapture(event.pointerId);
      point(event);
      event.preventDefault();
    });
    range.addEventListener('pointermove', function (event) {
      if (range.hasPointerCapture(event.pointerId)) point(event);
    });
    range.addEventListener('pointerup', function (event) {
      if (range.hasPointerCapture(event.pointerId)) range.releasePointerCapture(event.pointerId);
    });
    figure.querySelectorAll('image').forEach(function (image) {
      image.addEventListener('error', function () {
        figure.querySelector('.comparison__error').hidden = false;
      });
    });
    update();
  });
})();
