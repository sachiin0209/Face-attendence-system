/**
 * Admin Setup JavaScript
 * Handles first admin registration (no authorization required)
 */

document.addEventListener('DOMContentLoaded', async () => {
    // Verify this is actually first admin setup
    const response = await fetch('/api/admin/check-first');
    const data = await response.json();
    
    if (!data.is_first_admin) {
        window.location.href = '/admin';
        return;
    }
    
    setupEventListeners();
});

function setupEventListeners() {
    // Camera controls
    document.getElementById('start-camera')?.addEventListener('click', async () => {
        const started = await startCamera('setup-video');
        if (started) {
            document.getElementById('start-camera').disabled = true;
            document.getElementById('register-btn').disabled = false;
        }
    });
    
    // Register button
    document.getElementById('register-btn')?.addEventListener('click', registerFirstAdmin);
}

async function registerFirstAdmin() {
    const btn = document.getElementById('register-btn');
    const msgDiv = document.getElementById('setup-message');
    const progressContainer = document.getElementById('capture-progress');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    
    // Validate form
    const adminId = document.getElementById('admin-id').value.trim();
    const name = document.getElementById('admin-name').value.trim();
    const email = document.getElementById('admin-email').value.trim();
    
    if (!adminId || !name || !email) {
        msgDiv.className = 'message error';
        msgDiv.textContent = 'Please fill in all required fields';
        return;
    }
    
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Registering...';
    msgDiv.className = 'message';
    msgDiv.textContent = '';
    progressContainer.classList.remove('hidden');
    
    try {
        // Capture face images
        progressText.textContent = 'Capturing face images...';
        progressBar.style.width = '20%';
        
        const images = await captureMultipleFrames('setup-video', 'setup-canvas', 5, 500);
        const spoofFrames = await captureMultipleFrames('setup-video', 'setup-canvas', 15, 100);
        
        progressText.textContent = 'Processing...';
        progressBar.style.width = '50%';
        
        const response = await fetch('/api/admin/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                admin_id: adminId,
                name: name,
                email: email,
                images: images,
                spoof_frames: spoofFrames
            })
        });
        
        progressBar.style.width = '80%';
        
        const data = await response.json();
        
        progressBar.style.width = '100%';
        
        if (data.success) {
            progressText.textContent = 'Complete!';
            
            msgDiv.className = 'message success';
            msgDiv.textContent = 'Admin registered successfully! Redirecting to admin panel...';
            
            // Stop camera
            stopCamera();
            
            // Redirect after delay
            setTimeout(() => {
                window.location.href = '/admin';
            }, 2000);
        } else {
            progressContainer.classList.add('hidden');
            msgDiv.className = 'message error';
            msgDiv.textContent = data.message || 'Registration failed';
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-user-shield"></i> Register as First Admin';
        }
    } catch (error) {
        progressContainer.classList.add('hidden');
        msgDiv.className = 'message error';
        msgDiv.textContent = 'Error connecting to server';
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-user-shield"></i> Register as First Admin';
    }
}
