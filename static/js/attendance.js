/**
 * Attendance JavaScript
 * Handles automatic punch-in/out with face recognition
 * - Auto-detects whether to punch-in or punch-out
 * - Keeps camera on until face is detected
 * - Hides result until verification completes
 * - Discards attendance if punch-out is within 10-20 seconds of punch-in
 */

let isProcessing = false;
let cameraActive = false;
let retryCount = 0;
const MAX_RETRIES = 10;

document.addEventListener('DOMContentLoaded', () => {
    updateClock();
    setInterval(updateClock, 1000);
    setupEventListeners();
});

function updateClock() {
    const now = new Date();
    
    // Update time
    const timeEl = document.getElementById('current-time');
    if (timeEl) {
        timeEl.textContent = now.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: true
        });
    }
    
    // Update date
    const dateEl = document.getElementById('current-date');
    if (dateEl) {
        dateEl.textContent = now.toLocaleDateString('en-US', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    }
}

function setupEventListeners() {
    // Start camera button - starts camera and automatically processes attendance
    document.getElementById('start-camera')?.addEventListener('click', startAttendanceProcess);
}

async function startAttendanceProcess() {
    if (isProcessing) return;
    
    const btn = document.getElementById('start-camera');
    const processingStatus = document.getElementById('processing-status');
    const resultCard = document.getElementById('result-card');
    
    // Hide any previous results
    resultCard.classList.add('hidden');
    resultCard.classList.remove('show', 'success', 'error');
    
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Starting Camera...';
    isProcessing = true;
    retryCount = 0;
    
    try {
        // Start camera
        const started = await startCamera('attendance-video');
        if (!started) {
            displayResult({
                success: false,
                message: 'Could not access camera. Please ensure camera permissions are granted.'
            });
            resetButton();
            return;
        }
        
        cameraActive = true;
        
        // Show processing status
        processingStatus.classList.remove('hidden');
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Detecting Face...';
        
        // Wait for camera to stabilize
        await new Promise(resolve => setTimeout(resolve, 500));
        
        // Try to detect and verify face - keep trying until success or max retries
        await attemptFaceDetection();
        
    } catch (error) {
        console.error('Attendance error:', error);
        stopCameraAndReset();
        displayResult({
            success: false,
            message: 'Error during attendance process. Please try again.'
        });
    }
}

async function attemptFaceDetection() {
    const processingStatus = document.getElementById('processing-status');
    const statusText = document.getElementById('status-text');
    
    while (cameraActive && retryCount < MAX_RETRIES) {
        retryCount++;
        statusText.textContent = `Detecting face... (Attempt ${retryCount}/${MAX_RETRIES})`;
        
        // Capture image
        const image = captureFrame('attendance-video', 'attendance-canvas');
        
        if (!image) {
            await new Promise(resolve => setTimeout(resolve, 500));
            continue;
        }
        
        // Capture spoof frames
        statusText.textContent = 'Verifying liveness...';
        const spoofFrames = await captureMultipleFrames('attendance-video', 'attendance-canvas', 5, 50);
        
        // Send to server for verification
        statusText.textContent = 'Verifying identity...';
        
        try {
            const response = await fetch('/api/attendance/mark', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    image: image,
                    spoof_frames: spoofFrames
                })
            });
            
            const data = await response.json();
            
            // Check if face was detected
            if (data.success || (data.message && !data.message.toLowerCase().includes('no face'))) {
                // Face was detected (success or other error like "not recognized")
                stopCameraAndReset();
                processingStatus.classList.add('hidden');
                displayResult(data);
                return;
            }
            
            // No face detected, wait and retry
            statusText.textContent = 'No face detected. Please position your face in the frame...';
            await new Promise(resolve => setTimeout(resolve, 1000));
            
        } catch (error) {
            console.error('API error:', error);
            statusText.textContent = 'Connection error. Retrying...';
            await new Promise(resolve => setTimeout(resolve, 1000));
        }
    }
    
    // Max retries reached
    stopCameraAndReset();
    processingStatus.classList.add('hidden');
    displayResult({
        success: false,
        message: 'Could not detect face after multiple attempts. Please ensure good lighting and face visibility.'
    });
}

