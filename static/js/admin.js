/**
 * Admin Panel JavaScript
 * Handles admin dashboard interactions
 */

document.addEventListener('DOMContentLoaded', () => {
    // Confirm delete user
    const deleteButtons = document.querySelectorAll('.delete-user-btn');
    deleteButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const userName = btn.dataset.userName || 'this user';
            if (!confirm(`Are you sure you want to delete ${userName}? This action cannot be undone.`)) {
                e.preventDefault();
            }
        });
    });

    // Log filter form auto-submit
    const filterSelects = document.querySelectorAll('.filter-bar select');
    filterSelects.forEach(select => {
        select.addEventListener('change', () => {
            select.closest('form')?.submit();
        });
    });

    // Toggle user status
    const toggleButtons = document.querySelectorAll('.toggle-user-btn');
    toggleButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const userName = btn.dataset.userName || 'this user';
            const currentStatus = btn.dataset.status === '1' ? 'active' : 'inactive';
            const newStatus = currentStatus === 'active' ? 'inactive' : 'active';

            if (!confirm(`Change ${userName}'s status to ${newStatus}?`)) {
                e.preventDefault();
            }
        });
    });

    // Animate stat numbers on load
    const statValues = document.querySelectorAll('.stat-value[data-count]');
    statValues.forEach(el => {
        const target = parseInt(el.dataset.count) || 0;
        let current = 0;
        const increment = Math.max(1, Math.ceil(target / 30));
        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                current = target;
                clearInterval(timer);
            }
            el.textContent = current;
        }, 30);
    });
});
