/**
 * Camera Utility Functions
 * Handles webcam access and image capture
 */

let currentStream = null;

/**
 * Start camera and display in video element
 * @param {string} videoElementId - ID of video element
 * @returns {Promise<boolean>} - Success status
 */
async function startCamera(videoElementId) {
    const video = document.getElementById(videoElementId);
    
    if (!video) {
        console.error('Video element not found:', videoElementId);
        return false;
    }
    
    try {
        // Stop any existing stream
        if (currentStream) {
            currentStream.getTracks().forEach(track => track.stop());
        }
        
        // Request camera access
        const stream = await navigator.mediaDevices.getUserMedia({
            video: {
                width: { ideal: 640 },
                height: { ideal: 480 },
                facingMode: 'user'
            },
            audio: false
        });
        
        currentStream = stream;
        video.srcObject = stream;
        
        return new Promise((resolve) => {
            video.onloadedmetadata = () => {
                video.play();
                resolve(true);
            };
        });
        
    } catch (error) {
        console.error('Camera access error:', error);
        alert('Could not access camera. Please ensure camera permissions are granted.');
        return false;
    }
}

/**
 * Stop camera stream
 */
function stopCamera() {
    if (currentStream) {
        currentStream.getTracks().forEach(track => track.stop());
        currentStream = null;
    }
}

/**
 * Capture frame from video as base64 image
 * @param {string} videoElementId - ID of video element
 * @param {string} canvasElementId - ID of canvas element
 * @returns {string|null} - Base64 image data URL or null
 */
function captureFrame(videoElementId, canvasElementId) {
    const video = document.getElementById(videoElementId);
    const canvas = document.getElementById(canvasElementId);
    
    if (!video || !canvas) {
        console.error('Video or canvas element not found');
        return null;
    }
    
    const ctx = canvas.getContext('2d');
    
    // Set canvas size to match video
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    
    // Draw mirrored (to match video display)
    ctx.save();
    ctx.scale(-1, 1);
    ctx.drawImage(video, -canvas.width, 0, canvas.width, canvas.height);
    ctx.restore();
    
    // Return as base64 JPEG
    return canvas.toDataURL('image/jpeg', 0.9);
}

/**
 * Capture multiple frames for anti-spoofing
 * @param {string} videoElementId - ID of video element
 * @param {string} canvasElementId - ID of canvas element
 * @param {number} count - Number of frames to capture
 * @param {number} interval - Interval between frames in ms
 * @returns {Promise<string[]>} - Array of base64 images
 */
async function captureMultipleFrames(videoElementId, canvasElementId, count = 10, interval = 100) {
    const frames = [];
    
    for (let i = 0; i < count; i++) {
        const frame = captureFrame(videoElementId, canvasElementId);
        if (frame) {
            frames.push(frame);
        }
        await new Promise(resolve => setTimeout(resolve, interval));
    }
    
    return frames;
}

/**
 * Check if camera is active
 * @returns {boolean}
 */
function isCameraActive() {
    return currentStream !== null && currentStream.active;
}
