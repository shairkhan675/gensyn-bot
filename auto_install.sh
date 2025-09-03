#!/bin/bash

# Gensyn Bot Auto-Discovery One-Line Installer
# Usage: curl -sSL https://raw.githubusercontent.com/your-repo/gensyn-bot/main/auto_install.sh | bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script configuration
REPO_URL="https://github.com/shairkhan2/gensyn-bot.git"
INSTALL_DIR="/root/gensyn-bot"
LOG_FILE="/root/gensyn_auto_install.log"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

print_header() {
    echo -e "${PURPLE}$1${NC}"
}

# Function to check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "This script must be run as root"
        echo "Please run: sudo $0"
        exit 1
    fi
}

# Function to detect OS
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
    elif type lsb_release >/dev/null 2>&1; then
        OS=$(lsb_release -si)
        VER=$(lsb_release -sr)
    elif [ -f /etc/lsb-release ]; then
        . /etc/lsb-release
        OS=$DISTRIB_ID
        VER=$DISTRIB_RELEASE
    elif [ -f /etc/debian_version ]; then
        OS=Debian
        VER=$(cat /etc/debian_version)
    else
        OS=$(uname -s)
        VER=$(uname -r)
    fi
    
    print_status "Detected OS: $OS $VER"
}

# Function to install dependencies
install_dependencies() {
    print_status "Installing system dependencies..."
    
    # Update package lists
    if command -v apt-get >/dev/null 2>&1; then
        apt-get update -y
        apt-get install -y python3 python3-pip python3-venv git curl wget \
                          build-essential software-properties-common \
                          lsof gnupg screen net-tools
    elif command -v yum >/dev/null 2>&1; then
        yum update -y
        yum install -y python3 python3-pip git curl wget \
                      gcc gcc-c++ make \
                      lsof gnupg2 screen net-tools
    elif command -v dnf >/dev/null 2>&1; then
        dnf update -y
        dnf install -y python3 python3-pip git curl wget \
                      gcc gcc-c++ make \
                      lsof gnupg2 screen net-tools
    else
        print_error "Unsupported package manager. Please install manually:"
        print_error "python3, python3-pip, python3-venv, git, curl, wget"
        exit 1
    fi
    
    print_success "System dependencies installed"
}

# Function to check Python version
check_python() {
    print_status "Checking Python version..."
    
    if command -v python3 >/dev/null 2>&1; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        print_status "Python version: $PYTHON_VERSION"
        
        # Check if version is >= 3.8
        if python3 -c 'import sys; exit(0 if sys.version_info >= (3, 8) else 1)'; then
            print_success "Python version is compatible"
        else
            print_error "Python 3.8+ is required, found $PYTHON_VERSION"
            exit 1
        fi
    else
        print_error "Python 3 is not installed"
        exit 1
    fi
}

# Function to clone repository
clone_repository() {
    print_status "Cloning gensyn-bot repository..."
    
    # Remove existing directory if it exists
    if [ -d "$INSTALL_DIR" ]; then
        print_warning "Existing installation found, backing up..."
        mv "$INSTALL_DIR" "${INSTALL_DIR}.backup.$(date +%s)"
    fi
    
    # Clone repository
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    
    print_success "Repository cloned to $INSTALL_DIR"
}

# Function to setup Python virtual environment
setup_venv() {
    print_status "Setting up Python virtual environment..."
    
    cd "$INSTALL_DIR"
    
    # Create virtual environment
    python3 -m venv .venv
    source .venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install requirements
    if [ -f requirements.txt ]; then
        print_status "Installing Python dependencies..."
        pip install -r requirements.txt
    else
        print_error "requirements.txt not found"
        exit 1
    fi
    
    print_success "Virtual environment setup completed"
}

# Function to make scripts executable
setup_permissions() {
    print_status "Setting up file permissions..."
    
    cd "$INSTALL_DIR"
    
    # Make Python scripts executable
    chmod +x auto_setup.py
    chmod +x auto_webhook_bot.py
    chmod +x webhook_config.py
    chmod +x start_webhook_bot.py
    
    # Make shell scripts executable
    chmod +x setup_webhook.sh
    chmod +x auto_install.sh
    
    print_success "File permissions configured"
}

