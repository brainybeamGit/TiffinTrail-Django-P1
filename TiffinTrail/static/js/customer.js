/**
 * TiffinTrail - Customer Website JavaScript
 * Pure Vanilla JavaScript - No external libraries or CDN dependencies
 */

document.addEventListener('DOMContentLoaded', function () {
  // 1. Interactive Star Rating Selector
  const starPickers = document.querySelectorAll('.tt-star-picker');
  starPickers.forEach(picker => {
    const stars = picker.querySelectorAll('.star-btn');
    const hiddenInput = picker.querySelector('input[type="hidden"], select');

    stars.forEach(star => {
      star.addEventListener('click', function () {
        const val = parseInt(this.getAttribute('data-value'), 10);
        if (hiddenInput) {
          hiddenInput.value = val;
        }
        stars.forEach(s => {
          const sVal = parseInt(s.getAttribute('data-value'), 10);
          if (sVal <= val) {
            s.classList.add('active');
            s.textContent = '★';
          } else {
            s.classList.remove('active');
            s.textContent = '☆';
          }
        });
      });

      star.addEventListener('mouseenter', function () {
        const val = parseInt(this.getAttribute('data-value'), 10);
        stars.forEach(s => {
          const sVal = parseInt(s.getAttribute('data-value'), 10);
          s.style.color = sVal <= val ? '#eab308' : '#cbd5e1';
        });
      });

      picker.addEventListener('mouseleave', function () {
        const curVal = hiddenInput ? parseInt(hiddenInput.value, 10) || 5 : 5;
        stars.forEach(s => {
          const sVal = parseInt(s.getAttribute('data-value'), 10);
          s.style.color = '';
          if (sVal <= curVal) {
            s.classList.add('active');
            s.textContent = '★';
          } else {
            s.classList.remove('active');
            s.textContent = '☆';
          }
        });
      });
    });
  });

  // 2. Checkout Saved Address Toggle
  const addressRadios = document.querySelectorAll('input[name="address_choice"]');
  const newAddressFields = document.getElementById('ttNewAddressFields');

  if (addressRadios.length > 0 && newAddressFields) {
    function toggleNewAddressFields() {
      let isNewSelected = false;
      addressRadios.forEach(radio => {
        if (radio.checked && radio.value === 'new') {
          isNewSelected = true;
        }
      });
      if (isNewSelected || addressRadios.length === 0) {
        newAddressFields.style.display = 'block';
      } else {
        newAddressFields.style.display = 'none';
      }
    }

    addressRadios.forEach(r => r.addEventListener('change', toggleNewAddressFields));
    toggleNewAddressFields();
  }

  // 3. Auto-dismiss alerts after 6 seconds
  const alerts = document.querySelectorAll('.alert-dismissible');
  alerts.forEach(alert => {
    setTimeout(() => {
      try {
        if (window.bootstrap && bootstrap.Alert) {
          const bsAlert = new bootstrap.Alert(alert);
          bsAlert.close();
        } else {
          alert.remove();
        }
      } catch (e) {
        alert.remove();
      }
    }, 6000);
  });

  // 4. Quantity Increment / Decrement
  const qtyBtns = document.querySelectorAll('[data-qty-action]');
  qtyBtns.forEach(btn => {
    btn.addEventListener('click', function (e) {
      const action = this.getAttribute('data-qty-action');
      const targetId = this.getAttribute('data-target');
      const input = document.getElementById(targetId);
      if (input) {
        let val = parseInt(input.value, 10) || 1;
        if (action === 'increment') {
          val = Math.min(20, val + 1);
        } else if (action === 'decrement') {
          val = Math.max(1, val - 1);
        }
        input.value = val;
      }
    });
  });
});
