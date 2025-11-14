#!/bin/bash

# AutoPentest Tools Installation Script
# This script installs the required security tools for AutoPentest

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to detect OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command_exists apt-get; then
            echo "ubuntu"
        elif command_exists yum; then
            echo "centos"
        elif command_exists dnf; then
            echo "fedora"
        else
            echo "linux"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

# Function to install tools on Ubuntu/Debian
install_ubuntu() {
    print_status "Installing tools on Ubuntu/Debian..."
    
    # Update package list
    sudo apt-get update
    
    # Install basic tools
    sudo apt-get install -y nmap nikto hydra
    
    # Install Python tools
    pip3 install sqlmap
    
    # Install additional tools
    sudo apt-get install -y dirb gobuster wfuzz
    
    # Install Amass
    if ! command_exists amass; then
        print_status "Installing Amass..."
        sudo snap install amass
    fi
    
    # Install TheHarvester
    if ! command_exists theHarvester; then
        print_status "Installing TheHarvester..."
        pip3 install theHarvester
    fi
    
    # Install XSStrike
    if ! command_exists xsstrike; then
        print_status "Installing XSStrike..."
        git clone https://github.com/s0md3v/XSStrike.git /tmp/XSStrike
        cd /tmp/XSStrike
        pip3 install -r requirements.txt
        sudo ln -sf /tmp/XSStrike/xsstrike.py /usr/local/bin/xsstrike
        cd -
    fi
}

# Function to install tools on CentOS/RHEL
install_centos() {
    print_status "Installing tools on CentOS/RHEL..."
    
    # Install EPEL repository
    sudo yum install -y epel-release
    
    # Install basic tools
    sudo yum install -y nmap nikto hydra
    
    # Install Python tools
    pip3 install sqlmap
    
    # Install additional tools
    sudo yum install -y dirb gobuster
    
    # Install Amass (if available)
    if command_exists dnf; then
        sudo dnf install -y amass
    else
        print_warning "Amass not available in default repositories. Please install manually."
    fi
}

# Function to install tools on macOS
install_macos() {
    print_status "Installing tools on macOS..."
    
    # Check if Homebrew is installed
    if ! command_exists brew; then
        print_error "Homebrew is required but not installed. Please install Homebrew first."
        print_status "Visit: https://brew.sh"
        exit 1
    fi
    
    # Install basic tools
    brew install nmap nikto hydra
    
    # Install Python tools
    pip3 install sqlmap
    
    # Install additional tools
    brew install gobuster dirb
    
    # Install Amass
    brew install amass
    
    # Install TheHarvester
    pip3 install theHarvester
    
    # Install XSStrike
    if ! command_exists xsstrike; then
        print_status "Installing XSStrike..."
        git clone https://github.com/s0md3v/XSStrike.git /tmp/XSStrike
        cd /tmp/XSStrike
        pip3 install -r requirements.txt
        ln -sf /tmp/XSStrike/xsstrike.py /usr/local/bin/xsstrike
        cd -
    fi
}

# Function to install tools on Windows
install_windows() {
    print_status "Installing tools on Windows..."
    
    # Check if Chocolatey is installed
    if ! command_exists choco; then
        print_error "Chocolatey is required but not installed. Please install Chocolatey first."
        print_status "Visit: https://chocolatey.org/install"
        exit 1
    fi
    
    # Install basic tools
    choco install -y nmap nikto hydra
    
    # Install Python tools
    pip3 install sqlmap
    
    # Install additional tools
    choco install -y gobuster
    
    print_warning "Some tools may need to be installed manually on Windows."
    print_warning "Please check the documentation for Windows-specific installation instructions."
}

# Function to verify tool installation
verify_tools() {
    print_status "Verifying tool installations..."
    
    local tools=("nmap" "nikto" "sqlmap" "hydra" "gobuster")
    local missing_tools=()
    
    for tool in "${tools[@]}"; do
        if command_exists "$tool"; then
            print_success "$tool is installed"
        else
            print_warning "$tool is not installed or not in PATH"
            missing_tools+=("$tool")
        fi
    done
    
    # Check optional tools
    local optional_tools=("amass" "theHarvester" "xsstrike")
    for tool in "${optional_tools[@]}"; do
        if command_exists "$tool"; then
            print_success "$tool is installed (optional)"
        else
            print_warning "$tool is not installed (optional)"
        fi
    done
    
    if [ ${#missing_tools[@]} -eq 0 ]; then
        print_success "All required tools are installed!"
    else
        print_warning "Some required tools are missing: ${missing_tools[*]}"
        print_warning "Please install them manually or check your PATH configuration."
    fi
}

# Function to create wordlists directory
setup_wordlists() {
    print_status "Setting up wordlists..."
    
    local wordlist_dir="$HOME/.autopentest/wordlists"
    mkdir -p "$wordlist_dir"
    
    # Download common wordlists if they don't exist
    if [ ! -f "$wordlist_dir/common.txt" ]; then
        print_status "Downloading common wordlist..."
        curl -L -o "$wordlist_dir/common.txt" "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/common.txt"
    fi
    
    if [ ! -f "$wordlist_dir/subdomains.txt" ]; then
        print_status "Downloading subdomain wordlist..."
        curl -L -o "$wordlist_dir/subdomains.txt" "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/DNS/subdomains-top1million-5000.txt"
    fi
    
    print_success "Wordlists setup complete"
}

# Main installation function
main() {
    print_status "AutoPentest Tools Installation Script"
    print_status "====================================="
    
    # Detect OS
    local os=$(detect_os)
    print_status "Detected OS: $os"
    
    # Install tools based on OS
    case $os in
        "ubuntu"|"debian")
            install_ubuntu
            ;;
        "centos"|"rhel"|"fedora")
            install_centos
            ;;
        "macos")
            install_macos
            ;;
        "windows")
            install_windows
            ;;
        *)
            print_error "Unsupported operating system: $os"
            print_error "Please install tools manually or contribute support for this OS."
            exit 1
            ;;
    esac
    
    # Verify installations
    verify_tools
    
    # Setup wordlists
    setup_wordlists
    
    print_success "Installation complete!"
    print_status "You can now use AutoPentest with the installed tools."
}

# Run main function
main "$@"
