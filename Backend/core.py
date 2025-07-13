# core.py
import subprocess, json, random, uuid, time, ipaddress, os, psutil, shutil, re , string , httpx
from db import SQLite
from nanoid import generate
from datetime import datetime , timedelta
from typing import Dict # New import for type hinting

netifaces = None
# --- Configuration Paths (Consider making these configurable in a real app) ---
SERVER_PUBLIC_KEY_PATH = "/etc/wireguard/server_public_wgX.key"
SERVER_PRIVATE_KEY_PATH = "/etc/wireguard/server_private_wgX.key"
WG_CONF_PATH = "/etc/wireguard/wgX.conf"
WG_DIR = "/etc/wireguard"
DB_FILE = "total_traffic.json" # File to store cumulative traffic data (will be superseded by DB logic)

# Custom exception for command execution errors
class CommandExecutionError(Exception):
    pass

# New: RemoteAgentClient for communicating with remote WireGuard servers
class RemoteAgentClient:
    def __init__(self, ip_address: str, agent_port: int, api_key: str):
        self.base_url = f"http://{ip_address}:{agent_port}/agent_api"
        self.api_key = api_key

    def post(self, endpoint: str, data: dict = None):
        headers = {"X-API-Key": self.api_key, "Content-Type": "application/json"}
        try:
            with httpx.AsyncClient() as client:
                response =  client.post(f"{self.base_url}{endpoint}", json=data, headers=headers, timeout=30)
                response.raise_for_status() # Raise an exception for 4xx/5xx responses
                return response.json()
        except httpx.HTTPStatusError as e:
            # Re-raise with more specific error message for HTTP errors
            raise Exception(f"Agent HTTP error ({e.response.status_code}) from {endpoint}: {e.response.text}")
        except httpx.RequestError as e:
            # Re-raise with more specific error message for network errors
            raise Exception(f"Agent network error to {endpoint}: {e}")
        except Exception as e:
            # Catch any other unexpected errors
            raise Exception(f"Agent unexpected error to {endpoint}: {e}")


class CandyPanel:
    # Modified: db_path parameter added to allow agent to use a different DB file
    def __init__(self, db_path='CandyPanel.db'):
        """
        Initializes the CandyPanel with a SQLite database connection.
        In multi-server mode, this central panel instance will manage 'servers',
        'clients', 'interfaces' (with server_id), and 'settings' locally.
        It communicates with remote agents for actual WireGuard operations.
        """
        self.db = SQLite(db_path=db_path) # Pass db_path to SQLite constructor
        self.agent_clients: Dict[int, RemoteAgentClient] = {} # Store agent clients by server_id
        # For the central panel, load agent clients on init.
        # For an agent, this map will remain empty as it only acts locally.
        if db_path == 'CandyPanel.db': # Only central panel manages remote agents
            self._load_agent_clients()

    def _load_agent_clients(self):
        """
        Loads server details from the database and initializes RemoteAgentClient instances.
        """
        servers = self.db.select('servers')
        self.agent_clients = {} # Clear existing clients
        for server_data in servers:
            server_id = server_data['server_id']
            try:
                self.agent_clients[server_id] = RemoteAgentClient(
                    server_data['ip_address'],
                    server_data['agent_port'],
                    server_data['api_key']
                )
            except Exception as e:
                print(f"Warning: Could not initialize agent client for server {server_id} ({server_data['name']}): {e}")
                # Optionally update server status to 'unreachable' in DB here

    # New: Methods for managing servers in the central database
    def add_server(self, name: str, ip_address: str, agent_port: int, api_key: str, description: str = '') -> tuple[bool, str, int | None]:
        """Adds a new remote server to the central panel's database."""
        if self.db.has('servers', {'name': name}):
            return False, f"Server with name '{name}' already exists.", None
        
        # Test connection to the agent
        test_agent = RemoteAgentClient(ip_address, agent_port, api_key)
        try:
            test_response =  test_agent.post("/dashboard")
            if not test_response.get('success'):
                return False, f"Could not connect to agent or agent returned error: {test_response.get('message', 'Unknown error')}", None
        except Exception as e:
            return False, f"Failed to connect to agent at {ip_address}:{agent_port}: {e}", None

        server_id = self.db.insert('servers', {
            'name': name,
            'ip_address': ip_address,
            'agent_port': agent_port,
            'api_key': api_key,
            'description': description,
            'status': 'active',
            'last_synced': datetime.now().isoformat(),
            'dashboard_cache': json.dumps({}) # Initialize empty cache
        })
        self._load_agent_clients() # Reload all agents after adding a new one
        return True, f"Server '{name}' added successfully with ID {server_id}.", server_id

    def update_server(self, server_id: int, name: str = None, ip_address: str = None, agent_port: int = None, api_key: str = None, description: str = None, status: str = None) -> tuple[bool, str]:
        """Updates an existing remote server's details."""
        current_server = self.db.get('servers', {'server_id': server_id})
        if not current_server:
            return False, f"Server with ID {server_id} not found."

        update_data = {}
        if name is not None: update_data['name'] = name
        if ip_address is not None: update_data['ip_address'] = ip_address
        if agent_port is not None: update_data['agent_port'] = agent_port
        if api_key is not None: update_data['api_key'] = api_key
        if description is not None: update_data['description'] = description
        if status is not None: update_data['status'] = status

        if update_data:
            self.db.update('servers', update_data, {'server_id': server_id})
            self._load_agent_clients() # Reload agent clients to reflect changes
            return True, f"Server '{server_id}' updated successfully."
        return False, "No update data provided."

    def delete_server(self, server_id: int) -> tuple[bool, str]:
        """Deletes a remote server from the central panel and all its associated clients/interfaces."""
        if not self.db.has('servers', {'server_id': server_id}):
            return False, f"Server with ID {server_id} not found."

        # Cascade delete is configured in DB schema for clients and interfaces
        # So, deleting the server record will automatically delete its associated clients and interfaces.
        self.db.delete('servers', {'server_id': server_id})
        self._load_agent_clients() # Reload agent clients
        return True, f"Server {server_id} and all associated data deleted successfully."

    def get_all_servers(self) -> list[dict]:
        """Retrieves all registered servers from the central database."""
        return self.db.select('servers')

    def get_server_by_id(self, server_id: int) -> dict | None:
        """Retrieves a single server by its ID."""
        return self.db.get('servers', {'server_id': server_id})

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

    # This method is primarily for agent's local operation now.
    # The central panel will get traffic via agent.
    def run_command(self, cmd: str, check: bool = True) -> str | None:
        """
        Executes a shell command and returns its stdout.
        Raises an exception if the command fails and 'check' is True.
        This method is now primarily used by the agent on its local machine.
        The central panel will not use this for remote operations.
        """
        try:
            result = subprocess.run(cmd, shell=True, check=check, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Error running command '{cmd}': {result.stderr.strip()}")
                raise Exception(f"Command failed: {result.stderr.strip()}")
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"Error running '{cmd}': {e.stderr.strip()}")
            if check:
                raise CommandExecutionError(f"Command '{cmd}' failed: {e.stderr.strip()}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred while running '{cmd}': {e}")
            if check:
                raise CommandExecutionError(f"Unexpected error: {e}")
            return None
    def _get_default_interface(self):
        """Gets the default network interface."""
        try:
            gateways = netifaces.gateways()
            return gateways['default'][netifaces.AF_INET][1]
        except Exception:
            result = self.run_command("ip route | grep default | awk '{print $5}'", check=False)
            if result:
                return result
            return "eth0"
    @staticmethod
    def load_traffic_db() -> dict:
        """
        Loads the total traffic data from the JSON file.
        (This old method is largely superseded by DB storage, but kept for compatibility if needed locally by agent.)
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
        (This old method is largely superseded by DB storage, but kept for compatibility if needed locally by agent.)
        """
        with open(DB_FILE, 'w') as f:
            json.dump(data, f, indent=4)

    def _get_interface_path(self, name: str) -> str:
        """
        Constructs the full path for a WireGuard interface configuration file.
        Used by the agent locally.
        """
        return os.path.join(WG_DIR, f"{name}.conf")

    def _interface_exists(self, name: str) -> bool:
        """
        Checks if a WireGuard interface configuration file exists.
        Used by the agent locally.
        """
        return os.path.exists(self._get_interface_path(name))

    def _get_all_ips_in_subnet(self, subnet_cidr: str) -> list[str]:
        """
        Returns all host IPs within a given subnet CIDR.
        Used by the agent locally.
        """
        network = ipaddress.ip_network(subnet_cidr, strict=False)
        return [str(ip) for ip in network.hosts()]

    def _get_server_public_key(self, wg_id: int) -> str:
        """
        Retrieves the server's public key for a specific WireGuard interface.
        Used by the agent locally.
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
        Used by the agent locally.
        """
        priv = self.run_command("wg genkey")
        pub = self.run_command(f"echo {priv} | wg pubkey")
        return priv, pub

    def _get_used_ips(self, wg_id: int) -> set[int]:
        """
        Parses the WireGuard configuration file to find used client IPs.
        Assumes IPs are in the format 10.0.0.X/32.
        Used by the agent locally.
        """
        try:
            # When run on agent, it will access its local config file
            with open(WG_CONF_PATH.replace('X', str(wg_id)), "r") as f:
                content = f.read()
            # Regex to find IPs in "AllowedIPs = 10.0.0.X/32" format
            ips = re.findall(r"AllowedIPs\s*=\s*\d+\.\d+\.\d+\.(\d+)/32", content)
            return set(int(ip) for ip in ips)
        except FileNotFoundError:
            print(f"Error: WireGuard config file not found for wg{wg_id}.")
            return set() # Return empty set if config file doesn't exist

    def _backup_config(self, wg_id: int):
        """
        Creates a backup of the WireGuard configuration file.
        Used by the agent locally.
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
        Used by the agent locally.
        """
        print(f"[*] Reloading WireGuard interface wg{wg_id}...")
        self.run_command(f"sudo wg-quick down wg{wg_id} || true", check=False)
        self.run_command(f"sudo wg-quick up wg{wg_id}")
        print(f"[*] WireGuard interface wg{wg_id} reloaded.")

    def _add_peer_to_config(self, wg_id: int, client_name: str, client_public_key: str, client_ip: str):
        """
        Adds a client peer entry to the WireGuard configuration file.
        Used by the agent locally.
        """
        config_path = WG_CONF_PATH.replace('X', str(wg_id))
        peer_entry = f"""
[Peer]
# {client_name}
PublicKey = {client_public_key}
AllowedIPs = {client_ip}/32
"""
        try:
            with open(config_path, "a") as f:
                f.write(peer_entry)
            self.run_command(f"sudo bash -c 'wg syncconf wg{wg_id} <(wg-quick strip wg{wg_id})'")
            print(f"[+] Client '{client_name}' added to wg{wg_id} config.")
        except Exception as e:
            raise CommandExecutionError(f"Failed to add client '{client_name}' to WireGuard configuration: {e}")

    def _remove_peer_from_config(self, wg_id: int, client_name: str):
        """
        Removes a client peer entry from the WireGuard configuration file.
        Used by the agent locally.
        """
        config_path = WG_CONF_PATH.replace('X', str(wg_id))

        if not os.path.exists(config_path):
            print(f"[!] WireGuard config file {config_path} not found. Cannot remove peer from config.")
            return

        self._backup_config(wg_id)

        try:
            with open(config_path, "r") as f:
                lines = f.readlines()

            new_lines = []
            in_peer_block = False
            peer_block_to_delete = False
            temp_block = []

            for line in lines:
                if line.strip().startswith("[Peer]"):
                    if in_peer_block:
                        if not peer_block_to_delete:
                            new_lines.extend(temp_block)
                    temp_block = [line]
                    in_peer_block = True
                    peer_block_to_delete = False
                elif in_peer_block:
                    temp_block.append(line)
                    if f"# {client_name}" in line.strip():
                        peer_block_to_delete = True
                    if not line.strip() and in_peer_block:
                        if not peer_block_to_delete:
                            new_lines.extend(temp_block)
                        in_peer_block = False
                        temp_block = []
                else:
                    new_lines.append(line)

            if in_peer_block and not peer_block_to_delete:
                new_lines.extend(temp_block)

            if peer_block_to_delete:
                with open(config_path, "w") as f:
                    f.writelines(new_lines)
                self.run_command(f"sudo bash -c 'wg syncconf wg{wg_id} <(wg-quick strip wg{wg_id})'")
                print(f"[+] Client '{client_name}' removed from wg{wg_id} config.")
            else:
                print(f"[!] Client '{client_name}' peer block not found in config file. No changes made to config.")

        except Exception as e:
            raise CommandExecutionError(f"Error removing client '{client_name}' from WireGuard configuration: {e}")


    def _get_current_wg_peer_traffic(self, wg_id: int) -> dict:
        """
        Retrieves current traffic statistics (rx, tx) for all WireGuard peers
        on a specific interface from 'wg show dump'.
        Returns a dictionary: {public_key: {'rx': int, 'tx': int}}
        Used by the agent locally.
        """
        traffic_data = {}
        try:
            result = subprocess.run(['sudo', 'wg', 'show', f"wg{wg_id}", 'dump'], capture_output=True, text=True, check=True)
            output_lines = result.stdout.strip().splitlines()

            for line in output_lines:
                parts = line.strip().split('\t')

                if len(parts) == 8:
                    try:
                        pubkey = parts[0]
                        rx = int(parts[5])
                        tx = int(parts[6])
                        traffic_data[pubkey] = {'rx': rx, 'tx': tx}
                    except (ValueError, IndexError) as e:
                        print(f"Warning: Could not parse wg dump peer line: '{line.strip()}'. Error: {e}")
                elif len(parts) == 4:
                    pass
                else:
                    print(f"Warning: Unexpected line format or number of parts in wg dump output: '{line.strip()}'")

        except subprocess.CalledProcessError as e:
            print(f"Warning: Failed to run `sudo wg show wg{wg_id} dump`. Error: {e.stderr.strip()}. Please ensure WireGuard is installed and you have appropriate permissions (e.g., sudo access).")
        except Exception as e:
            print(f"An unexpected error occurred while getting traffic for wg{wg_id}: {e}")
        return traffic_data

    # Modified: _install_candy_panel to self-register central server as agent
    def _install_candy_panel(self, server_ip: str,
                             wg_port: str,
                             wg_address_range: str = "10.0.0.1/24",
                             wg_dns: str = "8.8.8.8",
                             admin_user: str = 'admin',
                             admin_password: str = 'admin') -> tuple[bool, str]:
        """
        Installs WireGuard and initializes the CandyPanel server configuration.
        This runs on the central panel machine during its initial setup.
        It also self-registers this central server as the first managed agent.
        """
        if not self._is_valid_ip(server_ip):
            return False, 'IP INCORRECT'
        install_status = self.db.get('settings',where={'key':'install'})
        if bool(install_status and install_status['value'] == '1') : return False , 'Installed before !'

        # --- Initial WireGuard Setup on Central Panel (as it was before) ---
        print("[+] Updating system and installing WireGuard...")
        try:
            self.run_command("sudo apt update")
            self.run_command("sudo apt upgrade -y")
            self.run_command("sudo apt install -y wireguard qrencode")
        except Exception as e:
            return False, f"Failed to install WireGuard dependencies: {e}"

        print("[+] Installing and configuring UFW...")
        try:
            self.run_command("sudo apt install -y ufw")
            self.run_command("sudo ufw default deny incoming")
            self.run_command("sudo ufw default allow outgoing")
            self.run_command(f"sudo ufw allow {wg_port}/udp")
            self.run_command("sudo ufw allow ssh")
            ap_port = os.environ.get('AP_PORT', '3446') # Central panel's own API port
            agent_port = os.environ.get('AGENT_PORT', '3447') # Central panel's agent port
            self.run_command(f"sudo ufw allow {ap_port}/tcp")
            self.run_command(f"sudo ufw allow {agent_port}/tcp") # Open port for central agent
            self.run_command("sudo ufw --force enable")
            print("[+] UFW configured successfully.")
        except Exception as e:
            return False, f"Failed to configure UFW: {e}"

        print("[+] Enabling IP forwarding...")
        try:
            self.run_command("sudo sysctl -w net.ipv4.ip_forward=1")
            self.run_command("sudo sysctl -w net.ipv6.conf.all.forwarding=1")
            sysctl_conf_path = "/etc/sysctl.conf"
            with open(sysctl_conf_path, 'r+') as f:
                content = f.read()
                if 'net.ipv4.ip_forward = 1' not in content:
                    f.write("\nnet.ipv4.ip_forward = 1\n")
                if 'net.ipv6.conf.all.forwarding = 1' not in content:
                    f.write("net.ipv6.conf.all.forwarding = 1\n")
            self.run_command("sudo sysctl -p")
            print("[+] IP forwarding enabled successfully.")
        except Exception as e:
            return False, f"Failed to enable IP forwarding: {e}"


        print("[+] Creating /etc/wireguard if not exists...")
        os.makedirs("/etc/wireguard", exist_ok=True)
        os.chmod("/etc/wireguard", 0o700)
        
        wg_id = 0 # Default initial interface ID
        default_interface = self._get_default_interface()
        interface_name = f"wg{wg_id}"
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
MTU = 1420
DNS = 8.8.8.8

