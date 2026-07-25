/**
 * Secret Admin Portal Access — Shield Icon 7-Tap Detector & OTP Modal
 */

document.addEventListener('DOMContentLoaded', () => {
    let tapCount = 0;
    let tapTimeout = null;

    const shieldTrigger = document.getElementById('admin-shield-trigger');
    const modal = document.getElementById('admin-access-modal');
    const modalCloseBtn = document.getElementById('admin-modal-close');

    const stepCredentials = document.getElementById('admin-step-credentials');
    const stepOtp = document.getElementById('admin-step-otp');

    const credForm = document.getElementById('admin-cred-form');
    const credError = document.getElementById('admin-cred-error');
    const btnVerifyCred = document.getElementById('btn-verify-cred');

    const otpForm = document.getElementById('admin-otp-form');
    const otpError = document.getElementById('admin-otp-error');
    const otpSuccess = document.getElementById('admin-otp-success');
    const otpNotice = document.getElementById('otp-sent-notice');
    const btnVerifyOtp = document.getElementById('btn-verify-otp');
    const btnResendOtp = document.getElementById('btn-resend-otp');

    // ─── 1. Tap Counter Handler ─────────────────────────────
    if (shieldTrigger) {
        shieldTrigger.addEventListener('click', (e) => {
            // Prevent navigating home when tapping icon rapidly
            if (tapCount > 0) {
                e.preventDefault();
            }

            tapCount++;

            // Visual feedback pulse effect
            shieldTrigger.classList.add('shield-pulse');
            setTimeout(() => shieldTrigger.classList.remove('shield-pulse'), 300);

            // Toast feedback when getting close
            if (tapCount >= 4 && tapCount < 7) {
                showTapToast(`Tap ${7 - tapCount} more time(s) for Admin access`);
            }

            // Trigger modal on 7th tap
            if (tapCount >= 7) {
                e.preventDefault();
                tapCount = 0;
                clearTimeout(tapTimeout);
                openAdminModal();
                return;
            }

            // Reset tap count after 3 seconds of inactivity
            clearTimeout(tapTimeout);
            tapTimeout = setTimeout(() => {
                tapCount = 0;
            }, 3000);
        });
    }

    // ─── 2. Modal Display Helpers ───────────────────────────
    function openAdminModal() {
        if (!modal) return;
        resetModalState();
        modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
        document.getElementById('admin-username').focus();
    }

    function closeAdminModal() {
        if (!modal) return;
        modal.classList.add('hidden');
        document.body.style.overflow = '';
        resetModalState();
    }

    function resetModalState() {
        stepCredentials.classList.remove('hidden');
        stepOtp.classList.add('hidden');

        credError.classList.add('hidden');
        credError.textContent = '';
        otpError.classList.add('hidden');
        otpError.textContent = '';
        otpSuccess.classList.add('hidden');
        otpSuccess.textContent = '';

        credForm.reset();
        otpForm.reset();
    }

    if (modalCloseBtn) {
        modalCloseBtn.addEventListener('click', closeAdminModal);
    }

    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeAdminModal();
            }
        });
    }

    // ─── 3. Credential Submission (Step 1) ─────────────────
    if (credForm) {
        credForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            credError.classList.add('hidden');

            const username = document.getElementById('admin-username').value.trim();
            const password = document.getElementById('admin-password').value;

            btnVerifyCred.disabled = true;
            btnVerifyCred.textContent = 'Verifying credentials...';

            try {
                const response = await fetch('/admin/verify-credentials', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password })
                });

                const data = await response.json();

                if (response.ok && data.success) {
                    // Transition to OTP step
                    stepCredentials.classList.add('hidden');
                    stepOtp.classList.remove('hidden');

                    otpNotice.innerHTML = `An OTP code has been sent to <strong>${data.masked_email || 'your email'}</strong>.`;

                    document.getElementById('admin-otp-input').focus();
                } else {
                    credError.textContent = data.message || 'Verification failed.';
                    credError.classList.remove('hidden');
                }
            } catch (err) {
                console.error(err);
                credError.textContent = 'Network error. Please try again.';
                credError.classList.remove('hidden');
            } finally {
                btnVerifyCred.disabled = false;
                btnVerifyCred.textContent = 'Verify Credentials & Send OTP';
            }
        });
    }

    // ─── 4. OTP Submission (Step 2) ─────────────────────────
    if (otpForm) {
        otpForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            otpError.classList.add('hidden');
            otpSuccess.classList.add('hidden');

            const otp = document.getElementById('admin-otp-input').value.trim();

            btnVerifyOtp.disabled = true;
            btnVerifyOtp.textContent = 'Verifying OTP...';

            try {
                const response = await fetch('/admin/verify-otp', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ otp })
                });

                const data = await response.json();

                if (response.ok && data.success) {
                    otpSuccess.textContent = 'OTP verified successfully! Access granted.';
                    otpSuccess.classList.remove('hidden');

                    setTimeout(() => {
                        window.location.href = data.redirect_url || '/admin/dashboard';
                    }, 600);
                } else {
                    otpError.textContent = data.message || 'Invalid or expired OTP.';
                    otpError.classList.remove('hidden');
                }
            } catch (err) {
                console.error(err);
                otpError.textContent = 'Network error. Please try again.';
                otpError.classList.remove('hidden');
            } finally {
                btnVerifyOtp.disabled = false;
                btnVerifyOtp.textContent = 'Verify OTP & Access Portal';
            }
        });
    }

    // ─── 5. Resend OTP ──────────────────────────────────────
    if (btnResendOtp) {
        btnResendOtp.addEventListener('click', async () => {
            const username = document.getElementById('admin-username').value.trim();
            const password = document.getElementById('admin-password').value;

            if (!username || !password) {
                otpError.textContent = 'Please re-enter credentials to resend OTP.';
                otpError.classList.remove('hidden');
                stepOtp.classList.add('hidden');
                stepCredentials.classList.remove('hidden');
                return;
            }

            btnResendOtp.disabled = true;
            btnResendOtp.textContent = 'Resending...';

            try {
                const response = await fetch('/admin/verify-credentials', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password })
                });

                const data = await response.json();

                if (response.ok && data.success) {
                    otpSuccess.textContent = 'A new OTP has been dispatched!';
                    otpSuccess.classList.remove('hidden');

                    setTimeout(() => otpSuccess.classList.add('hidden'), 4000);
                } else {
                    otpError.textContent = data.message || 'Failed to resend OTP.';
                    otpError.classList.remove('hidden');
                }
            } catch (err) {
                otpError.textContent = 'Error resending OTP.';
                otpError.classList.remove('hidden');
            } finally {
                btnResendOtp.disabled = false;
                btnResendOtp.textContent = 'Resend OTP';
            }
        });
    }

    // ─── Utility: Temporary Toast Alert ────────────────────
    function showTapToast(message) {
        let toast = document.getElementById('shield-tap-toast');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'shield-tap-toast';
            toast.className = 'shield-tap-toast';
            document.body.appendChild(toast);
        }

        toast.textContent = message;
        toast.classList.add('show');

        clearTimeout(toast._timeout);
        toast._timeout = setTimeout(() => {
            toast.classList.remove('show');
        }, 1500);
    }
});
