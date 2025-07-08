# core.py
import subprocess, json, random, uuid, time, ipaddress, os, psutil, shutil, re
from db import SQLite
from datetime import datetime

# --- Configuration Paths (Consider making these configurable in a real app) ---
SERVER_PUBLIC_KEY_PATH = "/etc/wireguard/server_public_wgX.key"
SERVER_PRIVATE_KEY_PATH = "/etc/wireguard/server_private_wgX.key"
WG_CONF_PATH = "/etc/wireguard/wgX.conf"
WG_DIR = "/etc/wireguard"
DB_FILE = "total_traffic.json" # File to store cumulative traffic data

class CandyPanel:
    def __init__(self):
        """
        Initializes the CandyPanel with a SQLite database connection.
        """
        self.db = SQLite()

    @staticmethod
    def _is_valid_ip(ip: str) -> bool:
        """
        Checks if a given string is a valid IP address.
        """
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False

    def run_command(self, cmd: str, check: bool = True) -> str | None:
        """
        Executes a shell command and returns its stdout.
        Raises an exception if the command fails and 'check' is True.
        """
        try:
            result = subprocess.run(cmd, shell=True, check=check, capture_output=True, text=True)
            if result.returncode != 0:
                # Log the error instead of just printing and exiting
                print(f"Error running command '{cmd}': {result.stderr.strip()}")
                raise Exception(f"Command failed: {result.stderr.strip()}")
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"Error running '{cmd}': {e.stderr.strip()}")
            if check:
                # In a production app, consider raising a custom exception here
                # instead of exiting, to allow the caller to handle it gracefully.
                raise CommandExecutionError(f"Command '{cmd}' failed: {e.stderr.strip()}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred while running '{cmd}': {e}")
            if check:
                raise CommandExecutionError(f"Unexpected error: {e}")
            return None

    @staticmethod
    def load_traffic_db() -> dict:
        """
        Loads the total traffic data from the JSON file.
        """
        if os.path.exists(DB_FILE):
            try:
                with open(DB_FILE, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print(f"Error: Could not decode JSON from {DB_FILE}. Returning empty dict.")
                return {}
        return {}

    @staticmethod
    def save_traffic_db(data: dict):
        """
        Saves the total traffic data to the JSON file.
        """
        with open(DB_FILE, 'w') as f:
            json.dump(data, f, indent=4)

    def _get_interface_path(self, name: str) -> str:
        """
        Constructs the full path for a WireGuard interface configuration file.
        """
        return os.path.join(WG_DIR, f"{name}.conf")

    def _interface_exists(self, name: str) -> bool:
        """
        Checks if a WireGuard interface configuration file exists.
        """
        return os.path.exists(self._get_interface_path(name))

    def _get_all_ips_in_subnet(self, subnet_cidr: str) -> list[str]:
        """
        Returns all host IPs within a given subnet CIDR.
        """
        network = ipaddress.ip_network(subnet_cidr, strict=False)
        return [str(ip) for ip in network.hosts()]

    def _get_server_public_key(self, wg_id: int) -> str:
        """
        Retrieves the server's public key for a specific WireGuard interface.
        """
        try:
            with open(SERVER_PUBLIC_KEY_PATH.replace('X', str(wg_id))) as f:
                return f.read().strip()
        except FileNotFoundError:
            print(f"Error: Server public key file not found for wg{wg_id}.")
            raise

    def _generate_keypair(self) -> tuple[str, str]:
        """
        Generates a new WireGuard private and public key pair.
        """
        priv = self.run_command("wg genkey")
        pub = self.run_command(f"echo {priv} | wg pubkey")
        return priv, pub

    def _get_used_ips(self, wg_id: int) -> set[int]:
        """
        Parses the WireGuard configuration file to find used client IPs.
        Assumes IPs are in the format 10.0.0.X/32.
        """
        try:
            with open(WG_CONF_PATH.replace('X', str(wg_id)), "r") as f:
                content = f.read()
            # Regex to find IPs in "AllowedIPs = 10.0.0.X/32" format
            # This regex needs to be more flexible if address_range can vary significantly
            # For robustness, consider parsing the full IP and then checking if it's in the subnet
            ips = re.findall(r"AllowedIPs\s*=\s*\d+\.\d+\.\d+\.(\d+)/32", content)
            return set(int(ip) for ip in ips)
        except FileNotFoundError:
            print(f"Error: WireGuard config file not found for wg{wg_id}.")
            return set() # Return empty set if config file doesn't exist

    def _backup_config(self, wg_id: int):
        """
        Creates a backup of the WireGuard configuration file.
        """
        config_path = WG_CONF_PATH.replace('X', str(wg_id))
        backup_path = f"{config_path}.bak"
        try:
            shutil.copy(config_path, backup_path)
            print(f"[+] Backup created: {backup_path}")
        except FileNotFoundError:
            print(f"[!] Warning: Config file {config_path} not found for backup.")
        except Exception as e:
            print(f"[!] Error creating backup for wg{wg_id}: {e}")

    def _reload_wireguard(self, wg_id: int):
        """
        Reloads a specific WireGuard interface.
        """
        print(f"[*] Reloading WireGuard interface wg{wg_id}...")
        # Ensure the interface is down before bringing it up to apply changes
        self.run_command(f"wg-quick down wg{wg_id} || true", check=False) # '|| true' prevents error if already down
        self.run_command(f"wg-quick up wg{wg_id}")
        print(f"[*] WireGuard interface wg{wg_id} reloaded.")


    def _get_current_traffic(self) -> dict:
        """
        Retrieves current traffic statistics for all WireGuard peers across all interfaces.
        Returns a dictionary: {wg_id: {pubkey: {ip: str, rx: int, tx: int}}}
        """
        traffic = {}
        for interface_row in self.db.select('interfaces'):
            wg_id = interface_row['wg']
            result = subprocess.run(['wg', 'show', f"wg{wg_id}"], capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Warning: Failed to run `wg show wg{wg_id}`. Error: {result.stderr.strip()}")
                continue # Skip this interface if command fails

            output = result.stdout
            # Split output by 'peer:' to process each peer block
            peers_blocks = output.split('peer: ')[1:]

            traffic[wg_id] = {}
            for peer_block in peers_blocks:
                lines = peer_block.strip().splitlines()
                pubkey = lines[0].strip()

                # Extract AllowedIPs
                allowed_line = next((line for line in lines if 'allowed ips:' in line.lower()), None)
                ip = 'unknown'
                if allowed_line:
                    match = re.search(r'allowed ips:\s*(\S+)', allowed_line, re.IGNORECASE)
                    if match:
                        ip = match.group(1).split('/')[0] # Get just the IP, not the /32

                # Extract Transfer (rx/tx)
                transfer_line = next((line for line in lines if 'transfer:' in line.lower()), None)
                rx, tx = 0, 0
                if transfer_line:
                    tx_rx_matches = re.findall(r'(\d+)\sbytes', transfer_line)
                    if len(tx_rx_matches) >= 1:
                        rx = int(tx_rx_matches[0])
                    if len(tx_rx_matches) >= 2:
                        tx = int(tx_rx_matches[1])

                traffic[wg_id][pubkey] = {
                    'ip': ip,
                    'rx': rx,
                    'tx': tx
                }
        return traffic

    def _install_candy_panel(self, server_ip: str,
                             wg_port: str,
                             wg_address_range: str = "10.0.0.1/24",
                             wg_dns: str = "8.8.8.8",
                             admin_user: str = 'admin',
                             admin_password: str = 'admin') -> tuple[bool, str]:
        """
        Installs WireGuard and initializes the CandyPanel server configuration.
        """
        if not self._is_valid_ip(server_ip):
            return False, 'IP INCORRECT'
        install_status = self.db.get('settings',where={'key':'install'})
        if bool(install_status and install_status['value'] == '1') : return False , 'Installed before !'
        print("[+] Updating system and installing WireGuard...")
        try:
            self.run_command("sudo apt update")
            self.run_command("sudo apt upgrade -y")
            self.run_command("sudo apt install -y wireguard qrencode")
        except Exception as e:
            return False, f"Failed to install WireGuard dependencies: {e}"

        print("[+] Creating /etc/wireguard if not exists...")
        os.makedirs("/etc/wireguard", exist_ok=True)
        os.chmod("/etc/wireguard", 0o700)

        wg_id = 0 # Default initial interface ID
        server_private_key_path = SERVER_PRIVATE_KEY_PATH.replace('X', str(wg_id))
        server_public_key_path = SERVER_PUBLIC_KEY_PATH.replace('X', str(wg_id))
        wg_conf_path = WG_CONF_PATH.replace('X', str(wg_id))

        private_key, public_key = "", ""
        if not os.path.exists(server_private_key_path):
            print("[+] Generating server private/public keys...")
            private_key, public_key = self._generate_keypair()
            with open(server_private_key_path, "w") as f:
                f.write(private_key)
            os.chmod(server_private_key_path, 0o600)
            with open(server_public_key_path, "w") as f:
                f.write(public_key)
        else:
            with open(server_private_key_path) as f:
                private_key = f.read().strip()
            with open(server_public_key_path) as f:
                public_key = f.read().strip()

        wg_conf = f"""
[Interface]
Address = {wg_address_range}
ListenPort = {wg_port}
PrivateKey = {private_key}
SaveConfig = true
PostUp = ufw allow {wg_port}/udp
PostDown = ufw delete allow {wg_port}/udp
        """.strip()

        with open(wg_conf_path, "w") as f:
            f.write(wg_conf + "\n")
        os.chmod(wg_conf_path, 0o600)

        # Insert initial interface into DB
        if not self.db.has('interfaces', {'wg': wg_id}):
            self.db.insert('interfaces', {
                'wg': wg_id,
                'private_key': private_key,
                'public_key': public_key,
                'port': wg_port,
                'address_range': wg_address_range,
                'status': True # Default status is active
            })
        else:
            # Update if it already exists (e.g., re-running install)
            self.db.update('interfaces', {
                'private_key': private_key,
                'public_key': public_key,
                'port': wg_port,
                'address_range': wg_address_range,
                'status': True
            }, {'wg': wg_id})

        try:
            self.run_command(f"sudo systemctl enable wg-quick@wg{wg_id}")
            self.run_command(f"sudo systemctl start wg-quick@wg{wg_id}")
        except Exception as e:
            return False, f"Failed to start WireGuard service: {e}"

        # Update initial settings (e.g., server IP, DNS, admin credentials)
        self.db.update('settings', {'value': server_ip}, {'key': 'server_ip'})
        self.db.update('settings', {'value': wg_dns}, {'key': 'dns'})
        # IMPORTANT: In a real app, hash the admin password before storing!
        admin_data = json.dumps({'user': admin_user, 'password': admin_password})
        self.db.update('settings', {'value': admin_data}, {'key': 'admin'})
        self.db.update('settings', {'value': '1'}, {'key': 'install'})
        # Add cron job to run the script every 15 minutes (adjust as needed) self.run_command("*/15 * * * * python3 ./corn.py")
        return True, 'Installed successfully!'

    def _admin_login(self, user: str, password: str) -> tuple[bool, str]:
        """
        Authenticates an admin user.
        WARNING: Password stored in plaintext in DB. This should be hashed!
        """
        admin_settings = json.loads(self.db.get('settings', where={'key': 'admin'})['value'])
        # In a real app, compare hashed passwords here
        if admin_settings.get('user') == user and admin_settings.get('password') == password:
            session_token = str(uuid.uuid4())
            self.db.update('settings', {'value': session_token}, {'key': 'session_token'})
            return True, session_token
        else:
            return False, 'Wrong username or password!'

    def _dashboard_stats(self) -> dict:
        """
        Retrieves various system and application statistics for the dashboard.
        """
        mem = psutil.virtual_memory()
        net1 = psutil.net_io_counters()
        time.sleep(1) # Wait for 1 second to calculate network speed
        net2 = psutil.net_io_counters()

        bytes_sent = net2.bytes_sent - net1.bytes_sent
        bytes_recv = net2.bytes_recv - net1.bytes_recv
        upload_speed_kbps = bytes_sent / 1024 # KB/s
        download_speed_kbps = bytes_recv / 1024 # KB/s

        return {
            'cpu': f"{psutil.cpu_percent()}%", # psutil.cpu_percent() without interval calculates since last call
            'mem': {
                'total': f"{mem.total / (1024**3):.2f} GB",
                'available': f"{mem.available / (1024**3):.2f} GB",
                'usage': f"{mem.percent}%"
            },
            'clients_count': self.db.count('clients'),
            'status': self.db.get('settings', where={'key': 'status'})['value'],
            'alert': json.loads(self.db.get('settings', where={'key': 'alert'})['value']),
            'bandwidth': self.db.get('settings', where={'key': 'bandwidth'})['value'],
            'uptime': self.db.get('settings', where={'key': 'uptime'})['value'],
            'net': {'download': f"{download_speed_kbps:.2f} KB/s", 'upload': f"{upload_speed_kbps:.2f} KB/s"}
        }

    def _get_all_clients(self) -> list[dict]:
        """
        Retrieves all client records from the database.
        """
        return self.db.select('clients')

    def _new_client(self, name: str, expire: str, traffic: str, wg_id: int = 0, note: str = '') -> tuple[bool, str]:
        """
        Creates a new WireGuard client, generates its configuration, and adds it to the DB.
        'expire' should be a datetime string, 'traffic' should be a string representing bytes.
        """
        if self.db.has('clients', {'name': name}):
            return False, 'Client with this name already exists.'

        interface_wg = self.db.get('interfaces', where={'wg': wg_id})
        if not interface_wg:
            return False, f"WireGuard interface wg{wg_id} not found."

        used_ips = self._get_used_ips(wg_id)
        # Find the next available IP in the subnet
        # Assumes server IP is .1 and clients start from .2
        network_address_prefix = interface_wg['address_range'].rsplit('.', 1)[0]
        next_ip_host_part = 2
        # Ensure the generated IP is not already used by another client in the DB or in the WG config
        while f"{network_address_prefix}.{next_ip_host_part}" in [client['address'] for client in self.db.select('clients', where={'wg': wg_id})] or next_ip_host_part in used_ips:
            next_ip_host_part += 1
            if next_ip_host_part > 254: # Prevent infinite loop if subnet is full
                return False, "No available IP addresses in the subnet."

        client_ip = f"{network_address_prefix}.{next_ip_host_part}"
        client_private, client_public = self._generate_keypair()

        peer_entry = f"""
[Peer]
# {name}
PublicKey = {client_public}
AllowedIPs = {client_ip}/32
"""
        try:
            with open(WG_CONF_PATH.replace('X', str(wg_id)), "a") as f:
                f.write(peer_entry)
            # Apply changes to the running WireGuard interface without full restart
            self.run_command(f"bash -c 'wg syncconf wg{wg_id} <(wg-quick strip wg{wg_id})'")
        except Exception as e:
            return False, f"Failed to update WireGuard configuration: {e}"

        server_pubkey = self._get_server_public_key(wg_id)
        server_ip = self.db.get('settings', where={'key': 'server_ip'})['value']
        dns = self.db.get('settings', where={'key': 'dns'})['value']
        # MTU might not be available if not set in settings, provide a default
        mtu = self.db.get('settings', where={'key': 'mtu'})
        mtu_value = mtu['value'] if mtu else '1420' # Default MTU if not found

        client_config = f"""[Interface]
PrivateKey = {client_private}
Address = {client_ip}/32
DNS = {dns}
MTU = {mtu_value}

[Peer]
PublicKey = {server_pubkey}
Endpoint = {server_ip}:{interface_wg['port']}
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 25
"""
        # Store client data in DB
        self.db.insert('clients', {
            'name': name,
            'public_key': client_public,
            'private_key': client_private,
            'address': client_ip,
            'created_at': datetime.now().isoformat(), # Store as ISO format string
            'expires': expire, # Expecting ISO format or similar
            'traffic': traffic, # Total traffic quota in bytes
            'used_trafic': json.dumps({'download': 0, 'upload': 0}), # Initialize used traffic
            'wg': wg_id,
            'note': note,
            'connected_now': False, # Initial status
            'status': True # Active by default
        })
        return True, client_config

    def _delete_client(self, client_name: str) -> tuple[bool, str]:
        """
        Deletes a WireGuard client from the configuration and database.
        """
        client = self.db.get('clients', {'name': client_name})
        if not client:
            return False, f"Client '{client_name}' not found."

        wg_id = client['wg']
        config_path = WG_CONF_PATH.replace('X', str(wg_id))

        self._backup_config(wg_id) # Backup before modifying

        try:
            with open(config_path, "r") as f:
                lines = f.readlines()

            new_lines = []
            in_peer_block = False
            peer_block_to_delete = False
            temp_block = []

            for line in lines:
                if line.strip().startswith("[Peer]"):
                    if in_peer_block: # End of previous block, if any
                        new_lines.extend(temp_block)
                    temp_block = [line]
                    in_peer_block = True
                    peer_block_to_delete = False # Reset for new block
                elif in_peer_block:
                    temp_block.append(line)
                    if f"# {client_name}" in line.strip(): # Check for client name in comment
                        peer_block_to_delete = True
                    # An empty line or a new [Peer] indicates the end of the current peer block
                    if not line.strip() and in_peer_block:
                        if not peer_block_to_delete:
                            new_lines.extend(temp_block)
                        in_peer_block = False
                        temp_block = []
                else:
                    new_lines.append(line)

            # Handle the last block if file ends without an empty line
            if in_peer_block and not peer_block_to_delete:
                new_lines.extend(temp_block)

            if not peer_block_to_delete:
                print(f"[!] Client '{client_name}' peer block not found in config file. Proceeding with DB deletion.")
                # Even if not found in config, proceed to delete from DB if it exists there
                # This ensures DB is consistent even if config was manually altered
        except FileNotFoundError:
            print(f"[!] WireGuard config file {config_path} not found. Cannot delete peer from config.")
            # Still proceed to delete from DB
            new_lines = lines # Keep original lines if file not found to avoid writing empty file
        except Exception as e:
            print(f"[!] Error processing config file for client '{client_name}': {e}")
            new_lines = lines # Keep original lines if error to avoid data loss

        # Write the new configuration back only if the file exists and was successfully processed
        if os.path.exists(config_path):
            try:
                with open(config_path, "w") as f:
                    f.writelines(new_lines)
                self.run_command(f"wg syncconf wg{wg_id} <(wg-quick strip wg{wg_id})")
                print(f"[+] WireGuard config for wg{wg_id} updated.")
            except Exception as e:
                print(f"[!] Failed to update WireGuard config file for wg{wg_id}: {e}")
                # Decide if you want to abort here or proceed with DB deletion
        else:
            print(f"[!] Skipping config file update as {config_path} does not exist.")


        # Delete client from database
        self.db.delete('clients', {'name': client_name})
        print(f"[+] Client '{client_name}' deleted successfully from DB.")
        return True, f"Client '{client_name}' deleted successfully."


    def _edit_client(self, name: str, expire: str = None, traffic: str = None, status: bool = None, note: str = None) -> tuple[bool, str]:
        """
        Edits an existing client's details in the database.
        Allows partial updates by checking for None values.
        """
        if not self.db.has('clients', {'name': name}):
            return False, f"Client '{name}' not found."

        update_data = {}
        if expire is not None:
            update_data['expires'] = expire
        if traffic is not None:
            update_data['traffic'] = traffic
        if status is not None:
            update_data['status'] = status
        if note is not None:
            update_data['note'] = note

        if update_data:
            self.db.update('clients', update_data, {'name': name})
            return True, f"Client '{name}' edited successfully."
        else:
            return False, "No update data provided."


    def _new_interface_wg(self, address_range: str, port: int) -> tuple[bool, str]:
        """
        Creates a new WireGuard interface configuration and adds it to the database.
        """
        interfaces = self.db.select('interfaces')
        # Check for existing port or address range conflicts
        for interface in interfaces:
            if int(interface['port']) == port: # Ensure type consistency for comparison
                return False, f"An interface with port {port} already exists."
            if interface['address_range'] == address_range:
                return False, f"An interface with address range {address_range} already exists."

        # Find the next available wg ID
        existing_wg_ids = sorted([int(i['wg']) for i in interfaces])
        new_wg_id = 0
        while new_wg_id in existing_wg_ids:
            new_wg_id += 1

        interface_name = f"wg{new_wg_id}"
        path = self._get_interface_path(interface_name)

        if self._interface_exists(interface_name):
            return False, f"Interface {interface_name} configuration file already exists."

        private_key, public_key = self._generate_keypair()
        server_private_key_path = SERVER_PRIVATE_KEY_PATH.replace('X', str(new_wg_id))
        server_public_key_path = SERVER_PUBLIC_KEY_PATH.replace('X', str(new_wg_id))
        with open(server_private_key_path, "w") as f:
            f.write(private_key)
            os.chmod(server_private_key_path, 0o600)
            with open(server_public_key_path, "w") as f:
                f.write(public_key)
        config = f"""[Interface]
PrivateKey = {private_key}
Address = {address_range}
ListenPort = {port}
SaveConfig = true
PostUp = ufw allow {port}/udp
PostDown = ufw delete allow {port}/udp
"""
        try:
            with open(path, "w") as f:
                f.write(config)
            os.chmod(path, 0o600)
            print(f"[+] Interface {interface_name} created.")
            self.run_command(f"sudo systemctl enable wg-quick@{interface_name}") # Enable service
            self._reload_wireguard(new_wg_id) # Reload the new interface
        except Exception as e:
            return False, f"Failed to create or reload interface {interface_name}: {e}"

        self.db.insert('interfaces', {
            'wg': new_wg_id,
            'private_key': private_key,
            'public_key': public_key,
            'port': port,
            'address_range': address_range,
            'status': True
        })
        return True, 'New Interface Created!'

    def _edit_interface(self, name: str, address: str = None, port: int = None, status: bool = None) -> tuple[bool, str]:
        """
        Edits an existing WireGuard interface configuration and updates the database.
        'name' should be in 'wgX' format (e.g., 'wg0').
        """
        wg_id = int(name.replace('wg', ''))
        if not self.db.has('interfaces', {'wg': wg_id}):
            return False, f"Interface {name} does not exist in database."

        config_path = self._get_interface_path(name)
        if not self._interface_exists(name):
            return False, f"Interface {name} configuration file does not exist."

        try:
            with open(config_path, "r") as f:
                lines = f.readlines()

            new_lines = []
            update_data = {}

            for line in lines:
                if address is not None and line.strip().startswith("Address ="):
                    new_lines.append(f"Address = {address}\n")
                    update_data['address_range'] = address
                elif port is not None and line.strip().startswith("ListenPort ="):
                    new_lines.append(f"ListenPort = {port}\n")
                    update_data['port'] = port
                else:
                    new_lines.append(line)

            # Update status in DB if provided
            if status is not None:
                update_data['status'] = status

            # Perform DB update only if there's data to update
            if update_data:
                self.db.update('interfaces', update_data, {'wg': wg_id})

            with open(config_path, "w") as f:
                f.writelines(new_lines)

            print(f"[+] Interface {name} updated.")
            self._reload_wireguard(wg_id)
            return True, f"Interface {name} edited successfully."
        except Exception as e:
            return False, f"Error editing interface {name}: {e}"

    def _get_client_config(self, name: str) -> tuple[bool, str]:
        """
        Generates and returns the WireGuard client configuration for a given client name.
        """
        client = self.db.get('clients', where={'name': name})
        if not client:
            return False, 'Client not found.'

        interface = self.db.get('interfaces', where={'wg': client['wg']})
        if not interface:
            return False, f"Associated WireGuard interface wg{client['wg']} not found."

        dns = self.db.get('settings', where={'key': 'dns'})['value']
        mtu = self.db.get('settings', where={'key': 'mtu'})
        mtu_value = mtu['value'] if mtu else '1420' # Default MTU if not found

        server_ip = self.db.get('settings', where={'key': 'server_ip'})['value']

        client_config = f"""
[Interface]
PrivateKey = {client['private_key']}
Address = {client['address']}/32 # Corrected: Client's specific IP with /32 CIDR
DNS = {dns}
MTU = {mtu_value}

[Peer]
PublicKey = {interface['public_key']} # Server's public key
Endpoint = {server_ip}:{interface['port']}
AllowedIPs = 0.0.0.0/0, ::/0 # Allow all IPv4 and IPv6 traffic
PersistentKeepalive = 25
"""
        return True, client_config

    def _change_settings(self, key: str, value: str) -> tuple[bool, str]:
        """
        Changes a specific setting in the database.
        """
        if not self.db.has('settings', {'key': key}):
            return False, 'Invalid Key'
        # Corrected: Update the 'value' column for the given 'key'
        self.db.update('settings', {'value': value}, {'key': key})
        return True, 'Changed!'

    def _add_api_token(self, name: str, token: str) -> tuple[bool, str]:
        """
        Adds or updates an API token in the settings.
        Tokens are stored as a JSON string dictionary.
        """
        try:
            settings_entry = self.db.get('settings', where={'key': 'api_tokens'})
            # Initialize with empty dict if 'api_tokens' key doesn't exist or value is not valid JSON
            current_tokens = {}
            if settings_entry and settings_entry['value']:
                try:
                    current_tokens = json.loads(settings_entry['value'])
                except json.JSONDecodeError:
                    print(f"Warning: 'api_tokens' setting contains invalid JSON. Resetting.")

            current_tokens[name] = token
            self.db.update('settings', {'value': json.dumps(current_tokens)}, {'key': 'api_tokens'})
            return True, f"API token '{name}' added/updated successfully."
        except Exception as e:
            return False, f"Failed to add/update API token: {e}"

    def _delete_api_token(self, name: str) -> tuple[bool, str]:
        """
        Deletes an API token from the settings.
        """
        try:
            settings_entry = self.db.get('settings', where={'key': 'api_tokens'})
            if not settings_entry or not settings_entry['value']:
                return False, "API tokens setting not found or is empty."

            current_tokens = json.loads(settings_entry['value'])
            if name in current_tokens:
                del current_tokens[name]
                self.db.update('settings', {'value': json.dumps(current_tokens)}, {'key': 'api_tokens'})
                return True, f"API token '{name}' deleted successfully."
            else:
                return False, f"API token '{name}' not found."
        except json.JSONDecodeError:
            return False, "API tokens setting contains invalid JSON. Cannot delete token."
        except Exception as e:
            return False, f"Failed to delete API token: {e}"

    def _get_api_token(self, name: str) -> tuple[bool, str | None]:
        """
        Retrieves a specific API token from the settings.
        """
        try:
            settings_entry = self.db.get('settings', where={'key': 'api_tokens'})
            if not settings_entry or not settings_entry['value']:
                return False, "API tokens setting not found or is empty."

            current_tokens = json.loads(settings_entry['value'])
            if name in current_tokens:
                return True, current_tokens[name]
            else:
                return False, f"API token '{name}' not found."
        except json.JSONDecodeError:
            return False, "API tokens setting contains invalid JSON. Cannot retrieve token."
        except Exception as e:
            return False, f"Failed to retrieve API token: {e}"

    def _sync(self):
        """
        Synchronizes client data, traffic, and performs scheduled tasks.
        This method should be run periodically (e.g., via cron).
        """
        print("[*] Starting synchronization process...")

        # --- Handle Reset Timer for Interface Reloads ---
        reset_time_setting = self.db.get('settings', where={'key': 'reset_time'})
        reset_time = int(reset_time_setting['value']) if reset_time_setting and reset_time_setting['value'].isdigit() else 0

        reset_timer_file = 'reset.timer'
        if reset_time != 0:
            if not os.path.exists(reset_timer_file):
                # If timer file doesn't exist, create it with future reset time
                future_reset_timestamp = int(time.time()) + (reset_time * 60 * 60)
                with open(reset_timer_file, 'w') as o:
                    o.write(str(future_reset_timestamp))
                print(f"[*] Reset timer file created. Next reset scheduled for {datetime.fromtimestamp(future_reset_timestamp)}.")
            else:
                # Check if reset time has passed
                try:
                    with open(reset_timer_file, 'r') as o:
                        scheduled_reset_timestamp = int(float(o.read().strip())) # Use float for robustness
                except (ValueError, FileNotFoundError):
                    print(f"Warning: Could not read or parse {reset_timer_file}. Recreating.")
                    future_reset_timestamp = int(time.time()) + (reset_time * 60 * 60)
                    with open(reset_timer_file, 'w') as o:
                        o.write(str(future_reset_timestamp))
                    scheduled_reset_timestamp = future_reset_timestamp # Set for current cycle

                if int(time.time()) >= scheduled_reset_timestamp:
                    print("[*] Reset time reached. Reloading WireGuard interfaces...")
                    # Update timer for next reset
                    new_future_reset_timestamp = int(time.time()) + (reset_time * 60 * 60)
                    with open(reset_timer_file, 'w') as o:
                        o.write(str(new_future_reset_timestamp))
                    print(f"[*] Reset timer updated. Next reset scheduled for {datetime.fromtimestamp(new_future_reset_timestamp)}.")

                    # Reload all active interfaces
                    for interface in self.db.select('interfaces', where={'status': True}):
                        self._reload_wireguard(interface['wg'])
                else:
                    print(f"[*] Next reset in {scheduled_reset_timestamp - int(time.time())} seconds.")
        else:
            if os.path.exists(reset_timer_file):
                os.remove(reset_timer_file) # Clean up if reset_time is 0

        # --- Auto Backup ---
        auto_backup_setting = self.db.get('settings', where={'key': 'auto_backup'})
        auto_backup_enabled = bool(int(auto_backup_setting['value'])) if auto_backup_setting and auto_backup_setting['value'].isdigit() else False

        if auto_backup_enabled:
            print("[*] Performing auto backup of WireGuard configurations...")
            for interface in self.db.select('interfaces'):
                self._backup_config(interface['wg'])

        # --- Client Expiration and Traffic Limit Enforcement ---
        current_time = datetime.now()
        # Fetch all clients once to avoid repeated DB queries inside the loop
        all_clients = list(self.db.select('clients')) # Make a copy to iterate, as deletions modify the underlying data
        for user in all_clients:
            # Re-check if client still exists in DB, as it might have been deleted by a previous iteration
            # (e.g., if multiple clients expire in one sync and are processed in order)
            if not self.db.has('clients', {'name': user['name']}):
                continue

            should_delete = False
            delete_reason = ""

            # Check expiration
            try:
                expires_dt = datetime.fromisoformat(user['expires'])
                if current_time >= expires_dt:
                    should_delete = True
                    delete_reason = "expired"
            except (ValueError, TypeError):
                print(f"[!] Warning: Invalid expires date format for client '{user['name']}'. Skipping expiration check.")

            # Check traffic limit (only if not already marked for deletion by expiration)
            if not should_delete:
                try:
                    traffic_limit = int(user['traffic']) # Expected total traffic quota in bytes
                    used_traffic_data = json.loads(user['used_trafic'])
                    total_used_traffic = used_traffic_data.get('download', 0) + used_traffic_data.get('upload', 0)

                    if traffic_limit > 0 and total_used_traffic >= traffic_limit: # Only enforce if limit > 0
                        should_delete = True
                        delete_reason = "exceeded traffic limit"
                except (ValueError, TypeError, json.JSONDecodeError) as e:
                    print(f"[!] Warning: Invalid traffic data for client '{user['name']}'. Skipping traffic limit check. Error: {e}")

            if should_delete:
                print(f"[!] Client '{user['name']}' {delete_reason}. Deleting...")
                self._delete_client(user['name']) # This will remove it from DB and config

        # --- Update Traffic Statistics ---
        old_data = self.load_traffic_db() # Data from previous sync
        current_data = self._get_current_traffic() # Current data from 'wg show'

        total_bandwidth_consumed_this_cycle = 0

        for wg_id, peers in current_data.items():
            for pubkey, stats in peers.items():
                old_entry = old_data.get(pubkey, {
                    'allowed_ip': stats['ip'],
                    'total_rx': 0, # Cumulative download
                    'total_tx': 0, # Cumulative upload
                    'last_rx': 0,  # Last observed rx from wg show
                    'last_tx': 0,  # Last observed tx from wg show
                    'created_at': datetime.now().isoformat()
                })

                # --- Traffic Reset Handling (Point 19 Fix) ---
                # Calculate delta based on whether counters reset or are continuous
                # If current counter is less than last, assume reset and take current value as delta
                delta_rx = stats['rx'] - old_entry.get('last_rx', 0)
                if delta_rx < 0: # Counter reset detected
                    delta_rx = stats['rx'] # Add the current reading as the delta for this cycle
                    print(f"[*] Detected RX counter reset for {pubkey} on wg{wg_id}. Adding current RX ({stats['rx']} bytes) as delta.")
                delta_tx = stats['tx'] - old_entry.get('last_tx', 0)
                if delta_tx < 0: # Counter reset detected
                    delta_tx = stats['tx'] # Add the current reading as the delta for this cycle
                    print(f"[*] Detected TX counter reset for {pubkey} on wg{wg_id}. Adding current TX ({stats['tx']} bytes) as delta.")

                # Ensure deltas are non-negative (should be handled by above logic, but as a safeguard)
                delta_rx = max(0, delta_rx)
                delta_tx = max(0, delta_tx)

                # Update cumulative traffic
                old_entry['total_rx'] += delta_rx
                old_entry['total_tx'] += delta_tx

                # Update used_trafic in the clients table
                # Find the client by public key (assuming public_key is unique for clients)
                client_in_db = self.db.get('clients', where={'public_key': pubkey})
                if client_in_db:
                    # Ensure used_trafic in DB is always updated with cumulative values
                    traffic_to_db = {'download': old_entry['total_rx'], 'upload': old_entry['total_tx']}
                    self.db.update('clients', {'used_trafic': json.dumps(traffic_to_db)}, {'public_key': pubkey})
                else:
                    print(f"[!] Warning: Client with public key {pubkey} found in wg show but not in DB. Skipping DB update for this client's traffic.")

                # Update last observed values for the next sync cycle
                old_entry['last_rx'] = stats['rx']
                old_entry['last_tx'] = stats['tx']
                old_entry['updated_at'] = datetime.now().isoformat()
                old_data[pubkey] = old_entry

                # Accumulate total bandwidth for the server
                total_bandwidth_consumed_this_cycle += (delta_rx + delta_tx)

        self.save_traffic_db(old_data) # Save updated traffic data to file

        # Update server's total bandwidth in settings
        old_bandwidth_setting = self.db.get('settings', where={'key': 'bandwidth'})
        current_total_bandwidth = int(old_bandwidth_setting['value']) if old_bandwidth_setting and old_bandwidth_setting['value'].isdigit() else 0
        new_total_bandwidth = current_total_bandwidth + total_bandwidth_consumed_this_cycle
        self.db.update('settings', {'value': str(new_total_bandwidth)}, {'key': 'bandwidth'})


        # --- Update Uptime ---
        uptime_file = 'up.time'
        try:
            if not os.path.exists(uptime_file):
                start_timestamp = int(time.time())
                with open(uptime_file, 'w') as o:
                    o.write(f"{start_timestamp}|{start_timestamp}")
                # Initialize uptime in DB to 0 when file is first created
                self.db.update('settings', {'value': '0'}, {'key': 'uptime'})
            else:
                with open(uptime_file, 'r') as o:
                    content = o.read().split('|')
                    start_timestamp = int(content[0])
                current_timestamp = int(time.time())
                with open(uptime_file, 'w') as o:
                    o.write(f"{start_timestamp}|{current_timestamp}")
                calculated_uptime_seconds = current_timestamp - start_timestamp
                self.db.update('settings', {'value': str(calculated_uptime_seconds)}, {'key': 'uptime'})
        except (ValueError, IndexError, FileNotFoundError) as e:
            print(f"Error updating uptime: {e}. Uptime tracking might be inaccurate.")
            # Ensure uptime is reset/handled if file is corrupted
            self.db.update('settings', {'value': '0'}, {'key': 'uptime'})
            if os.path.exists(uptime_file):
                os.remove(uptime_file) # Remove corrupted file to allow recreation


        print("[*] Synchronization process completed.")

# Custom exception for command execution errors
class CommandExecutionError(Exception):
    pass

