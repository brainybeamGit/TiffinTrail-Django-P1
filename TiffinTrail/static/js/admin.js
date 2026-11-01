/**
 * TiffinTrail Admin Console – Interactive Microinteraction & Animation Engine
 * Vanilla JavaScript (No External CDN, Offline-First, Ultra High Performance)
 */

document.addEventListener('DOMContentLoaded', function () {
  // 1. Collapsible & Responsive Sidebar System
  const sidebar = document.getElementById('ttSidebar');
  const toggleBtn = document.getElementById('ttMenuToggle');
  const body = document.body;

  // Restore Desktop Collapsed State from localStorage
  const savedCollapsed = localStorage.getItem('tt_admin_sidebar_collapsed');
  if (savedCollapsed === 'true' && window.innerWidth >= 992) {
    body.classList.add('tt-collapsed-sidebar');
  }

  // Mobile Backdrop
  let backdrop = document.querySelector('.tt-sidebar-backdrop');
  if (!backdrop) {
    backdrop = document.createElement('div');
    backdrop.className = 'tt-sidebar-backdrop';
    document.body.appendChild(backdrop);
  }

  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener('click', function () {
      if (window.innerWidth >= 992) {
        // Desktop collapse toggle
        body.classList.toggle('tt-collapsed-sidebar');
        const isCollapsed = body.classList.contains('tt-collapsed-sidebar');
        localStorage.setItem('tt_admin_sidebar_collapsed', isCollapsed ? 'true' : 'false');
      } else {
        // Mobile drawer toggle
        sidebar.classList.toggle('show');
        backdrop.classList.toggle('show');
      }
    });

    backdrop.addEventListener('click', function () {
      sidebar.classList.remove('show');
      backdrop.classList.remove('show');
    });

    // Close mobile drawer on Escape key
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && sidebar.classList.contains('show')) {
        sidebar.classList.remove('show');
        backdrop.classList.remove('show');
      }
    });
  }

  // 2. Confirmation Prompts
  const confirmElements = document.querySelectorAll('[data-confirm]');
  confirmElements.forEach(el => {
    el.addEventListener('click', function (e) {
      const msg = this.getAttribute('data-confirm') || 'Are you sure you want to perform this administrative action?';
      if (!confirm(msg)) {
        e.preventDefault();
      }
    });
  });

  // 3. Auto-dismiss Flash Alerts with Smooth Slide & Fade
  const alerts = document.querySelectorAll('.alert-dismissible');
  alerts.forEach(alertEl => {
    setTimeout(() => {
      try {
        const bsAlert = bootstrap.Alert.getOrCreateInstance(alertEl);
        if (bsAlert) {
          alertEl.style.transition = 'all 0.4s cubic-bezier(0.16, 1, 0.3, 1)';
          alertEl.style.opacity = '0';
          alertEl.style.transform = 'translateY(-10px)';
          setTimeout(() => bsAlert.close(), 400);
        }
      } catch (err) {
        alertEl.style.transition = 'all 0.4s ease';
        alertEl.style.opacity = '0';
        alertEl.style.transform = 'translateY(-10px)';
        setTimeout(() => alertEl.remove(), 400);
      }
    }, 5500);
  });

  // 4. Ensure mouse wheel over tables scrolls the window vertically (no horizontal hijack)
  const tableContainers = document.querySelectorAll('.tt-table-responsive, .table-responsive');
  tableContainers.forEach(function (container) {
    container.addEventListener('wheel', function (e) {
      if (!e.shiftKey && Math.abs(e.deltaY) > 0) {
        e.preventDefault();
        window.scrollBy({
          top: e.deltaY,
          left: 0,
          behavior: 'auto'
        });
      }
    }, { passive: false });
  });

  // 5. High-Performance Animated Number Counter for KPI & Stats (Strictly 2 Decimals)
  function animateValue(el) {
    const rawText = el.innerText.trim();
    // Match optional prefix, the numeric part (with commas/decimals), and optional suffix
    const match = rawText.match(/^([^0-9]*)([0-9,]+(?:\.[0-9]+)?)([^0-9]*)$/);
    if (!match) return;

    const prefix = match[1] || '';
    const numClean = match[2].replace(/,/g, '');
    const suffix = match[3] || '';
    const target = parseFloat(numClean);
    if (isNaN(target) || target === 0) return;

    const hasDecimal = numClean.includes('.');
    const decimals = hasDecimal ? 2 : 0;
    const duration = 850; // ms
    const startTime = performance.now();

    function easeOutCubic(t) {
      return 1 - Math.pow(1 - t, 3);
    }

    function frame(now) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = easeOutCubic(progress);
      const current = target * eased;

      let formatted;
      if (hasDecimal) {
        formatted = current.toLocaleString('en-IN', {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2
        });
      } else {
        formatted = Math.round(current).toLocaleString('en-IN');
      }

      el.innerText = `${prefix}${formatted}${suffix}`;

      if (progress < 1) {
        requestAnimationFrame(frame);
      } else {
        const finalFormatted = hasDecimal
          ? target.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
          : Math.round(target).toLocaleString('en-IN');
        el.innerText = `${prefix}${finalFormatted}${suffix}`;
      }
    }

    requestAnimationFrame(frame);
  }

  // Trigger counters smoothly on page load
  const kpiValues = document.querySelectorAll('.tt-kpi-value, .tt-counter, .tt-stat-value, [data-counter]');
  kpiValues.forEach(el => animateValue(el));

  // 6. Modern Button Click Ripple Micro-Interaction
  document.querySelectorAll('.btn, .tt-btn-action, .tt-nav-tile').forEach(btn => {
    btn.addEventListener('click', function (e) {
      const rect = this.getBoundingClientRect();
      const ripple = document.createElement('span');
      ripple.className = 'tt-ripple-effect';
      const size = Math.max(rect.width, rect.height);
      ripple.style.width = ripple.style.height = `${size}px`;
      ripple.style.left = `${e.clientX - rect.left - size / 2}px`;
      ripple.style.top = `${e.clientY - rect.top - size / 2}px`;
      this.appendChild(ripple);
      setTimeout(() => ripple.remove(), 650);
    });
  });

  // 7. Interactive Chart Bars Reveal
  const chartBars = document.querySelectorAll('.tt-chart-bar-inner, .tt-chart-bar');
  if (chartBars.length > 0) {
    chartBars.forEach((bar, idx) => {
      bar.style.transformOrigin = 'bottom';
      bar.style.animation = `ttBarGrow 0.7s cubic-bezier(0.16, 1, 0.3, 1) ${0.08 * (idx + 1)}s both`;
    });
  }

  // 8. Password Visibility Toggle
  document.querySelectorAll('.tt-password-toggle').forEach(toggle => {
    toggle.addEventListener('click', function () {
      const input = this.closest('.input-group').querySelector('input');
      const icon = this.querySelector('i');
      if (input) {
        if (input.type === 'password') {
          input.type = 'text';
          if (icon) {
            icon.classList.remove('bi-eye');
            icon.classList.add('bi-eye-slash');
          }
        } else {
          input.type = 'password';
          if (icon) {
            icon.classList.remove('bi-eye-slash');
            icon.classList.add('bi-eye');
          }
        }
      }
    });
  });
});
