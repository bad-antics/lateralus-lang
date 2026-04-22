/* Lateralus — site-wide event handlers (replaces all inline scripts) */
document.addEventListener('DOMContentLoaded', function() {

  /* ── Hamburger menu toggle ── */
  var hamburger = document.querySelector('.hamburger');
  if (hamburger) {
    hamburger.addEventListener('click', function() {
      this.classList.toggle('open');
      document.querySelector('.topbar-links').classList.toggle('show');
    });
  }

  /* ── Copy install command button ── */
  var copyBtn = document.querySelector('[data-copy]');
  if (copyBtn) {
    copyBtn.addEventListener('click', function() {
      navigator.clipboard.writeText(this.getAttribute('data-copy'));
      this.textContent = 'OK!';
      var btn = this;
      setTimeout(function() { btn.textContent = 'COPY'; }, 1200);
    });
  }

  /* ── Blog mobile pagination ── */
  var blogCards = document.querySelectorAll('.blog-list .blog-card-y2k');
  var showMoreBtn = document.getElementById('showMoreBtn');
  if (blogCards.length && showMoreBtn) {
    var INITIAL = 8;
    var BATCH = 8;
    var shown = INITIAL;

    function isMobile() { return window.innerWidth <= 768; }

    function applyMobileState() {
      if (!isMobile()) {
        blogCards.forEach(function(c) { c.classList.remove('mobile-hidden'); });
        showMoreBtn.classList.add('all-shown');
        return;
      }
      blogCards.forEach(function(c, i) {
        if (i < shown) { c.classList.remove('mobile-hidden'); }
        else { c.classList.add('mobile-hidden'); }
      });
      if (shown >= blogCards.length) {
        showMoreBtn.classList.add('all-shown');
      } else {
        showMoreBtn.classList.remove('all-shown');
        showMoreBtn.textContent = '\u25bc SHOW MORE POSTS (' + (blogCards.length - shown) + ' remaining)';
      }
    }

    showMoreBtn.addEventListener('click', function() {
      shown = Math.min(shown + BATCH, blogCards.length);
      applyMobileState();
    });

    applyMobileState();
    window.addEventListener('resize', function() {
      if (!isMobile()) { shown = INITIAL; }
      applyMobileState();
    });
  }

  /* ── Papers filter buttons ── */
  var filterBtns = document.querySelectorAll('.filter-btn');
  var paperCards = document.querySelectorAll('.paper-card');
  var paperSections = document.querySelectorAll('.paper-section');
  if (filterBtns.length) {
    filterBtns.forEach(function(btn) {
      btn.addEventListener('click', function() {
        filterBtns.forEach(function(b) { b.classList.remove('active'); });
        btn.classList.add('active');
        var filter = btn.getAttribute('data-filter');
        if (filter === 'all') {
          paperCards.forEach(function(card) { card.style.display = ''; });
          paperSections.forEach(function(sec) { sec.style.display = ''; });
        } else {
          paperCards.forEach(function(card) {
            var cats = card.getAttribute('data-category') || '';
            card.style.display = cats.indexOf(filter) !== -1 ? '' : 'none';
          });
          paperSections.forEach(function(sec) {
            var cards = sec.querySelectorAll('.paper-card');
            var anyVisible = false;
            cards.forEach(function(c) { if (c.style.display !== 'none') anyVisible = true; });
            sec.style.display = anyVisible ? '' : 'none';
          });
        }
      });
    });
  }

});
