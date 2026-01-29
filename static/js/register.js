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
            document.getElementById('capture-face-btn').disabled = false;
        }
    });
    
    document.getElementById('capture-face-btn')?.addEventListener('click', registerUserFace);
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

async function registerUserFace() {
    const btn = document.getElementById('capture-face-btn');
    const msgDiv = document.getElementById('user-capture-message');
    const progressContainer = document.getElementById('capture-progress');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Capturing...';
    msgDiv.className = 'message';
    msgDiv.textContent = '';
    progressContainer.classList.remove('hidden');
    
    try {
        // Capture multiple frames for registration
        progressText.textContent = 'Capturing face images...';
        progressBar.style.width = '20%';
        
        const images = await captureMultipleFrames('user-video', 'user-canvas', 5, 500);
        const spoofFrames = await captureMultipleFrames('user-video', 'user-canvas', 15, 100);
        
        progressText.textContent = 'Processing...';
        progressBar.style.width = '50%';
        
        // Send registration request
        const response = await fetch('/api/users/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                admin_session_token: adminSessionToken,
                employee_id: userFormData.employee_id,
                name: userFormData.name,
                email: userFormData.email,
                department: userFormData.department,
                images: images,
                spoof_frames: spoofFrames
            })
        });
        
        progressBar.style.width = '80%';
        
        const data = await response.json();
        
        progressBar.style.width = '100%';
        
        if (data.success) {
            progressText.textContent = 'Complete!';
            
            // Update step indicator
            document.querySelector('[data-step="3"]').classList.add('completed');
            
            // Stop camera
            stopCamera();
            
            // Show success modal
            showModal('success', 'Registration Successful!', 
                `${userFormData.name} has been registered successfully.\nEmployee ID: ${userFormData.employee_id}`);
            
            // Reset after delay
            setTimeout(() => {
                resetRegistration();
            }, 3000);
        } else {
            progressContainer.classList.add('hidden');
            msgDiv.className = 'message error';
            msgDiv.textContent = data.message || 'Registration failed';
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-camera"></i> Capture & Register';
        }
    } catch (error) {
        progressContainer.classList.add('hidden');
        msgDiv.className = 'message error';
        msgDiv.textContent = 'Error connecting to server';
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-camera"></i> Capture & Register';
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
    document.querySelector('[data-step="2"]').classList.remove('completed');
    document.querySelector('[data-step="2"]').classList.add('active');
    document.querySelector('[data-step="3"]').classList.remove('completed');
    document.querySelector('[data-step="3"]').classList.remove('active');
    
    // Reset buttons
    document.getElementById('start-user-camera').disabled = false;
    document.getElementById('capture-face-btn').disabled = true;
    document.getElementById('capture-face-btn').innerHTML = '<i class="fas fa-camera"></i> Capture & Register';
    
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
