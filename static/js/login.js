/**
 * Login Page JavaScript
 * Handles the 2-step login flow: face detection → gesture verification
 */

document.addEventListener('DOMContentLoaded', () => {
    const startBtn = document.getElementById('start-login-btn');
    const statusContainer = document.getElementById('status-container');
    const gestureSection = document.getElementById('gesture-section');
    const faceSection = document.getElementById('face-section');

    let camera = null;
    let gestureCheckInterval = null;
    let gestureTimeLeft = 10;
    let gestureTimerInterval = null;

    // Step management
    function activateStep(stepNum) {
        document.querySelectorAll('.step').forEach(s => s.classList.remove('active', 'completed'));
        document.querySelectorAll('.step-connector').forEach(c => c.classList.remove('active'));

        for (let i = 1; i < stepNum; i++) {
            document.getElementById(`step-${i}`)?.classList.add('completed');
        }
        document.getElementById(`step-${stepNum}`)?.classList.add('active');

        if (stepNum >= 2) {
            document.querySelector('.step-connector')?.classList.add('active');
        }
    }

    // Start login: Initialize camera and detect face
    if (startBtn) {
        startBtn.onclick = async () => {
            startBtn.disabled = true;
            startBtn.innerHTML = '<span class="spinner" style="width:18px;height:18px;border-width:2px;margin:0;"></span> Starting camera...';

            camera = new CameraManager('login-video');
            const result = await camera.start();

            if (!result.success) {
                showStatus('status-container', result.message, 'error');
                startBtn.disabled = false;
                startBtn.textContent = '🔐 Start Authentication';
                return;
            }

            // Update camera status indicator
            const statusEl = document.getElementById('camera-status');
            if (statusEl) {
                statusEl.textContent = 'Camera Active';
                statusEl.classList.add('active');
            }

            activateStep(1);
            showStatus('status-container', 'Camera ready! Looking for your face...', 'info');

            startBtn.textContent = '📸 Capture & Identify';
            startBtn.disabled = false;

            // Change button to capture mode
            startBtn.onclick = captureAndIdentify;
        };
    }

    async function captureAndIdentify() {
        if (!camera || !camera.isActive) {
            showStatus('status-container', 'Camera is not ready.', 'error');
            return;
        }

        startBtn.disabled = true;
        startBtn.innerHTML = '<span class="spinner" style="width:18px;height:18px;border-width:2px;margin:0;"></span> Identifying...';

        const frame = camera.captureFrameNoMirror();
        if (!frame) {
            showStatus('status-container', 'Failed to capture image.', 'error');
            startBtn.disabled = false;
            startBtn.textContent = '📸 Capture & Identify';
            return;
        }

        const result = await apiPost('/api/login/detect', { image: frame });

        if (result.success) {
            // Face matched — show gesture challenge
            activateStep(2);
            showStatus('status-container', result.message, 'success');

            if (faceSection) faceSection.classList.add('hidden');
            if (gestureSection) gestureSection.classList.remove('hidden');

            showGestureChallenge(result);
        } else {
            showStatus('status-container', result.message, 'error');
            startBtn.disabled = false;
            startBtn.textContent = '📸 Capture & Identify';
        }
    }

    function showGestureChallenge(data) {
        const gestureEmoji = document.getElementById('gesture-emoji');
        const gestureName = document.getElementById('gesture-name');
        const gestureInstruction = document.getElementById('gesture-instruction');
        const gestureTimer = document.getElementById('gesture-timer');
        const verifyBtn = document.getElementById('verify-gesture-btn');

        const emojis = {
            'smile': '😊',
            'blink': '😑',
            'look_left': '👈',
            'look_right': '👉',
            'look_up': '👆',
            'look_down': '👇'
        };

        if (gestureEmoji) gestureEmoji.textContent = emojis[data.gesture] || '🎯';
        if (gestureName) gestureName.textContent = data.gesture_display;
        if (gestureInstruction) gestureInstruction.textContent = data.gesture_instruction;

        // Start timer
        gestureTimeLeft = 10;
        if (gestureTimer) gestureTimer.textContent = gestureTimeLeft;

        gestureTimerInterval = setInterval(() => {
            gestureTimeLeft--;
            if (gestureTimer) gestureTimer.textContent = gestureTimeLeft;

            if (gestureTimeLeft <= 0) {
                clearInterval(gestureTimerInterval);
                clearInterval(gestureCheckInterval);
                showStatus('status-container', 'Time expired! Please try again.', 'error');
                resetLogin();
            }
        }, 1000);

        // Auto-check gesture every 1.5 seconds
        gestureCheckInterval = setInterval(async () => {
            await checkGesture();
        }, 1500);

        // Manual verify button
        if (verifyBtn) {
            verifyBtn.onclick = async () => {
                verifyBtn.disabled = true;
                await checkGesture();
                verifyBtn.disabled = false;
            };
        }
    }

    async function checkGesture() {
        if (!camera || !camera.isActive) return;

        const frame = camera.captureFrameNoMirror();
        if (!frame) return;

        const result = await apiPost('/api/login/gesture', { image: frame });

        if (result.success) {
            // Gesture verified — authentication complete!
            clearInterval(gestureCheckInterval);
            clearInterval(gestureTimerInterval);

            camera.stop();

            // Show success
            gestureSection.innerHTML = `
                <div class="success-animation">
                    <div class="success-checkmark">✓</div>
                    <h3>Authentication Successful!</h3>
                    <p class="mt-1" style="color: var(--text-secondary);">${result.message}</p>
                    <p class="mt-2" style="color: var(--text-muted); font-size: 0.9rem;">Redirecting to dashboard...</p>
                </div>
            `;

            showStatus('status-container', 'Access granted! Redirecting...', 'success');

            // Redirect after animation
            setTimeout(() => {
                window.location.href = result.redirect || '/dashboard';
            }, 2000);
        } else if (result.message) {
            showStatus('status-container', result.message, 'warning');
        }
    }

    function resetLogin() {
        clearInterval(gestureCheckInterval);
        clearInterval(gestureTimerInterval);

        if (camera) camera.stop();

        if (faceSection) faceSection.classList.remove('hidden');
        if (gestureSection) gestureSection.classList.add('hidden');

        activateStep(1);

        if (startBtn) {
            startBtn.disabled = false;
            startBtn.textContent = '🔐 Start Authentication';
            startBtn.onclick = async () => {
                startBtn.disabled = true;
                camera = new CameraManager('login-video');
                const result = await camera.start();
                if (result.success) {
                    const statusEl = document.getElementById('camera-status');
                    if (statusEl) {
                        statusEl.textContent = 'Camera Active';
                        statusEl.classList.add('active');
                    }
                    startBtn.textContent = '📸 Capture & Identify';
                    startBtn.disabled = false;
                    startBtn.onclick = captureAndIdentify;
                    showStatus('status-container', 'Camera ready! Looking for your face...', 'info');
                } else {
                    showStatus('status-container', result.message, 'error');
                    startBtn.disabled = false;
                    startBtn.textContent = '🔐 Start Authentication';
                }
            };
        }
    }

    // Retry button
    const retryBtn = document.getElementById('retry-btn');
    if (retryBtn) {
        retryBtn.addEventListener('click', resetLogin);
    }

    // Cleanup on page leave
    window.addEventListener('beforeunload', () => {
        clearInterval(gestureCheckInterval);
        clearInterval(gestureTimerInterval);
        if (camera) camera.stop();
    });
});