function stopCameraAndReset() {
    cameraActive = false;
    stopCamera();
    resetButton();
}

function resetButton() {
    const btn = document.getElementById('start-camera');
    btn.disabled = false;
    btn.innerHTML = '<i class="fas fa-video"></i> Start Camera & Mark Attendance';
    isProcessing = false;
}

function displayResult(data) {
    const resultCard = document.getElementById('result-card');
    const resultIcon = document.getElementById('result-icon');
    const resultTitle = document.getElementById('result-title');
    const resultMessage = document.getElementById('result-message');
    
    // Get individual result fields
    const resultName = document.getElementById('result-name');
    const resultEmployeeId = document.getElementById('result-employee-id');
    const resultDepartment = document.getElementById('result-department');
    const resultAction = document.getElementById('result-action');
    const resultTime = document.getElementById('result-time');
    const resultConfidence = document.getElementById('result-confidence');
    const resultHours = document.getElementById('result-hours');
    const hoursWorkedRow = document.getElementById('hours-worked-row');
    
    if (data.success) {
        resultCard.className = 'result-card success show';
        resultCard.classList.remove('hidden');
        resultIcon.innerHTML = '<i class="fas fa-check-circle"></i>';
        if (resultTitle) resultTitle.textContent = 'Success!';
        if (resultMessage) resultMessage.textContent = data.message || '';
        
        // Update individual fields
        if (resultName) resultName.textContent = data.name || '-';
        if (resultEmployeeId) resultEmployeeId.textContent = data.employee_id || '-';
        if (resultDepartment) resultDepartment.textContent = data.department || '-';
        if (resultAction) resultAction.textContent = data.action || '-';
        if (resultTime) resultTime.textContent = data.time ? formatTime(data.time) : '-';
        if (resultConfidence) resultConfidence.textContent = data.confidence ? `${(data.confidence * 100).toFixed(1)}%` : '-';
        
        // Show hours worked for punch-out
        if (data.hours_worked && hoursWorkedRow && resultHours) {
            resultHours.textContent = `${data.hours_worked} hours`;
            hoursWorkedRow.style.display = 'block';
        } else if (hoursWorkedRow) {
            hoursWorkedRow.style.display = 'none';
        }
        
    } else {
        resultCard.className = 'result-card error show';
        resultCard.classList.remove('hidden');
        resultIcon.innerHTML = '<i class="fas fa-times-circle"></i>';
        if (resultTitle) resultTitle.textContent = 'Failed';
        if (resultMessage) resultMessage.textContent = data.message || 'Unable to process attendance';
        
        // Clear fields on error
        if (resultName) resultName.textContent = '-';
        if (resultEmployeeId) resultEmployeeId.textContent = '-';
        if (resultDepartment) resultDepartment.textContent = '-';
        if (resultAction) resultAction.textContent = '-';
        if (resultTime) resultTime.textContent = '-';
        if (resultConfidence) resultConfidence.textContent = '-';
        if (hoursWorkedRow) hoursWorkedRow.style.display = 'none';
    }
    
    // Auto-hide after 15 seconds
    setTimeout(() => {
        resultCard.classList.remove('show');
        resultCard.classList.add('hidden');
    }, 15000);
}

function formatTime(timeString) {
    try {
        // Handle both ISO format and simple datetime format
        const date = new Date(timeString);
        if (isNaN(date.getTime())) {
            return timeString;
        }
        return date.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            hour12: true
        });
    } catch {
        return timeString;
    }
}

// Keyboard shortcut - Space to start attendance
document.addEventListener('keydown', (e) => {
    if (e.code === 'Space' && !e.target.matches('input, textarea') && !isProcessing) {
        e.preventDefault();
        startAttendanceProcess();
    }
});
