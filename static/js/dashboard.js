/**
 * Dashboard JavaScript
 * Handles statistics and reports display
 */

let chartInstances = {};

document.addEventListener('DOMContentLoaded', () => {
    loadDashboardData();
    setupEventListeners();
});

function setupEventListeners() {
    // Report generation
    document.getElementById('generate-report')?.addEventListener('click', generateReport);
    
    // Refresh button
    document.getElementById('refresh-btn')?.addEventListener('click', () => {
        loadDashboardData();
    });
    
    // Date filter
    document.getElementById('date-filter')?.addEventListener('change', () => {
        loadTodayAttendance();
    });
}

async function loadDashboardData() {
    await Promise.all([
        loadStatistics(),
        loadTodayAttendance(),
        loadRecentActivity()
    ]);
}

async function loadStatistics() {
    try {
        const response = await fetch('/api/attendance/stats');
        const data = await response.json();
        
        if (data.success) {
            const stats = data.statistics;
            
            // Update stat cards
            document.getElementById('total-employees').textContent = stats.total_employees || 0;
            document.getElementById('present-today').textContent = stats.present_today || 0;
            document.getElementById('absent-today').textContent = stats.absent_today || 0;
            document.getElementById('late-today').textContent = stats.late_today || 0;
            
            // Update attendance rate
            const rate = stats.attendance_rate || 0;
            document.getElementById('attendance-rate').textContent = `${rate}%`;
            updateRateIndicator(rate);
        }
    } catch (error) {
        console.error('Error loading statistics:', error);
    }
}

function updateRateIndicator(rate) {
    const indicator = document.getElementById('rate-indicator');
    if (!indicator) return;
    
    if (rate >= 90) {
        indicator.className = 'rate-indicator excellent';
        indicator.innerHTML = '<i class="fas fa-arrow-up"></i> Excellent';
    } else if (rate >= 70) {
        indicator.className = 'rate-indicator good';
        indicator.innerHTML = '<i class="fas fa-check"></i> Good';
    } else if (rate >= 50) {
        indicator.className = 'rate-indicator warning';
        indicator.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Needs Improvement';
    } else {
        indicator.className = 'rate-indicator critical';
        indicator.innerHTML = '<i class="fas fa-times-circle"></i> Critical';
    }
}

