/**
 * ENGINEERING PACK - Dashboard Interactive JavaScript
 * Handlers for fixed header, sidebar off-canvas drawer, backdrop, keyboard navigation.
 */

document.addEventListener('DOMContentLoaded', () => {
  const sidebarToggleBtn = document.getElementById('sidebarToggleBtn');
  const headerSidebarToggle = document.getElementById('headerSidebarToggle');
  const dashboardSidebar = document.getElementById('dashboardSidebar');
  const sidebarBackdrop = document.getElementById('sidebarBackdrop');

  function openSidebar() {
    if (dashboardSidebar) {
      dashboardSidebar.classList.add('active');
    }
    if (sidebarBackdrop) {
      sidebarBackdrop.classList.add('active');
    }
    document.body.style.overflow = 'hidden';
  }

  function closeSidebar() {
    if (dashboardSidebar) {
      dashboardSidebar.classList.remove('active');
    }
    if (sidebarBackdrop) {
      sidebarBackdrop.classList.remove('active');
    }
    document.body.style.overflow = '';
  }

  function toggleSidebar(e) {
    if (e) e.stopPropagation();
    if (dashboardSidebar && dashboardSidebar.classList.contains('active')) {
      closeSidebar();
    } else {
      openSidebar();
    }
  }

  if (sidebarToggleBtn) {
    sidebarToggleBtn.addEventListener('click', toggleSidebar);
  }

  if (headerSidebarToggle) {
    headerSidebarToggle.addEventListener('click', toggleSidebar);
  }

  if (sidebarBackdrop) {
    sidebarBackdrop.addEventListener('click', closeSidebar);
  }

  // Close sidebar drawer on link click in mobile view
  if (dashboardSidebar) {
    const sidebarLinks = dashboardSidebar.querySelectorAll('.sidebar-link');
    sidebarLinks.forEach(link => {
      link.addEventListener('click', () => {
        if (window.innerWidth <= 992) {
          closeSidebar();
        }
      });
    });
  }

  // Close drawer when pressing Escape key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && dashboardSidebar && dashboardSidebar.classList.contains('active')) {
      closeSidebar();
    }
  });

  // Handle window resize cleanly
  window.addEventListener('resize', () => {
    if (window.innerWidth > 992) {
      closeSidebar();
    }
  });
});
