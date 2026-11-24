(function () {
  'use strict';
  var labels = {original: 'Original · 1×', medium: 'Medium · 2×', high: 'High · 3×', ultra: 'Ultra · 4×'};
  var cropLabels = {jacket: 'Jacket detail', patches: 'Patch close-up', full: 'Full store screenshot', detail: 'Garment detail', front: 'Front', back: 'Back'};
  var releases = [];
  var observer = 'IntersectionObserver' in window ? new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) { entry.target.activateImages(); observer.unobserve(entry.target); }
    });
  }, {rootMargin: '600px'}) : null;

  function comparison(current, index) {
    var card = document.getElementById('comparison-template').content.firstElementChild.cloneNode(true);
    var $ = function (name) { return card.querySelector('[data-control="' + name + '"]'); };
    var dragging = false, active = false;
    card.id = 'compare-' + (current.id || index);
    $('title').id = card.id + '-title';
    $('title').textContent = current.title;
    card.setAttribute('aria-labelledby', $('title').id);
    $('caption').textContent = current.caption;
    Object.keys(current.crops).forEach(function (key) {
      var option = document.createElement('option'); option.value = key;
      option.textContent = cropLabels[key] || key; $('crop').appendChild(option);
    });
    function split(value) {
      $('stage').style.setProperty('--split', value + '%');
      $('split').setAttribute('aria-valuetext', value + ' percent A, ' + (100 - value) + ' percent B');
      $('tag-a').hidden = value === 0; $('tag-b').hidden = value === 100;
    }
    function releaseHold() {
      $('hold').setAttribute('aria-pressed', 'false');
      if ($('mode').value === 'hold') split(100);
    }
    function pressHold() {
      if ($('mode').value !== 'hold') return;
      $('hold').setAttribute('aria-pressed', 'true'); split(0);
    }
    function mode() {
      releaseHold(); var hold = $('mode').value === 'hold';
      $('hold').hidden = !hold; $('split').hidden = hold; $('divider').hidden = hold;
      $('help').textContent = hold ? 'A is shown normally. Press and hold the button, Space or Enter to show B; release to return to A.' : 'Drag the line. Arrow keys, Home and End work when the slider is focused.';
      split(hold ? 100 : Number($('split').value));
    }
    function images() {
      var crop = current.crops[$('crop').value] || current.crops.full;
      var view = current.views && current.views[$('crop').value];
      $('stage').style.aspectRatio = crop[2] + '/' + crop[3];
      ['a', 'b'].forEach(function (side) {
        var key = $('quality-' + side).value;
        var path = (view ? view.variants : current.variants)[key], svg = $('image-' + side);
        svg.setAttribute('viewBox', crop.join(' '));
        svg.setAttribute('aria-label', current.title + ' — ' + labels[key]);
        var im = svg.querySelector('image');
        im.setAttribute('width', current.width); im.setAttribute('height', current.height);
        if (active) im.setAttribute('href', path);
        $('tag-' + side).textContent = labels[key]; $('full-' + side).href = path;
      });
      $('error').hidden = true; mode();
    }
    function activateImages() { active = true; images(); }
    card.activateImages = activateImages;
    ['quality-a', 'quality-b', 'crop'].forEach(function (name) { $(name).addEventListener('change', activateImages); });
    $('mode').addEventListener('change', mode);
    $('swap').addEventListener('click', function () {
      var a = $('quality-a').value; $('quality-a').value = $('quality-b').value; $('quality-b').value = a; activateImages();
    });
    $('split').addEventListener('input', function () { split(Number(this.value)); });
    function point(e) {
      var bounds = $('stage').getBoundingClientRect();
      var value = Math.max(0, Math.min(1, (e.clientX - bounds.left) / bounds.width));
      $('split').value = Math.round(value * 100); split(Number($('split').value));
    }
    $('split').addEventListener('pointerdown', function (e) {
      if (e.button !== 0) return;
      dragging = true; this.focus({preventScroll: true}); this.setPointerCapture(e.pointerId); point(e); e.preventDefault();
    });
    $('split').addEventListener('pointermove', function (e) { if (dragging) point(e); });
    ['pointerup', 'pointercancel', 'lostpointercapture'].forEach(function (event) {
      $('split').addEventListener(event, function () { dragging = false; });
    });
    $('hold').addEventListener('pointerdown', function (e) {
      if (e.button !== 0) return;
      this.setPointerCapture(e.pointerId); pressHold(); e.preventDefault();
    });
    ['pointerup', 'pointercancel', 'lostpointercapture', 'blur'].forEach(function (event) { $('hold').addEventListener(event, releaseHold); });
    $('hold').addEventListener('keydown', function (e) { if (e.code === 'Space' || e.code === 'Enter') { e.preventDefault(); pressHold(); } });
    $('hold').addEventListener('keyup', function (e) { if (e.code === 'Space' || e.code === 'Enter') { e.preventDefault(); releaseHold(); } });
    card.querySelectorAll('.comparison-image image').forEach(function (im) {
      im.addEventListener('error', function () { $('error').hidden = false; });
    });
    releases.push(releaseHold);
    images(); document.getElementById('comparison-gallery').appendChild(card);
    if (observer) observer.observe(card); else activateImages();
  }
  window.addEventListener('blur', function () { releases.forEach(function (release) { release(); }); });
  document.addEventListener('visibilitychange', function () { if (document.hidden) releases.forEach(function (release) { release(); }); });

  fetch('comparisons.json', {cache: 'no-cache'}).then(function (response) {
    if (!response.ok) throw Error('Comparison data unavailable'); return response.json();
  }).then(function (data) {
    document.getElementById('empty-comparisons').hidden = Boolean(data.comparisons.length);
    data.comparisons.forEach(comparison);
    if (data.status === 'published') document.getElementById('release-status').textContent = 'Available now · High is the recommended quality';
    if (data.status === 'review') document.getElementById('release-status').textContent = 'Review draft · Native comparisons and references prepared. Downloads pending.';
    Object.keys(data.packages || {}).forEach(function (key) {
      var a = document.querySelector('[data-package="' + key + '"]'); if (a) { a.href = data.packages[key]; a.hidden = false; }
    });
    (data.references || []).forEach(function (reference) {
      var article = document.createElement('article'); article.className = 'reference-case';
      var heading = document.createElement('h3'); heading.textContent = reference.title; article.appendChild(heading);
      var row = document.createElement('div'); row.className = 'reference-triptych';
      [['Original', reference.original], ['Ultra · 4×', reference.ultra], ['Real-life reference', reference.reference]].forEach(function (pair) {
        var figure = document.createElement('figure'), im = document.createElement('img'), caption = document.createElement('figcaption');
        im.src = pair[1]; im.alt = reference.title + ' — ' + pair[0]; im.loading = 'lazy'; caption.textContent = pair[0];
        figure.appendChild(im); figure.appendChild(caption); row.appendChild(figure);
      });
      article.appendChild(row); var p = document.createElement('p'); p.className = 'capture-note'; p.textContent = reference.caption;
      article.appendChild(p); document.getElementById('reference-cards').appendChild(article);
    });
    document.getElementById('empty-references').hidden = Boolean((data.references || []).length);
  }).catch(function (error) {
    document.getElementById('empty-comparisons').textContent = error.message + '. Static comparison screenshots will accompany the release.';
  });
})();
