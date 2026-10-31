/**
 * TiffinTrail Chef Studio – Interactive JavaScript
 * Vanilla JavaScript (No CDN, No external dependencies)
 */

document.addEventListener('DOMContentLoaded', function () {
  // 1. Mobile Sidebar Toggle
  const sidebar = document.getElementById('ttSidebar');
  const toggleBtn = document.getElementById('ttMenuToggle');

  // Create backdrop element if it doesn't exist
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

  // 2. Image Previews for File Inputs
  const imageInputs = document.querySelectorAll('input[type="file"][accept*="image"], input[type="file"]');
  imageInputs.forEach(input => {
    input.addEventListener('change', function () {
      const file = this.files[0];
      if (file) {
        // Validate file size (max 5MB)
        if (file.size > 5 * 1024 * 1024) {
          alert('File size exceeds 5MB limit. Please select a smaller image.');
          this.value = '';
          return;
        }

        // Look for sibling or related preview target
        const previewId = this.getAttribute('data-preview-target');
        const previewEl = previewId ? document.getElementById(previewId) : null;
        if (previewEl) {
          const reader = new FileReader();
          reader.onload = function (e) {
            previewEl.src = e.target.result;
            previewEl.style.display = 'block';
          };
          reader.readAsDataURL(file);
        }
      }
    });
  });

  // 3. Confirm Delete / Status actions
  const confirmTriggers = document.querySelectorAll('[data-confirm]');
  confirmTriggers.forEach(el => {
    el.addEventListener('click', function (e) {
      const msg = this.getAttribute('data-confirm') || 'Are you sure you want to proceed?';
      if (!confirm(msg)) {
        e.preventDefault();
      }
    });
  });

  // 4. Auto-dismiss Alert messages after 5 seconds
  const alerts = document.querySelectorAll('.alert-dismissible');
  alerts.forEach(alertEl => {
    setTimeout(() => {
      try {
        const bsAlert = bootstrap.Alert.getOrCreateInstance(alertEl);
        if (bsAlert) {
          bsAlert.close();
        }
      } catch (err) {
        // fallback removal if bootstrap js not active
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
