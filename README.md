# AutoPentest - Automated Penetration Testing Framework

AutoPentest is a comprehensive, automated penetration testing framework designed to streamline security assessments through a modular, configurable approach. It orchestrates reconnaissance, vulnerability scanning, exploitation, and post-exploitation phases while maintaining safety controls and generating detailed reports.

## Features

- **Modular Architecture**: Plugin-based design for easy tool integration
- **Multi-Phase Testing**: Complete penetration testing workflow automation
- **Safety Controls**: Safe mode and configurable exploitation limits
- **Comprehensive Reporting**: Multiple output formats (HTML, JSON, CSV, XML)
- **Tool Integration**: Support for popular security tools (nmap, nikto, sqlmap, etc.)
- **Configurable**: YAML-based configuration for flexible testing scenarios
- **Cross-Platform**: Works on Windows, Linux, and macOS

## Installation

### Prerequisites

- Python 3.8 or higher
- Required security tools (see [Tools Installation](#tools-installation))

### Quick Start

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Pavan-sk/autopentest.git
   cd autopentest
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Install required security tools**:
   ```bash
   # On Ubuntu/Debian
   sudo apt update
   sudo apt install nmap nikto sqlmap hydra
   
   # On macOS
   brew install nmap nikto sqlmap hydra
   
   # On Windows
   # Download and install tools manually or use Chocolatey
   choco install nmap nikto sqlmap hydra
   ```

4. **Run the installation script**:
   ```bash
   chmod +x scripts/install_tools.sh
   ./scripts/install_tools.sh
   ```

## Kali Linux Usage

Kali Linux is the **recommended platform** for AutoPentest as it comes with most security tools pre-installed and configured.

### Why Kali Linux?

- **Pre-installed Tools**: All required security tools are already available
- **Optimized Environment**: Configured for penetration testing workflows
- **Regular Updates**: Security tools are kept up-to-date
- **Compatibility**: Tested and verified tool versions

### Kali Linux Setup

```bash
# 1. Update Kali Linux
sudo apt update && sudo apt upgrade -y

# 2. Install Python dependencies
pip3 install -r requirements.txt

# 3. Verify tool availability
which nmap
which nikto
which sqlmap
which hydra
which amass
which gobuster

# 4. Install any missing tools
sudo apt install -y nmap nikto sqlmap hydra amass gobuster

# 5. Clone AutoPentest
git clone https://github.com/Pavan-sk/autopentest.git
cd autopentest

# 6. Make scripts executable
chmod +x scripts/install_tools.sh
```

### Kali Linux Quick Start

```bash
# Test on localhost (safe for learning)
python3 -m autopentest.cli -c sample_config.yaml -t 127.0.0.1 --recon-only

# Test on localhost with port scanning
python3 -m autopentest.cli -c sample_config.yaml -t localhost --recon-only

# Run a full scan on a test domain (replace example.com with your target)
python3 -m autopentest.cli -c sample_config.yaml -t example.com --safe-mode

# Run only vulnerability scanning
python3 -m autopentest.cli -c sample_config.yaml -t example.com --scan-only
```

### Kali Linux Configuration

Create a Kali-optimized configuration file:

```yaml
project_name: "Kali Linux Penetration Test"
safe_mode: true

recon:
  passive: true
  active: true
  subdomain_enumeration: true
  port_scanning: true
  tools:
    nmap:
      timeout: 300
      aggressive: false
    amass:
      timeout: 600
      passive: true

scan:
  scan_type: "comprehensive"
  web_vulnerabilities: true
  network_vulnerabilities: true
  tools:
    nikto:
      timeout: 300
    sqlmap:
      timeout: 600
      risk_level: 1
      level: 1

exploit:
  mode: "safe"
  allowed_exploits: []
  forbidden_exploits: []

report:
  format: ["html", "json"]
  include_raw_output: true
  output_dir: "./kali_results"
```

### Kali Linux Tips

- **Use Python3**: Kali uses `python3` command instead of `python`
- **Tool Paths**: Most tools are in `/usr/bin/` and available in PATH
- **Permissions**: Some tools may require `sudo` for certain operations
- **Updates**: Keep Kali updated for the latest security tool versions
- **Workspace**: Use dedicated directories for different projects

## Usage

### Basic Usage

```bash
# Run a complete penetration test
python -m autopentest.cli -c sample_config.yaml -t example.com

# Run only reconnaissance
python -m autopentest.cli -c sample_config.yaml -t example.com --recon-only

# Run with custom output directory
python -m autopentest.cli -c sample_config.yaml -t example.com -o ./my_results

# Run in verbose mode
python -m autopentest.cli -c sample_config.yaml -t example.com -vv
```

### Configuration

Create a configuration file (see `sample_config.yaml` for examples):

```yaml
project_name: "My Penetration Test"
safe_mode: true

recon:
  passive: true
  active: false
  subdomain_enumeration: true
  port_scanning: true

scan:
  scan_type: "quick"
  web_vulnerabilities: true
  network_vulnerabilities: true

exploit:
  mode: "safe"  # safe, simulation, active
  allowed_exploits: []
  forbidden_exploits: []

report:
  format: ["html", "json"]
  include_raw_output: true
```

### Command Line Options

```
usage: autopentest [-h] -c CONFIG -t TARGETS [-o OUTPUT] [--recon-only] [--scan-only]
                   [--exploit-only] [--post-only] [--safe-mode] [-v] [-q] [--version]

AutoPentest - Automated Penetration Testing Framework

required arguments:
  -c CONFIG, --config CONFIG     Path to configuration file (YAML)
  -t TARGETS, --targets TARGETS  Target specification (domain, IP, or file with targets)

optional arguments:
  -o OUTPUT, --output OUTPUT     Output directory for results (default: ./results)
  --recon-only                   Run only reconnaissance phase
  --scan-only                    Run only vulnerability scanning phase
  --exploit-only                 Run only exploitation phase (safe mode)
  --post-only                    Run only post-exploitation phase
  --safe-mode                    Enable safe mode (no actual exploitation) (default: True)
  -v, --verbose                  Increase verbosity (-v, -vv, -vvv)
  -q, --quiet                    Suppress output except errors
  --version                      Show version and exit
```

## Architecture

### Core Components

- **Orchestrator**: Coordinates the entire penetration testing pipeline
- **Modules**: High-level phase implementations (recon, scan, exploit, post)
- **Plugins**: Tool-specific adapters for security tools
- **Storage**: Results management and report generation
- **Utils**: Common utilities for execution, parsing, and severity mapping

### Directory Structure

```
autopentest/
├── autopentest/
│   ├── __init__.py
│   ├── cli.py                     # Entry point (argparse)
│   ├── config.py                  # Config loader & validation
│   ├── storage.py                 # Results dir mgmt, JSON/CSV/HTML writers
│   ├── orchestrator.py            # Orchestrates end-to-end pipeline
│   ├── logging_setup.py           # Unified logging
│   ├── utils/
│   │   ├── exec.py                # Safe subprocess runner
│   │   ├── parsers.py             # Common parsers (nmap XML, etc.)
│   │   └── severity.py            # Severity mapping & CVSS helpers
│   ├── schemas/
│   │   ├── findings.py            # Dataclasses for Findings/Targets
│   │   └── report.py              # Report datamodel
│   ├── modules/
│   │   ├── recon.py               # High-level recon pipeline
│   │   ├── scanner.py             # High-level vuln scanning
│   │   ├── exploit.py             # High-level exploitation (safe-mode aware)
│   │   └── post.py                # Post-exploitation
│   └── plugins/                   # Tool adapters (each tool = file)
│       ├── nmap.py
│       ├── amass.py
│       ├── theharvester.py
│       ├── nikto.py
│       ├── sqlmap.py
│       ├── xsstrike.py
│       ├── gobuster.py
│       ├── metasploit.py
│       └── hydra.py
├── templates/
│   ├── report.html.j2             # Jinja2 HTML report template
│   └── css/
│       └── report.css
├── scripts/
│   └── install_tools.sh           # Helper: apt/pip installs & sanity checks
├── sample_config.yaml             # Example config
├── requirements.txt
├── pyproject.toml                 # Build metadata (optional)
├── README.md
└── LICENSE
```

## Supported Tools

### Reconnaissance
- **nmap**: Port scanning and service detection
- **amass**: Subdomain enumeration and DNS reconnaissance
- **theHarvester**: Email and subdomain discovery

### Vulnerability Scanning
- **nikto**: Web vulnerability scanner
- **sqlmap**: SQL injection testing
- **XSStrike**: XSS vulnerability detection
- **gobuster**: Directory and file enumeration

### Exploitation
- **Metasploit**: Exploit framework integration
- **Hydra**: Credential brute forcing

### Post-Exploitation
- Custom scripts and modules for privilege escalation, lateral movement, etc.

## Safety Features

- **Safe Mode**: Default mode that simulates exploitation without actual execution
- **Exploit Allowlists**: Configure which exploits are allowed to run
- **Exploit Blocklists**: Configure which exploits are forbidden
- **Timeout Controls**: Prevent tools from running indefinitely
- **Audit Logging**: Complete logging of all activities

## Reporting

AutoPentest generates comprehensive reports in multiple formats:

- **HTML Reports**: Professional, interactive reports with charts and graphs
- **JSON Reports**: Machine-readable format for integration
- **CSV Reports**: Spreadsheet-friendly format
- **XML Reports**: Structured data format

### Report Contents

- Executive summary with risk assessment
- Detailed findings with evidence and recommendations
- Technical details and raw tool outputs
- Statistics and metrics
- Remediation guidance

## Development

### Adding New Tools

1. Create a new plugin file in `autopentest/plugins/`
2. Implement the required interface
3. Add tool configuration to the config schema
4. Update the appropriate module to use the new plugin

### Example Plugin Structure

```python
class MyToolPlugin:
    def __init__(self, config: Config, storage: Storage):
        self.config = config
        self.storage = storage
        self.logger = logging.getLogger(__name__)
    
    def is_available(self) -> bool:
        """Check if tool is available."""
        pass
    
    def run(self, target: str) -> Dict[str, Any]:
        """Run the tool against target."""
        pass
```

### Testing

```bash
# Run tests
pytest tests/

# Run with coverage
pytest --cov=autopentest tests/

# Run linting
flake8 autopentest/
black autopentest/
```

## Contributing

We welcome contributions from the security community! 

### How to Contribute

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

### Contributors

- **Pavan-sk** - Project maintainer and lead developer
- AutoPentest Team - Core development team

## Security Considerations

- **Legal Compliance**: Always ensure you have proper authorization before testing
- **Safe Mode**: Use safe mode in production environments
- **Network Impact**: Be aware of potential network impact from aggressive scanning
- **Data Handling**: Ensure sensitive data is handled appropriately
- **Logging**: Review logs for sensitive information before sharing

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This tool is for authorized security testing only. Users are responsible for ensuring they have proper authorization before using this tool against any target. The authors are not responsible for any misuse of this software.

## Support

- **Documentation**: [Wiki](https://github.com/Pavan-sk/autopentest/wiki)
- **Issues**: [GitHub Issues](https://github.com/Pavan-sk/autopentest/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Pavan-sk/autopentest/discussions)

## Acknowledgments

- **Pavan-sk** - Project creator and maintainer
- Security tool developers and maintainers
- Open source security community
- Contributors and testers
