/**
 * User Registration JavaScript
 * Handles admin authorization and user face registration
 */

let adminSessionToken = null;
let adminData = null;
let currentStep = 1;
let userFormData = {};

document.addEventListener('DOMContentLoaded', () => {
    // Check if this is the first admin setup redirect
    checkAdminSetup();
    setupEventListeners();
});

async function checkAdminSetup() {
    try {
        const response = await fetch('/api/admin/check-first');
        const data = await response.json();
        
        if (data.is_first_admin) {
            // Show message about needing admin setup first
            showStep1Message('No admins registered yet. Please set up the first admin.', 'error');
            document.getElementById('start-admin-camera').disabled = true;
            
            setTimeout(() => {
                window.location.href = '/admin/setup';
            }, 2000);
        }
    } catch (error) {
        console.error('Error checking admin setup:', error);
    }
}

function setupEventListeners() {
    // Step 1: Admin Authorization
    document.getElementById('start-admin-camera')?.addEventListener('click', async () => {
        const started = await startCamera('admin-video');
        if (started) {
            document.getElementById('start-admin-camera').disabled = true;
            document.getElementById('admin-auth-btn').disabled = false;
        }
    });
    
    document.getElementById('admin-auth-btn')?.addEventListener('click', authorizeAdmin);
    
    // Step 2: User Details
    document.getElementById('user-form')?.addEventListener('submit', handleUserFormSubmit);
    
    // Step 3: Face Capture
    document.getElementById('start-user-camera')?.addEventListener('click', async () => {
        const started = await startCamera('user-video');
        if (started) {
            document.getElementById('start-user-camera').disabled = true;
            document.getElementById('capture-btn').disabled = false;
        }
    });
    
    document.getElementById('capture-btn')?.addEventListener('click', captureFaceImage);
    document.getElementById('clear-btn')?.addEventListener('click', clearCapturedImages);
    document.getElementById('register-btn')?.addEventListener('click', registerUser);
}

async function authorizeAdmin() {
    const btn = document.getElementById('admin-auth-btn');
    const msgDiv = document.getElementById('admin-auth-status');
    
    if (!btn) {
        console.error('Button not found');
        return;
    }
    
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Verifying...';
    if (msgDiv) {
        msgDiv.className = 'auth-status';
        msgDiv.textContent = '';
    }
    
    try {
        // Capture admin face
        const image = captureFrame('admin-video', 'admin-canvas');
        const spoofFrames = await captureMultipleFrames('admin-video', 'admin-canvas', 10, 100);
        
        const response = await fetch('/api/admin/authenticate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                image: image,
                spoof_frames: spoofFrames
            })
        });
        
        const data = await response.json();
        
        if (data.success && data.authenticated) {
            adminSessionToken = data.session_token;
            adminData = {
                name: data.admin_name,
                id: data.admin_id
            };
            
            if (msgDiv) {
                msgDiv.className = 'auth-status success';
                msgDiv.textContent = `Welcome, ${data.admin_name}! You are now authorized to register users.`;
            }
            
            // Update authorizing admin display
            const authAdmin = document.getElementById('authorizing-admin');
            if (authAdmin) authAdmin.textContent = data.admin_name;
            
            // Stop admin camera
            stopCamera();
            
            // Show user registration section
            setTimeout(() => {
                const adminAuthSection = document.getElementById('admin-auth-section');
                const userRegSection = document.getElementById('user-reg-section');
                if (adminAuthSection) adminAuthSection.classList.add('hidden');
                if (userRegSection) userRegSection.classList.remove('hidden');
            }, 1500);
        } else {
            if (msgDiv) {
                msgDiv.className = 'auth-status error';
                msgDiv.textContent = data.message || 'Admin authorization failed';
            }
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-fingerprint"></i> Authorize';
        }
    } catch (error) {
        if (msgDiv) {
            msgDiv.className = 'auth-status error';
            msgDiv.textContent = 'Error connecting to server';
        }
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-fingerprint"></i> Authorize';
    }
}

