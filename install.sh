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
    echo -e "\n${BOLD}${CYAN}====================================================${RESET}"
    echo -e "${BOLD}${CYAN} Candy Panel Deployment Script                      ${RESET}"
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

# --- Pre-checks and Setup ---
check_prerequisites() {
    print_info "Checking for required system packages..."
    local missing_packages=()
    # Removed nginx and certbot
    for cmd in git python3 ufw cron python3.10-venv; do # Removed python3.10-venv as it's often part of python3-full or can be installed via pip
        if ! command -v "$cmd" &> /dev/null; then
            missing_packages+=("$cmd")
        fi
    done

    # Add curl for NVM installation check
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
            exit 1
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

    # Prompt for CandyPanel User
    read -p "$(echo -e "${YELLOW}INPUT:${RESET} Please enter the username that will run the CandyPanel application (e.g., candypaneluser): ")" CANDYPANEL_USER

    # Validate if the user exists
    if ! id "$CANDYPANEL_USER" &>/dev/null; then
        print_error "Error: User '$CANDYPANEL_USER' does not exist."
        print_error "Please create the user first (e.g., 'sudo adduser $CANDYPANEL_USER') or enter an existing one."
        exit 1
    fi

    echo "User '$CANDYPANEL_USER' selected for CandyPanel operations."

    # Install WireGuard, qrencode, and psutil system packages
    print_info "Installing core system packages: wireguard, qrencode, python3-psutil..."
    sudo apt install -y wireguard qrencode python3-psutil || { print_error "Failed to install core system packages."; exit 1; }
    print_success "Core system packages installed."

    # Configure sudoers for the CandyPanel User
    print_info "Configuring sudoers for user '$CANDYPANEL_USER' to allow specific commands without password..."

    SUDOERS_FILE="/etc/sudoers.d/candypanel_permissions"

    # Define the commands the user is allowed to run with sudo without password.
    # We specify full paths to executables to enhance security and prevent path injection.
    # The '*' wildcard allows any arguments to these commands.
    # WARNING: NOPASSWD should be used with caution and only for specific, necessary commands.
    cat <<EOF | sudo tee "$SUDOERS_FILE" > /dev/null
# Allow $CANDYPANEL_USER to manage WireGuard, UFW, systemctl, and cron for CandyPanel
$CANDYPANEL_USER ALL=(ALL) NOPASSWD: \\
    /usr/bin/wg genkey, \\
    /usr/bin/wg pubkey, \\
    /usr/bin/wg show *, \\
    /usr/bin/wg syncconf *, \\
    /usr/bin/wg-quick up *, \\
    /usr/bin/wg-quick down *, \\
    /usr/bin/systemctl enable wg-quick@*, \\
    /usr/bin/systemctl start wg-quick@*, \\
    /usr/bin/systemctl stop wg-quick@*, \\
    /usr/sbin/ufw allow *, \\
    /usr/sbin/ufw delete *, \\
    /usr/bin/crontab
EOF

    # Set secure permissions for the sudoers file (read-only for root, no other permissions)
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
        . "$HOME/.nvm/nvm.sh" # Source NVM
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
    print_header
    print_info "Starting deployment process for $PROJECT_NAME..."
    sleep 1

    if [ -d "$PROJECT_ROOT" ]; then
        print_warning "Project directory '$PROJECT_ROOT' already exists."
        confirm_action "Do you want to pull the latest changes from the repository?"
        print_info "Navigating to $PROJECT_ROOT and pulling latest changes..."
        sudo git -C "$PROJECT_ROOT" pull origin dev.test || sudo git -C "$PROJECT_ROOT" pull origin dev.test
        if [ $? -ne 0 ]; then
            print_error "Failed to pull latest changes from repository. Check permissions or network."
            exit 1
        fi
        print_success "Repository updated."
    else
        print_info "Cloning repository '$REPO_URL' into '$PROJECT_ROOT'..."
        # Corrected: Create parent directory correctly if it doesn't exist
        sudo mkdir -p "$(dirname "$PROJECT_ROOT")"

        sudo git clone --branch dev.test --single-branch "$REPO_URL" "$PROJECT_ROOT" || { print_error "Failed to clone repository"; exit 1; }
        sudo chown -R "$LINUX_USER:$LINUX_USER" "$PROJECT_ROOT" || { print_warning "Could not change ownership of $PROJECT_ROOT to $LINUX_USER. Manual intervention might be needed for permissions."; }
        print_success "Repository cloned successfully."
    fi
    sleep 1
}

