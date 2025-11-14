# AutoPentest Web Interface

Modern, interactive web dashboard for AutoPentest framework with real-time updates, beautiful UI effects, and comprehensive features.

## Features

### 🎨 Modern UI Design
- **Dark/Light Theme** - Toggle between themes with smooth transitions
- **Glassmorphism Effects** - Modern glass-like UI elements
- **Smooth Animations** - Fluid transitions and hover effects
- **Responsive Design** - Works on all screen sizes
- **Interactive Charts** - Beautiful data visualizations

### 📊 Dashboard
- **Real-time Statistics** - Live updates of findings and scans
- **Severity Distribution** - Interactive doughnut chart
- **Phase Distribution** - Bar chart showing findings by phase
- **Recent Activity** - Latest scan results and findings
- **Risk Score** - Calculated overall risk assessment

### 🔍 Scanning
- **Start New Scans** - Easy scan configuration and execution
- **Real-time Progress** - Live progress updates via WebSockets
- **Scan History** - Complete history of all scans
- **Active Scan Monitoring** - Track running scans in real-time

### 📋 Reports
- **Filtering** - Filter by phase, severity, and host
- **Export Options** - Export to JSON, CSV formats
- **Interactive Cards** - Click to view detailed report information
- **Search** - Quick search through reports

### 🎯 Targets
- **Target Management** - Add and manage scan targets
- **Target History** - View all findings for specific targets
- **Quick Actions** - Start scans directly from target list

## Installation

1. Install web dependencies:
```bash
pip install flask flask-socketio
```

2. Run the web server:
```bash
cd project/web
python app.py
```

3. Open in browser:
```
http://localhost:5000
```

## Usage

### Starting a Scan
1. Navigate to the "Scans" section
2. Fill in the scan form:
   - Target: Enter domain or IP address
   - Phase: Select scan phase (all, recon, scan, exploit)
   - Config: Configuration file path
3. Click "Start Scan"
4. Monitor progress in real-time

### Viewing Reports
1. Go to "Reports" section
2. Use filters to narrow down results
3. Click on any report card to view details
4. Export reports in desired format

### Dashboard Features
- View overall statistics
- Monitor recent activity
- Track active scans
- Analyze severity distribution

## API Endpoints

- `GET /api/stats` - Get overall statistics
- `GET /api/reports` - List all reports (with filters)
- `GET /api/report?path=...` - Get specific report
- `POST /api/scan/start` - Start new scan
- `GET /api/scans` - List all scans
- `GET /api/scan/status/<scan_id>` - Get scan status
- `POST /api/export` - Export reports

## WebSocket Events

- `scan_status` - Scan status updates
- `scan_update` - Progress updates
- `scan_complete` - Scan completion notification
- `scan_error` - Error notifications

## Customization

### Themes
Themes can be customized in `static/css/dashboard.css`:
- Dark theme: Default
- Light theme: Toggle via theme button

### Colors
Primary colors can be adjusted in CSS variables:
```css
:root {
    --primary-color: #6366f1;
    --secondary-color: #8b5cf6;
    /* ... more colors ... */
}
```

## Requirements

- Flask 2.3.0+
- Flask-SocketIO 5.3.0+
- Python 3.8+

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Opera (latest)

## Features Coming Soon

- [ ] PDF export
- [ ] Scan scheduling
- [ ] Email notifications
- [ ] Custom dashboards
- [ ] Advanced filters
- [ ] Report templates
- [ ] API documentation viewer