function handleUserFormSubmit(e) {
    e.preventDefault();
    
    // Validate form
    const employeeId = document.getElementById('employee-id').value.trim();
    const name = document.getElementById('user-name').value.trim();
    const email = document.getElementById('user-email').value.trim();
    const department = document.getElementById('department').value.trim();
    
    if (!employeeId || !name || !email) {
        showStep2Message('Please fill in all required fields', 'error');
        return;
    }
    
    // Store form data
    userFormData = {
        employee_id: employeeId,
        name: name,
        email: email,
        department: department
    };
    
    // Update step indicator
    document.querySelector('[data-step="2"]').classList.add('completed');
    document.querySelector('[data-step="2"]').classList.remove('active');
    document.querySelector('[data-step="3"]').classList.add('active');
    
    // Proceed to step 3
    goToStep(3);
    
    // Show user preview
    document.getElementById('preview-id').textContent = employeeId;
    document.getElementById('preview-name').textContent = name;
}

// Store captured images
let capturedImages = [];

function captureFaceImage() {
    const image = captureFrame('user-video', 'user-canvas');
    if (!image) {
        alert('Failed to capture image. Please ensure camera is active.');
        return;
    }
    
    capturedImages.push(image);
    
    // Update UI
    const countSpan = document.getElementById('capture-count');
    if (countSpan) {
        countSpan.textContent = capturedImages.length;
    }
    
    // Display captured image thumbnail
    const container = document.getElementById('captured-images');
    if (container) {
        const imgDiv = document.createElement('div');
        imgDiv.className = 'captured-thumbnail';
        imgDiv.innerHTML = `<img src="${image}" alt="Captured ${capturedImages.length}">`;
        container.appendChild(imgDiv);
    }
    
    // Enable clear button
    const clearBtn = document.getElementById('clear-btn');
    if (clearBtn) clearBtn.disabled = false;
    
    // Enable register button if we have at least 3 images
    const registerBtn = document.getElementById('register-btn');
    if (registerBtn && capturedImages.length >= 3) {
        registerBtn.disabled = false;
    }
    
    // Update capture button text
    const captureBtn = document.getElementById('capture-btn');
    if (captureBtn && capturedImages.length >= 5) {
        captureBtn.disabled = true;
    }
}

function clearCapturedImages() {
    capturedImages = [];
    
    // Update UI
    const countSpan = document.getElementById('capture-count');
    if (countSpan) countSpan.textContent = '0';
    
    const container = document.getElementById('captured-images');
    if (container) container.innerHTML = '';
    
    // Disable buttons
    const clearBtn = document.getElementById('clear-btn');
    if (clearBtn) clearBtn.disabled = true;
    
    const registerBtn = document.getElementById('register-btn');
    if (registerBtn) registerBtn.disabled = true;
    
    // Re-enable capture button
    const captureBtn = document.getElementById('capture-btn');
    if (captureBtn) captureBtn.disabled = false;
}

async function registerUser() {
    const btn = document.getElementById('register-btn');
    
    if (capturedImages.length < 3) {
        alert('Please capture at least 3 images');
        return;
    }
    
    // Get form values directly from the form
    const employeeId = document.getElementById('employee_id')?.value.trim();
    const name = document.getElementById('name')?.value.trim();
    const email = document.getElementById('email')?.value.trim();
    const department = document.getElementById('department')?.value.trim() || '';
    
    // Validate required fields
    if (!employeeId || !name || !email) {
        alert('Please fill in all required fields (Employee ID, Name, Email)');
        return;
    }
    
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Registering...';
    
    try {
        // Capture spoof frames for liveness check
        const spoofFrames = await captureMultipleFrames('user-video', 'user-canvas', 10, 100);
        
        // Send registration request
        const response = await fetch('/api/users/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                admin_session_token: adminSessionToken,
                employee_id: employeeId,
                name: name,
                email: email,
                department: department,
                images: capturedImages,
                spoof_frames: spoofFrames
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Stop camera
            stopCamera();
            
            // Show success message
            alert(`Registration successful!\n${name} has been registered.\nEmployee ID: ${employeeId}`);
            
            // Reset for next registration
            clearCapturedImages();
            document.getElementById('registration-form')?.reset();
            
            // Reset camera button
            document.getElementById('start-user-camera').disabled = false;
            document.getElementById('capture-btn').disabled = true;
            
        } else {
            alert(data.message || 'Registration failed');
        }
        
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-check"></i> Complete Registration';
        
    } catch (error) {
        console.error('Registration error:', error);
        alert('Error connecting to server');
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-check"></i> Complete Registration';
    }
}

