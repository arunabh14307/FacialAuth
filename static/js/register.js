/**
 * Registration Page JavaScript
 * Handles the user registration flow with face capture
 */

document.addEventListener('DOMContentLoaded', () => {
    const registerForm = document.getElementById('register-form');
    const cameraSection = document.getElementById('camera-section');
    const captureBtn = document.getElementById('capture-btn');
    const retakeBtn = document.getElementById('retake-btn');
    const submitBtn = document.getElementById('submit-btn');
    const nextStepBtn = document.getElementById('next-step-btn');
    const capturedPreview = document.getElementById('captured-preview');
    const statusContainer = document.getElementById('status-container');

    let camera = null;
    let capturedImage = null;

    // Step 1: Form → Step 2: Camera → Step 3: Confirm
    const steps = {
        form: document.getElementById('step-form'),
        camera: document.getElementById('step-camera'),
        confirm: document.getElementById('step-confirm')
    };

    function showStep(stepName) {
        Object.values(steps).forEach(s => s && s.classList.add('hidden'));
        if (steps[stepName]) {
            steps[stepName].classList.remove('hidden');
        }

        // Update step indicators
        document.querySelectorAll('.step').forEach(s => s.classList.remove('active', 'completed'));

        if (stepName === 'form') {
            document.getElementById('step-1')?.classList.add('active');
        } else if (stepName === 'camera') {
            document.getElementById('step-1')?.classList.add('completed');
            document.getElementById('step-2')?.classList.add('active');
            document.querySelector('.step-connector')?.classList.add('active');
        } else if (stepName === 'confirm') {
            document.getElementById('step-1')?.classList.add('completed');
            document.getElementById('step-2')?.classList.add('completed');
            document.getElementById('step-3')?.classList.add('active');
            document.querySelectorAll('.step-connector').forEach(c => c.classList.add('active'));
        }
    }

    // Next: Move to camera step
    if (nextStepBtn) {
        nextStepBtn.addEventListener('click', async () => {
            const name = document.getElementById('reg-name')?.value.trim();
            const email = document.getElementById('reg-email')?.value.trim();

            if (!name) {
                showStatus('status-container', 'Please enter your name.', 'warning');
                return;
            }
            if (!email || !email.includes('@')) {
                showStatus('status-container', 'Please enter a valid email.', 'warning');
                return;
            }

            hideStatus('status-container');
            showStep('camera');

            // Start camera
            camera = new CameraManager('reg-video');
            const result = await camera.start();

            if (!result.success) {
                showStatus('status-container', result.message, 'error');
            } else {
                showStatus('status-container', 'Camera ready! Position your face in the frame and click "Capture Face".', 'info');
            }
        });
    }

    // Capture face
    if (captureBtn) {
        captureBtn.addEventListener('click', () => {
            if (!camera || !camera.isActive) {
                showStatus('status-container', 'Camera is not ready.', 'error');
                return;
            }

            // Countdown animation
            captureBtn.disabled = true;
            captureBtn.textContent = '3...';

            setTimeout(() => {
                captureBtn.textContent = '2...';
                setTimeout(() => {
                    captureBtn.textContent = '1...';
                    setTimeout(() => {
                        // Capture
                        capturedImage = camera.captureFrameNoMirror();

                        if (capturedImage) {
                            // Show preview
                            if (capturedPreview) {
                                capturedPreview.src = capturedImage;
                            }
                            camera.stop();
                            showStep('confirm');
                            showStatus('status-container', 'Face captured! Review the image and click "Register" to complete.', 'success');
                        } else {
                            showStatus('status-container', 'Failed to capture image. Please try again.', 'error');
                            captureBtn.disabled = false;
                            captureBtn.textContent = '📸 Capture Face';
                        }
                    }, 800);
                }, 800);
            }, 800);
        });
    }

    // Retake
    if (retakeBtn) {
        retakeBtn.addEventListener('click', async () => {
            capturedImage = null;
            captureBtn.disabled = false;
            captureBtn.textContent = '📸 Capture Face';
            showStep('camera');

            camera = new CameraManager('reg-video');
            const result = await camera.start();
            if (!result.success) {
                showStatus('status-container', result.message, 'error');
            } else {
                hideStatus('status-container');
            }
        });
    }

    // Submit registration
    if (submitBtn) {
        submitBtn.addEventListener('click', async () => {
            const name = document.getElementById('reg-name')?.value.trim();
            const email = document.getElementById('reg-email')?.value.trim();

            if (!capturedImage) {
                showStatus('status-container', 'No face image captured.', 'error');
                return;
            }

            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner" style="width:18px;height:18px;border-width:2px;margin:0;"></span> Registering...';

            const result = await apiPost('/api/register', {
                name: name,
                email: email,
                image: capturedImage
            });

            if (result.success) {
                showStep('confirm');
                document.getElementById('step-confirm').innerHTML = `
                    <div class="success-animation">
                        <div class="success-checkmark">✓</div>
                        <h3>Registration Successful!</h3>
                        <p class="mt-1" style="color: var(--text-secondary);">${result.message}</p>
                        <a href="/login" class="btn btn-primary btn-lg mt-3">Proceed to Login →</a>
                    </div>
                `;
                hideStatus('status-container');
            } else {
                showStatus('status-container', result.message, 'error');
                submitBtn.disabled = false;
                submitBtn.innerHTML = '✓ Register';
            }
        });
    }

    // Initialize
    showStep('form');
});
