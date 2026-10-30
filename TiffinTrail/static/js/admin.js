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

  // 4. Click & Drag to Scroll for Table Details (.tt-table-responsive, .table-responsive)
  function initDragScroll() {
    const tableContainers = document.querySelectorAll('.tt-table-responsive, .table-responsive');
    tableContainers.forEach(container => {
      let isDown = false;
      let startX = 0;
      let scrollLeft = 0;
      let hasDragged = false;
      const dragThreshold = 6;

      container.classList.add('tt-drag-scrollable');

      container.addEventListener('mousedown', function (e) {
        // Allow direct clicks on interactive elements without drag lock
        if (e.target.closest('input, select, textarea, .dropdown-menu, .modal')) {
          return;
        }
        isDown = true;
        hasDragged = false;
        container.classList.add('tt-is-dragging');
        startX = e.pageX - container.offsetLeft;
        scrollLeft = container.scrollLeft;
      });

      window.addEventListener('mouseup', function () {
        if (isDown) {
          isDown = false;
          container.classList.remove('tt-is-dragging');
          setTimeout(() => { hasDragged = false; }, 60);
        }
      });

      container.addEventListener('mouseleave', function () {
        if (isDown) {
          isDown = false;
          container.classList.remove('tt-is-dragging');
        }
      });

      container.addEventListener('mousemove', function (e) {
        if (!isDown) return;
        const x = e.pageX - container.offsetLeft;
        const walk = (x - startX);
        if (Math.abs(walk) > dragThreshold) {
          hasDragged = true;
          e.preventDefault();
          container.scrollLeft = scrollLeft - walk;
        }
      });

      // Prevent link/button trigger if the user was actively dragging
      container.addEventListener('click', function (e) {
        if (hasDragged) {
          e.preventDefault();
          e.stopPropagation();
        }
      }, true);

      // Mouse Wheel horizontal scroll support over tables
      container.addEventListener('wheel', function (e) {
        if (container.scrollWidth > container.clientWidth) {
          if (e.shiftKey) return;
          const atStart = container.scrollLeft <= 0;
          const atEnd = Math.ceil(container.scrollLeft + container.clientWidth) >= container.scrollWidth;
          if ((e.deltaY > 0 && !atEnd) || (e.deltaY < 0 && !atStart)) {
            e.preventDefault();
            container.scrollLeft += e.deltaY;
          }
        }
      }, { passive: false });
    });
  }

  initDragScroll();
});
