#!/bin/bash

# --- Configuration Variables ---
PROJECT_NAME="CandyPanelAgent" # Name for this agent deployment
REPO_URL="https://github.com/AmiRCandy/Candy-Panel.git" # URL to your Candy Panel repository
AGENT_ROOT="/var/www/$PROJECT_NAME" # Directory where the agent will be installed
BACKEND_CODE_DIR="$AGENT_ROOT/Backend" # Directory where core.py, db.py, agent.py will reside after cloning
AGENT_APP_ENTRY="agent.py" # Agent app entry point
LINUX_USER=$(whoami) # User who will run the agent service

# Default Agent Port (ensure this is unique and open on remote servers)
DEFAULT_AGENT_PORT="3447"

# NVM specific (only if you need Node.js on the agent server for other purposes, usually not required for agent itself)
# NVM_VERSION="v0.40.3"
# NODE_VERSION="22"

SUDOERS_FILE="/etc/sudoers.d/candypanel_agent_permissions" # For agent-specific sudoers config

# --- Styling Functions ---
GREEN='\e[32m'
BLUE='\e[34m'
RED='\e[31m'
YELLOW='\e[33m'
CYAN='\e[36m'
RESET='\e[0m'
BOLD='\e[1m'
UNDERLINE='\e[4m'

print_header() {
    local title=$1
    echo -e "\n${BOLD}${CYAN}====================================================${RESET}"
    echo -e "${BOLD}${CYAN} $title ${RESET}"
    echo -e "${BOLD}${CYAN}====================================================${RESET}"
    echo -e "${BOLD}${YELLOW} Agent Name: $PROJECT_NAME${RESET}"
    echo -e "${BOLD}${YELLOW} User: $LINUX_USER${RESET}"
    echo -e "${BOLD}${CYAN}====================================================${RESET}\n"
    sleep 1
}

print_info() {
    echo -e "${BLUE}INFO:${RESET} $1"
}

print_success() {
    echo -e "${GREEN}SUCCESS:${RESET} $1"
}

print_error() {
    echo -e "${RED}ERROR:${RESET} $1" >&2
}

print_warning() {
    echo -e "${YELLOW}WARNING:${RESET} $1"
}

confirm_action() {
    read -p "$(echo -e "${YELLOW}CONFIRM:${RESET} $1 (y/N)? ") " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_error "Operation cancelled by user."
        exit 1
    fi
}