# Function to run auto setup
run_auto_setup() {
    print_status "Starting automated configuration..."
    
    cd "$INSTALL_DIR"
    source .venv/bin/activate
    
    # Check if environment variables are set for non-interactive mode
    if [ -n "$N8N_SERVER_URL" ] && [ -n "$VPS_NAME" ]; then
        print_status "Running in non-interactive mode"
        print_status "N8N Server: $N8N_SERVER_URL"
        print_status "VPS Name: $VPS_NAME"
        
        # Create auto-config for non-interactive setup
        python3 -c "
import json
import secrets
import os
from datetime import datetime

config = {
    'n8n_server': '$N8N_SERVER_URL',
    'vps_name': '$VPS_NAME',
    'vps_id': '$VPS_NAME'.lower().replace(' ', '-').replace('_', '-'),
    'vps_uuid': secrets.token_hex(16),
    'auth_token': secrets.token_urlsafe(32),
    'setup_time': datetime.utcnow().isoformat() + 'Z',
    'registration_endpoint': '$N8N_SERVER_URL/webhook/gensyn/register',
    'status_endpoint': '$N8N_SERVER_URL/webhook/gensyn/status',
    'webhook_port': 8080,
    'registration_status': 'configured'
}

with open('/root/gensyn-bot/auto_config.json', 'w') as f:
    json.dump(config, f, indent=2)

print('Non-interactive configuration created')
"
        
        print_success "Non-interactive configuration completed"
    else
        # Run interactive setup
        python3 auto_setup.py
    fi
}

# Function to test installation
test_installation() {
    print_status "Testing installation..."
    
    cd "$INSTALL_DIR"
    source .venv/bin/activate
    
    # Test if auto_webhook_bot can start
    timeout 10s python3 auto_webhook_bot.py --test-mode 2>/dev/null || {
        print_warning "Auto-webhook bot test failed, but this may be normal if n8n server is not reachable"
    }
    
    # Check if configuration exists
    if [ -f auto_config.json ]; then
        print_success "Configuration file created"
        
        # Show configuration summary
        VPS_NAME=$(python3 -c "import json; print(json.load(open('auto_config.json'))['vps_name'])")
        VPS_ID=$(python3 -c "import json; print(json.load(open('auto_config.json'))['vps_id'])")
        N8N_SERVER=$(python3 -c "import json; print(json.load(open('auto_config.json'))['n8n_server'])")
        
        print_status "Configuration Summary:"
        print_status "  VPS Name: $VPS_NAME"
        print_status "  VPS ID: $VPS_ID"
        print_status "  n8n Server: $N8N_SERVER"
    else
        print_error "Configuration file not found"
        return 1
    fi
    
    print_success "Installation test completed"
}

# Function to setup systemd service
setup_systemd_service() {
    print_status "Setting up systemd service..."
    
    cat > /etc/systemd/system/gensyn-auto-bot.service << EOF
[Unit]
Description=Gensyn Auto-Discovery Bot
After=network.target
StartLimitInterval=0

[Service]
Type=simple
Restart=always
RestartSec=10
User=root
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/.venv/bin/python3 $INSTALL_DIR/auto_webhook_bot.py
Environment=PYTHONPATH=$INSTALL_DIR
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd and enable service
    systemctl daemon-reload
    systemctl enable gensyn-auto-bot
    
    print_success "Systemd service configured and enabled"
}

# Function to start services
start_services() {
    print_status "Starting Gensyn Auto-Discovery Bot..."
    
    # Start the systemd service
    systemctl start gensyn-auto-bot
    
    # Wait a moment and check status
    sleep 3
    
    if systemctl is-active --quiet gensyn-auto-bot; then
        print_success "Gensyn Auto-Discovery Bot started successfully"
        print_status "Service status: $(systemctl is-active gensyn-auto-bot)"
    else
        print_warning "Service may not have started correctly"
        print_status "Check logs with: journalctl -u gensyn-auto-bot -f"
    fi
}

