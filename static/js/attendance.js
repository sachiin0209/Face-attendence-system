/**
 * Attendance JavaScript
 * Handles punch-in/out with face recognition
 */

let currentMode = 'in';
let lastPunchInfo = null;

document.addEventListener('DOMContentLoaded', () => {
    updateClock();
    setInterval(updateClock, 1000);
    setupEventListeners();
    checkUserInfo();
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
    // Mode toggle
    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentMode = btn.dataset.mode;
            updateModeDisplay();
        });
    });
    
    // Camera controls
    document.getElementById('start-camera')?.addEventListener('click', async () => {
        const started = await startCamera('attendance-video');
        if (started) {
            document.getElementById('start-camera').disabled = true;
            document.getElementById('punch-in-btn').disabled = false;
            document.getElementById('punch-out-btn').disabled = false;
        }
    });
    
    // Punch buttons
    document.getElementById('punch-in-btn')?.addEventListener('click', () => processPunch('in'));
    document.getElementById('punch-out-btn')?.addEventListener('click', () => processPunch('out'));
}

function updateModeDisplay() {
    const modeTitle = document.getElementById('mode-title');
    const punchBtn = document.getElementById('punch-btn');
    
    if (currentMode === 'in') {
        modeTitle.innerHTML = '<i class="fas fa-sign-in-alt"></i> Punch In';
        punchBtn.innerHTML = '<i class="fas fa-fingerprint"></i> Punch In';
        punchBtn.classList.remove('punch-out');
        punchBtn.classList.add('punch-in');
    } else {
        modeTitle.innerHTML = '<i class="fas fa-sign-out-alt"></i> Punch Out';
        punchBtn.innerHTML = '<i class="fas fa-fingerprint"></i> Punch Out';
        punchBtn.classList.remove('punch-in');
        punchBtn.classList.add('punch-out');
    }
}

async function processPunch(mode) {
    const btn = document.getElementById(mode === 'in' ? 'punch-in-btn' : 'punch-out-btn');
    const resultCard = document.getElementById('result-card');
    
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
    
    // Hide previous result
    resultCard.className = 'result-card';
    
    try {
        // Capture frames (reduced for speed - 5 frames, 50ms interval)
        const image = captureFrame('attendance-video', 'attendance-canvas');
        
        // Check if image capture was successful
        if (!image) {
            displayResult({
                success: false,
                message: 'Could not capture image. Please ensure camera is active and try again.'
            });
            btn.disabled = false;
            btn.innerHTML = mode === 'in' 
                ? '<i class="fas fa-sign-in-alt"></i> Punch In'
                : '<i class="fas fa-sign-out-alt"></i> Punch Out';
            return;
        }
        
        const spoofFrames = await captureMultipleFrames('attendance-video', 'attendance-canvas', 5, 50);
        
        const response = await fetch(`/api/attendance/${mode === 'in' ? 'punch-in' : 'punch-out'}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                image: image,
                spoof_frames: spoofFrames
            })
        });
        
        const data = await response.json();
        
        displayResult(data);
        
    } catch (error) {
        console.error('Punch error:', error);
        displayResult({
            success: false,
            message: 'Error connecting to server'
        });
    }
    
    btn.disabled = false;
    btn.innerHTML = mode === 'in' 
        ? '<i class="fas fa-sign-in-alt"></i> Punch In'
        : '<i class="fas fa-sign-out-alt"></i> Punch Out';
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
        if (resultTime) resultTime.textContent = data.time ? formatTime(data.time) : '-';
        if (resultConfidence) resultConfidence.textContent = data.confidence ? `${(data.confidence * 100).toFixed(1)}%` : '-';
        
        // Show hours worked for punch-out
        if (data.hours_worked && hoursWorkedRow && resultHours) {
            resultHours.textContent = data.hours_worked;
            hoursWorkedRow.style.display = 'block';
        } else if (hoursWorkedRow) {
            hoursWorkedRow.style.display = 'none';
        }
        
        // Store last punch info
        lastPunchInfo = data;
        
    } else {
        resultCard.className = 'result-card error show';
        resultCard.classList.remove('hidden');
        resultIcon.innerHTML = '<i class="fas fa-times-circle"></i>';
        if (resultTitle) resultTitle.textContent = 'Failed';
        if (resultMessage) resultMessage.textContent = data.message || 'Unable to process punch';
        
        // Clear fields on error
        if (resultName) resultName.textContent = '-';
        if (resultEmployeeId) resultEmployeeId.textContent = '-';
        if (resultDepartment) resultDepartment.textContent = '-';
        if (resultTime) resultTime.textContent = '-';
        if (resultConfidence) resultConfidence.textContent = '-';
    }
    
    // Auto-hide after 10 seconds
    setTimeout(() => {
        resultCard.classList.remove('show');
    }, 10000);
}

function formatTime(isoString) {
    const date = new Date(isoString);
    return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: true
    });
}

function updateUserInfo(data) {
    const userInfoSection = document.getElementById('user-info-section');
    if (userInfoSection) {
        document.getElementById('info-name').textContent = data.name;
        document.getElementById('info-id').textContent = data.employee_id;
        document.getElementById('info-punch-time').textContent = formatTime(data.time);
        userInfoSection.classList.remove('hidden');
    }
}

function checkUserInfo() {
    // Check localStorage for recent punch info
    const savedInfo = localStorage.getItem('lastPunchInfo');
    if (savedInfo) {
        try {
            const info = JSON.parse(savedInfo);
            const punchTime = new Date(info.time);
            const now = new Date();
            
            // Only show if punched in today
            if (punchTime.toDateString() === now.toDateString() && info.type === 'punch_in') {
                updateUserInfo(info);
            }
        } catch {}
    }
}

// Quick lookup functionality
async function quickLookup() {
    const employeeId = prompt('Enter Employee ID for quick lookup:');
    if (!employeeId) return;
    
    try {
        const response = await fetch(`/api/attendance/status/${employeeId}`);
        const data = await response.json();
        
        if (data.success) {
            alert(`Employee: ${data.name}\nStatus: ${data.status}\nLast Punch: ${data.last_punch_time || 'N/A'}`);
        } else {
            alert(data.message || 'Employee not found');
        }
    } catch {
        alert('Error fetching status');
    }
}

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Space to punch
    if (e.code === 'Space' && !e.target.matches('input, textarea')) {
        e.preventDefault();
        document.getElementById('punch-btn')?.click();
    }
    
    // I for punch in
    if (e.code === 'KeyI' && !e.target.matches('input, textarea')) {
        document.querySelector('[data-mode="in"]')?.click();
    }
    
    // O for punch out
    if (e.code === 'KeyO' && !e.target.matches('input, textarea')) {
        document.querySelector('[data-mode="out"]')?.click();
    }
});
