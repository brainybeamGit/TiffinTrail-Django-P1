/**
 * TiffinTrail Admin Console – Interactive JavaScript
 * Vanilla JavaScript (No CDN, Offline-First)
 */

document.addEventListener('DOMContentLoaded', function () {
  // 1. Mobile Sidebar Toggle
  const sidebar = document.getElementById('ttSidebar');
  const toggleBtn = document.getElementById('ttMenuToggle');

  let backdrop = document.querySelector('.tt-sidebar-backdrop');
  if (!backdrop) {
    backdrop = document.createElement('div');
    backdrop.className = 'tt-sidebar-backdrop';
    document.body.appendChild(backdrop);
  }

  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener('click', function () {
      sidebar.classList.toggle('show');
      backdrop.classList.toggle('show');
    });

    backdrop.addEventListener('click', function () {
      sidebar.classList.remove('show');
      backdrop.classList.remove('show');
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

  // 3. Auto-dismiss Flash Alerts
  const alerts = document.querySelectorAll('.alert-dismissible');
  alerts.forEach(alertEl => {
    setTimeout(() => {
      try {
        const bsAlert = bootstrap.Alert.getOrCreateInstance(alertEl);
        if (bsAlert) bsAlert.close();
      } catch (err) {
        alertEl.style.transition = 'opacity 0.5s ease';
        alertEl.style.opacity = '0';
        setTimeout(() => alertEl.remove(), 500);
      }
    }, 5000);
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
});
