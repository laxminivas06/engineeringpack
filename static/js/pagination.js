/**
 * ENGINEERING PACK - Universal Client-Side Dynamic Pagination Engine
 * Enables responsive pagination with items-per-page selector, page numbers,
 * and page count info for tables, card grids, and list containers.
 */

document.addEventListener('DOMContentLoaded', () => {
  initPaginations();
});

function initPaginations() {
  const containers = document.querySelectorAll('[data-paginate="true"]');
  containers.forEach(container => {
    setupContainerPagination(container);
  });
}

function setupContainerPagination(container) {
  const itemSelector = container.dataset.paginateItem || 'tr, .glass-card, .card, .stat-card, .timeline-item, .list-item';
  let pageSize = parseInt(container.dataset.pageSize || '10', 10);
  let currentPage = 1;

  let items = [];
  if (container.tagName.toLowerCase() === 'table') {
    const tbody = container.querySelector('tbody') || container;
    items = Array.from(tbody.children).filter(el => el.tagName.toLowerCase() === 'tr');
  } else if (container.querySelector('table')) {
    const tbody = container.querySelector('tbody') || container.querySelector('table');
    items = Array.from(tbody.querySelectorAll('tr'));
  } else {
    items = Array.from(container.children).filter(el => !el.classList.contains('pagination-wrapper') && !el.classList.contains('pagination-ignore'));
  }

  if (items.length === 0) return;

  // Locate or create pagination wrapper element
  let wrapper = container.parentElement.querySelector(`.pagination-wrapper[data-for="${container.id || 'pageContainer'}"]`);
  if (!wrapper) {
    wrapper = document.createElement('div');
    wrapper.className = 'pagination-wrapper';
    if (container.id) wrapper.dataset.for = container.id;
    container.parentElement.appendChild(wrapper);
  }

  function renderPage() {
    const totalItems = items.length;
    const totalPages = Math.ceil(totalItems / pageSize) || 1;
    if (currentPage > totalPages) currentPage = totalPages;
    if (currentPage < 1) currentPage = 1;

    const startIdx = (currentPage - 1) * pageSize;
    const endIdx = Math.min(startIdx + pageSize, totalItems);

    items.forEach((item, idx) => {
      if (idx >= startIdx && idx < endIdx) {
        item.style.display = '';
      } else {
        item.style.display = 'none';
      }
    });

    const startDisplay = totalItems > 0 ? startIdx + 1 : 0;
    const endDisplay = endIdx;

    let html = `
      <div class="pagination-info">
        <span>Showing <strong style="color: var(--primary-cyan);">${startDisplay}</strong> to <strong style="color: var(--primary-cyan);">${endDisplay}</strong> of <strong style="color: #fff;">${totalItems}</strong> entries</span>
      </div>

      <div style="display: flex; align-items: center; gap: 1rem; flex-wrap: wrap;">
        <div class="pagination-page-size">
          <label style="font-size: 0.82rem; color: var(--text-dim);">Show per page:</label>
          <select class="pagination-select">
            <option value="5" ${pageSize === 5 ? 'selected' : ''}>5</option>
            <option value="10" ${pageSize === 10 ? 'selected' : ''}>10</option>
            <option value="20" ${pageSize === 20 ? 'selected' : ''}>20</option>
            <option value="50" ${pageSize === 50 ? 'selected' : ''}>50</option>
          </select>
        </div>

        <div class="pagination-controls">
          <button class="pagination-btn first-btn" ${currentPage === 1 ? 'disabled' : ''} title="First Page"><i class="bi bi-chevron-double-left"></i></button>
          <button class="pagination-btn prev-btn" ${currentPage === 1 ? 'disabled' : ''} title="Previous Page"><i class="bi bi-chevron-left"></i></button>
    `;

    const maxButtons = 5;
    let startPage = Math.max(1, currentPage - 2);
    let endPage = Math.min(totalPages, startPage + maxButtons - 1);
    if (endPage - startPage < maxButtons - 1) {
      startPage = Math.max(1, endPage - maxButtons + 1);
    }

    for (let p = startPage; p <= endPage; p++) {
      html += `<button class="pagination-btn page-num-btn ${p === currentPage ? 'active' : ''}" data-page="${p}">${p}</button>`;
    }

    html += `
          <button class="pagination-btn next-btn" ${currentPage === totalPages ? 'disabled' : ''} title="Next Page"><i class="bi bi-chevron-right"></i></button>
          <button class="pagination-btn last-btn" ${currentPage === totalPages ? 'disabled' : ''} title="Last Page"><i class="bi bi-chevron-double-right"></i></button>
        </div>
      </div>
    `;

    wrapper.innerHTML = html;

    // Attach control event listeners
    const selectEl = wrapper.querySelector('.pagination-select');
    if (selectEl) {
      selectEl.addEventListener('change', (e) => {
        pageSize = parseInt(e.target.value, 10);
        currentPage = 1;
        renderPage();
      });
    }

    const firstBtn = wrapper.querySelector('.first-btn');
    if (firstBtn) firstBtn.addEventListener('click', () => { currentPage = 1; renderPage(); });

    const prevBtn = wrapper.querySelector('.prev-btn');
    if (prevBtn) prevBtn.addEventListener('click', () => { currentPage--; renderPage(); });

    const nextBtn = wrapper.querySelector('.next-btn');
    if (nextBtn) nextBtn.addEventListener('click', () => { currentPage++; renderPage(); });

    const lastBtn = wrapper.querySelector('.last-btn');
    if (lastBtn) lastBtn.addEventListener('click', () => { currentPage = totalPages; renderPage(); });

    const numBtns = wrapper.querySelectorAll('.page-num-btn');
    numBtns.forEach(btn => {
      btn.addEventListener('click', (e) => {
        currentPage = parseInt(e.currentTarget.dataset.page, 10);
        renderPage();
      });
    });
  }

  renderPage();
}