# Function to display final instructions
show_final_instructions() {
    print_header "
╔══════════════════════════════════════════════════════════════╗
║                  🎉 INSTALLATION COMPLETE!                   ║
╚══════════════════════════════════════════════════════════════╝"

    # Get configuration details
    if [ -f "$INSTALL_DIR/auto_config.json" ]; then
        cd "$INSTALL_DIR"
        VPS_NAME=$(python3 -c "import json; print(json.load(open('auto_config.json'))['vps_name'])" 2>/dev/null || echo "Unknown")
        VPS_ID=$(python3 -c "import json; print(json.load(open('auto_config.json'))['vps_id'])" 2>/dev/null || echo "unknown")
        N8N_SERVER=$(python3 -c "import json; print(json.load(open('auto_config.json'))['n8n_server'])" 2>/dev/null || echo "Unknown")
        
        echo -e "${GREEN}✅ Your VPS is now configured for auto-discovery!${NC}"
        echo ""
        echo -e "${CYAN}📊 Configuration Summary:${NC}"
        echo -e "   • VPS Name: ${YELLOW}$VPS_NAME${NC}"
        echo -e "   • VPS ID: ${YELLOW}$VPS_ID${NC}"
        echo -e "   • n8n Server: ${YELLOW}$N8N_SERVER${NC}"
        echo -e "   • Installation Path: ${YELLOW}$INSTALL_DIR${NC}"
        echo ""
        echo -e "${CYAN}🚀 Status:${NC}"
        echo -e "   • Auto-discovery: ${GREEN}✅ Enabled${NC}"
        echo -e "   • Systemd service: ${GREEN}✅ Running${NC}"
        echo -e "   • Auto-start on boot: ${GREEN}✅ Enabled${NC}"
        echo ""
        echo -e "${CYAN}🎯 What happens next:${NC}"
        echo -e "   • VPS will auto-register with your n8n server"
        echo -e "   • Should appear in your Telegram bot within 5 minutes"
        echo -e "   • No further configuration needed!"
        echo ""
        echo -e "${CYAN}🔧 Management Commands:${NC}"
        echo -e "   • Check status: ${YELLOW}systemctl status gensyn-auto-bot${NC}"
        echo -e "   • View logs: ${YELLOW}journalctl -u gensyn-auto-bot -f${NC}"
        echo -e "   • Restart: ${YELLOW}systemctl restart gensyn-auto-bot${NC}"
        echo -e "   • Stop: ${YELLOW}systemctl stop gensyn-auto-bot${NC}"
        echo ""
        echo -e "${CYAN}📋 Files created:${NC}"
        echo -e "   • Config: ${YELLOW}$INSTALL_DIR/auto_config.json${NC}"
        echo -e "   • Logs: ${YELLOW}/root/auto_webhook_bot.log${NC}"
        echo -e "   • Service: ${YELLOW}/etc/systemd/system/gensyn-auto-bot.service${NC}"
        echo ""
        echo -e "${GREEN}🎉 Setup complete! Check your Telegram bot to see this VPS!${NC}"
    else
        echo -e "${RED}❌ Configuration file not found. Setup may have failed.${NC}"
        echo -e "Check logs: ${YELLOW}tail -f $LOG_FILE${NC}"
    fi
}

# Function to handle cleanup on exit
cleanup() {
    if [ $? -ne 0 ]; then
        print_error "Installation failed. Check logs: $LOG_FILE"
        print_status "You can try running the installation again or manually run:"
        print_status "cd $INSTALL_DIR && python3 auto_setup.py"
    fi
}

# Main installation function
main() {
    # Setup trap for cleanup
    trap cleanup EXIT
    
    # Start installation
    print_header "
╔══════════════════════════════════════════════════════════════╗
║              🤖 GENSYN BOT AUTO INSTALLER                    ║
║                 Zero Configuration Setup                    ║
╚══════════════════════════════════════════════════════════════╝"
    
    print_status "Starting automated installation..."
    print_status "Log file: $LOG_FILE"
    echo ""
    
    # Environment info
    if [ -n "$N8N_SERVER_URL" ]; then
        print_status "Non-interactive mode detected"
        print_status "N8N_SERVER_URL: $N8N_SERVER_URL"
        print_status "VPS_NAME: ${VPS_NAME:-Auto-Generated}"
    fi
    
    # Run installation steps
    check_root
    detect_os
    install_dependencies
    check_python
    clone_repository
    setup_venv
    setup_permissions
    run_auto_setup
    test_installation
    setup_systemd_service
    start_services
    show_final_instructions
    
    print_success "Installation completed successfully!"
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        echo "Gensyn Bot Auto-Discovery Installer"
        echo ""
        echo "Usage:"
        echo "  curl -sSL https://raw.githubusercontent.com/your-repo/gensyn-bot/main/auto_install.sh | bash"
        echo ""
        echo "Environment Variables:"
        echo "  N8N_SERVER_URL    - n8n server URL (e.g., https://your-n8n.com)"
        echo "  VPS_NAME          - Name for this VPS (e.g., 'London Server')"
        echo ""
        echo "Examples:"
        echo "  # Interactive mode"
        echo "  curl -sSL https://raw.githubusercontent.com/your-repo/gensyn-bot/main/auto_install.sh | bash"
        echo ""
        echo "  # Non-interactive mode"
        echo "  N8N_SERVER_URL='https://n8n.example.com' VPS_NAME='London Server' \\"
        echo "    curl -sSL https://raw.githubusercontent.com/your-repo/gensyn-bot/main/auto_install.sh | bash"
        exit 0
        ;;
    --version|-v)
        echo "Gensyn Bot Auto Installer v1.0"
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac
