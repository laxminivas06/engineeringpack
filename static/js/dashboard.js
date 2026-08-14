/**
 * ENGINEERING PACK - Dashboard Interactive JavaScript
 */

document.addEventListener('DOMContentLoaded', () => {
  // Mobile Dashboard Sidebar Toggle
  const sidebarToggle = document.getElementById('sidebarToggleBtn');
  const dashboardSidebar = document.getElementById('dashboardSidebar');

  if (sidebarToggle && dashboardSidebar) {
    sidebarToggle.addEventListener('click', (e) => {
      e.stopPropagation();
      dashboardSidebar.classList.toggle('active');
    });

    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', (e) => {
      if (window.innerWidth <= 992 && dashboardSidebar.classList.contains('active')) {
        if (!dashboardSidebar.contains(e.target) && e.target !== sidebarToggle) {
          dashboardSidebar.classList.remove('active');
        }
      }
    });
  }
});
