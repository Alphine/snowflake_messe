(function () {
  'use strict';

  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- sortable watchlist table ---------- */
  function initSortableTable() {
    var table = document.querySelector('table.watchlist');
    if (!table) return;
    var tbody = table.tBodies[0];
    var headers = table.querySelectorAll('th[data-sort-key]');

    headers.forEach(function (th) {
      var btn = th.querySelector('button');
      if (!btn) return;
      btn.addEventListener('click', function () {
        var key = th.getAttribute('data-sort-key');
        var type = th.getAttribute('data-sort-type') || 'text';
        var current = th.getAttribute('aria-sort');
        var next = current === 'descending' ? 'ascending' : 'descending';

        headers.forEach(function (h) { h.removeAttribute('aria-sort'); });
        th.setAttribute('aria-sort', next);

        var rows = Array.prototype.slice.call(tbody.querySelectorAll('tr'));
        rows.sort(function (a, b) {
          var av = a.querySelector('[data-key="' + key + '"]').getAttribute('data-value');
          var bv = b.querySelector('[data-key="' + key + '"]').getAttribute('data-value');
          if (type === 'number') {
            av = parseFloat(av); bv = parseFloat(bv);
          }
          var cmp = av > bv ? 1 : av < bv ? -1 : 0;
          return next === 'ascending' ? cmp : -cmp;
        });
        rows.forEach(function (r) { tbody.appendChild(r); });
      });
    });
  }

  /* ---------- score bar grow-in ---------- */
  function initScoreBars() {
    var bars = document.querySelectorAll('.score-bar > span, .bucket-fill');
    if (reduceMotion) {
      bars.forEach(function (b) { b.classList.add('grown'); });
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('grown');
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.4 });
    bars.forEach(function (b) { io.observe(b); });
  }

  /* ---------- count-up for the honesty headline ---------- */
  function initCountUp() {
    var el = document.querySelector('[data-countup]');
    if (!el) return;
    var target = parseInt(el.getAttribute('data-countup'), 10);
    var suffix = el.getAttribute('data-countup-suffix') || '';
    if (reduceMotion || isNaN(target)) {
      el.textContent = target + suffix;
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        io.unobserve(entry.target);
        var start = null;
        var duration = 900;
        function step(ts) {
          if (!start) start = ts;
          var progress = Math.min((ts - start) / duration, 1);
          var eased = 1 - Math.pow(1 - progress, 3);
          el.textContent = Math.round(eased * target) + suffix;
          if (progress < 1) requestAnimationFrame(step);
        }
        requestAnimationFrame(step);
      });
    }, { threshold: 0.6 });
    io.observe(el);
  }

  /* ---------- scroll-reveal ---------- */
  function initReveal() {
    var items = document.querySelectorAll('.reveal');
    if (reduceMotion || !items.length) {
      items.forEach(function (i) { i.classList.add('in'); });
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('in');
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.15 });
    items.forEach(function (i) { io.observe(i); });
  }

  /* ---------- active nav link on scroll ---------- */
  function initActiveNav() {
    var links = document.querySelectorAll('.topnav-links a[href^="#"]');
    if (!links.length) return;
    var sections = Array.prototype.map.call(links, function (l) {
      return document.querySelector(l.getAttribute('href'));
    }).filter(Boolean);
    if (!sections.length) return;

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        var link = document.querySelector('.topnav-links a[href="#' + entry.target.id + '"]');
        if (!link) return;
        if (entry.isIntersecting) {
          links.forEach(function (l) { l.classList.remove('active'); });
          link.classList.add('active');
        }
      });
    }, { rootMargin: '-40% 0px -50% 0px' });
    sections.forEach(function (s) { io.observe(s); });
  }

  document.addEventListener('DOMContentLoaded', function () {
    initSortableTable();
    initScoreBars();
    initCountUp();
    initReveal();
    initActiveNav();
  });
})();
