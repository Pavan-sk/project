"""
Modern web interface for AutoPentest framework.
"""

from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit
import os
import json
import glob
import time
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import threading

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config['SECRET_KEY'] = os.urandom(24)
socketio = SocketIO(app, cors_allowed_origins="*")

# Get results directory
BASE_DIR = Path(__file__).parent.parent
RESULTS_DIR = BASE_DIR / "results"
RESULTS_DIR.mkdir(exist_ok=True)

# Scan status tracking
scan_status: Dict[str, Any] = {}
active_scans: Dict[str, threading.Thread] = {}


def safe_abspath(rel_path: str) -> Path:
    """Get safe absolute path within results directory."""
    p = RESULTS_DIR / rel_path
    if not str(p).startswith(str(RESULTS_DIR)):
        raise ValueError("Invalid path")
    return p


@app.route("/")
def index():
    """Main dashboard page."""
    return render_template("dashboard.html")


@app.route("/api/stats")
def api_stats():
    """Get overall statistics."""
    try:
        total_findings = 0
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        phase_counts = {"recon": 0, "scan": 0, "exploit": 0, "post": 0}
        hosts = set()
        tools_used = set()
        recent_scans = []
        
        pattern_path = RESULTS_DIR / "**" / "*.json"
        for fpath in glob.glob(str(pattern_path), recursive=True):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    total_findings += 1
                    
                    severity = data.get("severity", "info").lower()
                    if severity in severity_counts:
                        severity_counts[severity] += 1
                    
                    phase = data.get("phase", "unknown")
                    if phase in phase_counts:
                        phase_counts[phase] += 1
                    
                    if data.get("host"):
                        hosts.add(data["host"])
                    
                    if data.get("tool"):
                        tools_used.add(data["tool"])
                    
                    # Get recent scans
                    timestamp = data.get("timestamp", "")
                    if timestamp:
                        recent_scans.append({
                            "host": data.get("host", "Unknown"),
                            "timestamp": timestamp,
                            "severity": severity
                        })
            except Exception:
                pass
        
        # Sort recent scans by timestamp
        recent_scans.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        recent_scans = recent_scans[:10]
        
        return jsonify({
            "total_findings": total_findings,
            "severity_counts": severity_counts,
            "phase_counts": phase_counts,
            "unique_hosts": len(hosts),
            "tools_used": list(tools_used),
            "hosts": sorted(list(hosts)),
            "recent_scans": recent_scans,
            "risk_score": calculate_risk_score(severity_counts)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/reports")
def api_reports():
    """List all reports."""
    try:
        pattern = request.args.get("pattern", "**/*.json")
        phase_filter = request.args.get("phase")
        severity_filter = request.args.get("severity")
        host_filter = request.args.get("host")
        
        files = []
        pattern_path = RESULTS_DIR / pattern
        for fpath in glob.glob(str(pattern_path), recursive=True):
            if not fpath.endswith(".json"):
                continue
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                    # Apply filters
                    if phase_filter and data.get("phase") != phase_filter:
                        continue
                    if severity_filter and data.get("severity", "").lower() != severity_filter.lower():
                        continue
                    if host_filter and data.get("host") != host_filter:
                        continue
                    
                    files.append({
                        "path": os.path.relpath(fpath, RESULTS_DIR),
                        "host": data.get("host", "Unknown"),
                        "severity": data.get("severity", "info"),
                        "phase": data.get("phase", "unknown"),
                        "tool": data.get("tool", ""),
                        "timestamp": data.get("timestamp", ""),
                        "title": data.get("title", "")
                    })
            except Exception:
                pass
        
        # Sort by timestamp
        files.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return jsonify(files)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/report")
def get_report():
    """Get a specific report."""
    rel = request.args.get("path")
    if not rel:
        return jsonify({"error": "missing path parameter"}), 400
    try:
        p = safe_abspath(rel)
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify(data)
    except ValueError:
        return jsonify({"error": "invalid path"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/scan/start", methods=["POST"])
def start_scan():
    """Start a new scan."""
    try:
        data = request.get_json()
        target = data.get("target")
        config = data.get("config", "sample_config.yaml")
        phase = data.get("phase", "all")
        
        if not target:
            return jsonify({"error": "target required"}), 400
        
        scan_id = f"{target}_{int(time.time())}"
        
        # Start scan in background
        thread = threading.Thread(
            target=run_scan,
            args=(scan_id, target, config, phase),
            daemon=True
        )
        thread.start()
        active_scans[scan_id] = thread
        
        scan_status[scan_id] = {
            "id": scan_id,
            "target": target,
            "status": "running",
            "progress": 0,
            "phase": phase,
            "start_time": datetime.now().isoformat(),
            "findings": []
        }
        
        socketio.emit("scan_status", scan_status[scan_id])
        
        return jsonify({
            "success": True,
            "scan_id": scan_id,
            "message": f"Scan started for {target}"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/scan/status/<scan_id>")
def get_scan_status(scan_id):
    """Get scan status."""
    if scan_id in scan_status:
        return jsonify(scan_status[scan_id])
    return jsonify({"error": "scan not found"}), 404


@app.route("/api/scans")
def list_scans():
    """List all scans."""
    return jsonify(list(scan_status.values()))


@app.route("/api/export", methods=["POST"])
def export_reports():
    """Export reports in various formats."""
    try:
        data = request.get_json()
        format_type = data.get("format", "json")
        filters = data.get("filters", {})
        
        # Get filtered reports
        pattern_path = RESULTS_DIR / "**" / "*.json"
        reports = []
        for fpath in glob.glob(str(pattern_path), recursive=True):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    report_data = json.load(f)
                    
                    # Apply filters
                    if filters.get("phase") and report_data.get("phase") != filters["phase"]:
                        continue
                    if filters.get("severity") and report_data.get("severity", "").lower() != filters["severity"].lower():
                        continue
                    if filters.get("host") and report_data.get("host") != filters["host"]:
                        continue
                    
                    reports.append(report_data)
            except Exception:
                pass
        
        if format_type == "json":
            return jsonify(reports)
        elif format_type == "csv":
            return export_csv(reports)
        elif format_type == "pdf":
            return export_pdf(reports)
        else:
            return jsonify({"error": "unsupported format"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def run_scan(scan_id: str, target: str, config: str, phase: str):
    """Run a scan in the background."""
    try:
        # Update status
        scan_status[scan_id]["progress"] = 10
        socketio.emit("scan_update", {"scan_id": scan_id, "progress": 10})
        
        # Build command
        config_path = BASE_DIR / config
        cmd = [
            "python", "-m", "autopentest.cli",
            "-c", str(config_path),
            "-t", target
        ]
        
        if phase == "recon":
            cmd.append("--recon-only")
        elif phase == "scan":
            cmd.append("--scan-only")
        elif phase == "exploit":
            cmd.append("--exploit-only")
        
        scan_status[scan_id]["progress"] = 30
        socketio.emit("scan_update", {"scan_id": scan_id, "progress": 30})
        
        # Run command
        result = subprocess.run(
            cmd,
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=3600
        )
        
        scan_status[scan_id]["progress"] = 80
        socketio.emit("scan_update", {"scan_id": scan_id, "progress": 80})
        
        # Parse results
        if result.returncode == 0:
            scan_status[scan_id]["status"] = "completed"
            scan_status[scan_id]["progress"] = 100
            scan_status[scan_id]["end_time"] = datetime.now().isoformat()
        else:
            scan_status[scan_id]["status"] = "failed"
            scan_status[scan_id]["error"] = result.stderr
        
        socketio.emit("scan_complete", scan_status[scan_id])
        
    except Exception as e:
        scan_status[scan_id]["status"] = "failed"
        scan_status[scan_id]["error"] = str(e)
        socketio.emit("scan_error", {"scan_id": scan_id, "error": str(e)})


def calculate_risk_score(severity_counts: Dict[str, int]) -> float:
    """Calculate overall risk score."""
    weights = {
        "critical": 10,
        "high": 7,
        "medium": 4,
        "low": 1,
        "info": 0
    }
    
    total_weight = sum(severity_counts.get(sev, 0) * weights.get(sev, 0) for sev in weights)
    total_count = sum(severity_counts.values())
    
    if total_count == 0:
        return 0.0
    
    return min(100.0, (total_weight / total_count) * 10)


def export_csv(reports: List[Dict]) -> Any:
    """Export reports as CSV."""
    from flask import Response
    import csv
    import io
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        "Host", "Severity", "Phase", "Tool", "Title", "Description",
        "Evidence", "Recommendation", "Timestamp"
    ])
    
    # Write data
    for report in reports:
        writer.writerow([
            report.get("host", ""),
            report.get("severity", ""),
            report.get("phase", ""),
            report.get("tool", ""),
            report.get("title", ""),
            report.get("description", ""),
            report.get("evidence", ""),
            report.get("recommendation", ""),
            report.get("timestamp", "")
        ])
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=autopentest_report.csv"}
    )


def export_pdf(reports: List[Dict]) -> Any:
    """Export reports as PDF."""
    # Placeholder - would use reportlab or similar
    return jsonify({"error": "PDF export not yet implemented"}), 501


@socketio.on("connect")
def handle_connect():
    """Handle client connection."""
    emit("connected", {"status": "connected"})


@socketio.on("disconnect")
def handle_disconnect():
    """Handle client disconnection."""
    pass


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