# --- Backend Deployment ---
deploy_backend() {
    print_info "--- Deploying Flask Backend ---"
    sleep 1

    print_info "Navigating to backend directory: $BACKEND_DIR"
    cd "$BACKEND_DIR" || { print_error "Backend directory not found: $BACKEND_DIR"; exit 1; }

    print_info "Creating and activating Python virtual environment..."
    python3 -m venv venv || { print_error "Failed to create virtual environment."; exit 1; }
    source venv/bin/activate || { print_error "Failed to activate virtual environment."; exit 1; }
    print_success "Virtual environment activated."
    sleep 1

    print_info "Installing Python dependencies (Flask etc.)..."
    # Assuming requirements.txt exists and contains all necessary packages
    pip install pyrogram flask[async] requests flask_cors psutil || { print_error "Failed to install Python dependencies."; exit 1; }
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
# Explicitly tell Flask to run on the configured host and port
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

# --- Frontend Deployment ---
deploy_frontend() {
    print_info "--- Deploying React Vite Frontend ---"
    sleep 1

    print_info "Navigating to frontend directory: $FRONTEND_DIR"
    cd "$FRONTEND_DIR" || { print_error "Frontend directory not found: $FRONTEND_DIR"; exit 1; }

    # Ensure NVM is sourced again for this subshell
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

# --- Configure Frontend API URL in .env.production and Rebuild ---
configure_frontend_api_url() {
    print_info "--- Configuring Frontend API URL ---"
    sleep 1

    local server_ip
    read -p "$(echo -e "${YELLOW}INPUT:${RESET} Enter your server's public IP address (e.g., 192.168.1.100) or domain name if using one: ")" server_ip
    if [ -z "$server_ip" ]; then
        print_error "Server IP/Domain cannot be empty. Exiting."
        exit 1
    fi

    # API URL now points directly to Flask's address
    local frontend_api_url="http://$server_ip:$BACKEND_PORT"

    print_info "Writing frontend environment variable VITE_APP_API_URL to .env.production..."
    echo "export VITE_APP_API_URL=$frontend_api_url" | sudo tee "$FRONTEND_DIR/.env.production" > /dev/null || { print_error "Failed to write .env.production file. Check permissions."; exit 1; }
    echo "export AP_PORT=$BACKEND_PORT" | sudo tee "$FRONTEND_DIR/.env.production" > /dev/null || { print_error "Failed to write .env.production file. Check permissions."; exit 1; }
    print_success ".env.production created/updated with VITE_APP_API_URL=$frontend_api_url"
    sudo chown "$LINUX_USER:$LINUX_USER" "$FRONTEND_DIR/.env.production" || { print_warning "Could not change ownership of .env.production. Manual intervention might be needed for permissions."; }
    sleep 1

    # Rebuild frontend to apply the new .env.production
    print_info "Rebuilding frontend to apply new API URL..."
    cd "$FRONTEND_DIR" || { print_error "Frontend directory not found: $FRONTEND_DIR"; exit 1; }
    npm run build || { print_error "Failed to rebuild React Vite frontend after updating API URL."; exit 1; }
    print_success "Frontend rebuilt successfully with updated API URL."
    sleep 1
}


# --- Firewall Configuration ---
# --- Firewall Configuration ---
configure_firewall() {
    print_info "--- Configuring Firewall (UFW) ---"
    sleep 1

    print_info "Enabling UFW (if not already enabled)..."
    sudo ufw status | grep -q "Status: active" || sudo ufw enable
    print_success "UFW is active."
    sleep 1

    # Get the current SSH port
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

    # Only allow the backend port, as Flask serves everything directly
    print_info "Allowing external access to port $BACKEND_PORT for Flask application..."
    sudo ufw allow "$BACKEND_PORT"/tcp || { print_error "Failed to allow port $BACKEND_PORT through UFW."; exit 1; }
    print_success "Port $BACKEND_PORT allowed for external access."

    print_info "You can check UFW status with: sudo ufw status"
    sleep 2
}

# --- Main Execution Flow ---
main() {
    print_header
    confirm_action "This script will deploy your Candy panel with Flask serving both frontend and backend. Ensure you have updated the REPO_URL variable in the script."

    check_prerequisites
    setup_permissions # Call the new function here
    install_nodejs_with_nvm
    clone_or_update_repo
    deploy_backend
    deploy_frontend
    configure_frontend_api_url # New step to configure frontend URL
    configure_firewall
    # Removed setup_ssl as Nginx and Certbot are not used

    echo -e "\n${BOLD}${GREEN}====================================================${RESET}"
    echo -e "${BOLD}${GREEN} Deployment Complete!                               ${RESET}"
    echo -e "${BOLD}${GREEN}====================================================${RESET}"
    echo -e "${BOLD}${GREEN} Your Candy Panel should now be accessible at:${RESET}"
    echo -e "${BOLD}${GREEN} http://YOUR_SERVER_IP:$BACKEND_PORT${RESET}"
    print_warning "Remember to replace YOUR_SERVER_IP with your actual server's public IP address."
    print_warning "Note: SSL is NOT configured with this setup. For HTTPS, you will need to add a reverse proxy like Nginx or Caddy."
    echo -e "${BOLD}${GREEN}====================================================${RESET}\n"
    print_info "Ensure the Linux user '$LINUX_USER' has appropriate permissions for WireGuard operations."
    print_info "Flask application is running on port $BACKEND_PORT and serving all content."
}

main "$@"
