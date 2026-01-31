/**
 * Dashboard JavaScript
 * Handles statistics and reports display
 */

document.addEventListener('DOMContentLoaded', () => {
    // Set today's date
    const todayDateEl = document.getElementById('today-date');
    if (todayDateEl) {
        todayDateEl.textContent = new Date().toLocaleDateString('en-US', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    }
    
    // Set default report dates
    const today = new Date();
    const monthAgo = new Date();
    monthAgo.setMonth(monthAgo.getMonth() - 1);
    
    const startDateEl = document.getElementById('start-date');
    const endDateEl = document.getElementById('end-date');
    
    if (startDateEl) startDateEl.value = formatDate(monthAgo);
    if (endDateEl) endDateEl.value = formatDate(today);
    
    loadDashboardData();
    setupEventListeners();
});

function setupEventListeners() {
    // Report generation
    document.getElementById('generate-report')?.addEventListener('click', generateReport);
}

async function loadDashboardData() {
    await Promise.all([
        loadStatistics(),
        loadTodayAttendance()
    ]);
}

async function loadStatistics() {
    try {
        const response = await fetch('/api/attendance/statistics');
        const data = await response.json();
        
        if (data.success) {
            const stats = data.statistics;
            
            // Update stat cards
            document.getElementById('total-users').textContent = stats.total_days || 0;
            document.getElementById('today-present').textContent = stats.present_today || 0;
            document.getElementById('today-completed').textContent = stats.completed_today || 0;
            document.getElementById('avg-hours').textContent = stats.average_hours ? `${stats.average_hours}h` : '-';
        }
    } catch (error) {
        console.error('Error loading statistics:', error);
    }
}

async function loadTodayAttendance() {
    const tbody = document.getElementById('today-tbody');
    if (!tbody) return;
    
    tbody.innerHTML = '<tr><td colspan="7" class="loading">Loading...</td></tr>';
    
    try {
        const response = await fetch('/api/attendance/today');
        const data = await response.json();
        
        if (data.success && data.records && data.records.length > 0) {
            tbody.innerHTML = data.records.map(record => `
                <tr>
                    <td>${record.employee_id || '-'}</td>
                    <td>${record.users?.name || record.name || '-'}</td>
                    <td>${record.users?.department || record.department || '-'}</td>
                    <td>${formatTime(record.punch_in)}</td>
                    <td>${record.punch_out ? formatTime(record.punch_out) : '-'}</td>
                    <td>${record.hours_worked ? `${record.hours_worked}h` : '-'}</td>
                    <td>
                        <span class="status-badge ${getStatusClass(record)}">
                            ${getStatusText(record)}
                        </span>
                    </td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="7" class="empty">No attendance records for today</td></tr>';
        }
    } catch (error) {
        console.error('Error loading attendance:', error);
        tbody.innerHTML = '<tr><td colspan="7" class="error">Error loading attendance data</td></tr>';
    }
}

async function generateReport() {
    const btn = document.getElementById('generate-report');
    const tbody = document.getElementById('report-tbody');
    const startDate = document.getElementById('start-date')?.value;
    const endDate = document.getElementById('end-date')?.value;
    const employeeId = document.getElementById('filter-employee')?.value;
    
    if (!startDate || !endDate) {
        alert('Please select start and end dates');
        return;
    }
    
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
    tbody.innerHTML = '<tr><td colspan="6" class="loading">Generating report...</td></tr>';
    
    try {
        let url = `/api/attendance/report?start_date=${startDate}&end_date=${endDate}`;
        if (employeeId) {
            url += `&employee_id=${employeeId}`;
        }
        
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.success && data.records && data.records.length > 0) {
            tbody.innerHTML = data.records.map(record => `
                <tr>
                    <td>${record.date || '-'}</td>
                    <td>${record.employee_id || '-'}</td>
                    <td>${record.users?.name || record.name || '-'}</td>
                    <td>${formatTime(record.punch_in)}</td>
                    <td>${record.punch_out ? formatTime(record.punch_out) : '-'}</td>
                    <td>${record.hours_worked ? `${record.hours_worked}h` : '-'}</td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="6" class="empty">No records found for the selected period</td></tr>';
        }
    } catch (error) {
        console.error('Error generating report:', error);
        tbody.innerHTML = '<tr><td colspan="6" class="error">Error generating report</td></tr>';
    }
    
    btn.disabled = false;
    btn.innerHTML = '<i class="fas fa-search"></i> Generate';
}

function getStatusClass(record) {
    if (!record.punch_out) return 'working';
    return 'complete';
}

function getStatusText(record) {
    if (!record.punch_out) return 'Working';
    return 'Complete';
}

function formatTime(isoString) {
    if (!isoString) return '-';
    try {
        // Handle different date formats
        let dateStr = isoString;
        if (dateStr.endsWith('Z')) {
            dateStr = dateStr.slice(0, -1) + '+00:00';
        }
        const date = new Date(dateStr);
        if (isNaN(date.getTime())) return isoString;
        
        return date.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            hour12: true
        });
    } catch {
        return isoString;
    }
}

function formatDate(date) {
    return date.toISOString().split('T')[0];
}

// Auto-refresh every 60 seconds
setInterval(() => {
    loadTodayAttendance();
}, 60000);
