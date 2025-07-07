#!/bin/bash


# --- Configuration Variables ---
PROJECT_NAME="CandyPanel"
REPO_URL="https://github.com/AmiRCandy/Candy-Panel.git"
PROJECT_ROOT="/var/www/$PROJECT_NAME"
BACKEND_DIR="$PROJECT_ROOT/Backend"
FRONTEND_DIR="$PROJECT_ROOT/Frontend"
FASTAPI_APP_ENTRY="main:app"
LINUX_USER=$(whoami)
# --- Backend specific configuration (changed from Gunicorn Socket to Uvicorn TCP) ---
BACKEND_HOST="0.0.0.0"
BACKEND_PORT="3446" # Using 8000 for backend to avoid conflict with Nginx on 3445
# --- Nginx Configuration ---
NGINX_CONF_PATH="/etc/nginx/sites-available/$PROJECT_NAME"
NGINX_SYMLINK_PATH="/etc/nginx/sites-enabled/$PROJECT_NAME"
# --- No separate Gunicorn log directory needed for direct Uvicorn run ---
# GUNICORN_LOG_DIR="/var/log/gunicorn" # No longer needed, Uvicorn logs to stdout/stderr (journalctl)
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
    echo -e "${BOLD}${CYAN}  Candy Panel Deployment Script                     ${RESET}"
    echo -e "${BOLD}${CYAN}====================================================${RESET}"
    echo -e "${BOLD}${YELLOW}  Project: $PROJECT_NAME${RESET}"
    echo -e "${BOLD}${YELLOW}  Repo: $REPO_URL${RESET}"
    echo -e "${BOLD}${YELLOW}  User: $LINUX_USER${RESET}"
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
    # Removed 'npm' from this list as it will be installed via NVM
    # Removed 'gunicorn' from this list as we're using uvicorn directly
    for cmd in git python3 nginx ufw certbot python3.10-venv curl; do
        if ! command -v "$cmd" &> /dev/null; then
            missing_packages+=("$cmd")
        fi
    done

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