PostUp = iptables -A FORWARD -i {interface_name} -j ACCEPT; iptables -t nat -A POSTROUTING -o {default_interface} -j MASQUERADE
PostDown = iptables -D FORWARD -i {interface_name} -j ACCEPT; iptables -t nat -D POSTROUTING -o {default_interface} -j MASQUERADE
        """.strip()

        with open(wg_conf_path, "w") as f:
            f.write(wg_conf + "\n")
        os.chmod(wg_conf_path, 0o600)

        # Update initial settings (e.g., server IP, DNS, admin credentials) for central panel
        self.db.update('settings', {'value': server_ip}, {'key': 'server_ip'})
        self.db.update('settings', {'value': server_ip}, {'key': 'custom_endpont'})
        self.db.update('settings', {'value': wg_dns}, {'key': 'dns'})
        admin_data = json.dumps({'user': admin_user, 'password': admin_password})
        self.db.update('settings', {'value': admin_data}, {'key': 'admin'})
        self.db.update('settings', {'value': '1'}, {'key': 'install'})
        
        # Cron job for central panel's sync (already there)
        current_dir = os.path.abspath(os.path.dirname(__file__))
        cron_script_path = os.path.join(current_dir, 'cron.py')
        backend_dir = os.path.dirname(cron_script_path)
        cron_line = f"*/5 * * * * cd {backend_dir} && python3 {cron_script_path} >> /var/log/candy-sync.log 2>&1"
        self.run_command(f'(crontab -l 2>/dev/null; echo "{cron_line}") | crontab -')

        # --- Self-Register Central Panel as the First Managed Server ---
        print("[+] Self-registering central panel as the first managed server...")
        central_agent_ip = "127.0.0.1" # Agent runs locally
        central_agent_port = int(os.environ.get('AGENT_PORT', '3447')) # Assuming agent listens on 3447
        
        # Generate a unique API key for the central server's agent.
        # This key should be stored securely and passed to the agent's environment.
        central_agent_api_key = os.environ.get('AGENT_API_KEY_CENTRAL', str(uuid.uuid4())) # Use env var or generate
        
        # Insert initial interface into central DB, linked to its self-registered server_id
        # This is crucial: the *central* DB now records the interface as belonging to itself.
        # We need the server_id *before* adding the interface.
        
        # First, add the central server as a managed server
        success_add_server, msg_add_server, new_server_id =  self.add_server(
            name="Central Panel Server",
            ip_address=central_agent_ip,
            agent_port=central_agent_port,
            api_key=central_agent_api_key,
            description="This server runs the central CandyPanel.",
        )
        if not success_add_server:
            return False, f"Failed to self-register central server: {msg_add_server}"
        
        # Now, insert the initial wg0 interface and link it to this new server_id
        # Note: This is inserting into the CENTRAL panel's DB.
        # The agent's local DB will have its own interfaces.
        if not self.db.has('interfaces', {'wg': wg_id, 'server_id': new_server_id}):
            self.db.insert('interfaces', {
                'wg': wg_id,
                'server_id': new_server_id, # Link to self-registered server
                'private_key': private_key,
                'public_key': public_key,
                'port': wg_port, # The WireGuard port for this interface
                'address_range': wg_address_range,
                'status': True
            })
        
        print(f"[+] Central panel self-registered as Server ID: {new_server_id}. Initial interface wg{wg_id} linked.")
        
        # Ensure the central panel's WireGuard interface starts
        try:
            self.run_command(f"sudo systemctl enable wg-quick@wg{wg_id}")
            self.run_command(f"sudo systemctl start wg-quick@wg{wg_id}")
        except Exception as e:
            print(f"[!] Warning: Failed to start central WireGuard service wg{wg_id}: {e}")
            # Do not fail installation for this, but warn

        return True, 'Installed successfully! Central server self-registered.'


    def _admin_login(self, user: str, password: str) -> tuple[bool, str]:
        """
        Authenticates an admin user for the local agent's panel (if accessed directly).
        WARNING: Password stored in plaintext in DB. This should be hashed!
        """
        admin_settings = json.loads(self.db.get('settings', where={'key': 'admin'})['value'])
        if admin_settings.get('user') == user and admin_settings.get('password') == password:
            session_token = str(uuid.uuid4())
            self.db.update('settings', {'value': session_token}, {'key': 'session_token'})
            return True, session_token
        else:
            return False, 'Wrong username or password!'

    # Modified: _dashboard_stats no longer takes server_id (it's called by agent locally or centrally calls agent)
    def _dashboard_stats(self) -> dict:
        """
        Retrieves various system and application statistics for the dashboard.
        This method will be called locally by the agent to get its server's stats.
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
            'cpu': f"{psutil.cpu_percent()}%",
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
    
    # New: Helper to get live dashboard stats for a specific server (from agent)
    def _dashboard_stats_for_server(self, server_id: int) -> dict:
        """
        Fetches live dashboard statistics from a specific remote agent.
        """
        agent = self.agent_clients.get(server_id)
        if not agent:
            return {"success": False, "message": f"Server with ID {server_id} not found or agent not configured."}
        try:
            response =  agent.post("/dashboard")
            return response # Returns the full API response (success, message, data)
        except Exception as e:
            return {"success": False, "message": f"Failed to get dashboard stats from agent: {e}"}


    # Modified: _get_all_clients now takes server_id
    def _get_all_clients(self, server_id: int | None = None) -> list[dict]:
        """
        Retrieves all client records from the database.
        If server_id is provided, it's for the central panel fetching clients for a specific server.
        If server_id is None, it's for the agent getting its local clients.
        """
        if server_id is not None: # Central panel requesting clients for a specific server
            return self.db.select('clients', where={'server_id': server_id})
        else: # Agent requesting its local clients (no server_id column in its local DB's clients table)
            return self.db.select('clients')


    # Modified: _new_client now takes server_id for central panel, or operates locally on agent
    def _new_client(self, name: str, expire: str, traffic: str, wg_id: int = 0, note: str = '', server_id: int | None = None) -> tuple[bool, str]:
        """
        Creates a new WireGuard client.
        If server_id is provided (by central panel), it orchestrates creation via remote agent.
        If server_id is None (agent acting locally), it performs local creation.
        Returns: True, client_config_string OR False, error_message
        """
        if server_id is not None: # Central panel's call
            agent = self.agent_clients.get(server_id)
            if not agent:
                return False, f"Server with ID {server_id} not found or agent not configured."

            try:
                # Delegate client creation to the remote agent
                response =  agent.post("/client/create", {
                    "name": name,
                    "expires": expire,
                    "traffic": traffic,
                    "wg_id": wg_id,
                    "note": note
                })
                if response.get('success'):
                    # Agent successfully created client, now store in central DB
                    self.db.insert('clients', {
                        'name': name,
                        'server_id': server_id, # Link to the server
                        'public_key': response['data']['public_key'],
                        'private_key': response['data']['private_key'],
                        'address': response['data']['address'],
                        'created_at': datetime.now().isoformat(),
                        'expires': expire,
                        'traffic': traffic,
                        'used_trafic': json.dumps({'download': 0, 'upload': 0, 'last_wg_rx': 0, 'last_wg_tx': 0}),
                        'wg': wg_id,
                        'note': note,
                        'connected_now': False,
                        'status': True
                    })
                    return True, response['data']['client_config'] # Return client config from agent
                return False, response.get('message', 'Unknown error from agent.')
            except Exception as e:
                return False, f"Failed to create client on remote server: {e}"
        else: # Agent's local call
            if self.db.has('clients', {'name': name}): # Agent's local client name check
                return False, 'Client with this name already exists.'

            interface_wg = self.db.get('interfaces', where={'wg': wg_id})
            if not interface_wg:
                return False, f"WireGuard interface wg{wg_id} not found."

            used_ips = self._get_used_ips(wg_id)
            network_address_prefix = interface_wg['address_range'].rsplit('.', 1)[0]
            next_ip_host_part = 2

            # Get IPs already assigned to clients in the agent's local DB for the current interface
            existing_client_ips = {c['address'] for c in self.db.select('clients', where={'wg': wg_id})}

            while f"{network_address_prefix}.{next_ip_host_part}" in existing_client_ips or next_ip_host_part in used_ips:
                next_ip_host_part += 1
                if next_ip_host_part > 254:
                    return False, "No available IP addresses in the subnet."

            client_ip = f"{network_address_prefix}.{next_ip_host_part}"
            client_private, client_public = self._generate_keypair()

            try:
                self._add_peer_to_config(wg_id, name, client_public, client_ip)
            except CommandExecutionError as e:
                return False, str(e)

            server_ip = self.db.get('settings', where={'key': 'custom_endpont'})['value']
            dns = self.db.get('settings', where={'key': 'dns'})['value']
            mtu = self.db.get('settings', where={'key': 'mtu'})
            mtu_value = mtu['value'] if mtu else '1420'

            client_config = f"""[Interface]
PrivateKey = {client_private}
Address = {client_ip}/32
DNS = {dns}
MTU = {mtu_value}

[Peer]
PublicKey = {interface_wg['public_key']}
Endpoint = {server_ip}:{interface_wg['port']}
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 25
"""
            initial_used_traffic = json.dumps({'download': 0, 'upload': 0, 'last_wg_rx': 0, 'last_wg_tx': 0})

            # Store in agent's local DB (without server_id)
            self.db.insert('clients', {
                'name': name,
                'public_key': client_public,
                'private_key': client_private,
                'address': client_ip,
                'created_at': datetime.now().isoformat(),
                'expires': expire,
                'traffic': traffic,
                'used_trafic': initial_used_traffic,
                'wg': wg_id,
                'note': note,
                'connected_now': False,
                'status': True
            })
            return True, client_config

    # Modified: _disable_client takes server_id or operates locally
    def _disable_client(self, client_name: str, server_id: int | None = None) -> tuple[bool, str]:
        """
        Disables a WireGuard client.
        If server_id is provided (by central panel), it orchestrates via remote agent.
        If server_id is None (agent acting locally), it performs local disabling.
        """
        if server_id is not None: # Central panel's call
            client_record = self.db.get('clients', {'name': client_name, 'server_id': server_id})
            if not client_record:
                return False, f"Client '{client_name}' on server {server_id} not found."

            agent = self.agent_clients.get(server_id)
            if not agent:
                return False, f"Server with ID {server_id} not found or agent not configured."
            try:
                # Delegate to agent
                response =  agent.post("/client/update", {"name": client_name, "status": False})
                if response.get('success'):
                    self.db.update('clients', {'status': False}, {'name': client_name, 'server_id': server_id})
                    return True, response.get('message', f"Client '{client_name}' disabled successfully on server {server_id}.")
                return False, response.get('message', f"Failed to disable client '{client_name}' on agent.")
            except Exception as e:
                return False, f"Failed to disable client on remote server: {e}"
        else: # Agent's local call
            client = self.db.get('clients', {'name': client_name})
            if not client:
                return False, f"Client '{client_name}' not found."

            wg_id = client['wg']
            try:
                self._remove_peer_from_config(wg_id, client_name)
            except CommandExecutionError as e:
                print(f"[!] Error during peer removal from config for disabling: {e}. Proceeding with DB status update.")
                return False, f"Failed to remove peer from config: {e}"

            self.db.update('clients', {'status': False}, {'name': client_name})
            print(f"[+] Client '{client_name}' disabled successfully in DB.")
            return True, f"Client '{client_name}' disabled successfully."

    # Modified: _delete_client takes server_id or operates locally
    def _delete_client(self, client_name: str, server_id: int | None = None) -> tuple[bool, str]:
        """
        Deletes a WireGuard client completely (DB and config).
        If server_id is provided (by central panel), it orchestrates via remote agent.
        If server_id is None (agent acting locally), it performs local deletion.
        """
        if server_id is not None: # Central panel's call
            client_record = self.db.get('clients', {'name': client_name, 'server_id': server_id})
            if not client_record:
                return False, f"Client '{client_name}' on server {server_id} not found."

            agent = self.agent_clients.get(server_id)
            if not agent:
                return False, f"Server with ID {server_id} not found or agent not configured."
            try:
                response =  agent.post("/client/delete", {"name": client_name})
                if response.get('success'):
                    self.db.delete('clients', {'name': client_name, 'server_id': server_id})
                    return True, response.get('message', f"Client '{client_name}' deleted successfully from server {server_id}.")
                return False, response.get('message', f"Failed to delete client '{client_name}' on agent.")
            except Exception as e:
                return False, f"Failed to delete client on remote server: {e}"
        else: # Agent's local call
            client = self.db.get('clients', {'name': client_name})
            if not client:
                return False, f"Client '{client_name}' not found."

            wg_id = client['wg']
            try:
                self._remove_peer_from_config(wg_id, client['name'])
            except CommandExecutionError as e:
                print(f"[!] Error during peer removal from config during deletion: {e}. Proceeding with DB deletion.")

            self.db.delete('clients', {'name': client_name})
            print(f"[+] Client '{client_name}' deleted successfully from DB.")
            return True, f"Client '{client_name}' deleted successfully."


    # Modified: _edit_client takes server_id or operates locally
    def _edit_client(self, name: str, expire: str = None, traffic: str = None, status: bool = None, note: str = None, server_id: int | None = None) -> tuple[bool, str]:
        """
        Edits an existing client's details.
        If server_id is provided (by central panel), it orchestrates via remote agent.
        If server_id is None (agent acting locally), it performs local editing.
        """
        if server_id is not None: # Central panel's call
            current_client = self.db.get('clients', {'name': name, 'server_id': server_id})
            if not current_client:
                return False, f"Client '{name}' on server {server_id} not found."

            agent = self.agent_clients.get(server_id)
            if not agent:
                return False, f"Server with ID {server_id} not found or agent not configured."

            update_data_agent = {"name": name}
            if expire is not None: update_data_agent['expires'] = expire
            if traffic is not None: update_data_agent['traffic'] = traffic
            if status is not None: update_data_agent['status'] = status
            if note is not None: update_data_agent['note'] = note

            try:
                response =  agent.post("/client/update", update_data_agent)
                if response.get('success'):
                    # Update central DB
                    update_data_central = {}
                    if expire is not None: update_data_central['expires'] = expire
                    if traffic is not None: update_data_central['traffic'] = traffic
                    if status is not None: update_data_central['status'] = status
                    if note is not None: update_data_central['note'] = note
                    if update_data_central:
                        self.db.update('clients', update_data_central, {'name': name, 'server_id': server_id})
                    return True, response.get('message', f"Client '{name}' updated successfully on server {server_id}.")
                return False, response.get('message', f"Failed to update client '{name}' on agent.")
            except Exception as e:
                return False, f"Failed to update client on remote server: {e}"
        else: # Agent's local call
            current_client = self.db.get('clients', {'name': name})
            if not current_client:
                return False, f"Client '{name}' not found."

            update_data = {}

            if expire is not None:
                update_data['expires'] = expire
            if traffic is not None:
                update_data['traffic'] = traffic
            if note is not None:
                update_data['note'] = note

            if status is not None and status != current_client['status']:
                update_data['status'] = status
                wg_id = current_client['wg']

                if status: # Changing to Active
                    try:
                        self._add_peer_to_config(wg_id, name, current_client['public_key'], current_client['address'])
                    except CommandExecutionError as e:
                        return False, str(e)
                else: # Changing to Inactive
                    try:
                        self._remove_peer_from_config(wg_id, name)
                    except CommandExecutionError as e:
                        return False, str(e)

            if update_data:
                self.db.update('clients', update_data, {'name': name})
                return True, f"Client '{name}' edited successfully."
            else:
                return False, "No valid update data provided."


    # Modified: _new_interface_wg takes server_id or operates locally
    def _new_interface_wg(self, address_range: str, port: int, server_id: int | None = None) -> tuple[bool, str]:
        """
        Creates a new WireGuard interface configuration.
        If server_id is provided (by central panel), it orchestrates via remote agent.
        If server_id is None (agent acting locally), it performs local creation.
        """
        if server_id is not None: # Central panel's call
            agent = self.agent_clients.get(server_id)
            if not agent:
                return False, f"Server with ID {server_id} not found or agent not configured."

            # Check for existing port or address range conflicts on the target server
            existing_interfaces =  self.db.select('interfaces', where={'server_id': server_id})
            for interface in existing_interfaces:
                if int(interface['port']) == port:
                    return False, f"An interface with port {port} already exists on server {server_id}."
                if interface['address_range'] == address_range:
                    return False, f"An interface with address range {address_range} already exists on server {server_id}."

            try:
                response =  agent.post("/interface/create", {"address_range": address_range, "port": port})
                if response.get('success'):
                    # Agent successfully created interface, now store its details in central DB
                    interface_details = response['data'] # Agent now returns these details explicitly
                    new_wg_id = interface_details["wg_id"]
                    private_key = interface_details["private_key"]
                    public_key = interface_details["public_key"]

                    self.db.insert('interfaces', {
                        'wg': new_wg_id,
                        'server_id': server_id,
                        'private_key': private_key,
                        'public_key': public_key,
                        'port': port,
                        'address_range': address_range,
                        'status': True
                    })
                    return True, response.get('message', f"New Interface wg{new_wg_id} created on server {server_id}!")
                return False, response.get('message', 'Unknown error from agent.')
            except Exception as e:
                return False, f"Failed to create interface on remote server: {e}"
        else: # Agent's local call
            interfaces = self.db.select('interfaces')
            for interface in interfaces:
                if int(interface['port']) == port:
                    return False, f"An interface with port {port} already exists."
                if interface['address_range'] == address_range:
                    return False, f"An interface with address range {address_range} already exists."

            existing_wg_ids = sorted([int(i['wg']) for i in interfaces])
            new_wg_id = 0
            while new_wg_id in existing_wg_ids:
                new_wg_id += 1

            interface_name = f"wg{new_wg_id}"
            path = self._get_interface_path(interface_name)
            print("[+] Installing and configuring UFW...")
            try:
                self.run_command("sudo ufw default deny incoming")
                self.run_command("sudo ufw default allow outgoing")
                self.run_command(f"sudo ufw allow {port}/udp")
                self.run_command("sudo ufw --force enable")
                print("[+] UFW configured successfully.")
            except Exception as e:
                return False, f"Failed to configure UFW: {e}"
            if self._interface_exists(interface_name):
                return False, f"Interface {interface_name} configuration file already exists."
            default_interface = self._get_default_interface()
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
MTU = 1420
DNS = 8.8.8.8

