// Modern Dashboard JavaScript with Real-time Updates

let socket;
let severityChart, phaseChart;
let refreshInterval;

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    initializeSocket();
    initializeCharts();
    loadDashboard();
    setupEventListeners();
    startAutoRefresh();
});

// Socket.IO Connection
function initializeSocket() {
    socket = io();
    
    socket.on('connect', function() {
        console.log('Connected to server');
    });
    
    socket.on('scan_status', function(data) {
        updateScanStatus(data);
    });
    
    socket.on('scan_update', function(data) {
        updateScanProgress(data);
    });
    
    socket.on('scan_complete', function(data) {
        handleScanComplete(data);
        loadDashboard(); // Reload dashboard
    });
    
    socket.on('scan_error', function(data) {
        showNotification('Scan error: ' + data.error, 'error');
    });
}

// Initialize Charts
function initializeCharts() {
    const severityCtx = document.getElementById('severityChart').getContext('2d');
    severityChart = new Chart(severityCtx, {
        type: 'doughnut',
        data: {
            labels: ['Critical', 'High', 'Medium', 'Low', 'Info'],
            datasets: [{
                data: [0, 0, 0, 0, 0],
                backgroundColor: [
                    '#ef4444',
                    '#f59e0b',
                    '#3b82f6',
                    '#10b981',
                    '#6b7280'
                ],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#e4e6eb'
                    }
                }
            }
        }
    });
    
    const phaseCtx = document.getElementById('phaseChart').getContext('2d');
    phaseChart = new Chart(phaseCtx, {
        type: 'bar',
        data: {
            labels: ['Recon', 'Scan', 'Exploit', 'Post'],
            datasets: [{
                label: 'Findings',
                data: [0, 0, 0, 0],
                backgroundColor: 'rgba(99, 102, 241, 0.8)',
                borderColor: 'rgba(99, 102, 241, 1)',
                borderWidth: 2,
                borderRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        color: '#e4e6eb'
                    },
                    grid: {
                        color: '#2d3748'
                    }
                },
                x: {
                    ticks: {
                        color: '#e4e6eb'
                    },
                    grid: {
                        color: '#2d3748'
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                }
            }
        }
    });
}

// Load Dashboard Data
async function loadDashboard() {
    try {
        showLoading();
        
        const response = await fetch('/api/stats');
        const stats = await response.json();
        
        updateStats(stats);
        updateCharts(stats);
        
        await loadRecentActivity();
        await loadActiveScans();
        await loadReports();
        
        hideLoading();
    } catch (error) {
        console.error('Error loading dashboard:', error);
        hideLoading();
        showNotification('Error loading dashboard', 'error');
    }
}

// Update Statistics
function updateStats(stats) {
    document.getElementById('stat-critical').textContent = stats.severity_counts.critical || 0;
    document.getElementById('stat-high').textContent = stats.severity_counts.high || 0;
    document.getElementById('stat-medium').textContent = stats.severity_counts.medium || 0;
    document.getElementById('stat-total').textContent = stats.total_findings || 0;
    
    // Animate numbers
    animateValue('stat-critical', 0, stats.severity_counts.critical || 0, 1000);
    animateValue('stat-high', 0, stats.severity_counts.high || 0, 1000);
    animateValue('stat-medium', 0, stats.severity_counts.medium || 0, 1000);
    animateValue('stat-total', 0, stats.total_findings || 0, 1000);
}

// Animate Value
function animateValue(id, start, end, duration) {
    const element = document.getElementById(id);
    const range = end - start;
    const increment = range / (duration / 16);
    let current = start;
    
    const timer = setInterval(() => {
        current += increment;
        if ((increment > 0 && current >= end) || (increment < 0 && current <= end)) {
            element.textContent = Math.round(end);
            clearInterval(timer);
        } else {
            element.textContent = Math.round(current);
        }
    }, 16);
}

// Update Charts
function updateCharts(stats) {
    severityChart.data.datasets[0].data = [
        stats.severity_counts.critical || 0,
        stats.severity_counts.high || 0,
        stats.severity_counts.medium || 0,
        stats.severity_counts.low || 0,
        stats.severity_counts.info || 0
    ];
    severityChart.update('active');
    
    phaseChart.data.datasets[0].data = [
        stats.phase_counts.recon || 0,
        stats.phase_counts.scan || 0,
        stats.phase_counts.exploit || 0,
        stats.phase_counts.post || 0
    ];
    phaseChart.update('active');
}

