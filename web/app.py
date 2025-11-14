from flask import Flask, send_from_directory, jsonify, request
import os
import glob
import json
import time
import subprocess

try:
    import openai
except Exception:
    openai = None

try:
    import google.generativeai as genai
except Exception:
    genai = None

app = Flask(__name__, static_folder="static", template_folder="templates")

BASE_RESULTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "results"))

def safe_abspath(rel_path):
    p = os.path.abspath(os.path.join(BASE_RESULTS_DIR, rel_path))
    if not p.startswith(BASE_RESULTS_DIR):
        raise ValueError("Invalid path")
    return p

@app.route("/")
def index():
    return send_from_directory(app.template_folder, "index.html")

@app.route("/api/reports")
def list_reports():
    pattern = request.args.get("pattern", "**/*.json")
    glob_path = os.path.join(BASE_RESULTS_DIR, pattern)
    files = [os.path.relpath(p, BASE_RESULTS_DIR) for p in glob.glob(glob_path, recursive=True) if p.endswith(".json")]
    return jsonify(sorted(files))

@app.route("/api/report")
def get_report():
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

def list_gemini_models():
    """Return a list of available Gemini model names or raise an informative error."""
    if genai is None:
        raise RuntimeError("Gemini SDK not installed (google-generativeai). Install with: pip install google-generativeai")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")

    # Try new Client surface first
    try:
        if hasattr(genai, "Client"):
            client = genai.Client(api_key=api_key)
            if hasattr(client.models, "list"):
                res = client.models.list()
                # common shapes:
                if hasattr(res, "models"):
                    return [m.name for m in res.models]
                if isinstance(res, list):
                    return [getattr(m, "name", str(m)) for m in res]
                return [str(r) for r in res]
            else:
                raise RuntimeError("Installed google-generativeai Client does not expose client.models.list()")
    except Exception:
        # fall through to older surfaces
        pass

    # Try older module-level APIs
    try:
        if hasattr(genai, "list_models"):
            res = genai.list_models()
            if isinstance(res, list):
                return [m.name if hasattr(m, "name") else m for m in res]
            if isinstance(res, dict) and "models" in res:
                return [m.get("name") for m in res["models"]]
            return [getattr(m, "name", str(m)) for m in res]
        if hasattr(genai, "models") and hasattr(genai.models, "list"):
            res = genai.models.list()
            if hasattr(res, "models"):
                return [m.name for m in res.models]
            if isinstance(res, list):
                return [getattr(m, "name", str(m)) for m in res]
            return [str(res)]
    except Exception as e:
        raise RuntimeError(f"Failed to list Gemini models: {e}")

    raise RuntimeError("Could not determine model listing API for installed google-generativeai version. Upgrade or consult SDK docs.")

@app.route("/api/gemini-models")
def api_gemini_models():
    try:
        models = list_gemini_models()
        return jsonify(sorted(models))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/commands", methods=["GET"])
def api_commands():
    """Return list of available commands"""
    return jsonify({
        "commands": [],
        "tools": [
            {
                "name": "Port Scanner (Simulation)",
                "id": "tool-nmap",
                "description": "Simulate port scanning on a target host (creates sample findings)",
                "args": []
            },
            {
                "name": "Web Vulnerability Scanner (Simulation)",
                "id": "tool-web-scan",
                "description": "Simulate web vulnerability scanning (creates sample findings)",
                "args": []
            },
            {
                "name": "Network Enumeration (Simulation)",
                "id": "tool-enum",
                "description": "Simulate network enumeration and service discovery",
                "args": []
            },
            {
                "name": "SSL/TLS Certificate Checker",
                "id": "tool-ssl",
                "description": "Check SSL/TLS certificate validity and cipher strength",
                "args": []
            },
            {
                "name": "DNS Enumeration",
                "id": "tool-dns",
                "description": "Enumerate DNS records and subdomains",
                "args": []
            },
            {
                "name": "Credential Strength Analyzer",
                "id": "tool-cred",
                "description": "Analyze password policies and credential strength",
                "args": []
            },
            {
                "name": "API Security Audit",
                "id": "tool-api",
                "description": "Audit API endpoints for common security issues",
                "args": []
            },
            {
                "name": "Configuration Review",
                "id": "tool-config",
                "description": "Review system configuration for security best practices",
                "args": []
            },
        ]
    })