PostUp = iptables -A FORWARD -i {interface_name} -j ACCEPT; iptables -t nat -A POSTROUTING -o {default_interface} -j MASQUERADE
PostDown = iptables -D FORWARD -i {interface_name} -j ACCEPT; iptables -t nat -D POSTROUTING -o {default_interface} -j MASQUERADE
"""
            try:
                with open(path, "w") as f:
                    f.write(config)
                os.chmod(path, 0o600)
                print(f"[+] Interface {interface_name} created.")
                self.run_command(f"sudo systemctl enable wg-quick@{interface_name}")
                self._reload_wireguard(new_wg_id)
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
            # For agent, return the new interface details, for central panel to record
            return True, json.dumps({
                "message": 'New Interface Created!',
                "wg_id": new_wg_id,
                "private_key": private_key,
                "public_key": public_key
            })


    # Modified: _edit_interface takes server_id or operates locally
    def _edit_interface(self, name: str, address: str = None, port: int = None, status: bool = None, server_id: int | None = None) -> tuple[bool, str]:
        """
        Edits an existing WireGuard interface configuration.
        If server_id is provided (by central panel), it orchestrates via remote agent.
        If server_id is None (agent acting locally), it performs local editing.
        """
        if server_id is not None: # Central panel's call
            wg_id = int(name.replace('wg', ''))
            current_interface = self.db.get('interfaces', {'wg': wg_id, 'server_id': server_id})
            if not current_interface:
                return False, f"Interface {name} on server {server_id} does not exist in database."

            agent = self.agent_clients.get(server_id)
            if not agent:
                return False, f"Server with ID {server_id} not found or agent not configured."

            update_data_agent = {"name": name}
            if address is not None: update_data_agent['address'] = address
            if port is not None: update_data_agent['port'] = port
            if status is not None: update_data_agent['status'] = status

            try:
                response =  agent.post("/interface/update", update_data_agent)
                if response.get('success'):
                    # Update central DB
                    update_data_central = {}
                    if address is not None: update_data_central['address_range'] = address
                    if port is not None: update_data_central['port'] = port
                    if status is not None: update_data_central['status'] = status
                    if update_data_central:
                        self.db.update('interfaces', update_data_central, {'wg': wg_id, 'server_id': server_id})
                    return True, response.get('message', f"Interface {name} updated successfully on server {server_id}.")
                return False, response.get('message', f"Failed to update interface {name} on agent.")
            except Exception as e:
                return False, f"Failed to update interface on remote server: {e}"
        else: # Agent's local call
            wg_id = int(name.replace('wg', ''))
            current_interface = self.db.get('interfaces', {'wg': wg_id})
            if not current_interface:
                return False, f"Interface {name} does not exist in database."

            config_path = self._get_interface_path(name)
            if not self._interface_exists(name):
                return False, f"Interface {name} configuration file does not exist."

            update_data = {}
            reload_needed = False
            service_action_needed = False

            try:
                with open(config_path, "r") as f:
                    lines = f.readlines()

                new_lines = []
                for line in lines:
                    if address is not None and line.strip().startswith("Address ="):
                        if line.strip() != f"Address = {address}":
                            new_lines.append(f"Address = {address}\n")
                            update_data['address_range'] = address
                            reload_needed = True
                        else:
                            new_lines.append(line)
                    elif port is not None and line.strip().startswith("ListenPort ="):
                        if line.strip() != f"ListenPort = {port}":
                            new_lines.append(f"ListenPort = {port}\n")
                            update_data['port'] = port
                            reload_needed = True
                        else:
                            new_lines.append(line)
                    else:
                        new_lines.append(line)

                if reload_needed:
                    with open(config_path, "w") as f:
                        f.writelines(new_lines)

                if status is not None and status != current_interface['status']:
                    update_data['status'] = status
                    service_action_needed = True
                    if status:
                        self.run_command(f"sudo systemctl start wg-quick@{name}")
                        print(f"[+] Interface {name} started.")
                    else:
                        self.run_command(f"sudo systemctl stop wg-quick@{name}")
                        print(f"[+] Interface {name} stopped.")

                if update_data:
                    self.db.update('interfaces', update_data, {'wg': wg_id})

                if reload_needed and not service_action_needed:
                    self._reload_wireguard(wg_id)

                return True, f"Interface {name} edited successfully."
            except Exception as e:
                return False, f"Error editing interface {name}: {e}"

    # Modified: _delete_interface takes server_id or operates locally
    def _delete_interface(self, wg_id: int, server_id: int | None = None) -> tuple[bool, str]:
        """
        Deletes a WireGuard interface.
        If server_id is provided (by central panel), it orchestrates via remote agent.
        If server_id is None (agent acting locally), it performs local deletion.
        """
        if server_id is not None: # Central panel's call
            current_interface = self.db.get('interfaces', {'wg': wg_id, 'server_id': server_id})
            if not current_interface:
                return False, f"Interface wg{wg_id} on server {server_id} not found."

            agent = self.agent_clients.get(server_id)
            if not agent:
                return False, f"Server with ID {server_id} not found or agent not configured."

            try:
                response =  agent.post("/interface/delete", {"wg_id": wg_id})
                if response.get('success'):
                    self.db.delete('interfaces', {'wg': wg_id, 'server_id': server_id})
                    # Also delete associated clients from central DB
                    self.db.delete('clients', {'wg': wg_id, 'server_id': server_id})
                    return True, response.get('message', f"Interface wg{wg_id} and associated clients deleted successfully from server {server_id}.")
                return False, response.get('message', f"Failed to delete interface wg{wg_id} on agent.")
            except Exception as e:
                return False, f"Failed to delete interface on remote server: {e}"
        else: # Agent's local call
            interface_name = f"wg{wg_id}"
            interface = self.db.get('interfaces', {'wg': wg_id})
            if not interface:
                return False, f"Interface {interface_name} not found."

            try:
                self.run_command(f"sudo systemctl stop wg-quick@{interface_name}", check=False)
                self.run_command(f"sudo systemctl disable wg-quick@{interface_name}", check=False)
                print(f"[+] WireGuard service wg-quick@{interface_name} stopped and disabled.")

                config_path = WG_CONF_PATH.replace('X', str(wg_id))
                private_key_path = SERVER_PRIVATE_KEY_PATH.replace('X', str(wg_id))
                public_key_path = SERVER_PUBLIC_KEY_PATH.replace('X', str(wg_id))

                if os.path.exists(config_path):
                    os.remove(config_path)
                    print(f"[+] Removed config file: {config_path}")
                if os.path.exists(private_key_path):
                    os.remove(private_key_path)
                    print(f"[+] Removed private key: {private_key_path}")
                if os.path.exists(public_key_path):
                    os.remove(public_key_path)
                    print(f"[+] Removed public key: {public_key_path}")

                clients_to_delete = self.db.select('clients', where={'wg': wg_id})
                for client in clients_to_delete:
                    self.db.delete('clients', {'name': client['name']})
                    print(f"[+] Deleted associated client: {client['name']}")

                self.db.delete('interfaces', {'wg': wg_id})
                print(f"[+] Interface {interface_name} deleted from database.")

                return True, f"Interface {interface_name} and all associated clients deleted successfully."
            except Exception as e:
                return False, f"Error deleting interface {interface_name}: {e}"


    # Modified: _get_client_config takes server_id or operates locally
    def _get_client_config(self, name: str, server_id: int | None = None) -> tuple[bool, str]:
        """
        Generates and returns the WireGuard client configuration.
        If server_id is provided (by central panel), it retrieves config via remote agent.
        If server_id is None (agent acting locally), it generates local config.
        """
        if server_id is not None: # Central panel's call
            client_record = self.db.get('clients', {'name': name, 'server_id': server_id})
            if not client_record:
                return False, f"Client '{name}' on server {server_id} not found in central DB."

            agent = self.agent_clients.get(server_id)
            if not agent:
                return False, f"Server with ID {server_id} not found or agent not configured."
            try:
                response =  agent.post("/client/get_config", {"name": name})
                if response.get('success'):
                    return True, response['data']['config']
                return False, response.get('message', f"Failed to get config for client '{name}' from agent.")
            except Exception as e:
                return False, f"Failed to get client config from remote server: {e}"
        else: # Agent's local call
            client = self.db.get('clients', where={'name': name})
            if not client:
                return False, 'Client not found.'

            interface = self.db.get('interfaces', where={'wg': client['wg']})
            if not interface:
                return False, f"Associated WireGuard interface wg{client['wg']} not found."

            dns = self.db.get('settings', where={'key': 'dns'})['value']
            mtu = self.db.get('settings', where={'key': 'mtu'})
            mtu_value = mtu['value'] if mtu else '1420'

            server_ip = self.db.get('settings', where={'key': 'custom_endpont'})['value']

            client_config = f"""
[Interface]
PrivateKey = {client['private_key']}
Address = {client['address']}/32
DNS = {dns}
MTU = {mtu_value}

[Peer]
PublicKey = {interface['public_key']}
Endpoint = {server_ip}:{interface['port']}
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 25
"""
            return True, client_config

    def _change_settings(self, key: str, value: str) -> tuple[bool, str]:
        """
        Changes a specific setting in the database.
        This method operates on the local database (either central panel's or agent's).
        """
        if not self.db.has('settings', {'key': key}):
            return False, 'Invalid Key'
        self.db.update('settings', {'value': value}, {'key': key})
        return True, 'Changed!'

    def _add_api_token(self, name: str, token: str) -> tuple[bool, str]:
        """
        Adds or updates an API token in the settings.
        This operates on the local database.
        """
        try:
            settings_entry = self.db.get('settings', where={'key': 'api_tokens'})
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
        This operates on the local database.
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
        This operates on the local database.
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
    def _generate_unique_short_code(self, length=7): #
        """
        Generates a unique short alphanumeric code for a URL.
        """
        characters = string.ascii_letters + string.digits
        while True:
            short_code = generate(characters, length) #
            if not self.db.has('shortlinks', {'short_code': short_code}): #
                return short_code
    def _get_client_by_name_and_public_key(self, name: str, public_key: str, server_id: int | None = None) -> dict | None:
        """
        Retrieves a client record by its name AND public key.
        This is used for public-facing client detail pages.
        If server_id is provided, it attempts to fetch from a specific server's agent.
        If server_id is None, it iterates through all servers to find the client.
        Otherwise (for local agent's direct call), it fetches from its local database.
        """
        if server_id is not None: # Central panel trying to get details for specific server's client
            # Fetch from central DB for high-level info, then query agent for live data
            client = self.db.get('clients', where={'name': name, 'public_key': public_key, 'server_id': server_id})
            if not client:
                return None

            agent = self.agent_clients.get(server_id)
            if not agent:
                print(f"Warning: Agent for server {server_id} not found, cannot get live details.")
                return None

            try:
                # Get live data from agent
                response = agent.post("/client/get_details", {"name": name, "public_key": public_key})
                if response.get('success') and response.get('data'):
                    agent_data = response['data']
                    client.update(agent_data)
                    client.pop('private_key', None)
                    return client
                else:
                    print(f"Warning: Failed to get live client details from agent for {name}: {response.get('message')}")
                    return None
            except Exception as e:
                print(f"Error communicating with agent for client details: {e}")
                return None
        elif self.db.db_path == 'CandyPanel.db': # Central panel trying to find client across *all* servers (for public shortlink)
            all_servers = self.db.select('servers')
            for server_data in all_servers:
                current_server_id = server_data['server_id']
                agent = self.agent_clients.get(current_server_id)
                if not agent:
                    continue # Skip if agent not initialized for this server

                try:
                    # Query agent for client details by name & public key
                    response = agent.post("/client/get_details", {"name": name, "public_key": public_key})
                    if response.get('success') and response.get('data'):
                        client_data = response['data']
                        # Ensure server-specific endpoint/DNS/MTU are correct for config generation
                        client_data['server_endpoint_ip'] = server_data['ip_address']
                        client_data['interface_port'] = self.db.get('interfaces', {'wg': client_data.get('wg',0), 'server_id': current_server_id})['port'] # Fetch correct port for this server
                        client_data['server_dns'] = self.db.get('settings', {'key': 'dns'})['value'] # Central DNS
                        client_data['server_mtu'] = self.db.get('settings', {'key': 'mtu'})['value'] # Central MTU
                        client_data['server_id'] = current_server_id # Add server_id for context
                        return client_data
                except Exception as e:
                    print(f"Warning: Error searching for client {name} on server {current_server_id}: {e}")
            return None # Client not found on any server
        else: # Agent's local call or direct local access to panel (db_path != 'CandyPanel.db')
            client = self.db.get('clients', where={'name': name, 'public_key': public_key})
            if not client:
                return None

            # Parse used_trafic JSON string into a dict
            try:
                client['used_trafic'] = json.loads(client['used_trafic'])
            except (json.JSONDecodeError, TypeError):
                client['used_trafic'] = {"download": 0, "upload": 0}

            # Remove sensitive data like private_key for public view
            client.pop('private_key', None)
            client.pop('wg', None) # Pop wg as it's an internal ID

            # Fetch relevant interface details from agent's local DB
            interface = self.db.get('interfaces', where={'wg': client.get('wg', 0)}) # Use .get with default in case 'wg' was popped
            if interface:
                client['interface_public_key'] = interface['public_key']
                client['interface_port'] = interface['port']
            else:
                client['interface_public_key'] = None
                client['interface_port'] = None

            # Add server endpoint details from agent's local settings
            client['server_endpoint_ip'] = self.db.get('settings', where={'key': 'custom_endpont'})['value']
            client['server_dns'] = self.db.get('settings', where={'key': 'dns'})['value']
            client['server_mtu'] = self.db.get('settings', where={'key': 'mtu'})['value']
            return client
    def _is_telegram_bot_running(self, pid: int) -> bool:
        """
        Checks if the Telegram bot process with the given PID is running.
        (Relevant only for the central panel if bot runs there, or locally on agent if bot runs on agent)
        """
        if pid <= 0:
            return False
        try:
            process = psutil.Process(pid)
            return process.is_running() and "bot.py" in " ".join(process.cmdline())
        except psutil.NoSuchProcess:
            return False
        except Exception as e:
            print(f"Error checking Telegram bot status for PID {pid}: {e}")
            return False
    def _manage_telegram_bot_process(self, action: str) -> bool:
        """
        Starts or stops the bot.py script as a detached subprocess.
        Stores/clears its PID in the settings.
        This method is called directly by API for immediate effect.
        (Relevant only for the central panel if bot runs there, or locally on agent if bot runs on agent)
        """
        pid_setting = self.db.get('settings', where={'key': 'telegram_bot_pid'})
        current_pid = int(pid_setting['value']) if pid_setting and pid_setting['value'].isdigit() else 0

        is_running = self._is_telegram_bot_running(current_pid)

        # Get the path to the virtual environment's python interpreter
        current_script_dir = os.path.abspath(os.path.dirname(__file__))
        venv_python_path = os.path.join(current_script_dir, 'venv', 'bin', 'python3')

        if action == 'start':
            if is_running:
                print(f"[*] Telegram bot (PID: {current_pid}) is already running.")
                return True
            print("[*] Attempting to start Telegram bot...")
            try:
                bot_token_setting = self.db.get('settings', where={'key': 'telegram_bot_token'})
                api_id_setting = self.db.get('settings', where={'key': 'telegram_api_id'})
                api_hash_setting = self.db.get('settings', where={'key': 'telegram_api_hash'})
                ap_port_setting = self.db.get('settings', where={'key': 'ap_port'})

                if not bot_token_setting or bot_token_setting['value'] == 'YOUR_TELEGRAM_BOT_TOKEN':
                    print("[!] Telegram bot token not configured. Cannot start bot.")
                    return False
                if not api_id_setting or not api_id_setting['value'].isdigit():
                    print("[!] Telegram API ID not configured or invalid. Cannot start bot.")
                    return False
                if not api_hash_setting or not api_hash_setting['value']:
                    print("[!] Telegram API Hash not configured. Cannot start bot.")
                    return False

                bot_script_path = os.path.join(current_script_dir, 'bot.py')

                if not os.path.exists(venv_python_path):
                    print(f"[!] Error: Virtual environment Python interpreter not found at {venv_python_path}. Please ensure the virtual environment is correctly set up.")
                    return False

                env = os.environ.copy()
                env["TELEGRAM_API_ID"] = api_id_setting['value']
                env["TELEGRAM_API_HASH"] = api_hash_setting['value']
                if ap_port_setting and ap_port_setting['value'].isdigit():
                    env["AP_PORT"] = ap_port_setting['value']
                else:
                    # For agent's local bot, AP_PORT refers to agent's own port
                    env["AP_PORT"] = os.environ.get('AGENT_PORT', '3447')

                log_file_path = "/var/log/candy-telegram-bot.log"
                with open(log_file_path, "a") as log_file:
                    process = subprocess.Popen(
                        [venv_python_path, bot_script_path],
                        stdout=log_file,
                        stderr=log_file,
                        preexec_fn=os.setsid,
                        env=env
                    )
                self.db.update('settings', {'value': str(process.pid)}, {'key': 'telegram_bot_pid'})
                self.db.update('settings', {'value': '1'}, {'key': 'telegram_bot_status'})
                print(f"[+] Telegram bot started with PID: {process.pid}")
                return True
            except FileNotFoundError:
                print(f"[!] Error: bot.py not found at {bot_script_path} or venv python not found. Cannot start bot.")
                self.db.update('settings', {'value': '0'}, {'key': 'telegram_bot_pid'})
                self.db.update('settings', {'value': '0'}, {'key': 'telegram_bot_status'})
                return False
            except Exception as e:
                print(f"[!] Failed to start Telegram bot: {e}")
                self.db.update('settings', {'value': '0'}, {'key': 'telegram_bot_pid'})
                self.db.update('settings', {'value': '0'}, {'key': 'telegram_bot_status'})
                return False

        elif action == 'stop':
            if not is_running:
                print("[*] Telegram bot is already stopped (or PID is stale).")
                self.db.update('settings', {'value': '0'}, {'key': 'telegram_bot_pid'})
                self.db.update('settings', {'value': '0'}, {'key': 'telegram_bot_status'})
                return True

            print("[*] Attempting to stop Telegram bot...")
            try:
                process = psutil.Process(current_pid)
                cmdline = " ".join(process.cmdline()).lower()
                if "bot.py" in cmdline and "python" in cmdline:
                    process.terminate()
                    process.wait(timeout=5)
                    print(f"[+] Telegram bot (PID: {current_pid}) stopped.")
                else:
                    print(f"[!] PID {current_pid} is not identified as the Telegram bot. Not terminating.")

                self.db.update('settings', {'value': '0'}, {'key': 'telegram_bot_pid'})
                self.db.update('settings', {'value': '0'}, {'key': 'telegram_bot_status'})
                return True
            except psutil.NoSuchProcess:
                print(f"[!] Telegram bot process with PID {current_pid} not found. Assuming it's already stopped.")
                self.db.update('settings', {'value': '0'}, {'key': 'telegram_bot_pid'})
                self.db.update('settings', {'value': '0'}, {'key': 'telegram_bot_status'})
                return True
            except psutil.TimeoutExpired:
                print(f"[!] Telegram bot process with PID {current_pid} did not terminate gracefully. Killing...")
                process.kill()
                process.wait()
                self.db.update('settings', {'value': '0'}, {'key': 'telegram_bot_pid'})
                self.db.update('settings', {'value': '0'}, {'key': 'telegram_bot_status'})
                return True
            except Exception as e:
                print(f"[!] Error stopping Telegram bot (PID: {current_pid}): {e}")
                return False
        return False # Invalid action

    # Modified: _calculate_and_update_traffic now takes server_id or operates locally
    def _calculate_and_update_traffic(self, server_id: int | None = None):
        """
        Calculates and updates cumulative traffic for all clients.
        If server_id is provided (by central panel), it queries agent for live traffic and updates central DB.
        If server_id is None (agent acting locally), it calculates and updates its local DB.
        """
        if server_id is not None: # Central panel's call to sync traffic for a specific server
            agent = self.agent_clients.get(server_id)
            if not agent:
                print(f"Warning: Agent for server {server_id} not found, cannot update traffic.")
                return

            try:
                # Get current traffic for all peers from the agent
                response =  agent.post("/traffic/dump")
                if not response.get('success') or not response.get('data'):
                    print(f"Error fetching traffic dump from agent {server_id}: {response.get('message', 'No data')}")
                    return

                agent_peer_traffic = response['data']['traffic_data'] # Assuming agent returns {public_key: {'rx': int, 'tx': int}}

                # Retrieve all clients associated with this server from central DB
                all_clients_on_server = self.db.select('clients', where={'server_id': server_id})

                total_bandwidth_consumed_this_cycle = 0

                for client in all_clients_on_server:
                    client_public_key = client['public_key']
                    client_name = client['name']

                    current_rx = agent_peer_traffic.get(client_public_key, {}).get('rx', 0)
                    current_tx = agent_peer_traffic.get(client_public_key, {}).get('tx', 0)

                    try:
                        used_traffic_data = json.loads(client.get('used_trafic', '{"download":0,"upload":0,"last_wg_rx":0,"last_wg_tx":0}'))

                        cumulative_download = used_traffic_data.get('download', 0)
                        cumulative_upload = used_traffic_data.get('upload', 0)
                        last_wg_rx = used_traffic_data.get('last_wg_rx', 0)
                        last_wg_tx = used_traffic_data.get('last_wg_tx', 0)

                        delta_rx = current_rx - last_wg_rx
                        if delta_rx < 0:
                            print(f"[*] Detected RX counter reset for client '{client_name}' on server {server_id}. Adding current RX ({current_rx} bytes) as delta.")
                            delta_rx = current_rx

                        delta_tx = current_tx - last_wg_tx
                        if delta_tx < 0:
                            print(f"[*] Detected TX counter reset for client '{client_name}' on server {server_id}. Adding current TX ({current_tx} bytes) as delta.")
                            delta_tx = current_tx

                        delta_rx = max(0, delta_rx)
                        delta_tx = max(0, delta_tx)

                        cumulative_download += delta_rx
                        cumulative_upload += delta_tx

                        updated_used_traffic = {
                            'download': cumulative_download,
                            'upload': cumulative_upload,
                            'last_wg_rx': current_rx,
                            'last_wg_tx': current_tx
                        }

                        self.db.update('clients', {'used_trafic': json.dumps(updated_used_traffic)}, {'name': client_name, 'server_id': server_id})

                        total_bandwidth_consumed_this_cycle += (delta_rx + delta_tx)

                    except (json.JSONDecodeError, ValueError, TypeError) as e:
                        print(f"[!] Error processing traffic for client '{client_name}' on server {server_id}: {e}. Skipping this client's traffic update.")

                # Update overall server bandwidth in central settings (aggregated or per-server total)
                # For now, let's update a global bandwidth stat or create a new per-server bandwidth stat if desired.
                # Assuming 'bandwidth' setting refers to overall panel usage.
                old_bandwidth_setting = self.db.get('settings', where={'key': 'bandwidth'})
                current_total_bandwidth = int(old_bandwidth_setting['value']) if old_bandwidth_setting and old_bandwidth_setting['value'].isdigit() else 0
                new_total_bandwidth = current_total_bandwidth + total_bandwidth_consumed_this_cycle
                self.db.update('settings', {'value': str(new_total_bandwidth)}, {'key': 'bandwidth'})
                self.db.update('servers', {'last_synced': datetime.now().isoformat(), 'status': 'active'}, {'server_id': server_id})

                print(f"[*] Traffic statistics updated for server {server_id}.")

            except Exception as e:
                print(f"[!] Error syncing traffic for server {server_id}: {e}")
                self.db.update('servers', {'status': 'unreachable'}, {'server_id': server_id}) # Mark server as unreachable
        else: # Agent's local call to sync its own traffic
            print("[*] Calculating and updating client traffic statistics locally...")

            current_wg_traffic = {}
            for interface_row in self.db.select('interfaces'): # Agent queries its local interfaces
                wg_id = interface_row['wg']
                current_wg_traffic.update(self._get_current_wg_peer_traffic(wg_id))

            total_bandwidth_consumed_this_cycle = 0

            all_clients_in_db = self.db.select('clients') # Agent queries its local clients
            for client in all_clients_in_db:
                client_public_key = client['public_key']
                client_name = client['name']

                current_rx = current_wg_traffic.get(client_public_key, {}).get('rx', 0)
                current_tx = current_wg_traffic.get(client_public_key, {}).get('tx', 0)

                try:
                    used_traffic_data = json.loads(client.get('used_trafic', '{"download":0,"upload":0,"last_wg_rx":0,"last_wg_tx":0}'))

                    cumulative_download = used_traffic_data.get('download', 0)
                    cumulative_upload = used_traffic_data.get('upload', 0)
                    last_wg_rx = used_traffic_data.get('last_wg_rx', 0)
                    last_wg_tx = used_traffic_data.get('last_wg_tx', 0)

                    delta_rx = current_rx - last_wg_rx
                    if delta_rx < 0:
                        print(f"[*] Detected RX counter reset for client '{client_name}'. Adding current RX ({current_rx} bytes) as delta.")
                        delta_rx = current_rx

                    delta_tx = current_tx - last_wg_tx
                    if delta_tx < 0:
                        print(f"[*] Detected TX counter reset for client '{client_name}'. Adding current TX ({current_tx} bytes) as delta.")
                        delta_tx = current_tx

                    delta_rx = max(0, delta_rx)
                    delta_tx = max(0, delta_tx)

                    cumulative_download += delta_rx
                    cumulative_upload += delta_tx

                    updated_used_traffic = {
                        'download': cumulative_download,
                        'upload': cumulative_upload,
                        'last_wg_rx': current_rx,
                        'last_wg_tx': current_tx
                    }

                    self.db.update('clients', {'used_trafic': json.dumps(updated_used_traffic)}, {'name': client_name})

                    total_bandwidth_consumed_this_cycle += (delta_rx + delta_tx)

                except (json.JSONDecodeError, ValueError, TypeError) as e:
                    print(f"[!] Error processing traffic for client '{client_name}': {e}. Skipping this client's traffic update.")

            # Update overall server bandwidth in agent's local settings
            old_bandwidth_setting = self.db.get('settings', where={'key': 'bandwidth'})
            current_total_bandwidth = int(old_bandwidth_setting['value']) if old_bandwidth_setting and old_bandwidth_setting['value'].isdigit() else 0
            new_total_bandwidth = current_total_bandwidth + total_bandwidth_consumed_this_cycle
            self.db.update('settings', {'value': str(new_total_bandwidth)}, {'key': 'bandwidth'})
            print("[*] Local client traffic statistics updated.")


    # Modified: _sync now takes server_id (for central panel to sync remote server) or operates locally (for agent's cron)
    def _sync(self, server_id: int | None = None):
        """
        Synchronizes client data, traffic, and performs scheduled tasks.
        If server_id is provided, central panel initiates sync on a remote agent.
        If server_id is None, agent performs its local sync process.
        """
        if server_id is not None: # Central panel's call to trigger sync on a remote agent
            agent = self.agent_clients.get(server_id)
            if not agent:
                print(f"Warning: Agent for server {server_id} not found, cannot initiate sync.")
                return

            print(f"[*] Initiating sync on remote server {server_id}...")
            try:
                response =  agent.post("/sync")
                if response.get('success'):
                    print(f"[*] Remote sync initiated successfully on server {server_id}.")
                    # After remote sync, pull traffic data and update central DB
                    self._calculate_and_update_traffic(server_id)
                    # Pull dashboard stats and update central DB cache
                    dashboard_stats_from_agent_response =  agent.post("/dashboard")
                    if dashboard_stats_from_agent_response.get('success') and dashboard_stats_from_agent_response.get('data'):
                        self.db.update('servers',
                                       {'status': 'active',
                                        'last_synced': datetime.now().isoformat(),
                                        'dashboard_cache': json.dumps(dashboard_stats_from_agent_response['data'])}, # Update cache
                                       {'server_id': server_id})
                        print(f"[*] Dashboard stats fetched and cached for server {server_id}.")
                    else:
                        print(f"Warning: Could not fetch dashboard stats from server {server_id} after sync: {dashboard_stats_from_agent_response.get('message', 'No data')}")
                        self.db.update('servers', {'status': 'active', 'last_synced': datetime.now().isoformat()}, {'server_id': server_id}) # Still mark active if sync was OK

                else:
                    print(f"[!] Failed to initiate remote sync on server {server_id}: {response.get('message', 'Unknown error from agent.')}")
                    self.db.update('servers', {'status': 'error'}, {'server_id': server_id})
            except Exception as e:
                print(f"[!] Error communicating with agent for sync on server {server_id}: {e}")
                self.db.update('servers', {'status': 'unreachable'}, {'server_id': server_id})

        else: # Agent's local call for its periodic sync
            print("[*] Starting local synchronization process...")

            reset_time_setting = self.db.get('settings', where={'key': 'reset_time'})
            reset_time = int(reset_time_setting['value']) if reset_time_setting and reset_time_setting['value'].isdigit() else 0

            reset_timer_file = 'reset.timer'
            if reset_time != 0:
                if not os.path.exists(reset_timer_file):
                    future_reset_timestamp = int(time.time()) + (reset_time * 60 * 60)
                    with open(reset_timer_file, 'w') as o:
                        o.write(str(future_reset_timestamp))
                    print(f"[*] Reset timer file created. Next reset scheduled for {datetime.fromtimestamp(future_reset_timestamp)}.")
                else:
                    try:
                        with open(reset_timer_file, 'r') as o:
                            scheduled_reset_timestamp = int(float(o.read().strip()))
                    except (ValueError, FileNotFoundError):
                        print(f"Warning: Could not read or parse {reset_timer_file}. Recreating.")
                        future_reset_timestamp = int(time.time()) + (reset_time * 60 * 60)
                        with open(reset_timer_file, 'w') as o:
                            o.write(str(future_reset_timestamp))
                        scheduled_reset_timestamp = future_reset_timestamp

                    if int(time.time()) >= scheduled_reset_timestamp:
                        print("[*] Reset time reached. Reloading WireGuard interfaces...")
                        new_future_reset_timestamp = int(time.time()) + (reset_time * 60 * 60)
                        with open(reset_timer_file, 'w') as o:
                            o.write(str(new_future_reset_timestamp))
                        print(f"[*] Reset timer updated. Next reset scheduled for {datetime.fromtimestamp(new_future_reset_timestamp)}.")

                        for interface in self.db.select('interfaces', where={'status': True}):
                            self._reload_wireguard(interface['wg'])
                    else:
                        print(f"[*] Next reset in {scheduled_reset_timestamp - int(time.time())} seconds.")
            else:
                if os.path.exists(reset_timer_file):
                    os.remove(reset_timer_file)


            auto_backup_setting = self.db.get('settings', where={'key': 'auto_backup'})
            auto_backup_enabled = bool(int(auto_backup_setting['value'])) if auto_backup_setting and auto_backup_setting['value'].isdigit() else False

            if auto_backup_enabled:
                print("[*] Performing auto backup of WireGuard configurations...")
                for interface in self.db.select('interfaces'):
                    self._backup_config(interface['wg'])

            current_time = datetime.now()
            clients_to_disable = []
            active_clients = self.db.select('clients', where={'status': True})
            for client in active_clients:
                should_disable = False
                disable_reason = ""

                try:
                    expires_dt = datetime.fromisoformat(client['expires'])
                    if current_time >= expires_dt:
                        should_disable = True
                        disable_reason = "expired"
                except (ValueError, TypeError):
                    print(f"[!] Warning: Invalid expires date format for client '{client['name']}'. Skipping expiration check.")

                if not should_disable:
                    try:
                        traffic_limit = int(client['traffic'])
                        used_traffic_data = json.loads(client['used_trafic'])
                        total_used_traffic = used_traffic_data.get('download', 0) + used_traffic_data.get('upload', 0)

                        if traffic_limit > 0 and total_used_traffic >= traffic_limit:
                            should_disable = True
                            disable_reason = "exceeded traffic limit"
                    except (ValueError, TypeError, json.JSONDecodeError) as e:
                        print(f"[!] Warning: Invalid traffic data for client '{client['name']}'. Skipping traffic limit check. Error: {e}")

                if should_disable:
                    clients_to_disable.append(client['name'])

            for client_name_to_disable in clients_to_disable:
                print(f"[!] Client '{client_name_to_disable}' needs disabling. Disabling...")
                self._disable_client(client_name_to_disable) # Agent's local _disable_client call

            self._calculate_and_update_traffic() # Agent's local traffic calculation

            boot_time_timestamp = psutil.boot_time()
            current_timestamp = time.time()
            calculated_uptime_seconds = int(current_timestamp - boot_time_timestamp)
            self.db.update('settings', {'value': str(calculated_uptime_seconds)}, {'key': 'uptime'})
            print("[*] Uptime updated.")

            actual_ap_port = os.environ.get('AP_PORT', os.environ.get('AGENT_PORT', '3447')) # Agent's port
            stored_ap_port = self.db.get('settings', where={'key': 'ap_port'})
            if not stored_ap_port or stored_ap_port['value'] != actual_ap_port:
                self.db.update('settings', {'value': actual_ap_port}, {'key': 'ap_port'})
                print(f"[*] Updated ap_port in settings to reflect environment variable: {actual_ap_port}")
            print("[*] Fetching and caching local dashboard stats for self-registered server...")
            try:
                local_dashboard_stats =  self._dashboard_stats() # Get local stats
                # Assuming the central panel itself is server_id = 1
                self.db.update('servers',
                               {'status': 'active', # Ensure local server is marked active
                                'last_synced': datetime.now().isoformat(),
                                'dashboard_cache': json.dumps(local_dashboard_stats)},
                               {'server_id': 1}) # Update the entry for the central server
                print("[*] Local dashboard stats cached for server ID 1.")
            except Exception as e:
                print(f"Warning: Failed to fetch and cache local dashboard stats for server ID 1: {e}")
                # Mark as error/unreachable if local dashboard fetch fails
                self.db.update('servers', {'status': 'error'}, {'server_id': 1})
            # --- END NEW ---
            print("[*] Local synchronization process completed.")