install_nodejs_with_nvm() {
    print_info "--- Installing Node.js and npm using NVM ---"
    sleep 1

    # Check if NVM is already installed
    if [ -s "$HOME/.nvm/nvm.sh" ]; then
        print_warning "NVM appears to be already installed. Sourcing it..."
        . "$HOME/.nvm/nvm.sh" # Source NVM
    else
        print_info "Installing NVM (Node Version Manager)..."
        # Download and run the NVM installation script
        curl -o- "https://raw.githubusercontent.com/nvm-sh/nvm/$NVM_VERSION/install.sh" | bash || { print_error "Failed to download and install NVM."; exit 1; }
        
        # Source NVM script to make 'nvm' command available in the current session
        export NVM_DIR="$HOME/.nvm"
        [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
        [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion
        
        # Verify NVM is sourced
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
        sudo git -C "$PROJECT_ROOT" pull origin main || sudo git -C "$PROJECT_ROOT" pull origin master # Adjust branch if needed
        if [ $? -ne 0 ]; then
            print_error "Failed to pull latest changes from repository. Check permissions or network."
            exit 1
        fi
        print_success "Repository updated."
    else
        print_info "Cloning repository '$REPO_URL' into '$PROJECT_ROOT'..."
        sudo mkdir -p "$(dirname "$PROJECT_ROOT")" || { print_error "Failed to create parent directory for $PROJECT_ROOT"; exit 1; }
        sudo git clone "$REPO_URL" "$PROJECT_ROOT" || { print_error "Failed to clone repository"; exit 1; }
        sudo chown -R "$LINUX_USER:$LINUX_USER" "$PROJECT_ROOT" || { print_warning "Could not change ownership of $PROJECT_ROOT to $LINUX_USER. Manual intervention might be needed for permissions."; }
        print_success "Repository cloned successfully."
    fi
    sleep 1
}

# --- Backend Deployment (Updated for Uvicorn direct run) ---
deploy_backend() {
    print_info "--- Deploying FastAPI Backend with Uvicorn ---"
    sleep 1

    print_info "Navigating to backend directory: $BACKEND_DIR"
    cd "$BACKEND_DIR" || { print_error "Backend directory not found: $BACKEND_DIR"; exit 1; }

    print_info "Creating and activating Python virtual environment..."
    python3 -m venv venv || { print_error "Failed to create virtual environment."; exit 1; }
    source venv/bin/activate || { print_error "Failed to activate virtual environment."; exit 1; }
    print_success "Virtual environment activated."
    sleep 1

    # Only install uvicorn[standard], no need for gunicorn
    print_info "Installing Python dependencies: fastapi, psutil, requests, pyrogram, uvicorn[standard]..."
    pip install fastapi psutil requests pyrogram "uvicorn[standard]" || { print_error "Failed to install Python dependencies."; exit 1; }
    print_success "Python dependencies installed."
    sleep 1

    # No Gunicorn configuration file needed for direct Uvicorn run
    # Removing the Gunicorn_LOG_DIR creation and gunicorn_config.py tee block

    print_info "Creating Systemd service file for FastAPI (Uvicorn)..."
    sudo tee "/etc/systemd/system/${PROJECT_NAME}_fastapi.service" > /dev/null <<EOF
[Unit]
Description=Uvicorn instance for ${PROJECT_NAME} FastAPI
After=network.target

[Service]
User=$LINUX_USER
Group=$LINUX_USER
WorkingDirectory=$BACKEND_DIR
ExecStart=$BACKEND_DIR/venv/bin/uvicorn $FASTAPI_APP_ENTRY --host $BACKEND_HOST --port $BACKEND_PORT --log-level info
Restart=always
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF
    print_success "Systemd service file created."
    sleep 1

    print_info "Reloading Systemd daemon, enabling and starting FastAPI service..."
    sudo systemctl daemon-reload || { print_error "Failed to reload Systemd daemon."; exit 1; }
    sudo systemctl enable "${PROJECT_NAME}_fastapi.service" || { print_error "Failed to enable FastAPI service."; exit 1; }
    sudo systemctl start "${PROJECT_NAME}_fastapi.service" || { print_error "Failed to start FastAPI service."; exit 1; }
    print_success "FastAPI service started and enabled to run on boot."
    print_info "You can check its status with: sudo systemctl status ${PROJECT_NAME}_fastapi.service"
    print_info "View logs with: journalctl -u ${PROJECT_NAME}_fastapi.service --since '1 hour ago'"
    sleep 2
}

# --- Frontend Deployment ---
deploy_frontend() {
    print_info "--- Deploying React Vite Frontend ---"
    sleep 1

    print_info "Navigating to frontend directory: $FRONTEND_DIR"
    cd "$FRONTEND_DIR" || { print_error "Frontend directory not found: $FRONTEND_DIR"; exit 1; }

    # Ensure NVM is sourced again for this subshell if not already
    if [ -s "$HOME/.nvm/nvm.sh" ]; then
        . "$HOME/.nvm/nvm.sh" # Source NVM
        nvm use "$NODE_VERSION" || print_warning "Could not activate Node.js v${NODE_VERSION} with nvm in this subshell. Continuing anyway."
    else
        print_error "NVM not found or not sourced. Node.js/npm commands might fail. Did install_nodejs_with_nvm run successfully?"
        exit 1
    fi

    print_info "Installing Node.js dependencies..."
    npm install || { print_error "Failed to install Node.js dependencies. Check npm logs and internet connection."; exit 1; }
    print_success "Node.js dependencies installed."
    sleep 1

    print_info "Building React Vite frontend for production..."
    npm run build || { print_error "Failed to build React Vite frontend. Check your package.json 'build' script and Node.js environment."; exit 1; }
    print_success "Frontend built successfully. Static files are in '$FRONTEND_DIR/dist'."
    sleep 2
}

# --- Nginx Configuration (Updated for Uvicorn TCP backend) ---
configure_nginx() {
    print_info "--- Configuring Nginx ---"
    sleep 1

    local domain_name
    read -p "$(echo -e "${YELLOW}INPUT:${RESET} Enter your domain name (e.g., example.com or your server IP): ")" domain_name
    if [ -z "$domain_name" ]; then
        print_error "Domain name cannot be empty. Exiting."
        exit 1
    fi

    print_info "Creating Nginx configuration file for $domain_name..."
    sudo tee "$NGINX_CONF_PATH" > /dev/null <<EOF
server {
    listen 3445 ; # Nginx listens for public traffic on 3445
    server_name $domain_name www.$domain_name; # Add www. if applicable

    # Serve React Vite frontend static files
    location / {
        root $FRONTEND_DIR/dist;
        try_files \$uri \$uri/ /index.html;
    }

    # Proxy API requests to FastAPI backend (listening on localhost:8000)
    location /api/ {
        proxy_pass http://127.0.0.1:$BACKEND_PORT; # Proxy to Uvicorn's TCP port
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_redirect off;
    }

    error_log /var/log/nginx/${PROJECT_NAME}_error.log warn;
    access_log /var/log/nginx/${PROJECT_NAME}_access.log combined;
}
EOF
    print_success "Nginx configuration created at $NGINX_CONF_PATH."
    sleep 1

    print_info "Creating symlink to enable Nginx site..."
    if [ -L "$NGINX_SYMLINK_PATH" ]; then
        print_warning "Nginx symlink already exists. Removing old one."
        sudo rm "$NGINX_SYMLINK_PATH"
    fi
    sudo ln -s "$NGINX_CONF_PATH" "$NGINX_SYMLINK_PATH" || { print_error "Failed to create Nginx symlink."; exit 1; }
    print_success "Nginx site enabled."
    sleep 1

    print_info "Testing Nginx configuration..."
    sudo nginx -t || { print_error "Nginx configuration test failed. Please check the config file: $NGINX_CONF_PATH"; exit 1; }
    print_success "Nginx configuration test successful."
    sleep 1

    print_info "Restarting Nginx service..."
    sudo systemctl restart nginx || { print_error "Failed to restart Nginx service."; exit 1; }
    print_success "Nginx service restarted."
    sleep 2

    # Store domain name for Certbot
    echo "$domain_name" > /tmp/${PROJECT_NAME}_domain.txt
}

# --- Firewall Configuration (Updated for backend port) ---
configure_firewall() {
    print_info "--- Configuring Firewall (UFW) ---"
    sleep 1

    print_info "Enabling UFW (if not already enabled)..."
    sudo ufw status | grep -q "Status: active" || sudo ufw enable
    print_success "UFW is active."
    sleep 1

    print_info "Allowing Nginx Full (HTTP and HTTPS) through firewall..."
    sudo ufw allow 'Nginx Full' || { print_error "Failed to allow Nginx Full through UFW."; exit 1; }
    print_success "Nginx Full profile allowed (ports 80, 443)."

    print_info "Allowing port 3445 for Nginx frontend access..."
    sudo ufw allow 3445/tcp || { print_error "Failed to allow port 3445 through UFW."; exit 1; }
    print_success "Port 3445 allowed."

    # Explicitly allow localhost connections to backend port (8000) for Nginx to connect
    # This is typically not strictly necessary for UFW defaults, but ensures it.
    # We do NOT open port 8000 to the public internet, as Nginx is the proxy.
    print_info "Allowing internal localhost access to backend port $BACKEND_PORT for Nginx..."
    sudo ufw allow from 127.0.0.1 to any port "$BACKEND_PORT" proto tcp || { print_error "Failed to allow localhost access to backend port $BACKEND_PORT."; exit 1; }
    print_success "Internal access to backend port $BACKEND_PORT allowed."

    print_info "You can check UFW status with: sudo ufw status"
    sleep 2
}

# --- SSL with Certbot ---
setup_ssl() {
    print_info "--- Setting up SSL with Let's Encrypt (Certbot) ---"
    sleep 1

    local domain_name=$(cat /tmp/${PROJECT_NAME}_domain.txt 2>/dev/null)
    if [ -z "$domain_name" ] || [[ "$domain_name" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
        print_warning "Skipping SSL setup: No valid domain name found or it's an IP address."
        print_warning "You can manually run 'sudo certbot --nginx -d your_domain.com' later if you set up a domain."
        return
    fi

    confirm_action "Do you want to set up HTTPS with Let's Encrypt for $domain_name?"
    print_info "Running Certbot to obtain and install SSL certificate..."
    # Certbot needs to verify domain ownership via standard HTTP/HTTPS ports (80/443).
    # Nginx Full profile should ensure these are open.
    sudo certbot --nginx -d "$domain_name" -d "www.$domain_name" || { print_error "Certbot failed. Check DNS records and Nginx configuration."; return; }
    print_success "SSL certificate obtained and installed successfully!"
    print_info "Your site should now be accessible via HTTPS."
    sleep 2
}

# --- Main Execution Flow ---
main() {
    print_header
    confirm_action "This script will deploy your Candy panel. Ensure you have updated the REPO_URL variable in the script."

    check_prerequisites
    install_nodejs_with_nvm
    clone_or_update_repo
    deploy_backend # Now uses Uvicorn directly
    deploy_frontend
    configure_nginx # Updated for Uvicorn TCP backend
    configure_firewall # Updated for Uvicorn TCP backend port
    setup_ssl

    echo -e "\n${BOLD}${GREEN}====================================================${RESET}"
    echo -e "${BOLD}${GREEN}  Deployment Complete!                                ${RESET}"
    echo -e "${BOLD}${GREEN}====================================================${RESET}"
    local final_domain=$(cat /tmp/${PROJECT_NAME}_domain.txt 2>/dev/null)
    if [ -n "$final_domain" ] && ! [[ "$final_domain" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
        echo -e "${BOLD}${GREEN}  Your Candy Panel should now be accessible at:${RESET}"
        echo -e "${BOLD}${GREEN}  https://$final_domain${RESET}"
    else
        echo -e "${BOLD}${GREEN}  Your Candy Panel should now be accessible at:${RESET}"
        echo -e "${BOLD}${GREEN}  http://YOUR_SERVER_IP:3445${RESET}" # Adjusted to reflect Nginx listening on 3445
        print_warning "Remember to replace YOUR_SERVER_IP with your actual server's public IP address."
        print_warning "Note: If using an IP, SSL will not be configured."
    fi
    echo -e "${BOLD}${GREEN}====================================================${RESET}\n"
    print_info "Ensure the Linux user '$LINUX_USER' has appropriate permissions for WireGuard operations."
    rm -f /tmp/${PROJECT_NAME}_domain.txt # Clean up temp file
}

main "$@"