# --- Install Functions ---
check_prerequisites() {
    print_info "Checking for required system packages..."
    local missing_packages=()
    
    PYTHON_VERSION=$(python3 -c "import sys; print(f'python3.{sys.version_info.minor}')")
    PYTHON_VENV_PACKAGE="${PYTHON_VERSION}-venv"

    for cmd in git python3 ufw cron build-essential python3-dev openresolv; do
        if ! command -v "$cmd" &> /dev/null; then
            missing_packages+=("$cmd")
        fi
    done

    if ! dpkg -s "$PYTHON_VENV_PACKAGE" &> /dev/null; then
        missing_packages+=("$PYTHON_VENV_PACKAGE")
    fi

    if ! command -v curl &> /dev/null; then
        missing_packages+=("curl")
    fi

    if [ ${#missing_packages[@]} -gt 0 ]; then
        print_warning "The following required packages are not installed: ${missing_packages[*]}"
        confirm_action "Attempt to install missing packages?"
        
        local package_manager=""
        if command -v apt &> /dev/null; then
            package_manager="apt"
        elif command -v yum &> /dev/null; then
            package_manager="yum"
        else
            print_error "No supported package manager (apt or yum) found. Please install packages manually."
            exit 1
        fi

        print_info "Using $package_manager to install missing packages..."
        if [ "$package_manager" == "apt" ]; then
            sudo apt update && sudo apt install -y "${missing_packages[@]}"
        elif [ "$package_manager" == "yum" ]; then
            sudo yum install -y "${missing_packages[@]}"
        fi

        if [ $? -ne 0 ]; then
            print_error "Failed to install some required packages. Please check the output and install them manually."
        else
            print_success "Missing packages installed successfully."
        fi
    else
        print_success "All required system packages found."
    fi
    sleep 1
}

setup_permissions() {
    print_info "--- Setting up System Permissions and Installing Core Dependencies ---"
    sleep 1

    # Ensure the user provided for CANDYPANEL_USER exists on this remote server
    if ! id "$LINUX_USER" &>/dev/null; then
        print_error "Error: User '$LINUX_USER' does not exist."
        print_error "Please create the user first (e.g., 'sudo adduser $LINUX_USER') or ensure you run this script as an existing user."
        exit 1
    fi

    print_info "Installing core system packages: wireguard, qrencode, python3-psutil..."
    sudo apt install -y wireguard qrencode python3-psutil || { print_error "Failed to install core system packages."; exit 1; }
    print_success "Core system packages installed."

    print_info "Configuring sudoers for user '$LINUX_USER' to allow specific WireGuard/UFW/systemctl commands without password..."

    cat <<EOF | sudo tee "$SUDOERS_FILE" > /dev/null
# Allow $LINUX_USER to manage WireGuard, UFW, systemctl, and cron for CandyPanel Agent
$LINUX_USER ALL=(ALL) NOPASSWD: /usr/bin/wg genkey, /usr/bin/wg pubkey, /usr/bin/wg show *, /usr/bin/wg syncconf *, /usr/bin/wg-quick up *, /usr/bin/wg-quick down *, /usr/bin/systemctl enable wg-quick@*, /usr/bin/systemctl start wg-quick@*, /usr/bin/systemctl stop wg-quick@*, /usr/sbin/ufw allow *, /usr/sbin/ufw delete *, /usr/bin/crontab
EOF

    sudo chmod 0440 "$SUDOERS_FILE" || { print_error "Failed to set permissions for sudoers file."; exit 1; }
    print_success "Sudoers configured successfully in '$SUDOERS_FILE'."
    print_info "You can verify the sudoers file with: 'sudo visudo -cf $SUDOERS_FILE'"
    sleep 1
}

clone_or_update_repo() {
    print_info "Starting agent deployment process..."
    sleep 1

    if [ -d "$AGENT_ROOT" ]; then
        print_warning "Agent directory '$AGENT_ROOT' already exists."
        confirm_action "Do you want to pull the latest agent changes from the repository?"
        print_info "Navigating to $BACKEND_CODE_DIR and pulling latest changes..."
        # Navigate to the Backend subdirectory of the cloned repo for pulling updates
        sudo git -C "$BACKEND_CODE_DIR" pull origin dev.test || sudo git -C "$BACKEND_CODE_DIR" pull origin dev.test
        if [ $? -ne 0 ]; then
            print_error "Failed to pull latest changes from repository. Check permissions or network."
            exit 1
        fi
        print_success "Agent repository updated."
    else
        print_info "Cloning repository '$REPO_URL' into '$AGENT_ROOT'..."
        sudo mkdir -p "$(dirname "$AGENT_ROOT")"
        # Clone the full repo, we will then specify the backend subdirectory for agent components
        sudo git clone --branch dev.test --single-branch "$REPO_URL" "$AGENT_ROOT" || { print_error "Failed to clone repository"; exit 1; }
        sudo chown -R "$LINUX_USER:$LINUX_USER" "$AGENT_ROOT" || { print_warning "Could not change ownership of $AGENT_ROOT to $LINUX_USER. Manual intervention might be needed for permissions."; }
        print_success "Repository cloned successfully."
    fi
    sleep 1
}

deploy_agent_backend() {
    print_info "--- Deploying Agent Backend ---"
    sleep 1

    print_info "Navigating to backend code directory: $BACKEND_CODE_DIR"
    cd "$BACKEND_CODE_DIR" || { print_error "Backend code directory not found: $BACKEND_CODE_DIR"; exit 1; }

    print_info "Creating and activating Python virtual environment..."
    python3 -m venv venv || { print_error "Failed to create virtual environment."; exit 1; }
    source venv/bin/activate || { print_error "Failed to activate virtual environment."; exit 1; }
    print_success "Virtual environment activated."
    sleep 1

    print_info "Installing Python dependencies (Flask, httpx etc.)..."
    # Agent only needs core Flask, httpx, psutil, nanoid, netifaces
    pip install flask[async] httpx psutil nanoid netifaces || { print_error "Failed to install Python dependencies for agent."; exit 1; }
    print_success "Python dependencies for agent installed."
    sleep 1

    print_info "Creating Systemd service file for Agent..."
    sudo tee "/etc/systemd/system/${PROJECT_NAME}.service" > /dev/null <<EOF
[Unit]
Description=CandyPanel Agent Service
After=network.target

[Service]
User=$LINUX_USER
Group=$LINUX_USER
WorkingDirectory=$BACKEND_CODE_DIR
Environment="AGENT_PORT=$AGENT_PORT"
Environment="AGENT_API_KEY=$AGENT_API_KEY_INPUT" # Use the API key provided by user
ExecStart=$BACKEND_CODE_DIR/venv/bin/python3 $AGENT_APP_ENTRY
Restart=always
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF
    print_success "Systemd service file created for Agent."
    sleep 1

    print_info "Reloading Systemd daemon, enabling and starting Agent service..."
    sudo systemctl daemon-reload || { print_error "Failed to reload Systemd daemon."; exit 1; }
    sudo systemctl enable "${PROJECT_NAME}.service" || { print_error "Failed to enable Agent service."; exit 1; }
    sudo systemctl start "${PROJECT_NAME}.service" || { print_error "Failed to start Agent service."; exit 1; }
    
    # Configure cron job for agent's local sync
    print_info "Setting up cron job for agent's local sync..."
    local cron_script_path="$BACKEND_CODE_DIR/cron.py" # cron.py is in the Backend directory of cloned repo
    local cron_line="*/5 * * * * cd $BACKEND_CODE_DIR && source venv/bin/activate && python3 $cron_script_path >> /var/log/${PROJECT_NAME}_sync.log 2>&1"
    (sudo crontab -l -u "$LINUX_USER" 2>/dev/null | grep -v "$cron_script_path"; echo "$cron_line") | sudo crontab -u "$LINUX_USER" -
    print_success "Cron job for agent sync configured."
    sudo systemctl start cron
    print_info "You can check Agent status with: sudo systemctl status ${PROJECT_NAME}.service"
    print_info "View Agent logs with: journalctl -u ${PROJECT_NAME}.service --since '1 hour ago'"
    sleep 2
}

configure_firewall_agent() {
    print_info "--- Configuring Firewall (UFW) for Agent ---"
    sleep 1

    print_info "Enabling UFW (if not already enabled)..."
    sudo ufw status | grep -q "Status: active" || sudo ufw enable
    print_success "UFW is active."
    sleep 1

    local ssh_port
    if [ -n "$SSH_CLIENT" ]; then
        ssh_port=$(echo "$SSH_CLIENT" | awk '{print $3}')
        print_info "Detected SSH port: $ssh_port"
        print_info "Allowing SSH access on port $ssh_port..."
        sudo ufw allow "$ssh_port"/tcp || { print_error "Failed to allow SSH port $ssh_port through UFW."; exit 1; }
        print_success "SSH port $ssh_port allowed for external access."
    else
        print_warning "Could not detect SSH port from \$SSH_CLIENT. Please ensure SSH access is configured manually if needed."
    fi

    # The agent will likely run on the same server as WireGuard itself.
    # We need to ask for the WireGuard port.
    local wg_port_input
    read -p "$(echo -e "${YELLOW}INPUT:${RESET} Enter the WireGuard UDP port for this server (e.g., 51820): ")" wg_port_input
    if [[ -z "$wg_port_input" ]]; then
        print_error "WireGuard port cannot be empty. Exiting."
        exit 1
    fi

    print_info "Allowing external UDP access to WireGuard port $wg_port_input..."
    sudo ufw allow "$wg_port_input"/udp || { print_error "Failed to allow WireGuard port $wg_port_input through UFW."; exit 1; }
    print_success "WireGuard port $wg_port_input allowed."

    print_info "Allowing external access to agent's port $AGENT_PORT..."
    sudo ufw allow "$AGENT_PORT"/tcp || { print_error "Failed to allow agent port $AGENT_PORT through UFW."; exit 1; }
    print_success "Agent port $AGENT_PORT allowed for external access."

    print_info "You can check UFW status with: sudo ufw status"
    sleep 2
}


# --- Main Install Logic for Agent ---
run_install_agent() {
    print_header "Candy Panel Agent Deployment Script"
    print_info "This script will deploy only the Candy Panel Agent on this server."
    print_info "You will need to provide an API Key that your Central Candy Panel will use to connect to this agent."
    
    read -p "$(echo -e "${YELLOW}INPUT:${RESET} Enter the Agent API Key for this server (MUST be a strong, unique string): ")" AGENT_API_KEY_INPUT
    if [ -z "$AGENT_API_KEY_INPUT" ]; then
        print_error "Agent API Key cannot be empty. Exiting."
        exit 1
    fi
    export AGENT_API_KEY_INPUT

    read -p "$(echo -e "${YELLOW}INPUT:${RESET} Enter the Agent Port for this server (default: $DEFAULT_AGENT_PORT): ")" AGENT_PORT_INPUT
    export AGENT_PORT="${AGENT_PORT_INPUT:-$DEFAULT_AGENT_PORT}"

    check_prerequisites
    setup_permissions
    clone_or_update_repo
    deploy_agent_backend
    configure_firewall_agent

    echo -e "\n${BOLD}${GREEN}====================================================${RESET}"
    echo -e "${BOLD}${GREEN} Agent Deployment Complete!                         ${RESET}"
    echo -e "${BOLD}${GREEN}====================================================${RESET}"
    echo -e "${BOLD}${GREEN} The agent is running on this server at: http://$(hostname -I | awk '{print $1}'):$AGENT_PORT${RESET}"
    print_warning "Copy the above IP and Agent Port, along with your AGENT_API_KEY_INPUT, into your Central Candy Panel's Server Management tab to register this server."
    echo -e "${BOLD}${GREEN}====================================================${RESET}\n"
}

# --- Menu Logic ---
show_menu() {
    print_header "Candy Panel Agent Management Script"
    echo -e "${BOLD}${BLUE}Please choose an option:${RESET}"
    echo -e "  ${GREEN}1) Install Candy Panel Agent${RESET}"
    echo -e "  ${CYAN}2) Quit${RESET}"
    echo -e "----------------------------------------------------"
    read -p "$(echo -e "${BOLD}${BLUE}Enter your choice [1-2]: ${RESET}")" choice
}

# --- Main execution ---
while true; do
    show_menu
    case $choice in
        1)
            run_install_agent
            break
            ;;
        2)
            print_info "Exiting script. Goodbye!"
            exit 0
            ;;
        *)
            print_error "Invalid choice. Please enter a number between 1 and 2."
            sleep 2
            ;;
    esajc
done