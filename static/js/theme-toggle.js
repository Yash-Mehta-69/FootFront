/**
 * Theme Toggle System for FootFront
 * Handles dark/light theme switching with localStorage persistence
 */

// Theme constants
const THEME_KEY = 'footfront-theme';
const THEME_DARK = 'dark';
const THEME_LIGHT = 'light';

/**
 * Initialize theme on page load
 */
/**
 * Initialize theme UI (icons) on page load
 * Theme attribute is already set in head to prevent FOUC
 */
function initTheme() {
    // Just sync the UI with the current state
    const currentTheme = document.documentElement.getAttribute('data-theme') || THEME_DARK;
    setTheme(currentTheme, false); // false = no transition on initial load
}

/**
 * Toggle between dark and light themes
 */
function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme') || THEME_DARK;
    const newTheme = currentTheme === THEME_DARK ? THEME_LIGHT : THEME_DARK;
    setTheme(newTheme, true); // true = with transition
}

/**
 * Set the theme
 * @param {string} theme - 'dark' or 'light'
 * @param {boolean} withTransition - whether to animate the transition
 */
function setTheme(theme, withTransition = true) {
    const html = document.documentElement;
    const themeIcon = document.getElementById('theme-icon');
    const themeIconMobile = document.getElementById('theme-icon-mobile');
    
    // Add transition class if needed
    if (withTransition) {
        html.style.transition = 'background-color 0.3s ease, color 0.3s ease';
        setTimeout(() => {
            html.style.transition = '';
        }, 300);
    }
    
    // Set theme attribute
    html.setAttribute('data-theme', theme);
    
    // Update desktop icon
    if (themeIcon) {
        if (theme === THEME_LIGHT) {
            themeIcon.classList.remove('fa-sun');
            themeIcon.classList.add('fa-moon');
        } else {
            themeIcon.classList.remove('fa-moon');
            themeIcon.classList.add('fa-sun');
        }
    }
    
    // Update mobile icon
    if (themeIconMobile) {
        if (theme === THEME_LIGHT) {
            themeIconMobile.classList.remove('fa-sun');
            themeIconMobile.classList.add('fa-moon');
        } else {
            themeIconMobile.classList.remove('fa-moon');
            themeIconMobile.classList.add('fa-sun');
        }
    }
    
    // Save to localStorage
    saveTheme(theme);
}

/**
 * Save theme preference to localStorage
 * @param {string} theme - 'dark' or 'light'
 */
function saveTheme(theme) {
    try {
        localStorage.setItem(THEME_KEY, theme);
    } catch (e) {
        console.warn('Unable to save theme preference:', e);
    }
}

/**
 * Get current theme
 * @returns {string} current theme ('dark' or 'light')
 */
function getCurrentTheme() {
    return document.documentElement.getAttribute('data-theme') || THEME_DARK;
}

// Initialize theme immediately (before DOM loads to prevent flash)
// initTheme(); // Handled by inline script + DOMContentLoaded

// Re-initialize when DOM is ready to update icons
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        const currentTheme = getCurrentTheme();
        setTheme(currentTheme, false);
    });
} else {
    const currentTheme = getCurrentTheme();
    setTheme(currentTheme, false);
}

// Listen for system theme changes
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
    // Only auto-switch if user hasn't set a preference
    if (!localStorage.getItem(THEME_KEY)) {
        setTheme(e.matches ? THEME_DARK : THEME_LIGHT, true);
    }
});
