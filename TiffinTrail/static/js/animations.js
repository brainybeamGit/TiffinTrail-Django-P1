/**
 * TiffinTrail Animation & Microinteraction Engine
 */
document.addEventListener('DOMContentLoaded', function () {
  // 1. Scroll-Triggered Reveal via IntersectionObserver
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const revealElements = document.querySelectorAll('.reveal-on-scroll, .reveal-fade');
  if (revealElements.length > 0) {
    if (prefersReducedMotion || !('IntersectionObserver' in window)) {
      revealElements.forEach(el => el.classList.add('is-visible'));
    } else {
      const observer = new IntersectionObserver((entries, obs) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            obs.unobserve(entry.target);
          }
        });
      }, {
        threshold: 0.12,
        rootMargin: '0px 0px -40px 0px'
      });

      revealElements.forEach(el => observer.observe(el));
    }
  }

  // 2. Sticky Navbar Elevation on Scroll
  const navbar = document.querySelector('.tt-navbar');
  if (navbar) {
    const handleScroll = () => {
      if (window.scrollY > 20) {
        navbar.classList.add('is-scrolled');
      } else {
        navbar.classList.remove('is-scrolled');
      }
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll();
  }

  // 3. Double-Submit Prevention with Loading State on Forms
  document.querySelectorAll('form:not([data-no-disable])').forEach(form => {
    form.addEventListener('submit', function (e) {
      if (form.checkValidity && !form.checkValidity()) {
        return;
      }
      const submitBtn = form.querySelector('button[type="submit"]:not(.no-spin)');
      if (submitBtn && !submitBtn.disabled) {
        // Delay disabling slightly so browser submits standard form data
        setTimeout(() => {
          submitBtn.disabled = true;
          const origText = submitBtn.innerHTML;
          submitBtn.setAttribute('data-orig-text', origText);
          submitBtn.innerHTML = `
            <span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>
            Processing...
          `;
        }, 10);
      }
    });
  });

  // 4. Micro-interaction: Quantity Selector Smooth Update
  document.querySelectorAll('.tt-qty-wrapper').forEach(wrapper => {
    const input = wrapper.querySelector('input[type="number"], .tt-qty-input');
    const plusBtn = wrapper.querySelector('.tt-qty-plus');
    const minusBtn = wrapper.querySelector('.tt-qty-minus');

    if (input && plusBtn && minusBtn) {
      plusBtn.addEventListener('click', () => {
        let val = parseInt(input.value, 10) || 1;
        const max = parseInt(input.getAttribute('max'), 10) || 99;
        if (val < max) {
          input.value = val + 1;
          input.dispatchEvent(new Event('change', { bubbles: true }));
        }
      });

      minusBtn.addEventListener('click', () => {
        let val = parseInt(input.value, 10) || 1;
        const min = parseInt(input.getAttribute('min'), 10) || 1;
        if (val > min) {
          input.value = val - 1;
          input.dispatchEvent(new Event('change', { bubbles: true }));
        }
      });
    }
  });

  // 5. Toast Notification Utility
  window.showToast = function (message, type = 'success') {
    let container = document.querySelector('.tt-toast-container');
    if (!container) {
      container = document.createElement('div');
      container.className = 'tt-toast-container';
      document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `tt-toast toast-${type}`;
    toast.innerHTML = `
      <div class="flex-grow-1">${message}</div>
      <button type="button" class="btn-close btn-close-sm" aria-label="Close"></button>
    `;

    toast.querySelector('.btn-close').addEventListener('click', () => {
      toast.remove();
    });

    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(15px)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 320);
    }, 4000);
  };
});
