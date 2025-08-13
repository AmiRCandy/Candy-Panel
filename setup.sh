#!/bin/bash

# --- Configuration Variables ---
PROJECT_NAME="CandyPanel"
REPO_URL="https://github.com/AmiRCandy/Candy-Panel.git"
PROJECT_ROOT="/var/www/$PROJECT_NAME"
BACKEND_DIR="$PROJECT_ROOT/Backend"
FRONTEND_DIR="$PROJECT_ROOT/Frontend"
FLASK_APP_ENTRY="main.py" # Ensure this is the file where your Flask app is defined and serves static files
LINUX_USER=$(whoami)
# --- Backend specific configuration ---
# Flask will now serve both frontend and backend on this port
BACKEND_HOST="0.0.0.0"
BACKEND_PORT="3446" # This will be the publicly accessible port for everything

# NVM specific
NVM_VERSION="v0.40.3" # Always check https://github.com/nvm-sh/nvm for the latest version
NODE_VERSION="22" # Install Node.js v22.x.x

SUDOERS_FILE="/etc/sudoers.d/candypanel_permissions" # For uninstall script

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
    echo -e "${BOLD}${YELLOW} Project: $PROJECT_NAME${RESET}"
    echo -e "${BOLD}${YELLOW} Repo: $REPO_URL${RESET}"
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
    
    # Get the system's default Python 3 version
    PYTHON_VERSION=$(python3 -c "import sys; print(f'python3.{sys.version_info.minor}')")
    PYTHON_VENV_PACKAGE="${PYTHON_VERSION}-venv"

    for cmd in git python3 ufw cron build-essential python3-dev openresolv; do
        if ! command -v "$cmd" &> /dev/null; then
            missing_packages+=("$cmd")
        fi
    done

    # Add the specific python3-venv package based on the system's Python 3 version
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
            #exit 1
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

    read -p "$(echo -e "${YELLOW}INPUT:${RESET} Please enter the username that will run the CandyPanel application (e.g., candypaneluser): ")" CANDYPANEL_USER

    if ! id "$CANDYPANEL_USER" &>/dev/null; then
        print_error "Error: User '$CANDYPANEL_USER' does not exist."
        print_error "Please create the user first (e.g., 'sudo adduser $CANDYPANEL_USER') or enter an existing one."
        exit 1
    fi

    echo "User '$CANDYPANEL_USER' selected for CandyPanel operations."

    print_info "Installing core system packages: wireguard, qrencode, python3-psutil..."
    sudo apt install -y wireguard qrencode python3-psutil || { print_error "Failed to install core system packages."; exit 1; }
    print_success "Core system packages installed."

    print_info "Configuring sudoers for user '$CANDYPANEL_USER' to allow specific commands without password..."

    cat <<EOF | sudo tee "$SUDOERS_FILE" > /dev/null
# Allow $CANDYPANEL_USER to manage WireGuard, UFW, systemctl, and cron for CandyPanel
$CANDYPANEL_USER ALL=(ALL) NOPASSWD: /usr/bin/wg genkey, /usr/bin/wg pubkey, /usr/bin/wg show *, /usr/bin/wg syncconf *, /usr/bin/wg-quick up *, /usr/bin/wg-quick down *, /usr/bin/systemctl enable wg-quick@*, /usr/bin/systemctl start wg-quick@*, /usr/bin/systemctl stop wg-quick@*, /usr/sbin/ufw allow *, /usr/sbin/ufw delete *, /usr/bin/crontab
EOF

    sudo chmod 0440 "$SUDOERS_FILE" || { print_error "Failed to set permissions for sudoers file."; exit 1; }
    print_success "Sudoers configured successfully in '$SUDOERS_FILE'."
    print_info "You can verify the sudoers file with: 'sudo visudo -cf $SUDOERS_FILE'"
    sleep 1
}

