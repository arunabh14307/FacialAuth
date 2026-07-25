/**
 * Logout Confirmation Modal with Hidden Admin Option
 */
document.addEventListener('DOMContentLoaded', () => {
    // Inject Logout Modal into DOM if not present
    if (!document.getElementById('logoutModal')) {
        const modalHtml = `
        <div id="logoutModal" class="modal-overlay" style="display: none;" role="dialog" aria-modal="true">
            <div class="modal-card">
                <button type="button" class="modal-close-btn" id="logoutModalClose" aria-label="Close modal">&times;</button>
                <div class="logout-icon-badge" id="logoutBadgeIcon" title="Click icon to toggle Admin option">
                    🛡️
                </div>
                <h3 style="margin-bottom: 0.25rem;">Logging Out</h3>
                <p style="color: var(--text-secondary); font-size: 0.9rem; margin-bottom: 1rem;">
                    Select portal destination for your next login:
                </p>

                <div class="logout-options-group">
                    <a id="logoutUserLink" href="/logout?next=user" class="btn-option-user">
                        👤 Login as User
                    </a>
                    
                    <a id="logoutHomeLink" href="/logout?next=home" class="btn btn-outline" style="border-color: var(--border); color: var(--text-secondary);">
                        🏠 Return to Home Page
                    </a>

                    <button type="button" class="btn-option-cancel" id="logoutModalCancel">
                        Cancel
                    </button>
                </div>
            </div>
        </div>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHtml);
    }

    const modal = document.getElementById('logoutModal');
    const closeBtn = document.getElementById('logoutModalClose');
    const cancelBtn = document.getElementById('logoutModalCancel');

    function openLogoutModal(logoutUrl) {
        if (!modal) return;
        const userLink = document.getElementById('logoutUserLink');
        const homeLink = document.getElementById('logoutHomeLink');
        
        // Base logout endpoint
        const isAppAdmin = logoutUrl && logoutUrl.includes('admin');
        const baseUrl = isAppAdmin ? '/admin/logout' : '/logout';

        userLink.href = `${baseUrl}?next=user`;
        homeLink.href = `${baseUrl}?next=home`;

        modal.style.display = 'flex';
    }

    function closeLogoutModal() {
        if (modal) modal.style.display = 'none';
    }

    if (closeBtn) closeBtn.addEventListener('click', closeLogoutModal);
    if (cancelBtn) cancelBtn.addEventListener('click', closeLogoutModal);

    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeLogoutModal();
        });
    }

    // Intercept clicks on user logout links/buttons (exclude admin logout & direct-logout)
    document.body.addEventListener('click', (e) => {
        const target = e.target.closest('a[href*="logout"], button[href*="logout"], .btn-logout');
        if (target) {
            const href = target.getAttribute('href') || '';
            if (href.includes('/admin/') || target.classList.contains('direct-logout') || target.dataset.direct === 'true') {
                return; // Direct navigation for direct logout
            }
            e.preventDefault();
            openLogoutModal(href);
        }
    });
});