async function loadTodayAttendance() {
    const tbody = document.getElementById('attendance-tbody');
    const dateFilter = document.getElementById('date-filter')?.value || formatDate(new Date());
    
    tbody.innerHTML = '<tr><td colspan="6" class="loading">Loading...</td></tr>';
    
    try {
        const response = await fetch(`/api/attendance/list?date=${dateFilter}`);
        const data = await response.json();
        
        if (data.success && data.records.length > 0) {
            tbody.innerHTML = data.records.map(record => `
                <tr>
                    <td>${record.employee_id}</td>
                    <td>${record.name}</td>
                    <td>${formatTime(record.punch_in)}</td>
                    <td>${record.punch_out ? formatTime(record.punch_out) : '-'}</td>
                    <td>${record.hours_worked || '-'}</td>
                    <td>
                        <span class="status-badge ${getStatusClass(record)}">
                            ${getStatusText(record)}
                        </span>
                    </td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="6" class="empty">No attendance records for this date</td></tr>';
        }
    } catch (error) {
        tbody.innerHTML = '<tr><td colspan="6" class="empty">Error loading attendance</td></tr>';
    }
}

async function loadRecentActivity() {
    const container = document.getElementById('recent-activity');
    if (!container) return;
    
    try {
        const response = await fetch('/api/attendance/recent');
        const data = await response.json();
        
        if (data.success && data.records.length > 0) {
            container.innerHTML = data.records.map(record => `
                <div class="activity-item ${record.type}">
                    <div class="activity-icon">
                        <i class="fas fa-${record.type === 'punch_in' ? 'sign-in-alt' : 'sign-out-alt'}"></i>
                    </div>
                    <div class="activity-info">
                        <span class="activity-name">${record.name}</span>
                        <span class="activity-action">${record.type === 'punch_in' ? 'Punched In' : 'Punched Out'}</span>
                    </div>
                    <div class="activity-time">${formatTimeAgo(record.time)}</div>
                </div>
            `).join('');
        } else {
            container.innerHTML = '<div class="empty">No recent activity</div>';
        }
    } catch (error) {
        container.innerHTML = '<div class="empty">Error loading activity</div>';
    }
}

async function generateReport() {
    const btn = document.getElementById('generate-report');
    const startDate = document.getElementById('report-start-date')?.value;
    const endDate = document.getElementById('report-end-date')?.value;
    const format = document.getElementById('report-format')?.value || 'csv';
    
    if (!startDate || !endDate) {
        alert('Please select start and end dates');
        return;
    }
    
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';
    
    try {
        const response = await fetch('/api/attendance/report', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                start_date: startDate,
                end_date: endDate,
                format: format
            })
        });
        
        if (format === 'csv') {
            const blob = await response.blob();
            downloadFile(blob, `attendance_report_${startDate}_to_${endDate}.csv`, 'text/csv');
        } else {
            const data = await response.json();
            if (data.success) {
                displayReportModal(data.report);
            } else {
                alert(data.message || 'Error generating report');
            }
        }
    } catch (error) {
        alert('Error generating report');
    }
    
    btn.disabled = false;
    btn.innerHTML = '<i class="fas fa-file-download"></i> Generate Report';
}

function downloadFile(blob, filename, type) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

function displayReportModal(report) {
    // Create modal for viewing report
    const modal = document.createElement('div');
    modal.className = 'report-modal';
    modal.innerHTML = `
        <div class="report-content">
            <button class="close-report" onclick="this.parentElement.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
            <h2>Attendance Report</h2>
            <div class="report-summary">
                <div class="summary-item">
                    <span class="label">Period:</span>
                    <span class="value">${report.period}</span>
                </div>
                <div class="summary-item">
                    <span class="label">Total Records:</span>
                    <span class="value">${report.total_records}</span>
                </div>
                <div class="summary-item">
                    <span class="label">Average Hours:</span>
                    <span class="value">${report.average_hours}</span>
                </div>
            </div>
            <table class="report-table">
                <thead>
                    <tr>
                        <th>Employee ID</th>
                        <th>Name</th>
                        <th>Days Present</th>
                        <th>Total Hours</th>
                        <th>Average Hours/Day</th>
                    </tr>
                </thead>
                <tbody>
                    ${report.employees.map(emp => `
                        <tr>
                            <td>${emp.employee_id}</td>
                            <td>${emp.name}</td>
                            <td>${emp.days_present}</td>
                            <td>${emp.total_hours}</td>
                            <td>${emp.avg_hours}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;
    document.body.appendChild(modal);
}

function getStatusClass(record) {
    if (!record.punch_out) return 'working';
    if (record.is_late) return 'late';
    return 'complete';
}

function getStatusText(record) {
    if (!record.punch_out) return 'Working';
    if (record.is_late) return 'Late';
    return 'Complete';
}

function formatTime(isoString) {
    if (!isoString) return '-';
    const date = new Date(isoString);
    return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: true
    });
}

function formatDate(date) {
    return date.toISOString().split('T')[0];
}

function formatTimeAgo(isoString) {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return formatDate(date);
}

// Auto-refresh every 30 seconds
setInterval(() => {
    loadRecentActivity();
}, 30000);

// Set default date filter to today
document.addEventListener('DOMContentLoaded', () => {
    const dateFilter = document.getElementById('date-filter');
    if (dateFilter) {
        dateFilter.value = formatDate(new Date());
    }
    
    // Set default report dates
    const today = new Date();
    const monthAgo = new Date();
    monthAgo.setMonth(monthAgo.getMonth() - 1);
    
    const startDateEl = document.getElementById('report-start-date');
    const endDateEl = document.getElementById('report-end-date');
    
    if (startDateEl) startDateEl.value = formatDate(monthAgo);
    if (endDateEl) endDateEl.value = formatDate(today);
});
