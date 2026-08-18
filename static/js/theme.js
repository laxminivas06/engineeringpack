/**
 * ENGINEERING PACK - Theme Switcher Engine (Light, Dark, System Default)
 * Manages theme persistence, OS preferences, and seamless DOM updates.
 */

(function() {
  // Apply theme immediately to documentElement to prevent Flash of Unstyled Content (FOUC)
  const savedTheme = localStorage.getItem('theme') || 'light';
  applyTheme(savedTheme, false);
})();

document.addEventListener('DOMContentLoaded', () => {
  const currentTheme = localStorage.getItem('theme') || 'light';
  syncThemeSelectors(currentTheme);

  // Listen for OS dark mode changes if system theme is selected
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
    const activeTheme = localStorage.getItem('theme') || 'light';
    if (activeTheme === 'system') {
      applyTheme('system', false);
    }
  });
});

function applyTheme(themeMode, saveToStorage = true) {
  if (saveToStorage) {
    localStorage.setItem('theme', themeMode);
  }

  let effectiveTheme = themeMode;
  if (themeMode === 'system') {
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    effectiveTheme = prefersDark ? 'dark' : 'light';
  }

  document.documentElement.setAttribute('data-theme', effectiveTheme);
  document.documentElement.setAttribute('data-theme-setting', themeMode);

  // Sync selector elements across header
  syncThemeSelectors(themeMode);
}

function syncThemeSelectors(themeMode) {
  const selectors = document.querySelectorAll('#themeSelector, .theme-select');
  selectors.forEach(sel => {
    if (sel.value !== themeMode) {
      sel.value = themeMode;
    }
  });
}

function setAppTheme(val) {
  applyTheme(val, true);
}
