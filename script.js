// Visual enhancements and project filters
(function () {
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  // Parallax effect on hero background layers
  const layers = $$('.layer');
  const onScroll = () => {
    const y = window.scrollY || window.pageYOffset;
    layers.forEach((el) => {
      const speed = parseFloat(el.dataset.speed || '0.04');
      el.style.transform = `translate3d(0, ${y * speed}px, 0)`;
    });
  };
  onScroll();
  window.addEventListener('scroll', onScroll, { passive: true });

  // Reveal elements while scrolling
  const revealTargets = [
    '.section',
    '.card',
    '.stat',
    '.hero h1',
    '.subtitle',
    '.cta',
  ].flatMap((sel) => $$(sel));
  revealTargets.forEach((el) => el.classList.add('reveal'));
  const revealObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('show');
        revealObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12 });
  revealTargets.forEach((el) => revealObserver.observe(el));

  // Navbar shadow on scroll
  const navbar = $('.navbar');
  const toggleNavShadow = () => {
    if (!navbar) return;
    navbar.style.boxShadow = window.scrollY > 8 ? 'var(--shadow)' : 'none';
  };
  toggleNavShadow();
  window.addEventListener('scroll', toggleNavShadow, { passive: true });

  // Smooth scroll for navigation links (with sticky offset)
  const navLinks = $$('.navbar nav a');
  const easeInOut = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
  const smoothScrollTo = (targetY, duration = 650) => {
    const startY = window.pageYOffset;
    const distance = targetY - startY;
    const startTime = performance.now();
    const step = (currentTime) => {
      const elapsed = Math.min(1, (currentTime - startTime) / duration);
      const eased = easeInOut(elapsed);
      window.scrollTo(0, startY + distance * eased);
      if (elapsed < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  };
  navLinks.forEach((link) => {
    link.addEventListener('click', (event) => {
      const hash = link.getAttribute('href');
      if (!hash || !hash.startsWith('#')) return;
      const section = document.querySelector(hash);
      if (!section) return;
      event.preventDefault();
      const navHeight = navbar ? navbar.offsetHeight : 0;
      const targetY = section.getBoundingClientRect().top + window.pageYOffset - navHeight + 4;
      smoothScrollTo(targetY);
      if (window.history && window.history.replaceState) {
        window.history.replaceState(null, '', hash);
      }
    });
  });

  // Animated counters
  const counters = $$('.num[data-count]');
  const animateCounter = (el) => {
    const target = Number(el.dataset.count || '0');
    const duration = 1200;
    const start = performance.now();
    const tick = (time) => {
      const progress = Math.min(1, (time - start) / duration);
      const eased = 0.2 + 0.8 * Math.pow(progress, 0.8);
      el.textContent = Math.floor(target * eased).toString();
      if (progress < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  };
  const counterObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        animateCounter(entry.target);
        counterObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.6 });
  counters.forEach((el) => counterObserver.observe(el));

  // Project filters
  const filterButtons = $$('.filter');
  const projects = $$('.project');
  filterButtons.forEach((button) => button.addEventListener('click', () => {
    const tag = button.dataset.filter;
    filterButtons.forEach((btn) => btn.classList.remove('active'));
    button.classList.add('active');
    projects.forEach((card) => {
      const tags = (card.dataset.tags || '').split(/\s+/);
      const visible = tag === 'all' || tags.includes(tag);
      card.style.display = visible ? '' : 'none';
    });
  }));
})();