// Load Recent Activity
async function loadRecentActivity() {
    try {
        const response = await fetch('/api/stats');
        const stats = await response.json();
        const activity = document.getElementById('recent-activity');
        
        activity.innerHTML = '';
        stats.recent_scans.slice(0, 10).forEach(scan => {
            const item = document.createElement('div');
            item.className = 'activity-item';
            item.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong>${scan.host}</strong>
                        <span class="badge badge-${scan.severity}">${scan.severity}</span>
                    </div>
                    <small>${formatDate(scan.timestamp)}</small>
                </div>
            `;
            activity.appendChild(item);
        });
    } catch (error) {
        console.error('Error loading activity:', error);
    }
}

// Load Active Scans
async function loadActiveScans() {
    try {
        const response = await fetch('/api/scans');
        const scans = await response.json();
        const container = document.getElementById('active-scans');
        
        container.innerHTML = '';
        scans.filter(s => s.status === 'running').forEach(scan => {
            const card = createScanCard(scan);
            container.appendChild(card);
        });
    } catch (error) {
        console.error('Error loading scans:', error);
    }
}

// Create Scan Card
function createScanCard(scan) {
    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: start;">
            <div style="flex: 1;">
                <h4>${scan.target}</h4>
                <p>Phase: ${scan.phase}</p>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${scan.progress || 0}%"></div>
                </div>
                <small>Progress: ${scan.progress || 0}%</small>
            </div>
            <div>
                <span class="badge badge-${scan.status}">${scan.status}</span>
            </div>
        </div>
    `;
    return card;
}

// Load Reports
async function loadReports() {
    try {
        const phase = document.getElementById('filter-phase')?.value || '';
        const severity = document.getElementById('filter-severity')?.value || '';
        const host = document.getElementById('filter-host')?.value || '';
        
        let url = '/api/reports?';
        if (phase) url += `phase=${phase}&`;
        if (severity) url += `severity=${severity}&`;
        if (host) url += `host=${host}&`;
        
        const response = await fetch(url);
        const reports = await response.json();
        const container = document.getElementById('reports-list');
        
        container.innerHTML = '';
        reports.forEach(report => {
            const card = createReportCard(report);
            container.appendChild(card);
        });
    } catch (error) {
        console.error('Error loading reports:', error);
    }
}

// Create Report Card
function createReportCard(report) {
    const card = document.createElement('div');
    card.className = `report-card ${report.severity || 'low'}`;
    card.onclick = () => showReportDetails(report.path);
    card.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 10px;">
            <h4>${report.title || 'Untitled'}</h4>
            <span class="badge badge-${report.severity || 'low'}">${report.severity || 'low'}</span>
        </div>
        <p style="color: #b0b3b8; margin-bottom: 10px;">${report.host}</p>
        <div style="display: flex; gap: 10px; font-size: 12px; color: #64748b;">
            <span><i class="fas fa-layer-group"></i> ${report.phase}</span>
            <span><i class="fas fa-wrench"></i> ${report.tool || 'N/A'}</span>
        </div>
    `;
    return card;
}

// Show Report Details
async function showReportDetails(path) {
    try {
        const response = await fetch(`/api/report?path=${encodeURIComponent(path)}`);
        const report = await response.json();
        
        const modal = document.getElementById('report-modal');
        const body = document.getElementById('modal-body');
        
        body.innerHTML = `
            <h2>${report.title || 'Report Details'}</h2>
            <div style="margin: 20px 0;">
                <p><strong>Host:</strong> ${report.host || 'N/A'}</p>
                <p><strong>Severity:</strong> <span class="badge badge-${report.severity}">${report.severity}</span></p>
                <p><strong>Phase:</strong> ${report.phase || 'N/A'}</p>
                <p><strong>Tool:</strong> ${report.tool || 'N/A'}</p>
            </div>
            <div style="margin: 20px 0;">
                <h3>Description</h3>
                <p>${report.description || 'N/A'}</p>
            </div>
            <div style="margin: 20px 0;">
                <h3>Evidence</h3>
                <pre style="background: #16213e; padding: 15px; border-radius: 8px; overflow-x: auto;">${report.evidence || 'N/A'}</pre>
            </div>
            <div style="margin: 20px 0;">
                <h3>Recommendation</h3>
                <p>${report.recommendation || 'N/A'}</p>
            </div>
        `;
        
        modal.classList.add('active');
    } catch (error) {
        console.error('Error loading report:', error);
        showNotification('Error loading report', 'error');
    }
}

// Start Scan
document.getElementById('scan-form')?.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const target = document.getElementById('scan-target').value;
    const phase = document.getElementById('scan-phase').value;
    const config = document.getElementById('scan-config').value;
    
    try {
        const response = await fetch('/api/scan/start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ target, phase, config })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('Scan started successfully', 'success');
            document.getElementById('scan-form').reset();
            showSection('scans');
            setTimeout(loadActiveScans, 1000);
        } else {
            showNotification(result.error || 'Failed to start scan', 'error');
        }
    } catch (error) {
        console.error('Error starting scan:', error);
        showNotification('Error starting scan', 'error');
    }
});

// Filter Reports
function filterReports() {
    loadReports();
}

// Export Reports
async function exportReports(format) {
    try {
        showLoading();
        const response = await fetch('/api/export', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ format })
        });
        
        if (format === 'csv') {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `autopentest_report_${Date.now()}.csv`;
            a.click();
        } else {
            const data = await response.json();
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `autopentest_report_${Date.now()}.json`;
            a.click();
        }
        
        hideLoading();
        showNotification('Report exported successfully', 'success');
    } catch (error) {
        console.error('Error exporting:', error);
        hideLoading();
        showNotification('Error exporting report', 'error');
    }
}

// Section Navigation
function showSection(sectionId) {
    document.querySelectorAll('.section').forEach(section => {
        section.classList.remove('active');
    });
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    
    document.getElementById(sectionId).classList.add('active');
    document.querySelector(`[onclick*="${sectionId}"]`)?.classList.add('active');
}

// Toggle Theme
function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    
    const icon = document.getElementById('theme-icon');
    icon.className = newTheme === 'light' ? 'fas fa-sun' : 'fas fa-moon';
}

// Setup Event Listeners
function setupEventListeners() {
    // Load saved theme
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    const icon = document.getElementById('theme-icon');
    icon.className = savedTheme === 'light' ? 'fas fa-sun' : 'fas fa-moon';
    
    // Close modal on outside click
    document.getElementById('report-modal')?.addEventListener('click', function(e) {
        if (e.target === this) {
            closeModal();
        }
    });
}

// Close Modal
function closeModal() {
    document.getElementById('report-modal')?.classList.remove('active');
}

// Update Scan Status
function updateScanStatus(data) {
    loadActiveScans();
}

// Update Scan Progress
function updateScanProgress(data) {
    const scanCards = document.querySelectorAll('.scan-card');
    scanCards.forEach(card => {
        const id = card.dataset.scanId;
        if (id === data.scan_id) {
            const progressBar = card.querySelector('.progress-fill');
            if (progressBar) {
                progressBar.style.width = data.progress + '%';
            }
        }
    });
}

// Handle Scan Complete
function handleScanComplete(data) {
    showNotification(`Scan completed: ${data.target}`, 'success');
    loadActiveScans();
}

// Show/Hide Loading
function showLoading() {
    document.getElementById('loading-overlay')?.classList.add('active');
}

function hideLoading() {
    document.getElementById('loading-overlay')?.classList.remove('active');
}

// Show Notification
function showNotification(message, type = 'info') {
    // Simple notification - can be enhanced
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.style.cssText = `
        position: fixed;
        top: 80px;
        right: 20px;
        background: ${type === 'error' ? '#ef4444' : type === 'success' ? '#10b981' : '#3b82f6'};
        color: white;
        padding: 15px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        z-index: 10000;
        animation: slideIn 0.3s;
    `;
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Format Date
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString();
}

// Start Auto Refresh
function startAutoRefresh() {
    const interval = parseInt(document.getElementById('refresh-interval')?.value || 30) * 1000;
    if (document.getElementById('auto-refresh')?.checked) {
        refreshInterval = setInterval(() => {
            if (document.getElementById('dashboard').classList.contains('active')) {
                loadDashboard();
            }
        }, interval);
    }
}

// Utility Functions
function animateCard(element) {
    element.style.animation = 'none';
    setTimeout(() => {
        element.style.animation = 'slideUp 0.5s ease-out';
    }, 10);
}

