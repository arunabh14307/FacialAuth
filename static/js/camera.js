/**
 * Camera Module — Webcam handling for face capture
 * Uses navigator.mediaDevices.getUserMedia API
 */

class CameraManager {
    constructor(videoElementId, options = {}) {
        this.videoElement = document.getElementById(videoElementId);
        this.stream = null;
        this.isActive = false;

        this.options = {
            width: options.width || 640,
            height: options.height || 480,
            facingMode: options.facingMode || 'user',
            ...options
        };

        // Create hidden canvas for frame capture
        this.canvas = document.createElement('canvas');
        this.canvas.width = this.options.width;
        this.canvas.height = this.options.height;
        this.ctx = this.canvas.getContext('2d');
    }

    /**
     * Start the webcam stream
     */
    async start() {
        try {
            const constraints = {
                video: {
                    width: { ideal: this.options.width },
                    height: { ideal: this.options.height },
                    facingMode: this.options.facingMode
                },
                audio: false
            };

            this.stream = await navigator.mediaDevices.getUserMedia(constraints);
            this.videoElement.srcObject = this.stream;

            await new Promise((resolve) => {
                this.videoElement.onloadedmetadata = () => {
                    this.videoElement.play();
                    resolve();
                };
            });

            this.isActive = true;
            return { success: true, message: 'Camera started' };
        } catch (error) {
            console.error('Camera error:', error);
            let message = 'Could not access camera.';

            if (error.name === 'NotAllowedError') {
                message = 'Camera permission denied. Please allow camera access.';
            } else if (error.name === 'NotFoundError') {
                message = 'No camera found. Please connect a webcam.';
            } else if (error.name === 'NotReadableError') {
                message = 'Camera is in use by another application.';
            }

            return { success: false, message };
        }
    }

    /**
     * Stop the webcam stream
     */
    stop() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        if (this.videoElement) {
            this.videoElement.srcObject = null;
        }
        this.isActive = false;
    }

    /**
     * Capture a single frame as base64 JPEG
     */
    captureFrame(quality = 0.92) {
        if (!this.isActive || !this.videoElement) {
            return null;
        }

        const width = (this.videoElement.videoWidth && this.videoElement.videoWidth > 0) ? this.videoElement.videoWidth : this.options.width;
        const height = (this.videoElement.videoHeight && this.videoElement.videoHeight > 0) ? this.videoElement.videoHeight : this.options.height;

        this.canvas.width = width;
        this.canvas.height = height;

        // Draw current frame (mirrored)
        this.ctx.save();
        this.ctx.scale(-1, 1);
        this.ctx.drawImage(this.videoElement, -width, 0, width, height);
        this.ctx.restore();

        // Convert to base64 JPEG
        return this.canvas.toDataURL('image/jpeg', quality);
    }

    /**
     * Capture frame without mirror (for server processing)
     */
    captureFrameNoMirror(quality = 0.92) {
        if (!this.isActive || !this.videoElement) {
            return null;
        }

        const width = (this.videoElement.videoWidth && this.videoElement.videoWidth > 0) ? this.videoElement.videoWidth : this.options.width;
        const height = (this.videoElement.videoHeight && this.videoElement.videoHeight > 0) ? this.videoElement.videoHeight : this.options.height;

        this.canvas.width = width;
        this.canvas.height = height;
        this.ctx.drawImage(this.videoElement, 0, 0, width, height);
        return this.canvas.toDataURL('image/jpeg', quality);
    }
}

/**
 * Show a status message in the UI
 */
function showStatus(containerId, message, type = 'info') {
    const container = document.getElementById(containerId);
    if (!container) return;

    const icons = {
        success: '✓',
        error: '✕',
        warning: '⚠',
        info: 'ℹ'
    };

    container.innerHTML = `
        <div class="status-panel ${type}">
            <span>${icons[type] || 'ℹ'}</span>
            <span>${message}</span>
        </div>
    `;
    container.classList.remove('hidden');
}

/**
 * Hide status message
 */
function hideStatus(containerId) {
    const container = document.getElementById(containerId);
    if (container) {
        container.classList.add('hidden');
    }
}

/**
 * POST JSON to an API endpoint
 */
async function apiPost(url, data) {
    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await response.json();
        return result;
    } catch (error) {
        console.error('API error:', error);
        return { success: false, message: 'Network error. Please try again.' };
    }
}

/**
 * Flash messages auto-dismiss
 */
document.addEventListener('DOMContentLoaded', () => {
    // Auto-dismiss flash messages after 5 seconds
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(msg => {
        setTimeout(() => {
            msg.style.animation = 'fadeInUp 0.3s ease reverse';
            setTimeout(() => msg.remove(), 300);
        }, 5000);

        msg.addEventListener('click', () => {
            msg.style.animation = 'fadeInUp 0.3s ease reverse';
            setTimeout(() => msg.remove(), 300);
        });
    });
});
