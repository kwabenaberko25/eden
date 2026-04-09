/**
 * Eden Admin Panel — Vanilla JS logic
 * Replaces AlpineJS for core interface interactions.
 */

window.Eden = window.Eden || {};

Eden.Admin = {
    init() {
        this.initSidebar();
        this.initDropdowns();
        this.initMobileNav();
        this.initHTMX();
    },

    /**
     * Handle sidebar toggling
     */
    initSidebar() {
        const toggleBtn = document.getElementById('sidebar-toggle');
        const sidebar = document.querySelector('.sidebar');
        const mainContent = document.querySelector('.main-content');

        if (toggleBtn && sidebar) {
            toggleBtn.addEventListener('click', () => {
                const isClosed = sidebar.classList.toggle('closed');
                if (mainContent) {
                    mainContent.classList.toggle('full-width', isClosed);
                }
                
                // For mobile
                sidebar.classList.toggle('open');
                
                // Save state in localStorage
                localStorage.setItem('eden_sidebar_closed', isClosed);
            });

            // Restore state
            const wasClosed = localStorage.getItem('eden_sidebar_closed') === 'true';
            if (wasClosed && window.innerWidth > 1024) {
                sidebar.classList.add('closed');
                mainContent?.classList.add('full-width');
            }
        }
    },

    /**
     * Simple dropdown logic
     */
    initDropdowns() {
        document.addEventListener('click', (e) => {
            const toggle = e.target.closest('[data-dropdown-toggle]');
            if (toggle) {
                e.preventDefault();
                const menuId = toggle.getAttribute('data-dropdown-toggle');
                const menu = document.getElementById(menuId);
                
                // Close others
                document.querySelectorAll('.dropdown-menu.show').forEach(m => {
                    if (m !== menu) m.classList.remove('show');
                });
                
                menu?.classList.toggle('show');
            } else {
                // Close all when clicking outside
                document.querySelectorAll('.dropdown-menu.show').forEach(m => {
                    m.classList.remove('show');
                });
            }
        });
    },

    /**
     * Mobile specific nav
     */
    initMobileNav() {
        // Overlay for mobile
        const overlay = document.createElement('div');
        overlay.className = 'sidebar-overlay';
        document.body.appendChild(overlay);

        overlay.addEventListener('click', () => {
             document.querySelector('.sidebar')?.classList.remove('open');
             overlay.classList.remove('active');
        });

        // Add CSS for overlay dynamically if needed, or just add to admin.css
        // I'll add it in admin.css in a follow up or assume it's there.
    },

    /**
     * Ensure HTMX events are handled
     */
    initHTMX() {
        document.addEventListener('htmx:afterSwap', (event) => {
            // Re-initialize any dynamic components in the swapped content
            console.log('HTMX content swapped, re-init scripts if needed');
        });
        
        document.addEventListener('htmx:configRequest', (event) => {
            // Ensure CSRF token is present for HTMX requests
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
            if (csrfToken) {
                event.detail.headers['X-CSRFToken'] = csrfToken;
            }
        });
    }
};

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
    Eden.Admin.init();
});
