/**
 * Admin Panel JavaScript
 * Handles admin authentication and management
 */

let adminSessionToken = null;
let sessionTimer = null;
let sessionEndTime = null;

// Check if admin setup is needed
document.addEventListener('DOMContentLoaded', async () => {
    const response = await fetch('/api/admin/check-first');
    const data = await response.json();
    
    if (data.is_first_admin) {
        window.location.href = '/admin/setup';
        return;
    }
    
    // Check for existing session in localStorage
    const savedToken = localStorage.getItem('adminSessionToken');
    if (savedToken) {
        const verified = await verifySession(savedToken);
        if (verified) {
            adminSessionToken = savedToken;
            showAdminPanel();
            loadAllData();
        }
    }
    
    setupEventListeners();
});

function setupEventListeners() {
    // Camera controls
    document.getElementById('start-auth-camera')?.addEventListener('click', async () => {
        const started = await startCamera('auth-video');
        if (started) {
            document.getElementById('start-auth-camera').disabled = true;
            document.getElementById('authenticate-btn').disabled = false;
        }
    });
    
    // Authenticate button
    document.getElementById('authenticate-btn')?.addEventListener('click', authenticateAdmin);
    
    // Logout button
    document.getElementById('logout-btn')?.addEventListener('click', logout);
    
    // Tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });
}

async function authenticateAdmin() {
    const btn = document.getElementById('authenticate-btn');
    const msgDiv = document.getElementById('auth-message');
    
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Authenticating...';
    msgDiv.className = 'auth-message';
    msgDiv.textContent = '';
    
    try {
        // Capture frame and spoof frames
        const image = captureFrame('auth-video', 'auth-canvas');
        const spoofFrames = await captureMultipleFrames('auth-video', 'auth-canvas', 10, 100);
        
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
            localStorage.setItem('adminSessionToken', adminSessionToken);
            
            msgDiv.className = 'auth-message success';
            msgDiv.textContent = data.message;
            
            // Start session timer
            startSessionTimer(data.expires_in);
            
            setTimeout(() => {
                stopCamera();
                showAdminPanel();
                loadAllData();
            }, 1000);
        } else {
            msgDiv.className = 'auth-message error';
            msgDiv.textContent = data.message || 'Authentication failed';
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-fingerprint"></i> Authenticate';
        }
    } catch (error) {
        msgDiv.className = 'auth-message error';
        msgDiv.textContent = 'Error connecting to server';
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-fingerprint"></i> Authenticate';
    }
}

async function verifySession(token) {
    try {
        const response = await fetch('/api/admin/verify-session', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_token: token })
        });
        
        const data = await response.json();
        
        if (data.valid) {
            document.getElementById('admin-name').textContent = data.name;
            startSessionTimer(data.remaining_time);
            return true;
        }
        
        localStorage.removeItem('adminSessionToken');
        return false;
    } catch {
        return false;
    }
}

function startSessionTimer(seconds) {
    sessionEndTime = Date.now() + (seconds * 1000);
    
    if (sessionTimer) clearInterval(sessionTimer);
    
    sessionTimer = setInterval(() => {
        const remaining = Math.max(0, Math.floor((sessionEndTime - Date.now()) / 1000));
        const minutes = Math.floor(remaining / 60);
        const secs = remaining % 60;
        
        const timerEl = document.getElementById('session-timer');
        if (timerEl) {
            timerEl.textContent = `${minutes}:${secs.toString().padStart(2, '0')}`;
        }
        
        if (remaining <= 0) {
            clearInterval(sessionTimer);
            logout();
        } else if (remaining <= 60) {
            // Extend session if active
            extendSession();
        }
    }, 1000);
}

async function extendSession() {
    if (!adminSessionToken) return;
    
    try {
        const response = await fetch('/api/admin/extend-session', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_token: adminSessionToken })
        });
        
        const data = await response.json();
        if (data.success) {
            sessionEndTime = Date.now() + (data.expires_in * 1000);
        }
    } catch (error) {
        console.error('Failed to extend session');
    }
}

async function logout() {
    if (adminSessionToken) {
        try {
            await fetch('/api/admin/logout', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_token: adminSessionToken })
            });
        } catch {}
    }
    
    adminSessionToken = null;
    localStorage.removeItem('adminSessionToken');
    if (sessionTimer) clearInterval(sessionTimer);
    
    window.location.reload();
}

function showAdminPanel() {
    document.getElementById('auth-section').classList.add('hidden');
    document.getElementById('admin-panel').classList.remove('hidden');
    document.getElementById('session-status').classList.remove('hidden');
}

function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });
    
    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.toggle('active', content.id === `${tabName}-tab`);
    });
}

