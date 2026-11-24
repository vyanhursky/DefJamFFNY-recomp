(function () {
  'use strict';
  var $ = function (id) { return document.getElementById(id); };
  var labels = {original: 'Original · 1×', medium: 'Medium · 2×', high: 'High · 3×', ultra: 'Ultra · 4×'};
  var current, dragging = false, held = false;
  function split(value) {
    $('stage').style.setProperty('--split', value + '%');
    $('split').setAttribute('aria-valuetext', value + ' percent A, ' + (100-value) + ' percent B');
    $('tag-a').hidden = value === 0; $('tag-b').hidden = value === 100;
  }
  function releaseHold() { held = false; $('hold').setAttribute('aria-pressed','false'); if ($('mode').value === 'hold') split(100); }
  function pressHold() { if ($('mode').value !== 'hold') return; held = true; $('hold').setAttribute('aria-pressed','true'); split(0); }
  function mode() {
    releaseHold(); var hold = $('mode').value === 'hold';
    $('hold').hidden = !hold; $('split').hidden = hold; $('divider').hidden = hold;
    $('comparison-help').textContent = hold ? 'A is shown normally. Press and hold the button, Space or Enter to show B; release to return to A.' : 'Drag the line. Arrow keys, Home and End work when the slider is focused.';
    split(hold ? 100 : Number($('split').value));
  }
  function images() {
    releaseHold(); if (!current) return;
    var crop = current.crops[$('crop').value] || current.crops.full;
    $('stage').style.aspectRatio = crop[2] + '/' + crop[3];
    ['a','b'].forEach(function (side) {
      var key = $('quality-'+side).value;
      var view = current.views && current.views[$('crop').value];
      var v = (view ? view.variants : current.variants)[key], svg = $('image-'+side);
      svg.setAttribute('viewBox',crop.join(' ')); svg.setAttribute('aria-label', current.title+' — '+labels[key]);
      var im = svg.querySelector('image'); im.setAttribute('width',current.width); im.setAttribute('height',current.height); im.setAttribute('href',v);
      $('tag-'+side).textContent = labels[key]; $('full-'+side).href = v;
    });
    $('image-error').hidden = true; mode();
  }
  function loadSubject(data) {
    current = data.comparisons[$('subject').selectedIndex]; $('subject-title').textContent = current.title;
    $('capture-note').textContent = current.caption;
    $('crop').innerHTML = Object.keys(current.crops).map(function (key) { return '<option value="'+key+'">'+({jacket:'Jacket detail',patches:'Patch close-up',full:'Full store screenshot',detail:'Garment detail',artwork:'Tattoo artwork',front:'Front',back:'Back'}[key] || key)+'</option>'; }).join('');
    images();
  }
  $('quality-a').addEventListener('change',images); $('quality-b').addEventListener('change',images); $('crop').addEventListener('change',images); $('mode').addEventListener('change',mode);
  $('swap').addEventListener('click',function () { var a=$('quality-a').value; $('quality-a').value=$('quality-b').value; $('quality-b').value=a; images(); });
  $('split').addEventListener('input',function () { split(Number(this.value)); });
  function point(e) { var b=$('stage').getBoundingClientRect(); $('split').value=Math.round(Math.max(0,Math.min(1,(e.clientX-b.left)/b.width))*100); split(Number($('split').value)); }
  $('split').addEventListener('pointerdown',function (e) { if(e.button!==0)return; dragging=true; this.focus({preventScroll:true}); this.setPointerCapture(e.pointerId); point(e); e.preventDefault(); });
  $('split').addEventListener('pointermove',function(e){if(dragging)point(e);});
  ['pointerup','pointercancel','lostpointercapture'].forEach(function(ev){$('split').addEventListener(ev,function(){dragging=false;});});
  $('hold').addEventListener('pointerdown',function(e){if(e.button!==0)return;this.setPointerCapture(e.pointerId);pressHold();e.preventDefault();});
  ['pointerup','pointercancel','lostpointercapture','blur'].forEach(function(ev){$('hold').addEventListener(ev,releaseHold);});
  $('hold').addEventListener('keydown',function(e){if(e.code==='Space'||e.code==='Enter'){e.preventDefault();pressHold();}});
  $('hold').addEventListener('keyup',function(e){if(e.code==='Space'||e.code==='Enter'){e.preventDefault();releaseHold();}});
  window.addEventListener('blur',releaseHold); document.addEventListener('visibilitychange',function(){if(document.hidden)releaseHold();});
  document.querySelectorAll('.comparison-image image').forEach(function(im){im.addEventListener('error',function(){$('image-error').hidden=false;});});
  fetch('comparisons.json', {cache: 'no-cache'}).then(function(r){if(!r.ok)throw Error('Comparison data unavailable');return r.json();}).then(function(data){
    if(data.comparisons.length){$('empty-comparisons').hidden=true;$('comparison').hidden=false;data.comparisons.forEach(function(c){var o=document.createElement('option');o.textContent=c.title;$('subject').appendChild(o);});$('subject').addEventListener('change',function(){loadSubject(data);});loadSubject(data);}
    if(data.status==='published')$('release-status').textContent='Available now · High is the recommended quality';
    if(data.status==='review')$('release-status').textContent='Review draft · Native comparisons and references prepared. Downloads pending.';
    Object.keys(data.packages||{}).forEach(function(key){var a=document.querySelector('[data-package="'+key+'"]');if(a){a.href=data.packages[key];a.hidden=false;}});
    (data.references||[]).forEach(function(r){var a=document.createElement('article');a.className='reference-case';var h=document.createElement('h3');h.textContent=r.title;a.appendChild(h);var row=document.createElement('div');row.className='reference-triptych';[['Original',r.original],['Ultra · 4×',r.ultra],['Real-life reference',r.reference]].forEach(function(pair){var f=document.createElement('figure'),im=document.createElement('img'),c=document.createElement('figcaption');im.src=pair[1];im.alt=r.title+' — '+pair[0];im.loading='lazy';c.textContent=pair[0];f.appendChild(im);f.appendChild(c);row.appendChild(f);});a.appendChild(row);var p=document.createElement('p');p.className='capture-note';p.textContent=r.caption;a.appendChild(p);$('reference-cards').appendChild(a);});
    $('empty-references').hidden=Boolean((data.references||[]).length);
  }).catch(function(e){$('empty-comparisons').textContent=e.message+'. Static comparison screenshots will accompany the release.';});
})();
