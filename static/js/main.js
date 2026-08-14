/**
 * ENGINEERING PACK - Main Interactive JavaScript
 */

document.addEventListener('DOMContentLoaded', () => {
  // Mobile Nav Menu Drawer Toggle
  const navToggle = document.getElementById('navToggle');
  const mobileDrawer = document.getElementById('mobileDrawer');

  if (navToggle && mobileDrawer) {
    navToggle.addEventListener('click', () => {
      const isActive = mobileDrawer.classList.contains('active');
      if (isActive) {
        mobileDrawer.classList.remove('active');
        navToggle.innerHTML = '<i class="bi bi-list"></i>';
      } else {
        mobileDrawer.classList.add('active');
        navToggle.innerHTML = '<i class="bi bi-x-lg"></i>';
      }
    });

    // Close mobile drawer when clicking a link inside it
    const mobileLinks = mobileDrawer.querySelectorAll('.mobile-nav-link');
    mobileLinks.forEach(link => {
      link.addEventListener('click', () => {
        mobileDrawer.classList.remove('active');
        navToggle.innerHTML = '<i class="bi bi-list"></i>';
      });
    });
  }

  // Flash Alert Dismissal
  const alertCloseBtns = document.querySelectorAll('.alert .btn-close');
  alertCloseBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const alert = btn.closest('.alert');
      if (alert) {
        alert.style.opacity = '0';
        alert.style.transform = 'translateX(100%)';
        setTimeout(() => alert.remove(), 300);
      }
    });
  });

  // Auto dismiss flash messages after 5 seconds
  const autoAlerts = document.querySelectorAll('.flash-messages-container .alert');
  autoAlerts.forEach(alert => {
    setTimeout(() => {
      if (alert && alert.parentNode) {
        alert.style.opacity = '0';
        alert.style.transform = 'translateX(100%)';
        setTimeout(() => alert.remove(), 300);
      }
    }, 5000);
  });
});