async function loadAllData() {
    loadUsers();
    loadAdmins();
    loadActivityLog();
}

async function loadUsers() {
    const tbody = document.getElementById('users-tbody');
    tbody.innerHTML = '<tr><td colspan="7" class="loading">Loading...</td></tr>';
    
    try {
        const response = await fetch('/api/users/list');
        const data = await response.json();
        
        if (data.success && data.users.length > 0) {
            tbody.innerHTML = data.users.map(user => `
                <tr>
                    <td>${user.employee_id}</td>
                    <td>${user.name}</td>
                    <td>${user.email}</td>
                    <td>${user.department || '-'}</td>
                    <td>${user.registered_by || '-'}</td>
                    <td>
                        <span class="badge ${user.is_registered ? 'badge-success' : 'badge-warning'}">
                            ${user.is_registered ? 'Registered' : 'Pending'}
                        </span>
                    </td>
                    <td>
                        <button class="btn btn-sm btn-danger" onclick="deleteUser('${user.employee_id}')">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="7" class="empty">No users registered</td></tr>';
        }
    } catch (error) {
        tbody.innerHTML = '<tr><td colspan="7" class="empty">Error loading users</td></tr>';
    }
}

async function loadAdmins() {
    const tbody = document.getElementById('admins-tbody');
    tbody.innerHTML = '<tr><td colspan="6" class="loading">Loading...</td></tr>';
    
    try {
        const response = await fetch('/api/admin/list');
        const data = await response.json();
        
        if (data.success && data.admins.length > 0) {
            tbody.innerHTML = data.admins.map(admin => `
                <tr>
                    <td>${admin.admin_id}</td>
                    <td>${admin.name}</td>
                    <td>${admin.email}</td>
                    <td>
                        <span class="badge ${admin.role === 'super_admin' ? 'badge-info' : 'badge-success'}">
                            ${admin.role}
                        </span>
                    </td>
                    <td>
                        <span class="badge ${admin.is_active ? 'badge-success' : 'badge-danger'}">
                            ${admin.is_active ? 'Active' : 'Inactive'}
                        </span>
                    </td>
                    <td>
                        ${admin.is_active ? `
                            <button class="btn btn-sm btn-danger" onclick="deactivateAdmin('${admin.admin_id}')">
                                <i class="fas fa-ban"></i>
                            </button>
                        ` : '-'}
                    </td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="6" class="empty">No admins</td></tr>';
        }
    } catch (error) {
        tbody.innerHTML = '<tr><td colspan="6" class="empty">Error loading admins</td></tr>';
    }
}

async function loadActivityLog() {
    const tbody = document.getElementById('activity-tbody');
    tbody.innerHTML = '<tr><td colspan="5" class="loading">Loading...</td></tr>';
    
    try {
        const response = await fetch('/api/admin/activity-log');
        const data = await response.json();
        
        if (data.success && data.logs.length > 0) {
            tbody.innerHTML = data.logs.map(log => `
                <tr>
                    <td>${formatDateTime(log.created_at)}</td>
                    <td>${log.admin_id}</td>
                    <td>${formatAction(log.action)}</td>
                    <td>${log.target_employee_id || '-'}</td>
                    <td>${JSON.stringify(log.details || {})}</td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="5" class="empty">No activity logs</td></tr>';
        }
    } catch (error) {
        tbody.innerHTML = '<tr><td colspan="5" class="empty">Error loading logs</td></tr>';
    }
}

async function deleteUser(employeeId) {
    if (!confirm(`Are you sure you want to delete user ${employeeId}?`)) return;
    
    try {
        const response = await fetch(`/api/users/${employeeId}`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ admin_session_token: adminSessionToken })
        });
        
        const data = await response.json();
        
        if (data.success) {
            loadUsers();
        } else {
            alert(data.message);
        }
    } catch (error) {
        alert('Error deleting user');
    }
}

async function deactivateAdmin(adminId) {
    if (!confirm(`Are you sure you want to deactivate admin ${adminId}?`)) return;
    
    try {
        const response = await fetch(`/api/admin/deactivate/${adminId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_token: adminSessionToken })
        });
        
        const data = await response.json();
        
        if (data.success) {
            loadAdmins();
        } else {
            alert(data.message);
        }
    } catch (error) {
        alert('Error deactivating admin');
    }
}

function formatDateTime(isoString) {
    const date = new Date(isoString);
    return date.toLocaleString();
}

function formatAction(action) {
    const actions = {
        'admin_registration': 'Admin Registered',
        'admin_authentication': 'Admin Login',
        'admin_deactivation': 'Admin Deactivated',
        'user_registration': 'User Registered'
    };
    return actions[action] || action;
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