install_nodejs_with_nvm() {
    print_info "--- Installing Node.js and npm using NVM ---"
    sleep 1

    if [ -s "$HOME/.nvm/nvm.sh" ]; then
        print_warning "NVM appears to be already installed. Sourcing it..."
        . "$HOME/.nvm/nvm.sh"
    else
        print_info "Installing NVM (Node Version Manager)..."
        curl -o- "https://raw.githubusercontent.com/nvm-sh/nvm/$NVM_VERSION/install.sh" | bash || { print_error "Failed to download and install NVM."; exit 1; }
        
        export NVM_DIR="$HOME/.nvm"
        [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
        [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"
        
        if ! command -v nvm &> /dev/null; then
            print_error "NVM command not found after installation and sourcing. Please check NVM installation manually."
            exit 1
        fi
        print_success "NVM installed successfully."
    fi

    print_info "Installing Node.js v${NODE_VERSION} (and bundled npm)..."
    nvm install "$NODE_VERSION" || { print_error "Failed to install Node.js v${NODE_VERSION}."; exit 1; }
    print_success "Node.js v${NODE_VERSION} and npm installed."

    print_info "Setting Node.js v${NODE_VERSION} as the default version..."
    nvm alias default "$NODE_VERSION" || { print_error "Failed to set default Node.js version."; exit 1; }
    print_success "Node.js v${NODE_VERSION} set as default."

    print_info "Using Node.js v${NODE_VERSION} for current session..."
    nvm use "$NODE_VERSION" || { print_error "Failed to switch to Node.js v${NODE_VERSION}."; exit 1; }
    print_success "Node.js v${NODE_VERSION} is now active."

    node -v
    npm -v
    sleep 1
}

clone_or_update_repo() {
    print_info "Starting deployment process for $PROJECT_NAME..."
    sleep 1

    if [ -d "$PROJECT_ROOT" ]; then
        print_warning "Project directory '$PROJECT_ROOT' already exists."
        confirm_action "Do you want to pull the latest changes from the repository?"
        print_info "Navigating to $PROJECT_ROOT and pulling latest changes..."
        sudo git -C "$PROJECT_ROOT" pull origin main || sudo git -C "$PROJECT_ROOT" pull origin main
        if [ $? -ne 0 ]; then
            print_error "Failed to pull latest changes from repository. Check permissions or network."
            exit 1
        fi
        print_success "Repository updated."
    else
        print_info "Cloning repository '$REPO_URL' into '$PROJECT_ROOT'..."
        sudo mkdir -p "$(dirname "$PROJECT_ROOT")"

        sudo git clone --branch main --single-branch "$REPO_URL" "$PROJECT_ROOT" || { print_error "Failed to clone repository"; exit 1; }
        sudo chown -R "$LINUX_USER:$LINUX_USER" "$PROJECT_ROOT" || { print_warning "Could not change ownership of $PROJECT_ROOT to $LINUX_USER. Manual intervention might be needed for permissions."; }
        print_success "Repository cloned successfully."
    fi
    sleep 1
}

deploy_backend() {
    print_info "--- Deploying Flask Backend ---"
    sleep 1

    print_info "Navigating to backend directory: $BACKEND_DIR"
    cd "$BACKEND_DIR" || { print_error "Backend directory not found: $BACKEND_DIR"; exit 1; }

    print_info "Creating and activating Python virtual environment..."
    # Use the discovered Python executable
    python3 -m venv venv || { print_error "Failed to create virtual environment."; exit 1; }
    source venv/bin/activate || { print_error "Failed to activate virtual environment."; exit 1; }
    print_success "Virtual environment activated."
    sleep 1

    print_info "Installing Python dependencies (Flask etc.)..."
    # Install netifaces with required build dependencies if needed
    pip install pyrogram flask[async] requests flask_cors psutil httpx tgcrypto nanoid || { print_error "Failed to install Python dependencies."; exit 1; }
    print_info "Attempting to install netifaces specifically, including build dependencies..."
    
    # Try installing netifaces with potential build dependencies for different distros
    if command -v apt &> /dev/null; then
        sudo apt install -y python3-netifaces || { print_error "Failed to install netifaces. Check build-essential and python3-dev installations."; exit 1; }
        pip install netifaces || { print_error "Failed to install netifaces. Check build-essential and python3-dev installations."; exit 1; }
    elif command -v yum &> /dev/null; then
        sudo yum install -y python3-netifaces || { print_error "Failed to install netifaces. Check build-essential and python3-devel installations."; exit 1; }
        pip install netifaces || { print_error "Failed to install netifaces. Check build-essential and python3-dev installations."; exit 1; }
    else
        pip install netifaces || print_warning "Failed to install netifaces. Please install it manually with appropriate system headers if needed."
    fi

    print_success "Python dependencies installed."
    sleep 1

    print_info "Creating Systemd service file for Flask..."
    sudo tee "/etc/systemd/system/${PROJECT_NAME}_flask.service" > /dev/null <<EOF
[Unit]
Description=Flask instance for ${PROJECT_NAME}
After=network.target

[Service]
User=$LINUX_USER
Group=$LINUX_USER
WorkingDirectory=$BACKEND_DIR
Environment="FLASK_APP=$FLASK_APP_ENTRY"
Environment="FLASK_RUN_HOST=$BACKEND_HOST"
Environment="FLASK_RUN_PORT=$BACKEND_PORT"
ExecStart=$BACKEND_DIR/venv/bin/python3 $FLASK_APP_ENTRY
Restart=always
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF
    print_success "Systemd service file created."
    sleep 1

    print_info "Reloading Systemd daemon, enabling and starting Flask service..."
    sudo systemctl daemon-reload || { print_error "Failed to reload Systemd daemon."; exit 1; }
    sudo systemctl enable "${PROJECT_NAME}_flask.service" || { print_error "Failed to enable Flask service."; exit 1; }
    sudo systemctl enable cron
    sudo systemctl start "${PROJECT_NAME}_flask.service" || { print_error "Failed to start Flask service."; exit 1; }
    sudo systemctl start cron
    print_success "Flask service started and enabled to run on boot."
    print_info "You can check its status with: sudo systemctl status ${PROJECT_NAME}_flask.service"
    print_info "View logs with: journalctl -u ${PROJECT_NAME}_flask.service --since '1 hour ago'"
    sleep 2
}

deploy_frontend() {
    print_info "--- Deploying React Vite Frontend ---"
    sleep 1

    print_info "Navigating to frontend directory: $FRONTEND_DIR"
    cd "$FRONTEND_DIR" || { print_error "Frontend directory not found: $FRONTEND_DIR"; exit 1; }

    if [ -s "$HOME/.nvm/nvm.sh" ]; then
        . "$HOME/.nvm/nvm.sh"
        nvm use "$NODE_VERSION" || print_warning "Could not activate Node.js v${NODE_VERSION} with nvm in this subshell. Continuing anyway."
    else
        print_error "NVM not found or not sourced. Node.js/npm commands might fail."
        exit 1
    fi

    print_info "Installing Node.js dependencies..."
    npm install || { print_error "Failed to install Node.js dependencies. Check npm logs and internet connection."; exit 1; }
    print_success "Node.js dependencies installed."
    sleep 1
}

configure_frontend_api_url() {
    print_info "--- Configuring Frontend API URL ---"
    sleep 1

    local server_ip
    read -p "$(echo -e "${YELLOW}INPUT:${RESET} Enter your server's public IP address (e.g., 192.168.1.100) or domain name if using one: ")" server_ip
    if [ -z "$server_ip" ]; then
        print_error "Server IP/Domain cannot be empty. Exiting."
        exit 1
    fi

    local frontend_api_url="http://$server_ip:$BACKEND_PORT"

    print_info "Writing frontend environment variable VITE_APP_API_URL to .env.production..."
    echo "export VITE_APP_API_URL=$frontend_api_url" | sudo tee "$FRONTEND_DIR/.env.production" > /dev/null || { print_error "Failed to write .env.production file. Check permissions."; exit 1; }
    echo "export AP_PORT=$BACKEND_PORT" | sudo tee "$FRONTEND_DIR/.env.production" > /dev/null || { print_error "Failed to write .env.production file. Check permissions."; exit 1; }
    print_success ".env.production created/updated with VITE_APP_API_URL=$frontend_api_url"
    sudo chown "$LINUX_USER:$LINUX_USER" "$FRONTEND_DIR/.env.production" || { print_warning "Could not change ownership of .env.production. Manual intervention might be needed for permissions."; }
    sleep 1

    print_info "Rebuilding frontend to apply new API URL..."
    cd "$FRONTEND_DIR" || { print_error "Frontend directory not found: $FRONTEND_DIR"; exit 1; }
    npm run build || { print_error "Failed to rebuild React Vite frontend after updating API URL."; exit 1; }
    print_success "Frontend rebuilt successfully with updated API URL."
    sleep 1
}

configure_firewall() {
    print_info "--- Configuring Firewall (UFW) ---"
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

    print_info "Allowing external access to port $BACKEND_PORT for Flask application..."
    sudo ufw allow "$BACKEND_PORT"/tcp || { print_error "Failed to allow port $BACKEND_PORT through UFW."; exit 1; }
    print_success "Port $BACKEND_PORT allowed for external access."

    print_info "You can check UFW status with: sudo ufw status"
    sleep 2
}

# --- Uninstall Functions ---
get_backend_port() {
    if [ -n "$AP_PORT" ]; then
        BACKEND_PORT="$AP_PORT"
        print_info "Using BACKEND_PORT from AP_PORT environment variable: $BACKEND_PORT"
    else
        while true; do
            read -p "$(echo -e "${YELLOW}INPUT:${RESET} Please enter the backend port used by CandyPanel (e.g., 3446): ")" user_port
            if [[ "$user_port" =~ ^[0-9]+$ ]] && [ "$user_port" -ge 1 ] && [ "$user_port" -le 65535 ]; then
                BACKEND_PORT="$user_port"
                print_info "Using BACKEND_PORT from user input: $BACKEND_PORT"
                break
            else
                print_error "Invalid port number. Please enter a number between 1 and 65535."
            fi
        done
    fi
    export BACKEND_PORT
    sleep 1
}

uninstall_backend_service() {
    print_info "--- Stopping and Disabling Flask Backend Service ---"
    sleep 1

    local service_name="${PROJECT_NAME}_flask.service"

    if sudo systemctl is-active --quiet "$service_name"; then
        print_info "Stopping Flask service: $service_name..."
        sudo systemctl stop "$service_name" || { print_warning "Failed to stop Flask service. It might not be running."; }
        print_success "Flask service stopped."
    else
        print_info "Flask service '$service_name' is not active."
    fi

    if sudo systemctl is-enabled --quiet "$service_name"; then
        print_info "Disabling Flask service: $service_name..."
        sudo systemctl disable "$service_name" || { print_warning "Failed to disable Flask service. It might already be disabled."; }
        print_success "Flask service disabled."
    else
        print_info "Flask service '$service_name' is not enabled."
    fi

    if [ -f "/etc/systemd/system/$service_name" ]; then
        print_info "Removing Systemd service file: /etc/systemd/system/$service_name..."
        sudo rm "/etc/systemd/system/$service_name" || { print_error "Failed to remove Systemd service file."; exit 1; }
        print_success "Systemd service file removed."
    else
        print_info "Systemd service file '/etc/systemd/system/$service_name' not found."
    fi
    
    print_info "Reloading Systemd daemon..."
    sudo systemctl daemon-reload || { print_warning "Failed to reload Systemd daemon. This might not be critical for uninstallation."; }
    print_success "Systemd daemon reloaded."
    sleep 2
}

remove_project_directory() {
    print_info "--- Removing Project Directory ---"
    sleep 1

    if [ -d "$PROJECT_ROOT" ]; then
        confirm_action "Are you sure you want to delete the project directory '$PROJECT_ROOT' and all its contents? This action is irreversible."
        print_info "Deleting project directory: $PROJECT_ROOT..."
        sudo rm -rf "$PROJECT_ROOT" || { print_error "Failed to remove project directory. Check permissions."; exit 1; }
        print_success "Project directory '$PROJECT_ROOT' removed successfully."
    else
        print_info "Project directory '$PROJECT_ROOT' does not exist. Nothing to remove."
    fi
    sleep 1
}

remove_firewall_rules() {
    print_info "--- Removing Firewall Rules ---"
    sleep 1

    if sudo ufw status | grep -q "Status: active"; then
        print_info "Checking for UFW rule for port $BACKEND_PORT..."
        if sudo ufw status | grep -q "ALLOW IN.*$BACKEND_PORT/tcp"; then
            print_info "Deleting UFW rule for port $BACKEND_PORT..."
            sudo ufw delete allow $BACKEND_PORT/tcp || { print_warning "Failed to delete UFW rule for port $BACKEND_PORT. Manual removal might be needed."; }
            print_success "UFW rule for port $BACKEND_PORT removed."
        else
            print_info "No UFW rule found for port $BACKEND_PORT."
        fi
    else
        print_info "UFW is not active. No firewall rules to remove via UFW."
    fi
    sleep 1
}

uninstall_nvm() {
    print_info "--- Uninstalling NVM and Node.js (Optional) ---"
    sleep 1

    if [ -d "$HOME/.nvm" ]; then
        confirm_action "Do you want to uninstall NVM (Node Version Manager) and all Node.js versions managed by it? This will remove '$HOME/.nvm'."
        print_info "Attempting to uninstall NVM..."
        if [ -s "$HOME/.nvm/nvm.sh" ]; then
            . "$HOME/.nvm/nvm.sh"
            nvm deactivate > /dev/null 2>&1
            nvm uninstall --lts > /dev/null 2>&1
            nvm uninstall "$(nvm current)" > /dev/null 2>&1
        fi

        rm -rf "$HOME/.nvm"
        sed -i '/NVM_DIR/d' "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile" 2>/dev/null
        sed -i '/nvm.sh/d' "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile" 2>/dev/null
        sed -i '/bash_completion/d' "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile" 2>/dev/null
        print_success "NVM and associated Node.js versions removed."
        print_warning "You may need to manually remove any remaining Node.js related binaries from your PATH if they were installed globally outside NVM."
    else
        print_info "NVM directory '$HOME/.nvm' not found. Nothing to uninstall."
    fi
    sleep 1
}

remove_sudoers_file() {
    print_info "--- Removing Sudoers Configuration ---"
    sleep 1

    if [ -f "$SUDOERS_FILE" ]; then
        confirm_action "Do you want to remove the sudoers file '$SUDOERS_FILE' created for CandyPanel permissions? This will revoke specific passwordless sudo access for the CandyPanel user."
        print_info "Removing sudoers file: $SUDOERS_FILE..."
        sudo rm "$SUDOERS_FILE" || { print_error "Failed to remove sudoers file. Manual removal might be needed."; exit 1; }
        print_success "Sudoers file removed."
    else
        print_info "Sudoers file '$SUDOERS_FILE' not found. Nothing to remove."
    fi
    sleep 1
}

uninstall_wireguard() {
    print_info "--- Uninstalling WireGuard and its Configurations ---"
    sleep 1

    confirm_action "Do you want to uninstall WireGuard and remove its configuration files? This will remove all VPN configurations."

    print_info "Attempting to stop all active WireGuard interfaces..."
    for conf_file in /etc/wireguard/*.conf; do
        if [ -f "$conf_file" ]; then
            local interface_name=$(basename "$conf_file" .conf)
            print_info "Stopping WireGuard interface: $interface_name..."
            sudo wg-quick down "$interface_name" > /dev/null 2>&1 || print_warning "Could not stop WireGuard interface '$interface_name'. It might not be active or already stopped."
            sudo systemctl disable "wg-quick@${interface_name}.service" > /dev/null 2>&1 || print_warning "Could not disable WireGuard service for '$interface_name'. It might not be enabled."
            sudo rm -f "/etc/systemd/system/wg-quick@${interface_name}.service" > /dev/null 2>&1
        fi
    done
    print_success "Attempted to stop and disable WireGuard interfaces."

    print_info "Removing WireGuard packages (wireguard and wireguard-tools)..."
    if command -v apt &> /dev/null; then
        sudo apt purge -y wireguard wireguard-tools || print_warning "Failed to purge WireGuard packages. They might not be installed or require manual removal."
    elif command -v dnf &> /dev/null; then
        sudo dnf remove -y wireguard-tools || print_warning "Failed to remove WireGuard packages. They might not be installed or require manual removal."
    elif command -v pacman &> /dev/null; then
        sudo pacman -Rs --noconfirm wireguard-tools || print_warning "Failed to remove WireGuard packages. They might not be installed or require manual removal."
    else
        print_warning "Package manager not recognized. Please manually uninstall 'wireguard' and 'wireguard-tools' packages."
    fi
    print_success "WireGuard packages removal attempt complete."

    print_info "Removing WireGuard configuration directory: /etc/wireguard/..."
    if [ -d "/etc/wireguard/" ]; then
        sudo rm -rf "/etc/wireguard/" || { print_error "Failed to remove /etc/wireguard/. Check permissions."; }
        print_success "WireGuard configuration directory removed."
    else
        print_info "/etc/wireguard/ directory not found. Nothing to remove."
    fi

    print_info "Removing WireGuard connections from NetworkManager (if any)..."
    if command -v nmcli &> /dev/null; then
        local wg_connections=$(nmcli -t -f UUID,TYPE connection show --active | grep 'wireguard' | cut -d':' -f1)
        if [ -n "$wg_connections" ]; then
            for uuid in $wg_connections; do
                print_info "Deleting NetworkManager WireGuard connection (UUID: $uuid)..."
                sudo nmcli connection delete uuid "$uuid" || print_warning "Failed to delete NetworkManager WireGuard connection $uuid."
            done
            print_success "NetworkManager WireGuard connections removed."
        else
            print_info "No active WireGuard connections found in NetworkManager."
        fi
    else
        print_info "nmcli (NetworkManager CLI) not found. Skipping NetworkManager cleanup."
    fi
    
    print_info "Reloading Systemd daemon after WireGuard cleanup..."
    sudo systemctl daemon-reload || { print_warning "Failed to reload Systemd daemon. This might not be critical."; }
    print_success "Systemd daemon reloaded."
    sleep 2
}

# --- Main Install/Update/Uninstall Logic ---
run_install() {
    print_header "Candy Panel Deployment Script"
    confirm_action "This script will deploy your Candy panel with Flask serving both frontend and backend. Ensure you have updated the REPO_URL variable in the script."

    check_prerequisites
    setup_permissions
    install_nodejs_with_nvm
    clone_or_update_repo

    # Prompt for IPv6 information
    local ipv6_address_range
    local ipv6_dns
    read -p "$(echo -e "${YELLOW}INPUT:${RESET} Do you want to enable IPv6 support? (y/N)? ")" -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "$(echo -e "${YELLOW}INPUT:${RESET} Enter IPv6 Address Range for WireGuard clients (e.g., fd86:ea04:1115::1/64): ")" ipv6_address_range
        read -p "$(echo -e "${YELLOW}INPUT:${RESET} Enter IPv6 DNS Server (e.g., 2001:4860:4860::8888): ")" ipv6_dns
    fi

    deploy_backend "$ipv6_address_range" "$ipv6_dns"
    deploy_frontend
    configure_frontend_api_url
    configure_firewall

    echo -e "\n${BOLD}${GREEN}====================================================${RESET}"
    echo-e "${BOLD}${GREEN} Deployment Complete!                               ${RESET}"
    echo -e "${BOLD}${GREEN}====================================================${RESET}"
    echo -e "${BOLD}${GREEN} Your Candy Panel should now be accessible at:${RESET}"
    echo -e "${BOLD}${GREEN} http://YOUR_SERVER_IP:$BACKEND_PORT${RESET}"
    print_warning "Remember to replace YOUR_SERVER_IP with your actual server's public IP address."
    print_warning "Note: SSL is NOT configured with this setup. For HTTPS, you will need to add a reverse proxy like Nginx or Caddy."
    echo -e "${BOLD}${GREEN}====================================================${RESET}\n"
    print_info "Ensure the Linux user '$LINUX_USER' has appropriate permissions for WireGuard operations."
    print_info "Flask application is running on port $BACKEND_PORT and serving all content."
}
# A separate function for backend deployment to pass the new variables
deploy_backend() {
    local ipv6_address_range=$1
    local ipv6_dns=$2
    
    print_info "--- Deploying Flask Backend ---"
    sleep 1

    print_info "Navigating to backend directory: $BACKEND_DIR"
    cd "$BACKEND_DIR" || { print_error "Backend directory not found: $BACKEND_DIR"; exit 1; }

    print_info "Creating and activating Python virtual environment..."
    # Use the discovered Python executable
    python3 -m venv venv || { print_error "Failed to create virtual environment."; exit 1; }
    source venv/bin/activate || { print_error "Failed to activate virtual environment."; exit 1; }
    print_success "Virtual environment activated."
    sleep 1

    print_info "Installing Python dependencies (Flask etc.)..."
    # Install netifaces with required build dependencies if needed
    pip install pyrogram flask[async] requests flask_cors psutil httpx tgcrypto nanoid || { print_error "Failed to install Python dependencies."; exit 1; }
    print_info "Attempting to install netifaces specifically, including build dependencies..."
    
    # Try installing netifaces with potential build dependencies for different distros
    if command -v apt &> /dev/null; then
        sudo apt install -y python3-netifaces || { print_error "Failed to install netifaces. Check build-essential and python3-dev installations."; exit 1; }
        pip install netifaces || { print_error "Failed to install netifaces. Check build-essential and python3-dev installations."; exit 1; }
    elif command -v yum &> /dev/null; then
        sudo yum install -y python3-netifaces || { print_error "Failed to install netifaces. Check build-essential and python3-devel installations."; exit 1; }
        pip install netifaces || { print_error "Failed to install netifaces. Check build-essential and python3-dev installations."; exit 1; }
    else
        pip install netifaces || print_warning "Failed to install netifaces. Please install it manually with appropriate system headers if needed."
    fi

    print_success "Python dependencies installed."
    sleep 1

    print_info "Creating Systemd service file for Flask..."
    sudo tee "/etc/systemd/system/${PROJECT_NAME}_flask.service" > /dev/null <<EOF
[Unit]
Description=Flask instance for ${PROJECT_NAME}
After=network.target

[Service]
User=$LINUX_USER
Group=$LINUX_USER
WorkingDirectory=$BACKEND_DIR
Environment="FLASK_APP=$FLASK_APP_ENTRY"
Environment="FLASK_RUN_HOST=$BACKEND_HOST"
Environment="FLASK_RUN_PORT=$BACKEND_PORT"
Environment="WG_IPV6_ADDRESS=$ipv6_address_range"
Environment="WG_IPV6_DNS=$ipv6_dns"
ExecStart=$BACKEND_DIR/venv/bin/python3 $FLASK_APP_ENTRY
Restart=always
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF
    print_success "Systemd service file created."
    sleep 1

    print_info "Reloading Systemd daemon, enabling and starting Flask service..."
    sudo systemctl daemon-reload || { print_error "Failed to reload Systemd daemon."; exit 1; }
    sudo systemctl enable "${PROJECT_NAME}_flask.service" || { print_error "Failed to enable Flask service."; exit 1; }
    sudo systemctl enable cron
    sudo systemctl start "${PROJECT_NAME}_flask.service" || { print_error "Failed to start Flask service."; exit 1; }
    sudo systemctl start cron
    print_success "Flask service started and enabled to run on boot."
    print_info "You can check its status with: sudo systemctl status ${PROJECT_NAME}_flask.service"
    print_info "View logs with: journalctl -u ${PROJECT_NAME}_flask.service --since '1 hour ago'"
    sleep 2
}

deploy_frontend() {
    print_info "--- Deploying React Vite Frontend ---"
    sleep 1

    print_info "Navigating to frontend directory: $FRONTEND_DIR"
    cd "$FRONTEND_DIR" || { print_error "Frontend directory not found: $FRONTEND_DIR"; exit 1; }

    if [ -s "$HOME/.nvm/nvm.sh" ]; then
        . "$HOME/.nvm/nvm.sh"
        nvm use "$NODE_VERSION" || print_warning "Could not activate Node.js v${NODE_VERSION} with nvm in this subshell. Continuing anyway."
    else
        print_error "NVM not found or not sourced. Node.js/npm commands might fail."
        exit 1
    fi

    print_info "Installing Node.js dependencies..."
    npm install || { print_error "Failed to install Node.js dependencies. Check npm logs and internet connection."; exit 1; }
    print_success "Node.js dependencies installed."
    sleep 1
}

configure_frontend_api_url() {
    print_info "--- Configuring Frontend API URL ---"
    sleep 1

    local server_ip
    read -p "$(echo -e "${YELLOW}INPUT:${RESET} Enter your server's public IP address (e.g., 192.168.1.100) or domain name if using one: ")" server_ip
    if [ -z "$server_ip" ]; then
        print_error "Server IP/Domain cannot be empty. Exiting."
        exit 1
    fi

    local frontend_api_url="http://$server_ip:$BACKEND_PORT"

    print_info "Writing frontend environment variable VITE_APP_API_URL to .env.production..."
    echo "export VITE_APP_API_URL=$frontend_api_url" | sudo tee "$FRONTEND_DIR/.env.production" > /dev/null || { print_error "Failed to write .env.production file. Check permissions."; exit 1; }
    echo "export AP_PORT=$BACKEND_PORT" | sudo tee "$FRONTEND_DIR/.env.production" > /dev/null || { print_error "Failed to write .env.production file. Check permissions."; exit 1; }
    print_success ".env.production created/updated with VITE_APP_API_URL=$frontend_api_url"
    sudo chown "$LINUX_USER:$LINUX_USER" "$FRONTEND_DIR/.env.production" || { print_warning "Could not change ownership of .env.production. Manual intervention might be needed for permissions."; }
    sleep 1

    print_info "Rebuilding frontend to apply new API URL..."
    cd "$FRONTEND_DIR" || { print_error "Frontend directory not found: $FRONTEND_DIR"; exit 1; }
    npm run build || { print_error "Failed to rebuild React Vite frontend after updating API URL."; exit 1; }
    print_success "Frontend rebuilt successfully with updated API URL."
    sleep 1
}

configure_firewall() {
    print_info "--- Configuring Firewall (UFW) ---"
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

    print_info "Allowing external access to port $BACKEND_PORT for Flask application..."
    sudo ufw allow "$BACKEND_PORT"/tcp || { print_error "Failed to allow port $BACKEND_PORT through UFW."; exit 1; }
    print_success "Port $BACKEND_PORT allowed for external access."

    print_info "You can check UFW status with: sudo ufw status"
    sleep 2
}

# --- Uninstall Functions ---
get_backend_port() {
    if [ -n "$AP_PORT" ]; then
        BACKEND_PORT="$AP_PORT"
        print_info "Using BACKEND_PORT from AP_PORT environment variable: $BACKEND_PORT"
    else
        while true; do
            read -p "$(echo -e "${YELLOW}INPUT:${RESET} Please enter the backend port used by CandyPanel (e.g., 3446): ")" user_port
            if [[ "$user_port" =~ ^[0-9]+$ ]] && [ "$user_port" -ge 1 ] && [ "$user_port" -le 65535 ]; then
                BACKEND_PORT="$user_port"
                print_info "Using BACKEND_PORT from user input: $BACKEND_PORT"
                break
            else
                print_error "Invalid port number. Please enter a number between 1 and 65535."
            fi
        done
    fi
    export BACKEND_PORT
    sleep 1
}

uninstall_backend_service() {
    print_info "--- Stopping and Disabling Flask Backend Service ---"
    sleep 1

    local service_name="${PROJECT_NAME}_flask.service"

    if sudo systemctl is-active --quiet "$service_name"; then
        print_info "Stopping Flask service: $service_name..."
        sudo systemctl stop "$service_name" || { print_warning "Failed to stop Flask service. It might not be running."; }
        print_success "Flask service stopped."
    else
        print_info "Flask service '$service_name' is not active."
    fi

    if sudo systemctl is-enabled --quiet "$service_name"; then
        print_info "Disabling Flask service: $service_name..."
        sudo systemctl disable "$service_name" || { print_warning "Failed to disable Flask service. It might already be disabled."; }
        print_success "Flask service disabled."
    else
        print_info "Flask service '$service_name' is not enabled."
    fi

    if [ -f "/etc/systemd/system/$service_name" ]; then
        print_info "Removing Systemd service file: /etc/systemd/system/$service_name..."
        sudo rm "/etc/systemd/system/$service_name" || { print_error "Failed to remove Systemd service file."; exit 1; }
        print_success "Systemd service file removed."
    else
        print_info "Systemd service file '/etc/systemd/system/$service_name' not found."
    fi
    
    print_info "Reloading Systemd daemon..."
    sudo systemctl daemon-reload || { print_warning "Failed to reload Systemd daemon. This might not be critical for uninstallation."; }
    print_success "Systemd daemon reloaded."
    sleep 2
}

remove_project_directory() {
    print_info "--- Removing Project Directory ---"
    sleep 1

    if [ -d "$PROJECT_ROOT" ]; then
        confirm_action "Are you sure you want to delete the project directory '$PROJECT_ROOT' and all its contents? This action is irreversible."
        print_info "Deleting project directory: $PROJECT_ROOT..."
        sudo rm -rf "$PROJECT_ROOT" || { print_error "Failed to remove project directory. Check permissions."; exit 1; }
        print_success "Project directory '$PROJECT_ROOT' removed successfully."
    else
        print_info "Project directory '$PROJECT_ROOT' does not exist. Nothing to remove."
    fi
    sleep 1
}

remove_firewall_rules() {
    print_info "--- Removing Firewall Rules ---"
    sleep 1

    if sudo ufw status | grep -q "Status: active"; then
        print_info "Checking for UFW rule for port $BACKEND_PORT..."
        if sudo ufw status | grep -q "ALLOW IN.*$BACKEND_PORT/tcp"; then
            print_info "Deleting UFW rule for port $BACKEND_PORT..."
            sudo ufw delete allow $BACKEND_PORT/tcp || { print_warning "Failed to delete UFW rule for port $BACKEND_PORT. Manual removal might be needed."; }
            print_success "UFW rule for port $BACKEND_PORT removed."
        else
            print_info "No UFW rule found for port $BACKEND_PORT."
        fi
    else
        print_info "UFW is not active. No firewall rules to remove via UFW."
    fi
    sleep 1
}

uninstall_nvm() {
    print_info "--- Uninstalling NVM and Node.js (Optional) ---"
    sleep 1

    if [ -d "$HOME/.nvm" ]; then
        confirm_action "Do you want to uninstall NVM (Node Version Manager) and all Node.js versions managed by it? This will remove '$HOME/.nvm'."
        print_info "Attempting to uninstall NVM..."
        if [ -s "$HOME/.nvm/nvm.sh" ]; then
            . "$HOME/.nvm/nvm.sh"
            nvm deactivate > /dev/null 2>&1
            nvm uninstall --lts > /dev/null 2>&1
            nvm uninstall "$(nvm current)" > /dev/null 2>&1
        fi

        rm -rf "$HOME/.nvm"
        sed -i '/NVM_DIR/d' "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile" 2>/dev/null
        sed -i '/nvm.sh/d' "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile" 2>/dev/null
        sed -i '/bash_completion/d' "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile" 2>/dev/null
        print_success "NVM and associated Node.js versions removed."
        print_warning "You may need to manually remove any remaining Node.js related binaries from your PATH if they were installed globally outside NVM."
    else
        print_info "NVM directory '$HOME/.nvm' not found. Nothing to uninstall."
    fi
    sleep 1
}

remove_sudoers_file() {
    print_info "--- Removing Sudoers Configuration ---"
    sleep 1

    if [ -f "$SUDOERS_FILE" ]; then
        confirm_action "Do you want to remove the sudoers file '$SUDOERS_FILE' created for CandyPanel permissions? This will revoke specific passwordless sudo access for the CandyPanel user."
        print_info "Removing sudoers file: $SUDOERS_FILE..."
        sudo rm "$SUDOERS_FILE" || { print_error "Failed to remove sudoers file. Manual removal might be needed."; exit 1; }
        print_success "Sudoers file removed."
    else
        print_info "Sudoers file '$SUDOERS_FILE' not found. Nothing to remove."
    fi
    sleep 1
}

uninstall_wireguard() {
    print_info "--- Uninstalling WireGuard and its Configurations ---"
    sleep 1

    confirm_action "Do you want to uninstall WireGuard and remove its configuration files? This will remove all VPN configurations."

    print_info "Attempting to stop all active WireGuard interfaces..."
    for conf_file in /etc/wireguard/*.conf; do
        if [ -f "$conf_file" ]; then
            local interface_name=$(basename "$conf_file" .conf)
            print_info "Stopping WireGuard interface: $interface_name..."
            sudo wg-quick down "$interface_name" > /dev/null 2>&1 || print_warning "Could not stop WireGuard interface '$interface_name'. It might not be active or already stopped."
            sudo systemctl disable "wg-quick@${interface_name}.service" > /dev/null 2>&1 || print_warning "Could not disable WireGuard service for '$interface_name'. It might not be enabled."
            sudo rm -f "/etc/systemd/system/wg-quick@${interface_name}.service" > /dev/null 2>&1
        fi
    done
    print_success "Attempted to stop and disable WireGuard interfaces."

    print_info "Removing WireGuard packages (wireguard and wireguard-tools)..."
    if command -v apt &> /dev/null; then
        sudo apt purge -y wireguard wireguard-tools || print_warning "Failed to purge WireGuard packages. They might not be installed or require manual removal."
    elif command -v dnf &> /dev/null; then
        sudo dnf remove -y wireguard-tools || print_warning "Failed to remove WireGuard packages. They might not be installed or require manual removal."
    elif command -v pacman &> /dev/null; then
        sudo pacman -Rs --noconfirm wireguard-tools || print_warning "Failed to remove WireGuard packages. They might not be installed or require manual removal."
    else
        print_warning "Package manager not recognized. Please manually uninstall 'wireguard' and 'wireguard-tools' packages."
    fi
    print_success "WireGuard packages removal attempt complete."

    print_info "Removing WireGuard configuration directory: /etc/wireguard/..."
    if [ -d "/etc/wireguard/" ]; then
        sudo rm -rf "/etc/wireguard/" || { print_error "Failed to remove /etc/wireguard/. Check permissions."; }
        print_success "WireGuard configuration directory removed."
    else
        print_info "/etc/wireguard/ directory not found. Nothing to remove."
    fi

    print_info "Removing WireGuard connections from NetworkManager (if any)..."
    if command -v nmcli &> /dev/null; then
        local wg_connections=$(nmcli -t -f UUID,TYPE connection show --active | grep 'wireguard' | cut -d':' -f1)
        if [ -n "$wg_connections" ]; then
            for uuid in $wg_connections; do
                print_info "Deleting NetworkManager WireGuard connection (UUID: $uuid)..."
                sudo nmcli connection delete uuid "$uuid" || print_warning "Failed to delete NetworkManager WireGuard connection $uuid."
            done
            print_success "NetworkManager WireGuard connections removed."
        else
            print_info "No active WireGuard connections found in NetworkManager."
        fi
    else
        print_info "nmcli (NetworkManager CLI) not found. Skipping NetworkManager cleanup."
    fi
    
    print_info "Reloading Systemd daemon after WireGuard cleanup..."
    sudo systemctl daemon-reload || { print_warning "Failed to reload Systemd daemon. This might not be critical."; }
    print_success "Systemd daemon reloaded."
    sleep 2
}

# --- Main Install/Update/Uninstall Logic ---
run_install() {
    print_header "Candy Panel Deployment Script"
    confirm_action "This script will deploy your Candy panel with Flask serving both frontend and backend. Ensure you have updated the REPO_URL variable in the script."

    check_prerequisites
    setup_permissions
    install_nodejs_with_nvm
    clone_or_update_repo

    # Prompt for IPv6 information
    local ipv6_address_range
    local ipv6_dns
    read -p "$(echo -e "${YELLOW}INPUT:${RESET} Do you want to enable IPv6 support? (y/N)? ")" -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "$(echo -e "${YELLOW}INPUT:${RESET} Enter IPv6 Address Range for WireGuard clients (e.g., fd86:ea04:1115::1/64): ")" ipv6_address_range
        read -p "$(echo -e "${YELLOW}INPUT:${RESET} Enter IPv6 DNS Server (e.g., 2001:4860:4860::8888): ")" ipv6_dns
    fi

    deploy_backend
    deploy_frontend
    configure_frontend_api_url
    configure_firewall

    echo -e "\n${BOLD}${GREEN}====================================================${RESET}"
    echo-e "${BOLD}${GREEN} Deployment Complete!                               ${RESET}"
    echo -e "${BOLD}${GREEN}====================================================${RESET}"
    echo -e "${BOLD}${GREEN} Your Candy Panel should now be accessible at:${RESET}"
    echo -e "${BOLD}${GREEN} http://YOUR_SERVER_IP:$BACKEND_PORT${RESET}"
    print_warning "Remember to replace YOUR_SERVER_IP with your actual server's public IP address."
    print_warning "Note: SSL is NOT configured with this setup. For HTTPS, you will need to add a reverse proxy like Nginx or Caddy."
    echo -e "${BOLD}${GREEN}====================================================${RESET}\n"
    print_info "Ensure the Linux user '$LINUX_USER' has appropriate permissions for WireGuard operations."
    print_info "Flask application is running on port $BACKEND_PORT and serving all content."
}
# A separate function for backend deployment to pass the new variables
deploy_backend() {
    
    print_info "--- Deploying Flask Backend ---"
    sleep 1

    print_info "Navigating to backend directory: $BACKEND_DIR"
    cd "$BACKEND_DIR" || { print_error "Backend directory not found: $BACKEND_DIR"; exit 1; }

    print_info "Creating and activating Python virtual environment..."
    # Use the discovered Python executable
    python3 -m venv venv || { print_error "Failed to create virtual environment."; exit 1; }
    source venv/bin/activate || { print_error "Failed to activate virtual environment."; exit 1; }
    print_success "Virtual environment activated."
    sleep 1

    print_info "Installing Python dependencies (Flask etc.)..."
    # Install netifaces with required build dependencies if needed
    pip install pyrogram flask[async] requests flask_cors psutil httpx tgcrypto nanoid || { print_error "Failed to install Python dependencies."; exit 1; }
    print_info "Attempting to install netifaces specifically, including build dependencies..."
    
    # Try installing netifaces with potential build dependencies for different distros
    if command -v apt &> /dev/null; then
        sudo apt install -y python3-netifaces || { print_error "Failed to install netifaces. Check build-essential and python3-dev installations."; exit 1; }
        pip install netifaces || { print_error "Failed to install netifaces. Check build-essential and python3-dev installations."; exit 1; }
    elif command -v yum &> /dev/null; then
        sudo yum install -y python3-netifaces || { print_error "Failed to install netifaces. Check build-essential and python3-devel installations."; exit 1; }
        pip install netifaces || { print_error "Failed to install netifaces. Check build-essential and python3-dev installations."; exit 1; }
    else
        pip install netifaces || print_warning "Failed to install netifaces. Please install it manually with appropriate system headers if needed."
    fi

    print_success "Python dependencies installed."
    sleep 1

    print_info "Creating Systemd service file for Flask..."
    sudo tee "/etc/systemd/system/${PROJECT_NAME}_flask.service" > /dev/null <<EOF
[Unit]
Description=Flask instance for ${PROJECT_NAME}
After=network.target

[Service]
User=$LINUX_USER
Group=$LINUX_USER
WorkingDirectory=$BACKEND_DIR
Environment="FLASK_APP=$FLASK_APP_ENTRY"
Environment="FLASK_RUN_HOST=$BACKEND_HOST"
Environment="FLASK_RUN_PORT=$BACKEND_PORT"
ExecStart=$BACKEND_DIR/venv/bin/python3 $FLASK_APP_ENTRY
Restart=always
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF
    print_success "Systemd service file created."
    sleep 1

    print_info "Reloading Systemd daemon, enabling and starting Flask service..."
    sudo systemctl daemon-reload || { print_error "Failed to reload Systemd daemon."; exit 1; }
    sudo systemctl enable "${PROJECT_NAME}_flask.service" || { print_error "Failed to enable Flask service."; exit 1; }
    sudo systemctl enable cron
    sudo systemctl start "${PROJECT_NAME}_flask.service" || { print_error "Failed to start Flask service."; exit 1; }
    sudo systemctl start cron
    print_success "Flask service started and enabled to run on boot."
    print_info "You can check its status with: sudo systemctl status ${PROJECT_NAME}_flask.service"
    print_info "View logs with: journalctl -u ${PROJECT_NAME}_flask.service --since '1 hour ago'"
    sleep 2
}

deploy_frontend() {
    print_info "--- Deploying React Vite Frontend ---"
    sleep 1

    print_info "Navigating to frontend directory: $FRONTEND_DIR"
    cd "$FRONTEND_DIR" || { print_error "Frontend directory not found: $FRONTEND_DIR"; exit 1; }

    if [ -s "$HOME/.nvm/nvm.sh" ]; then
        . "$HOME/.nvm/nvm.sh"
        nvm use "$NODE_VERSION" || print_warning "Could not activate Node.js v${NODE_VERSION} with nvm in this subshell. Continuing anyway."
    else
        print_error "NVM not found or not sourced. Node.js/npm commands might fail."
        exit 1
    fi

    print_info "Installing Node.js dependencies..."
    npm install || { print_error "Failed to install Node.js dependencies. Check npm logs and internet connection."; exit 1; }
    print_success "Node.js dependencies installed."
    sleep 1
}

configure_frontend_api_url() {
    print_info "--- Configuring Frontend API URL ---"
    sleep 1

    local server_ip
    read -p "$(echo -e "${YELLOW}INPUT:${RESET} Enter your server's public IP address (e.g., 192.168.1.100) or domain name if using one: ")" server_ip
    if [ -z "$server_ip" ]; then
        print_error "Server IP/Domain cannot be empty. Exiting."
        exit 1
    fi

    local frontend_api_url="http://$server_ip:$BACKEND_PORT"

    print_info "Writing frontend environment variable VITE_APP_API_URL to .env.production..."
    echo "export VITE_APP_API_URL=$frontend_api_url" | sudo tee "$FRONTEND_DIR/.env.production" > /dev/null || { print_error "Failed to write .env.production file. Check permissions."; exit 1; }
    echo "export AP_PORT=$BACKEND_PORT" | sudo tee "$FRONTEND_DIR/.env.production" > /dev/null || { print_error "Failed to write .env.production file. Check permissions."; exit 1; }
    print_success ".env.production created/updated with VITE_APP_API_URL=$frontend_api_url"
    sudo chown "$LINUX_USER:$LINUX_USER" "$FRONTEND_DIR/.env.production" || { print_warning "Could not change ownership of .env.production. Manual intervention might be needed for permissions."; }
    sleep 1

    print_info "Rebuilding frontend to apply new API URL..."
    cd "$FRONTEND_DIR" || { print_error "Frontend directory not found: $FRONTEND_DIR"; exit 1; }
    npm run build || { print_error "Failed to rebuild React Vite frontend after updating API URL."; exit 1; }
    print_success "Frontend rebuilt successfully with updated API URL."
    sleep 1
}

configure_firewall() {
    print_info "--- Configuring Firewall (UFW) ---"
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

    print_info "Allowing external access to port $BACKEND_PORT for Flask application..."
    sudo ufw allow "$BACKEND_PORT"/tcp || { print_error "Failed to allow port $BACKEND_PORT through UFW."; exit 1; }
    print_success "Port $BACKEND_PORT allowed for external access."

    print_info "You can check UFW status with: sudo ufw status"
    sleep 2
}

# --- Uninstall Functions ---
get_backend_port() {
    if [ -n "$AP_PORT" ]; then
        BACKEND_PORT="$AP_PORT"
        print_info "Using BACKEND_PORT from AP_PORT environment variable: $BACKEND_PORT"
    else
        while true; do
            read -p "$(echo -e "${YELLOW}INPUT:${RESET} Please enter the backend port used by CandyPanel (e.g., 3446): ")" user_port
            if [[ "$user_port" =~ ^[0-9]+$ ]] && [ "$user_port" -ge 1 ] && [ "$user_port" -le 65535 ]; then
                BACKEND_PORT="$user_port"
                print_info "Using BACKEND_PORT from user input: $BACKEND_PORT"
                break
            else
                print_error "Invalid port number. Please enter a number between 1 and 65535."
            fi
        done
    fi
    export BACKEND_PORT
    sleep 1
}

uninstall_backend_service() {
    print_info "--- Stopping and Disabling Flask Backend Service ---"
    sleep 1

    local service_name="${PROJECT_NAME}_flask.service"

    if sudo systemctl is-active --quiet "$service_name"; then
        print_info "Stopping Flask service: $service_name..."
        sudo systemctl stop "$service_name" || { print_warning "Failed to stop Flask service. It might not be running."; }
        print_success "Flask service stopped."
    else
        print_info "Flask service '$service_name' is not active."
    fi

    if sudo systemctl is-enabled --quiet "$service_name"; then
        print_info "Disabling Flask service: $service_name..."
        sudo systemctl disable "$service_name" || { print_warning "Failed to disable Flask service. It might already be disabled."; }
        print_success "Flask service disabled."
    else
        print_info "Flask service '$service_name' is not enabled."
    fi

    if [ -f "/etc/systemd/system/$service_name" ]; then
        print_info "Removing Systemd service file: /etc/systemd/system/$service_name..."
        sudo rm "/etc/systemd/system/$service_name" || { print_error "Failed to remove Systemd service file."; exit 1; }
        print_success "Systemd service file removed."
    else
        print_info "Systemd service file '/etc/systemd/system/$service_name' not found."
    fi
    
    print_info "Reloading Systemd daemon..."
    sudo systemctl daemon-reload || { print_warning "Failed to reload Systemd daemon. This might not be critical for uninstallation."; }
    print_success "Systemd daemon reloaded."
    sleep 2
}

remove_project_directory() {
    print_info "--- Removing Project Directory ---"
    sleep 1

    if [ -d "$PROJECT_ROOT" ]; then
        confirm_action "Are you sure you want to delete the project directory '$PROJECT_ROOT' and all its contents? This action is irreversible."
        print_info "Deleting project directory: $PROJECT_ROOT..."
        sudo rm -rf "$PROJECT_ROOT" || { print_error "Failed to remove project directory. Check permissions."; exit 1; }
        print_success "Project directory '$PROJECT_ROOT' removed successfully."
    else
        print_info "Project directory '$PROJECT_ROOT' does not exist. Nothing to remove."
    fi
    sleep 1
}

remove_firewall_rules() {
    print_info "--- Removing Firewall Rules ---"
    sleep 1

    if sudo ufw status | grep -q "Status: active"; then
        print_info "Checking for UFW rule for port $BACKEND_PORT..."
        if sudo ufw status | grep -q "ALLOW IN.*$BACKEND_PORT/tcp"; then
            print_info "Deleting UFW rule for port $BACKEND_PORT..."
            sudo ufw delete allow $BACKEND_PORT/tcp || { print_warning "Failed to delete UFW rule for port $BACKEND_PORT. Manual removal might be needed."; }
            print_success "UFW rule for port $BACKEND_PORT removed."
        else
            print_info "No UFW rule found for port $BACKEND_PORT."
        fi
    else
        print_info "UFW is not active. No firewall rules to remove via UFW."
    fi
    sleep 1
}

uninstall_nvm() {
    print_info "--- Uninstalling NVM and Node.js (Optional) ---"
    sleep 1

    if [ -d "$HOME/.nvm" ]; then
        confirm_action "Do you want to uninstall NVM (Node Version Manager) and all Node.js versions managed by it? This will remove '$HOME/.nvm'."
        print_info "Attempting to uninstall NVM..."
        if [ -s "$HOME/.nvm/nvm.sh" ]; then
            . "$HOME/.nvm/nvm.sh"
            nvm deactivate > /dev/null 2>&1
            nvm uninstall --lts > /dev/null 2>&1
            nvm uninstall "$(nvm current)" > /dev/null 2>&1
        fi

        rm -rf "$HOME/.nvm"
        sed -i '/NVM_DIR/d' "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile" 2>/dev/null
        sed -i '/nvm.sh/d' "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile" 2>/dev/null
        sed -i '/bash_completion/d' "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile" 2>/dev/null
        print_success "NVM and associated Node.js versions removed."
        print_warning "You may need to manually remove any remaining Node.js related binaries from your PATH if they were installed globally outside NVM."
    else
        print_info "NVM directory '$HOME/.nvm' not found. Nothing to uninstall."
    fi
    sleep 1
}

remove_sudoers_file() {
    print_info "--- Removing Sudoers Configuration ---"
    sleep 1

    if [ -f "$SUDOERS_FILE" ]; then
        confirm_action "Do you want to remove the sudoers file '$SUDOERS_FILE' created for CandyPanel permissions? This will revoke specific passwordless sudo access for the CandyPanel user."
        print_info "Removing sudoers file: $SUDOERS_FILE..."
        sudo rm "$SUDOERS_FILE" || { print_error "Failed to remove sudoers file. Manual removal might be needed."; exit 1; }
        print_success "Sudoers file removed."
    else
        print_info "Sudoers file '$SUDOERS_FILE' not found. Nothing to remove."
    fi
    sleep 1
}

uninstall_wireguard() {
    print_info "--- Uninstalling WireGuard and its Configurations ---"
    sleep 1

    confirm_action "Do you want to uninstall WireGuard and remove its configuration files? This will remove all VPN configurations."

    print_info "Attempting to stop all active WireGuard interfaces..."
    for conf_file in /etc/wireguard/*.conf; do
        if [ -f "$conf_file" ]; then
            local interface_name=$(basename "$conf_file" .conf)
            print_info "Stopping WireGuard interface: $interface_name..."
            sudo wg-quick down "$interface_name" > /dev/null 2>&1 || print_warning "Could not stop WireGuard interface '$interface_name'. It might not be active or already stopped."
            sudo systemctl disable "wg-quick@${interface_name}.service" > /dev/null 2>&1 || print_warning "Could not disable WireGuard service for '$interface_name'. It might not be enabled."
            sudo rm -f "/etc/systemd/system/wg-quick@${interface_name}.service" > /dev/null 2>&1
        fi
    done
    print_success "Attempted to stop and disable WireGuard interfaces."

    print_info "Removing WireGuard packages (wireguard and wireguard-tools)..."
    if command -v apt &> /dev/null; then
        sudo apt purge -y wireguard wireguard-tools || print_warning "Failed to purge WireGuard packages. They might not be installed or require manual removal."
    elif command -v dnf &> /dev/null; then
        sudo dnf remove -y wireguard-tools || print_warning "Failed to remove WireGuard packages. They might not be installed or require manual removal."
    elif command -v pacman &> /dev/null; then
        sudo pacman -Rs --noconfirm wireguard-tools || print_warning "Failed to remove WireGuard packages. They might not be installed or require manual removal."
    else
        print_warning "Package manager not recognized. Please manually uninstall 'wireguard' and 'wireguard-tools' packages."
    fi
    print_success "WireGuard packages removal attempt complete."

    print_info "Removing WireGuard configuration directory: /etc/wireguard/..."
    if [ -d "/etc/wireguard/" ]; then
        sudo rm -rf "/etc/wireguard/" || { print_error "Failed to remove /etc/wireguard/. Check permissions."; }
        print_success "WireGuard configuration directory removed."
    else
        print_info "/etc/wireguard/ directory not found. Nothing to remove."
    fi

    print_info "Removing WireGuard connections from NetworkManager (if any)..."
    if command -v nmcli &> /dev/null; then
        local wg_connections=$(nmcli -t -f UUID,TYPE connection show --active | grep 'wireguard' | cut -d':' -f1)
        if [ -n "$wg_connections" ]; then
            for uuid in $wg_connections; do
                print_info "Deleting NetworkManager WireGuard connection (UUID: $uuid)..."
                sudo nmcli connection delete uuid "$uuid" || print_warning "Failed to delete NetworkManager WireGuard connection $uuid."
            done
            print_success "NetworkManager WireGuard connections removed."
        else
            print_info "No active WireGuard connections found in NetworkManager."
        fi
    else
        print_info "nmcli (NetworkManager CLI) not found. Skipping NetworkManager cleanup."
    fi
    
    print_info "Reloading Systemd daemon after WireGuard cleanup..."
    sudo systemctl daemon-reload || { print_warning "Failed to reload Systemd daemon. This might not be critical."; }
    print_success "Systemd daemon reloaded."
    sleep 2
}

# --- Main Install/Update/Uninstall Logic ---
run_install() {
    print_header "Candy Panel Deployment Script"
    confirm_action "This script will deploy your Candy panel with Flask serving both frontend and backend. Ensure you have updated the REPO_URL variable in the script."

    check_prerequisites
    setup_permissions
    install_nodejs_with_nvm
    clone_or_update_repo

    # Prompt for IPv6 information
    local ipv6_address_range
    local ipv6_dns
    read -p "$(echo -e "${YELLOW}INPUT:${RESET} Do you want to enable IPv6 support? (y/N)? ")" -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "$(echo -e "${YELLOW}INPUT:${RESET} Enter IPv6 Address Range for WireGuard clients (e.g., fd86:ea04:1115::1/64): ")" ipv6_address_range
        read -p "$(echo -e "${YELLOW}INPUT:${RESET} Enter IPv6 DNS Server (e.g., 2001:4860:4860::8888): ")" ipv6_dns
    fi

    deploy_backend "$ipv6_address_range" "$ipv6_dns"
    deploy_frontend
    configure_frontend_api_url
    configure_firewall

    echo -e "\n${BOLD}${GREEN}====================================================${RESET}"
    echo-e "${BOLD}${GREEN} Deployment Complete!                               ${RESET}"
    echo -e "${BOLD}${GREEN}====================================================${RESET}"
    echo -e "${BOLD}${GREEN} Your Candy Panel should now be accessible at:${RESET}"
    echo -e "${BOLD}${GREEN} http://YOUR_SERVER_IP:$BACKEND_PORT${RESET}"
    print_warning "Remember to replace YOUR_SERVER_IP with your actual server's public IP address."
    print_warning "Note: SSL is NOT configured with this setup. For HTTPS, you will need to add a reverse proxy like Nginx or Caddy."
    echo -e "${BOLD}${GREEN}====================================================${RESET}\n"
    print_info "Ensure the Linux user '$LINUX_USER' has appropriate permissions for WireGuard operations."
    print_info "Flask application is running on port $BACKEND_PORT and serving all content."
}

run_uninstall() {
    print_header "Candy Panel UNINSTALL Script"
    confirm_action "This script will attempt to UNINSTALL the Candy Panel project. This includes stopping services, removing files, and reverting firewall rules. Proceed with uninstallation?"

    get_backend_port

    uninstall_backend_service
    remove_project_directory
    remove_firewall_rules
    remove_sudoers_file
    uninstall_nvm
    uninstall_wireguard

    echo -e "\n${BOLD}${GREEN}====================================================${RESET}"
    echo -e "${BOLD}${GREEN} Uninstallation Attempt Complete!                 ${RESET}"
    echo -e "${BOLD}${GREEN}====================================================${RESET}"
    print_warning "Manual cleanup might still be required for some system packages (e.g., qrencode, python3-psutil) if they were installed solely for this project and are no longer needed."
    print_warning "To uninstall other system packages, you can use: sudo apt remove qrencode python3-psutil"
    echo -e "${BOLD}${GREEN}====================================================${RESET}\n"
}

run_update() {
    print_header "Candy Panel UPDATE Script"
    confirm_action "This script will update the Candy Panel project by pulling the latest changes from the repository and reinstalling dependencies. Proceed with update?"

    print_info "--- Stopping Services for Update ---"
    sudo systemctl stop "${PROJECT_NAME}_flask.service" || print_warning "Flask service might not be running or failed to stop."
    print_success "Services stopped."
    sleep 1

    clone_or_update_repo # This function already handles pulling latest changes

    print_info "--- Updating Backend Dependencies ---"
    cd "$BACKEND_DIR" || { print_error "Backend directory not found: $BACKEND_DIR"; exit 1; }
    source venv/bin/activate || { print_error "Failed to activate virtual environment. Cannot update backend dependencies."; exit 1; }
    pip install -r requirements.txt || { print_warning "Failed to install Python dependencies from requirements.txt. Attempting direct install..."; pip install pyrogram flask[async] requests flask_cors psutil || { print_error "Failed to install Python dependencies directly."; exit 1; }; }
    
    # Re-attempt netifaces installation during update
    print_info "Attempting to install netifaces specifically during update..."
    if command -v apt &> /dev/null; then
        sudo apt install -y python3-netifaces || pip install netifaces || print_warning "Failed to install netifaces during update. Manual intervention might be needed."
    elif command -v yum &> /dev/null; then
        sudo yum install -y python3-netifaces || pip install netifaces || print_warning "Failed to install netifaces during update. Manual intervention might be needed."
    else
        pip install netifaces || print_warning "Failed to install netifaces during update. Please install it manually with appropriate system headers if needed."
    fi

    deactivate
    print_success "Backend dependencies updated."
    sleep 1

    print_info "--- Updating Frontend Dependencies and Rebuilding ---"
    deploy_frontend # This will navigate, source NVM, and run npm install
    configure_frontend_api_url # This will rebuild the frontend

    print_info "--- Starting Services after Update ---"
    sudo systemctl start "${PROJECT_NAME}_flask.service" || { print_error "Failed to start Flask service after update."; exit 1; }
    print_success "Flask service started."
    print_info "You can check its status with: sudo systemctl status ${PROJECT_NAME}_flask.service"
    print_info "View logs with: journalctl -u ${PROJECT_NAME}_flask.service --since '1 hour ago'"
    sleep 2

    echo -e "\n${BOLD}${GREEN}====================================================${RESET}"
    echo -e "${BOLD}${GREEN} Update Complete!                                 ${RESET}"
    echo -e "${BOLD}${GREEN}====================================================${RESET}"
    echo -e "${BOLD}${GREEN} Your Candy Panel should now be running the latest version.${RESET}"
    echo -e "${BOLD}${GREEN} Access it at: http://YOUR_SERVER_IP:$BACKEND_PORT${RESET}"
    print_warning "Remember to replace YOUR_SERVER_IP with your actual server's public IP address."
    echo -e "${BOLD}${GREEN}====================================================${RESET}\n"
}


# --- Menu Logic ---
show_menu() {
    print_header "Candy Panel Management Script"
    echo -e "${BOLD}${BLUE}Please choose an option:${RESET}"
    echo -e "  ${GREEN}1) Install Candy Panel${RESET}"
    echo -e "  ${YELLOW}2) Update Candy Panel${RESET}"
    echo -e "  ${RED}3) Uninstall Candy Panel${RESET}"
    echo -e "  ${CYAN}4) Quit${RESET}"
    echo -e "----------------------------------------------------"
    read -p "$(echo -e "${BOLD}${BLUE}Enter your choice [1-4]: ${RESET}")" choice
}

# --- Main execution ---
while true; do
    show_menu
    case $choice in
        1)
            run_install
            break
            ;;
        2)
            run_update
            break
            ;;
        3)
            run_uninstall
            break
            ;;
        4)
            print_info "Exiting script. Goodbye!"
            exit 0
            ;;
        *)
            print_error "Invalid choice. Please enter a number between 1 and 4."
            sleep 2
            ;;
    esac
done