function goToStep(step) {
    document.querySelectorAll('.step-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`step-${step}`).classList.add('active');
    currentStep = step;
}

function showStep1Message(msg, type) {
    const msgDiv = document.getElementById('admin-auth-message');
    msgDiv.className = `message ${type}`;
    msgDiv.textContent = msg;
}

function showStep2Message(msg, type) {
    const msgDiv = document.getElementById('user-form-message');
    if (msgDiv) {
        msgDiv.className = `message ${type}`;
        msgDiv.textContent = msg;
    }
}

function resetRegistration() {
    // Reset form
    document.getElementById('user-form')?.reset();
    userFormData = {};
    
    // Keep admin session but allow new registration
    goToStep(2);
    
    // Reset step indicators (keep step 1 completed)
    document.querySelector('[data-step="2"]')?.classList.remove('completed');
    document.querySelector('[data-step="2"]')?.classList.add('active');
    document.querySelector('[data-step="3"]')?.classList.remove('completed');
    document.querySelector('[data-step="3"]')?.classList.remove('active');
    
    // Reset buttons and captured images
    capturedImages = [];
    const countSpan = document.getElementById('capture-count');
    if (countSpan) countSpan.textContent = '0';
    
    const capturedContainer = document.getElementById('captured-images');
    if (capturedContainer) capturedContainer.innerHTML = '';
    
    document.getElementById('start-user-camera').disabled = false;
    document.getElementById('capture-btn').disabled = true;
    document.getElementById('clear-btn').disabled = true;
    document.getElementById('register-btn').disabled = true;
    
    // Hide progress
    document.getElementById('capture-progress')?.classList.add('hidden');
    
    // Close modal
    closeModal();
}

function fullReset() {
    adminSessionToken = null;
    adminData = null;
    resetRegistration();
    
    // Reset to step 1
    goToStep(1);
    
    // Reset all step indicators
    document.querySelectorAll('.step').forEach(step => {
        step.classList.remove('completed', 'active');
    });
    document.querySelector('[data-step="1"]').classList.add('active');
    
    // Reset admin section
    document.getElementById('admin-badge').innerHTML = `
        <i class="fas fa-lock"></i> Admin Authorization Required
    `;
    document.getElementById('admin-badge').classList.remove('success');
    document.getElementById('start-admin-camera').disabled = false;
    document.getElementById('authorize-btn').disabled = true;
    document.getElementById('authorize-btn').innerHTML = '<i class="fas fa-check-circle"></i> Authorize & Continue';
}

function showModal(type, title, message) {
    const modal = document.getElementById('message-modal');
    const icon = document.getElementById('modal-icon');
    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-message').textContent = message;
    
    icon.innerHTML = type === 'success' 
        ? '<i class="fas fa-check-circle" style="color: #10b981; font-size: 48px;"></i>'
        : '<i class="fas fa-times-circle" style="color: #ef4444; font-size: 48px;"></i>';
    
    modal.style.display = 'flex';
}

function closeModal() {
    document.getElementById('message-modal').style.display = 'none';
}

document.querySelector('.close-modal')?.addEventListener('click', closeModal);

// Add another user button in modal
document.getElementById('register-another-btn')?.addEventListener('click', resetRegistration);
