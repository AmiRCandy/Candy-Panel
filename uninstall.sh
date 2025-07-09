#!/bin/bash

# --- Configuration Variables (MUST match install.sh) ---
PROJECT_NAME="CandyPanel"
PROJECT_ROOT="/var/www/$PROJECT_NAME"
SUDOERS_FILE="/etc/sudoers.d/candypanel_permissions"
LINUX_USER=$(whoami) # User who ran the install script

# --- Styling Functions ---
GREEN='\e[32m'
BLUE='\e[34m'
RED='\e[31m'
YELLOW='\e[33m'
CYAN='\e[36m'
RESET='\\e[0m'
BOLD='\\e[1m'
UNDERLINE='\\e[4m'

print_header() {
    echo -e "\n${BOLD}${RED}====================================================${RESET}"
    echo -e "${BOLD}${RED} Candy Panel UNINSTALL Script                       ${RESET}"
    echo -e "${BOLD}${RED}====================================================${RESET}"
    echo -e "${BOLD}${YELLOW} Project: $PROJECT_NAME${RESET}"
    echo -e "${BOLD}${YELLOW} Project Root: $PROJECT_ROOT${RESET}"
    echo -e "${BOLD}${YELLOW} User: $LINUX_USER${RESET}"
    echo -e "${BOLD}${RED}====================================================${RESET}\n"
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

# --- Get BACKEND_PORT from environment or user input ---
get_backend_port() {
    # Check if AP_PORT environment variable is set
    if [ -n "$AP_PORT" ]; then
        BACKEND_PORT="$AP_PORT"
        print_info "Using BACKEND_PORT from AP_PORT environment variable: $BACKEND_PORT"
    else
        # If AP_PORT is not set, ask the user
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
    # Export the variable so it's available in functions
    export BACKEND_PORT
    sleep 1
}

# --- Uninstall Functions ---

# Function to stop and disable Flask service
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
    fi # Corrected missing 'fi' for the if-else block
    
    print_info "Reloading Systemd daemon..."
    sudo systemctl daemon-reload || { print_warning "Failed to reload Systemd daemon. This might not be critical for uninstallation."; }
    print_success "Systemd daemon reloaded."
    sleep 2
}

# Function to remove the project directory
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

# Function to remove firewall rules
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

# Function to remove NVM and Node.js (optional)
uninstall_nvm() {
    print_info "--- Uninstalling NVM and Node.js (Optional) ---"
    sleep 1

    if [ -d "$HOME/.nvm" ]; then
        confirm_action "Do you want to uninstall NVM (Node Version Manager) and all Node.js versions managed by it? This will remove '$HOME/.nvm'."
        print_info "Attempting to uninstall NVM..."
        # Source NVM if it's installed to use nvm uninstall
        if [ -s "$HOME/.nvm/nvm.sh" ]; then
            . "$HOME/.nvm/nvm.sh"
            nvm deactivate > /dev/null 2>&1 # Deactivate any active Node.js version
            nvm uninstall --lts > /dev/null 2>&1 # Uninstall LTS versions
            nvm uninstall "$(nvm current)" > /dev/null 2>&1 # Uninstall current version
        fi

        # Remove NVM directory and related lines from shell config files
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

# Function to remove the sudoers file created by install.sh
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

# --- Main Execution Flow ---
main() {
    print_header
    confirm_action "This script will attempt to UNINSTALL the Candy Panel project. This includes stopping services, removing files, and reverting firewall rules. Proceed with uninstallation?"

    get_backend_port # Call function to determine BACKEND_PORT

    uninstall_backend_service
    remove_project_directory
    remove_firewall_rules
    remove_sudoers_file
    uninstall_nvm # Optional: Call NVM uninstallation

    echo -e "\n${BOLD}${GREEN}====================================================${RESET}"
    echo -e "${BOLD}${GREEN} Uninstallation Attempt Complete!                   ${RESET}"
    echo -e "${BOLD}${GREEN}====================================================${RESET}"
    print_warning "Manual cleanup might still be required for some system packages (e.g., wireguard, qrencode, python3-psutil) if they were installed solely for this project and are no longer needed."
    print_warning "To uninstall system packages, you can use: sudo apt remove wireguard qrencode python3-psutil"
    echo -e "${BOLD}${GREEN}====================================================${RESET}\n"
}

main "$@"