@app.route("/api/stats")
def api_stats():
    """Get summary statistics from reports"""
    try:
        pattern_path = os.path.join(BASE_RESULTS_DIR, "**/*.json")
        total_reports = 0
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        hosts = set()
        tools_used = set()
        
        for fpath in glob.glob(pattern_path, recursive=True):
            if fpath.endswith(".json"):
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        total_reports += 1
                        severity = data.get("severity", "info").lower()
                        if severity in severity_counts:
                            severity_counts[severity] += 1
                        if data.get("host"):
                            hosts.add(data["host"])
                        if data.get("tool"):
                            tools_used.add(data["tool"])
                except Exception:
                    pass
        
        return jsonify({
            "total_reports": total_reports,
            "severity_counts": severity_counts,
            "unique_hosts": len(hosts),
            "tools_used": list(tools_used),
            "hosts": sorted(list(hosts)),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/export-report", methods=["GET"])
def api_export_report():
    """Export all findings as a formatted text report"""
    try:
        pattern_path = os.path.join(BASE_RESULTS_DIR, "**/*.json")
        reports = []
        
        for fpath in glob.glob(pattern_path, recursive=True):
            if fpath.endswith(".json"):
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        reports.append(json.load(f))
                except Exception:
                    pass
        
        # Generate text report
        report_text = "=" * 80 + "\n"
        report_text += "SECURITY ASSESSMENT REPORT\n"
        report_text += f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        report_text += "=" * 80 + "\n\n"
        
        report_text += f"Total Findings: {len(reports)}\n\n"
        
        for report in sorted(reports, key=lambda x: x.get("severity", "info"), reverse=True):
            report_text += "-" * 80 + "\n"
            report_text += f"Title: {report.get('title', 'N/A')}\n"
            report_text += f"Severity: {report.get('severity', 'N/A').upper()}\n"
            report_text += f"Host: {report.get('host', 'N/A')}\n"
            report_text += f"Description: {report.get('description', 'N/A')}\n"
            
            ai = report.get("ai_explanation", {})
            if ai:
                report_text += f"\nAI Analysis:\n{ai.get('summary', 'N/A')}\n"
                if ai.get('remediation_steps'):
                    report_text += "\nRecommended Actions:\n"
                    for i, step in enumerate(ai['remediation_steps'], 1):
                        report_text += f"  {i}. {step}\n"
            report_text += "\n"
        
        return jsonify({
            "success": True,
            "report": report_text,
            "filename": f"security_report_{time.strftime('%Y%m%d_%H%M%S')}.txt"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/run-command", methods=["POST"])
def api_run_command():
    """Execute a command (generate reports, show explanations, etc.)"""
    body = request.get_json(force=True)
    cmd_id = body.get("command_id")
    
    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts", "generate_ai_explanations.py"))
    results_dir = BASE_RESULTS_DIR
    
    if cmd_id == "gen-mock":
        args = ["python3", script_path, "--dir", results_dir, "--use-mock"]
    elif cmd_id == "gen-gemini":
        args = ["python3", script_path, "--dir", results_dir, "--use-gemini"]
    elif cmd_id == "show-explain":
        args = ["python3", script_path, "--dir", results_dir, "--show"]
    else:
        return jsonify({"error": f"Unknown command: {cmd_id}"}), 400
    
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=300,
            env={**os.environ}
        )
        
        # Extract hostnames from reports (for filtering after command execution)
        hostnames = set()
        pattern_path = os.path.join(results_dir, "**/*.json")
        for fpath in glob.glob(pattern_path, recursive=True):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("host"):
                        hostnames.add(data["host"])
            except Exception:
                pass
        
        return jsonify({
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "hostnames": sorted(list(hostnames)),
        })
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Command timed out after 5 minutes"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/reports-by-host")
def reports_by_host():
    """Get reports filtered by hostname"""
    hostname = request.args.get("host")
    pattern = request.args.get("pattern", "**/*.json")
    if not hostname:
        return jsonify({"error": "missing host parameter"}), 400
    
    glob_path = os.path.join(BASE_RESULTS_DIR, pattern)
    files = []
    for fpath in glob.glob(glob_path, recursive=True):
        if fpath.endswith(".json"):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("host") == hostname:
                        files.append(os.path.relpath(fpath, BASE_RESULTS_DIR))
            except Exception:
                pass
    return jsonify(sorted(files))

@app.route("/api/ask", methods=["POST"])
def ask_about_report():
    body = request.get_json(force=True)
    rel = body.get("path")
    question = body.get("question", "").strip()
    is_tool_result = body.get("is_tool_result", False)
    
    if not question:
        return jsonify({"error": "missing question"}), 400
    
    # Handle tool results (in-memory, not file-based)
    if is_tool_result:
        tool_output = body.get("tool_output", "")
        ai_analysis = body.get("ai_analysis", "")
        prompt = (
            "You are a concise security analyst. Use the following tool output and analysis to answer the question briefly.\n\n"
            f"Tool Output:\n{tool_output}\n\n"
            f"Initial Analysis:\n{ai_analysis}\n\n"
            f"Question: {question}\n\nAnswer concisely:"
        )
    else:
        # Handle regular file-based reports
        if not rel:
            return jsonify({"error": "missing path parameter"}), 400
        try:
            p = safe_abspath(rel)
            with open(p, "r", encoding="utf-8") as f:
                report = json.load(f)
        except ValueError:
            return jsonify({"error": "invalid path"}), 400
        except Exception as e:
            return jsonify({"error": str(e)}), 500

        summary = report.get("ai_explanation", {}).get("summary") or ""
        prompt = (
            "You are a concise security analyst. Use the following report and answer briefly.\n\n"
            f"Report summary:\n{summary}\n\nFull report JSON:\n{json.dumps(report, indent=2)}\n\n"
            f"Question: {question}\n\nAnswer concisely:"
        )

    # Use Gemini; support both Client and older SDK surfaces
    try:
        if genai is None:
            return jsonify({"error": "AI SDK not installed. Install with: pip install google-generativeai"}), 500
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return jsonify({"error": "API key not configured on server"}), 500

        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

        # Try new Client API if available
        if hasattr(genai, "Client"):
            try:
                client = genai.Client(api_key=api_key)
            except Exception as e:
                return jsonify({"error": f"Failed to initialize: {e}"}), 500
            try:
                resp = client.models.generate_content(model=model_name, contents=prompt)
            except Exception as e:
                return jsonify({
                    "error": f"Analysis request failed: {e}"
                }), 500
            answer = getattr(resp, "text", None) or getattr(resp, "output", None) or None
            if isinstance(answer, (list, dict)):
                answer = json.dumps(answer)
            answer = str(answer).strip() if answer else None
            if not answer:
                return jsonify({"error": "No response received"}), 500
        else:
            # Fallback to older API surfaces
            tried = False
            if hasattr(genai, "GenerativeModel"):
                try:
                    model = genai.GenerativeModel(model_name)
                    resp = model.generate_content(prompt)
                    answer = getattr(resp, "text", None) or None
                    if answer:
                        tried = True
                except Exception:
                    answer = None
            if not tried and hasattr(genai, "generate_text"):
                try:
                    resp = genai.generate_text(model=model_name, prompt=prompt)
                    answer = getattr(resp, "text", None) or getattr(resp, "output", None) or None
                    if isinstance(answer, (list, dict)):
                        answer = json.dumps(answer)
                    tried = True
                except Exception:
                    answer = None
            if not tried:
                return jsonify({"error": "AI SDK does not expose supported API"}), 500
            if not answer:
                return jsonify({"error": "No response received"}), 500

    except Exception as e:
        return jsonify({"error": f"Request failed: {e}"}), 500

    return jsonify({
        "answer": answer,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })

@app.route("/api/run-tool", methods=["POST"])
def api_run_tool():
    """Execute a tool and generate AI explanation for the output"""
    body = request.get_json(force=True)
    tool_id = body.get("tool_id")
    target_host = body.get("target_host", "127.0.0.1")
    
    # Simulate tool execution with sample outputs
    tool_outputs = {
        "tool-nmap": f"""[+] Starting Nmap 7.80 on {target_host}
[+] Scanning active hosts and services...

Nmap scan report for {target_host}
Host is up (0.0025s latency).

[+] Port Summary:
    1 host(s) up, 995 closed, 4 open ports

Open Ports:
  - SSH: Open (22/tcp)
  - HTTP: Open (80/tcp)
  - HTTPS: Open (443/tcp)
  - MySQL: Open (3306/tcp)
  - HTTP-Proxy: Open (8080/tcp)

[+] Service Detection:
  22/tcp   ssh      OpenSSH 7.4
  80/tcp   http     Apache 2.4.6
  443/tcp  https    Apache 2.4.6 (SSL)
  3306/tcp mysql    MySQL 5.7.30
  8080/tcp http     Apache Tomcat

[+] Nmap scan completed successfully
""",
        "tool-web-scan": f"""[*] Web Vulnerability Scanner v2.1
[+] Target: http://{target_host}
[+] Scanning for common vulnerabilities...

[+] Scan complete: 3 vulnerabilities found

VULNERABILITY #1: SQL Injection
  Location: /search endpoint (Parameter: q)
  Severity: HIGH
  CWE-89: Improper Neutralization of Special Elements in SQL Command
  Payload: ' OR '1'='1
  Status: EXPLOITABLE

VULNERABILITY #2: Cross-Site Scripting (XSS)
  Location: /comments endpoint
  Severity: MEDIUM
  CWE-79: Improper Neutralization of Input During Web Page Generation
  Payload: <script>alert('XSS')</script>
  Status: EXPLOITABLE

VULNERABILITY #3: Weak SSL/TLS Configuration
  Location: HTTPS Port 443
  Severity: MEDIUM
  Issue: SSL 3.0 and TLS 1.0 enabled
  Recommendation: Upgrade to TLS 1.2+

[+] Scan Summary:
    Total Issues: 3
    Critical: 0
    High: 1
    Medium: 2
    Low: 0
""",
        "tool-enum": f"""[*] Network Enumeration Report for {target_host}
[+] Scanning active hosts and services...

[+] Host Information:
    Hostname: {target_host}
    Status: UP
    Response Time: 2.5ms
    Uptime: Unknown

[+] Service Discovery:

SSH Service (Port 22)
  Version: OpenSSH 7.4
  Banner: OpenSSH_7.4p1 Debian 10+deb9u3
  Vulnerability: CVE-2018-15473 (User Enumeration)
  Status: VULNERABLE

HTTP Service (Port 80)
  Server: Apache/2.4.6 (Debian)
  Robots.txt: Found (11 entries)
  Directories: /admin, /upload, /api, /backup
  CMS: WordPress 5.2.3
  Status: EXPOSED

HTTPS Service (Port 443)
  Certificate: Self-signed (CRITICAL)
  Issuer: {target_host}
  Expiry: 2023-01-01 (EXPIRED)
  Key Size: 2048-bit
  Status: INVALID

MySQL Service (Port 3306)
  Version: MySQL 5.7.30
  Authentication: NONE REQUIRED (CRITICAL)
  Databases: wordpress, test, admin
  User Enum: Possible
  Status: CRITICAL

[+] Enumeration complete: 8 services found
""",
        "tool-ssl": f"""[*] SSL/TLS Certificate Check for {target_host}
[+] Performing certificate validation...

Certificate Information:
  Common Name (CN): {target_host}
  Subject Alt Names: *.{target_host}, www.{target_host}
  Issuer: Self-Signed Authority
  Valid From: 2023-01-15 10:30:00 UTC
  Valid Until: 2024-01-15 10:30:00 UTC (EXPIRED)
  Serial Number: 1A2B3C4D5E6F
  Key Size: 2048-bit RSA
  Signature Algorithm: sha256WithRSAEncryption
  Fingerprint (SHA-256): a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6

Cipher Suites Analysis:
  TLS 1.3: ECDHE-RSA-AES256-GCM-SHA384 ✓ SECURE
  TLS 1.2: ECDHE-RSA-AES256-GCM-SHA384 ✓ SECURE
  TLS 1.1: ECDHE-RSA-AES256-SHA ✗ DEPRECATED
  TLS 1.0: DES-CBC3-SHA ✗ BROKEN
  SSL 3.0: Enabled ✗ CRITICAL
  SSL 2.0: Not detected ✓ GOOD

Certificate Issues Found:
  ✗ CRITICAL: Certificate is EXPIRED (valid until 2024-01-15)
  ✗ HIGH: Self-signed certificate (not trusted)
  ✗ MEDIUM: TLS 1.1 support enabled
  ✗ CRITICAL: SSL 3.0 enabled (POODLE vulnerability)

Recommendations:
  1. Renew certificate with trusted CA
  2. Disable TLS 1.0, 1.1, and SSL 3.0
  3. Use only TLS 1.2 and 1.3
  4. Use modern cipher suites only
""",
        "tool-dns": f"""[*] DNS Enumeration Report for {target_host}
[+] Querying DNS records and subdomains...

Primary Domain: {target_host}

A Records (IPv4):
  {target_host} → 192.168.1.100
  www.{target_host} → 192.168.1.100

AAAA Records (IPv6):
  {target_host} → Not configured

CNAME Records:
  www.{target_host} → {target_host}
  mail.{target_host} → mail.external.com
  api.{target_host} → api.external.com

MX Records (Mail):
  Priority 10: mail.{target_host} (192.168.1.101)
  Priority 20: mail2.{target_host} (192.168.1.102)

TXT Records:
  v=spf1 include:google.com ~all
  google-site-verification=abc123xyz456
  _dmarc: v=DMARC1; p=quarantine

NS Records:
  ns1.{target_host}
  ns2.{target_host}

Subdomains Discovered:
  admin.{target_host} (Active)
  api.{target_host} (Active)
  staging.{target_host} (Active)
  dev.{target_host} (Active)
  backup.{target_host} (Active)
  test.{target_host} (Inactive)

Security Issues:
  ✗ MEDIUM: Multiple subdomains exposed
  ✓ GOOD: SPF record present
  ✓ GOOD: DMARC policy configured
  ✗ MEDIUM: Staging/Dev environments exposed
""",
        "tool-cred": f"""[*] Credential Strength Analysis for {target_host}
[+] Analyzing password policies and credentials...

Password Policy Assessment:
  Minimum Length: 8 characters (WEAK)
  Maximum Length: 64 characters (GOOD)
  Complexity Required: No (CRITICAL)
  Special Characters Enforced: No (WEAK)
  Numbers Required: No (WEAK)
  Uppercase Required: No (WEAK)
  Expiration Policy: 90 days (GOOD)
  History Enforcement: 3 previous passwords (GOOD)

Account Status Summary:
  Total Users: 127
  Active Accounts: 112
  Disabled Accounts: 8
  Inactive (>90 days): 7

Password Strength Distribution:
  Strong Passwords: 84 (66.1%)
  Weak Passwords: 43 (33.8%)
  Default Credentials: 5 (3.9%)
  Empty Passwords: 2 (1.6%)

Critical Issues Found:
  ✗ CRITICAL: 5 accounts with default credentials
  ✗ CRITICAL: 2 accounts with empty passwords
  ✗ HIGH: 43 users with weak passwords
  ✗ MEDIUM: No password complexity requirement
  ✗ MEDIUM: No uppercase/special char enforcement

Weak Passwords Examples:
  - admin:admin123
  - user:password123
  - test:test123

Recommendations:
  1. Enforce strong password policy
  2. Force password change for weak/default credentials
  3. Implement MFA for all accounts
  4. Regular password audits
""",
        "tool-api": f"""[*] API Security Audit for {target_host}
[+] Scanning API endpoints and security...

API Endpoints Found: 12

Endpoint Analysis:
  1. GET /api/users - No authentication ✗ CRITICAL
     Response: 200 OK (JSON)
     Data Exposed: User IDs, Emails, Full Names
     
  2. POST /api/admin - API Key Required ✓
     Response: 401 Unauthorized (without key)
     
  3. GET /api/data/{{id}} - Weak Authorization ✗ HIGH
     Vulnerability: IDOR (Insecure Direct Object Reference)
     Example: /api/data/1 returns user data for any ID
     
  4. POST /api/upload - No validation ✗ HIGH
     File Types: Allows .exe, .sh, .php
     Max Size: No limit
     Location: /var/www/uploads (Web-accessible)
     
  5. GET /api/config - Exposed ✗ CRITICAL
     Contains: Database credentials, API keys
     
  6. DELETE /api/users/{{id}} - No CSRF token ✗ MEDIUM

Authentication Analysis:
  API Key: Hardcoded in client-side code ✗ CRITICAL
  JWT: Not implemented
  Rate Limiting: Not implemented ✗ MEDIUM
  API Versioning: /api/v1 (Inconsistent)

CORS Configuration:
  Access-Control-Allow-Origin: * ✗ CRITICAL
  Access-Control-Allow-Methods: * ✗ HIGH
  Allows Credentials: Yes ✗ HIGH

Critical Issues Summary:
  ✗ CRITICAL: Unauthenticated API endpoints (3)
  ✗ CRITICAL: Hardcoded credentials
  ✗ HIGH: IDOR vulnerability
  ✗ HIGH: No file upload validation
  ✗ MEDIUM: No rate limiting
  ✗ MEDIUM: No CSRF protection
""",
        "tool-config": f"""[*] Configuration Review for {target_host}
[+] Analyzing system and application configuration...

Operating System:
  OS: Linux 5.10.0-8-generic (Debian 10)
  Last Update: 2022-06-15 (OUTDATED)
  Security Updates: 127 missing
  Status: VULNERABLE

Web Server (Apache):
  Version: 2.4.6 (Released 2014)
  Security Headers: MISSING
    ✗ X-Frame-Options
    ✗ X-Content-Type-Options
    ✗ Strict-Transport-Security
    ✗ Content-Security-Policy
    ✗ X-XSS-Protection

SSH Configuration:
  Version: OpenSSH 7.4 (2016)
  Root Login: ENABLED ✗ CRITICAL
  Password Auth: ENABLED ✗ MEDIUM
  Key Exchange: diffie-hellman-group1-sha1 ✗ WEAK
  Ciphers: aes128-cbc ✗ WEAK

Database (MySQL):
  Version: 5.7.30 (2020)
  Root Access: Exposed on port 3306 ✗ CRITICAL
  Bind Address: 0.0.0.0 (Accessible to all) ✗ CRITICAL
  Authentication: Basic password (no encryption) ✗ HIGH

File System Security:
  /var/www: World-readable ✗ MEDIUM
  /var/www/backups: World-readable ✗ CRITICAL
  /home/user/.ssh: Permissions OK ✓
  Cron jobs: Exposed ✗ MEDIUM

Firewall Status:
  UFW: DISABLED ✗ CRITICAL
  iptables: No rules configured ✗ CRITICAL

Logging Configuration:
  Syslog: ENABLED ✓
  Web Server Logs: Not rotated (100GB+) ✗ MEDIUM
  Database Logs: DISABLED ✗ MEDIUM

Security Issues Summary:
  ✗ CRITICAL: Outdated OS and software (127 updates missing)
  ✗ CRITICAL: Database and SSH exposed
  ✗ CRITICAL: Firewall disabled
  ✗ CRITICAL: Root login enabled
  ✗ HIGH: Missing security headers
  ✗ MEDIUM: Weak SSH ciphers
  ✗ MEDIUM: Large unrotated log files
""",
    }
    
    if tool_id not in tool_outputs:
        return jsonify({"error": f"Unknown tool: {tool_id}"}), 400
    
    tool_output = tool_outputs[tool_id]
    
    # Prepare AI explanation prompt
    prompt = (
        "You are a security expert. Analyze the following tool output and provide a concise security assessment.\n\n"
        f"Tool Output:\n{tool_output}\n\n"
        "Provide:\n"
        "1. Summary of findings\n"
        "2. Critical issues identified\n"
        "3. Recommended actions\n"
        "Answer concisely in 3-5 sentences."
    )
    
    # Generate AI explanation
    ai_explanation = None
    try:
        if genai is None:
            ai_explanation = "AI SDK not available. Please review the tool output above."
        else:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                ai_explanation = "API key not configured. Please review the tool output above."
            else:
                model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
                if hasattr(genai, "Client"):
                    try:
                        client = genai.Client(api_key=api_key)
                        resp = client.models.generate_content(model=model_name, contents=prompt)
                        ai_explanation = getattr(resp, "text", None) or getattr(resp, "output", None) or None
                    except Exception as e:
                        ai_explanation = f"AI analysis error: {e}"
                else:
                    if hasattr(genai, "GenerativeModel"):
                        try:
                            model = genai.GenerativeModel(model_name)
                            resp = model.generate_content(prompt)
                            ai_explanation = getattr(resp, "text", None) or None
                        except Exception as e:
                            ai_explanation = f"AI analysis error: {e}"
    except Exception as e:
        ai_explanation = f"Error: {e}"
    
    return jsonify({
        "success": True,
        "tool_id": tool_id,
        "target_host": target_host,
        "tool_output": tool_output,
        "ai_explanation": ai_explanation or "No explanation available",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })

@app.route("/api/host-stats/<hostname>")
def host_stats(hostname):
    """Get statistics and findings for a specific host"""
    try:
        pattern_path = os.path.join(BASE_RESULTS_DIR, "**/*.json")
        findings = []
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        
        for fpath in glob.glob(pattern_path, recursive=True):
            if fpath.endswith(".json"):
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if data.get("host") == hostname:
                            findings.append(data)
                            severity = data.get("severity", "info").lower()
                            if severity in severity_counts:
                                severity_counts[severity] += 1
                except Exception:
                    pass
        
        # Calculate risk score
        risk_score = (
            severity_counts["critical"] * 40 +
            severity_counts["high"] * 25 +
            severity_counts["medium"] * 10 +
            severity_counts["low"] * 5
        )
        
        # Group by severity
        by_severity = {}
        for finding in findings:
            sev = finding.get("severity", "info").lower()
            if sev not in by_severity:
                by_severity[sev] = []
            by_severity[sev].append(finding)
        
        return jsonify({
            "hostname": hostname,
            "total_findings": len(findings),
            "severity_counts": severity_counts,
            "risk_score": min(risk_score, 100),  # Cap at 100
            "findings": findings,
            "by_severity": by_severity,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Run: python app.py
    app.run(host="127.0.0.1", port=5000, debug=True)
