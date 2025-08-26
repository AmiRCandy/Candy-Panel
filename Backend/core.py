# core.py
import subprocess, json, random, uuid, time, ipaddress, os, psutil, shutil, re , netifaces , string
from db import SQLite
from nanoid import generate
from datetime import datetime , timedelta

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
        Checks if a given string is a valid IPv4 or IPv6 address.
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
        Returns all host IPs within a given subnet CIDR, supporting IPv4 and IPv6.
        """
        try:
            network = ipaddress.ip_network(subnet_cidr, strict=False)
            return [str(ip) for ip in network.hosts()]
        except ValueError:
            return []

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

    def _get_used_ips(self, wg_id: int) -> set[str]:
        """
        Parses the WireGuard configuration file to find used client IPs (IPv4 and IPv6).
        """
        used_ips = set()
        try:
            with open(WG_CONF_PATH.replace('X', str(wg_id)), "r") as f:
                content = f.read()
            # Regex to find IPs in "AllowedIPs = 10.0.0.X/32" or "AllowedIPs = XXXX::/128" format
            ips = re.findall(r"AllowedIPs\s*=\s*([0-9a-fA-F.:]+/\d+)", content)
            for ip in ips:
                # Normalize IP address to get just the host part
                network = ipaddress.ip_network(ip, strict=False)
                used_ips.add(str(network.network_address))
        except FileNotFoundError:
            print(f"Error: WireGuard config file not found for wg{wg_id}.")
        except Exception as e:
            print(f"Error parsing used IPs for wg{wg_id}: {e}")
        return used_ips

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
        # Use '|| true' to prevent error if already down, allowing 'up' to proceed
        self.run_command(f"sudo wg-quick down wg{wg_id} || true", check=False)
        self.run_command(f"sudo wg-quick up wg{wg_id}")
        print(f"[*] WireGuard interface wg{wg_id} reloaded.")

    def _add_peer_to_config(self, wg_id: int, client_name: str, client_public_key: str, client_ip: str, client_ipv6: str = None):
        """
        Adds a client peer entry to the WireGuard configuration file, including IPv6 if provided.
        """
        config_path = WG_CONF_PATH.replace('X', str(wg_id))
        allowed_ips = f"{client_ip}/32"
        if client_ipv6:
            allowed_ips += f", {client_ipv6}/128"

        peer_entry = f"""
[Peer]
# {client_name}
PublicKey = {client_public_key}
AllowedIPs = {allowed_ips}
"""
        try:
            with open(config_path, "a") as f:
                f.write(peer_entry)
            # Apply changes to the running WireGuard interface without full restart
            self.run_command(f"sudo bash -c 'wg syncconf wg{wg_id} <(wg-quick strip wg{wg_id})'")
            print(f"[+] Client '{client_name}' added to wg{wg_id} config.")
        except Exception as e:
            raise CommandExecutionError(f"Failed to add client '{client_name}' to WireGuard configuration: {e}")

    def _remove_peer_from_config(self, wg_id: int, client_name: str, client_public_key: str):
        """
        Removes a client peer entry from the WireGuard configuration file.
        """
        config_path = WG_CONF_PATH.replace('X', str(wg_id))

        if not os.path.exists(config_path):
            print(f"[!] WireGuard config file {config_path} not found. Cannot remove peer from config.")
            return # Cannot remove if file doesn't exist

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
                        if not peer_block_to_delete:
                            new_lines.extend(temp_block)
                    temp_block = [line]
                    in_peer_block = True
                    peer_block_to_delete = False # Reset for new block
                elif in_peer_block:
                    temp_block.append(line)
                    # Check for public key to identify the peer block, more reliable than comment
                    if f"PublicKey = {client_public_key}" in line.strip():
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
        """
        traffic_data = {}
        try:
            # Use 'sudo wg show <interface> dump' to get machine-readable output
            result = subprocess.run(['sudo', 'wg', 'show', f"wg{wg_id}", 'dump'], capture_output=True, text=True, check=True)
            output_lines = result.stdout.strip().splitlines()

            # The 'dump' output for an interface lists the interface details on the first line,
            # followed by a line for each peer.
            # Peer line format: <public_key>\t<preshared_key>\t<endpoint>\t<allowed_ips>\t<latest_handshake>\t<transfer_rx>\t<transfer_tx>\t<persistent_keepalive>
            for line in output_lines:
                parts = line.strip().split('\t') # Explicitly split by tab

                # A valid peer line should have exactly 8 parts
                if len(parts) == 8:
                    try:
                        pubkey = parts[0] # Peer public key is the first field
                        rx = int(parts[5]) # transfer_rx is the 6th field (index 5)
                        tx = int(parts[6]) # transfer_tx is the 7th field (index 6)
                        traffic_data[pubkey] = {'rx': rx, 'tx': tx}
                    except (ValueError, IndexError) as e:
                        print(f"Warning: Could not parse wg dump peer line: '{line.strip()}'. Error: {e}")
                elif len(parts) == 4:
                    # This is likely the interface line (Private Key, Public Key, Listen Port, FwMark)
                    # We can skip this line as it doesn't contain peer traffic info.
                    pass
                else:
                    # Other unexpected lines or malformed lines
                    print(f"Warning: Unexpected line format or number of parts in wg dump output: '{line.strip()}'")

        except subprocess.CalledProcessError as e:
            print(f"Warning: Failed to run `sudo wg show wg{wg_id} dump`. Error: {e.stderr.strip()}. Please ensure WireGuard is installed and you have appropriate permissions (e.g., sudo access).")
        except Exception as e:
            print(f"An unexpected error occurred while getting traffic for wg{wg_id}: {e}")
        return traffic_data

    def _install_candy_panel(self, server_ip: str,
                             wg_port: str,
                             wg_address_range: str = "10.0.0.1/24",
                             wg_dns: str = "8.8.8.8",
                             admin_user: str = 'admin',
                             admin_password: str = 'admin',
                             wg_ipv6_address: str = None,
                             wg_ipv6_dns: str = None) -> tuple[bool, str]:
        """
        Installs WireGuard and initializes the CandyPanel server configuration, with IPv6 support.
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

        # --- Add UFW Installation and Configuration ---
        print("[+] Installing and configuring UFW...")
        try:
            self.run_command("sudo apt install -y ufw")
            self.run_command("sudo ufw default deny incoming")
            self.run_command("sudo ufw default allow outgoing")
            # Allow both IPv4 and IPv6 for the WireGuard port
            self.run_command(f"sudo ufw allow {wg_port}/udp")
            self.run_command("sudo ufw allow ssh")
            ap_port = os.environ.get('AP_PORT', '3446')
            self.run_command(f"sudo ufw allow {ap_port}/tcp")
            self.run_command("sudo ufw --force enable")
            print("[+] UFW configured successfully.")
        except Exception as e:
            return False, f"Failed to configure UFW: {e}"

        # --- Add IP Forwarding Configuration ---
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
        env = os.environ.copy()
        env["AP_PORT"] = '3446' # Ensure this is set for `bot.py` and `main.py`
        wg_id = 0 # Default initial interface ID
        default_interface = self._get_default_interface()
        interface_name = f"wg{wg_id}"
        server_private_key_path = SERVER_PRIVATE_KEY_PATH.replace('X', str(wg_id))
        server_public_key_path = SERVER_PUBLIC_KEY_PATH.replace('X', str(wg_id))

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

        # Build Address and DNS lines for the config
        addresses = [wg_address_range]
        if wg_ipv6_address:
            addresses.append(wg_ipv6_address)
        address_line = "Address = " + ", ".join(addresses)
        
        dns_servers = [wg_dns]
        if wg_ipv6_dns:
            dns_servers.append(wg_ipv6_dns)
        dns_line = "DNS = " + ", ".join(dns_servers)

        wg_conf_path = WG_CONF_PATH.replace('X', str(wg_id))
        wg_conf = f"""
[Interface]
{address_line}
ListenPort = {wg_port}
PrivateKey = {private_key}
MTU = 1420
{dns_line}

PostUp = iptables -A FORWARD -i {interface_name} -j ACCEPT; iptables -t nat -A POSTROUTING -o {default_interface} -j MASQUERADE; ip6tables -A FORWARD -i {interface_name} -j ACCEPT; ip6tables -t nat -A POSTROUTING -o {default_interface} -j MASQUERADE
PostDown = iptables -D FORWARD -i {interface_name} -j ACCEPT; iptables -t nat -D POSTROUTING -o {default_interface} -j MASQUERADE; ip6tables -D FORWARD -i {interface_name} -j ACCEPT; ip6tables -t nat -D POSTROUTING -o {default_interface} -j MASQUERADE
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
                'status': True,
                'ipv6_address_range': wg_ipv6_address
            })
        else:
            # Update if it already exists (e.g., re-running install)
            self.db.update('interfaces', {
                'private_key': private_key,
                'public_key': public_key,
                'port': wg_port,
                'address_range': wg_address_range,
                'status': True,
                'ipv6_address_range': wg_ipv6_address
            }, {'wg': wg_id})

        try:
            self.run_command(f"sudo systemctl enable wg-quick@wg{wg_id}")
            self.run_command(f"sudo systemctl start wg-quick@wg{wg_id}")
        except Exception as e:
            return False, f"Failed to start WireGuard service: {e}"

        # Update initial settings (e.g., server IP, DNS, admin credentials)
        self.db.update('settings', {'value': server_ip}, {'key': 'server_ip'})
        self.db.update('settings', {'value': server_ip}, {'key': 'custom_endpont'})
        self.db.update('settings', {'value': wg_dns}, {'key': 'dns'})
        if wg_ipv6_dns:
            self.db.update('settings',  {'value': wg_ipv6_dns},{'key': 'ipv6_dns'})
        # IMPORTANT: In a real app, hash the admin password before storing!
        admin_data = json.dumps({'user': admin_user, 'password': admin_password})
        self.db.update('settings', {'value': admin_data}, {'key': 'admin'})
        self.db.update('settings', {'value': '1'}, {'key': 'install'})
        print("[+] Installation completed. Sync will run automatically in the background via main.py thread.")
        return True, 'Installed successfully!'

    def _admin_login(self, user: str, password: str) -> tuple[bool, str]:
        """
        Authenticates an admin user.
{{ ... }}
        WARNING: Password stored in plaintext in DB. This should be hashed!
        """
        admin_settings = json.loads(self.db.get('settings', where={'key': 'admin'})['value'])
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

    def _get_all_clients(self) -> list[dict]:
        """
        Retrieves all client records from the database.
        """
        return self.db.select('clients')

    def _new_client(self, name: str, expire: str, traffic: str, wg_id: int = 0, note: str = '') -> tuple[bool, str]:
        """
        Creates a new WireGuard client, generates its configuration, and adds it to the DB.
        'expire' should be a datetime string, 'traffic' should be a string representing bytes.
        Initializes used_trafic with last_wg_rx/tx for future syncs.
        """
        if self.db.has('clients', {'name': name}):
            return False, 'Client with this name already exists.'

        interface_wg = self.db.get('interfaces', where={'wg': wg_id})
        if not interface_wg:
            return False, f"WireGuard interface wg{wg_id} not found."

        # Get existing IPs from both DB and config file
        used_ips = self._get_used_ips(wg_id)
        existing_client_ips = {c['address'] for c in self.db.select('clients', where={'wg': wg_id})}

        # Find an available IPv4 address
        ipv4_network = ipaddress.ip_network(interface_wg['address_range'], strict=False)
        client_ipv4 = None
        for ip in ipv4_network.hosts():
            if str(ip) not in existing_client_ips and str(ip) not in used_ips:
                client_ipv4 = str(ip)
                break
        if not client_ipv4:
            return False, "No available IPv4 addresses in the subnet."
        
        # Find an available IPv6 address if an IPv6 range is configured
        client_ipv6 = None
        if interface_wg.get('ipv6_address_range'):
            ipv6_network = ipaddress.ip_network(interface_wg['ipv6_address_range'], strict=False)
            existing_client_ipv6s = {c['ipv6_address'] for c in self.db.select('clients', where={'wg': wg_id})}
            for ip in ipv6_network.hosts():
                if str(ip) not in existing_client_ipv6s and str(ip) not in used_ips:
                    client_ipv6 = str(ip)
                    break
            if not client_ipv6:
                print("[!] Warning: No available IPv6 addresses found. Creating client with IPv4 only.")
        
        client_private, client_public = self._generate_keypair()

        try:
            self._add_peer_to_config(wg_id, name, client_public, client_ipv4, client_ipv6)
        except CommandExecutionError as e:
            return False, str(e)
            
        server_ip = self.db.get('settings', where={'key': 'custom_endpont'})['value']
        dns = self.db.get('settings', where={'key': 'dns'})['value']
        mtu = self.db.get('settings', where={'key': 'mtu'})
        mtu_value = mtu['value'] if mtu else '1420'
        
        client_config_addresses = [client_ipv4 + "/32"]
        client_config_dns = [dns]
        
        if client_ipv6:
            client_config_addresses.append(client_ipv6 + "/128")
            ipv6_dns = self.db.get('settings', where={'key': 'ipv6_dns'})
            if ipv6_dns and ipv6_dns['value']:
                client_config_dns.append(ipv6_dns['value'])
        
        client_config = f"""[Interface]
PrivateKey = {client_private}
Address = {', '.join(client_config_addresses)}
DNS = {', '.join(client_config_dns)}
MTU = {mtu_value}

[Peer]
PublicKey = {interface_wg['public_key']}
Endpoint = {server_ip}:{interface_wg['port']}
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 25
"""
        initial_used_traffic = json.dumps({'download': 0, 'upload': 0, 'last_wg_rx': 0, 'last_wg_tx': 0})
        self.db.insert('clients', {
            'name': name,
            'public_key': client_public,
            'private_key': client_private,
            'address': client_ipv4,
            'ipv6_address': client_ipv6,
            'created_at': datetime.now().isoformat(),
            'expires': expire,
            'traffic': traffic, # Total traffic quota in bytes
            'used_trafic': initial_used_traffic,
            'wg': wg_id,
            'note': note,
            'connected_now': False,
            'status': True
        })
        return True, client_config

    def _disable_client(self, client_name: str) -> tuple[bool, str]:
        """
        Disables a WireGuard client by setting its status to False and removing from config.
        """
        client = self.db.get('clients', where={'name': client_name})
        if not client:
            return False, f"Client '{client_name}' not found."

        wg_id = client['wg']
        client_public_key = client['public_key']

        try:
            self._remove_peer_from_config(wg_id, client_name, client_public_key)
        except CommandExecutionError as e:
            print(f"[!] Error during peer removal from config for disabling: {e}. Proceeding with DB status update.")
            # Decide if you want to abort here or proceed with DB status update
            return False, f"Failed to remove peer from config: {e}"


        # Update client status in database
        self.db.update('clients', {'status': False}, {'name': client_name})
        print(f"[+] Client '{client_name}' disabled successfully in DB.")
        return True, f"Client '{client_name}' disabled successfully."

    def _delete_client(self, client_name: str) -> tuple[bool, str]:
        """
        Deletes a WireGuard client completely (DB and config).
        This should be a more manual, admin-triggered action, not automated by cron.
        """
        client = self.db.get('clients', where={'name': client_name})
        if not client:
            return False, f"Client '{client_name}' not found."

        wg_id = client['wg']
        client_public_key = client['public_key']
        try:
            self._remove_peer_from_config(wg_id, client['name'], client_public_key) # Use client['name']
        except CommandExecutionError as e:
            print(f"[!] Error during peer removal from config during deletion: {e}. Proceeding with DB deletion.")
            # Decide if you want to abort here or proceed with DB deletion
            # For a "delete" action, you might want to proceed even if config removal fails
            # to at least clean up the DB.

        self.db.delete('clients', {'name': client_name})
        print(f"[+] Client '{client_name}' deleted successfully from DB.")
        return True, f"Client '{client_name}' deleted successfully."


    def _edit_client(self, name: str, expire: str = None, traffic: str = None, status: bool = None, note: str = None) -> tuple[bool, str]:
        """
        Edits an existing client's details in the database and updates WireGuard config if status changes.
        Allows partial updates by checking for None values.
        """
        current_client = self.db.get('clients', where={'name': name})
        if not current_client:
            return False, f"Client '{name}' not found."

        update_data = {}
        client_public_key = current_client['public_key']

        if expire is not None:
            update_data['expires'] = expire
        if traffic is not None:
            update_data['traffic'] = traffic
        if note is not None:
            update_data['note'] = note

        # Handle status change
        if status is not None and status != current_client['status']:
            update_data['status'] = status
            wg_id = current_client['wg']

            if status: # Changing to Active
                try:
                    self._add_peer_to_config(wg_id, name, client_public_key, current_client['address'], current_client.get('ipv6_address'))
                except CommandExecutionError as e:
                    return False, str(e)
            else: # Changing to Inactive
                try:
                    self._remove_peer_from_config(wg_id, name, client_public_key)
                except CommandExecutionError as e:
                    return False, str(e)

        # Only update if there's actual data to change
        if update_data:
            self.db.update('clients', update_data, {'name': name})
            return True, f"Client '{name}' edited successfully."
        else:
            return False, "No valid update data provided." # Or True, "Nothing to update." if that's desired



    def _new_interface_wg(self, address_range: str, port: int, ipv6_address_range: str = None) -> tuple[bool, str]:
        """
        Creates a new WireGuard interface configuration and adds it to the database, with IPv6 support.
        """
        interfaces = self.db.select('interfaces')
        # Check for existing port or address range conflicts
        for interface in interfaces:
            if int(interface['port']) == port: # Ensure type consistency for comparison
                return False, f"An interface with port {port} already exists."
            if interface['address_range'] == address_range:
                return False, f"An interface with address range {address_range} already exists."
            if ipv6_address_range and interface.get('ipv6_address_range') == ipv6_address_range:
                return False, f"An interface with IPv6 address range {ipv6_address_range} already exists."

        # Find the next available wg ID
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

        # Build Address and DNS lines for the config
        addresses = [address_range]
        if ipv6_address_range:
            addresses.append(ipv6_address_range)
        address_line = "Address = " + ", ".join(addresses)
        
        dns_settings = self.db.get('settings', where={'key': 'dns'})
        dns = dns_settings['value'] if dns_settings else '8.8.8.8'
        dns_servers = [dns]
        ipv6_dns_settings = self.db.get('settings', where={'key': 'ipv6_dns'})
        if ipv6_dns_settings and ipv6_dns_settings['value']:
            dns_servers.append(ipv6_dns_settings['value'])
        dns_line = "DNS = " + ", ".join(dns_servers)

        config = f"""[Interface]
PrivateKey = {private_key}
{address_line}
ListenPort = {port}
MTU = 1420
{dns_line}

PostUp = iptables -A FORWARD -i {interface_name} -j ACCEPT; iptables -t nat -A POSTROUTING -o {default_interface} -j MASQUERADE; ip6tables -A FORWARD -i {interface_name} -j ACCEPT; ip6tables -t nat -A POSTROUTING -o {default_interface} -j MASQUERADE
PostDown = iptables -D FORWARD -i {interface_name} -j ACCEPT; iptables -t nat -D POSTROUTING -o {default_interface} -j MASQUERADE; ip6tables -D FORWARD -i {interface_name} -j ACCEPT; ip6tables -t nat -D POSTROUTING -o {default_interface} -j MASQUERADE
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
            'ipv6_address_range': ipv6_address_range,
            'status': True
        })
        return True, 'New Interface Created!'

    def _edit_interface(self, name: str, address: str = None, port: int = None, status: bool = None) -> tuple[bool, str]:
        """
        Edits an existing WireGuard interface configuration and updates the database, with IPv6 support.
        'name' should be in 'wgX' format (e.g., 'wg0').
        Handles starting/stopping the interface based on status change.
        """
        wg_id = int(name.replace('wg', ''))
        current_interface = self.db.get('interfaces', where={'wg': wg_id})
        if not current_interface:
            return False, f"Interface {name} does not exist in database."

        config_path = self._get_interface_path(name)
        if not self._interface_exists(name):
            return False, f"Interface {name} configuration file does not exist."

        update_data = {}
        reload_needed = False
        service_action_needed = False

        try:
            # Read current config to modify
            with open(config_path, "r") as f:
                lines = f.readlines()

            new_lines = []
            for line in lines:
                if line.strip().startswith("Address ="):
                    # This logic needs to be more robust for multiple addresses
                    if address is not None and current_interface['address_range'] != address:
                        new_line = line.replace(current_interface['address_range'], address)
                        new_lines.append(new_line)
                        update_data['address_range'] = address
                        reload_needed = True
                    else:
                        new_lines.append(line)
                elif port is not None and line.strip().startswith("ListenPort ="):
                    if int(current_interface['port']) != port:
                        new_lines.append(f"ListenPort = {port}\n")
                        update_data['port'] = port
                        reload_needed = True
                    else:
                        new_lines.append(line)
                else:
                    new_lines.append(line)

            # Write updated config back
            if reload_needed:
                with open(config_path, "w") as f:
                    f.writelines(new_lines)

            # Handle status change (start/stop service)
            if status is not None and status != current_interface['status']:
                update_data['status'] = status
                service_action_needed = True
                if status: # Changing to Active
                    self.run_command(f"sudo systemctl start wg-quick@{name}")
                    print(f"[+] Interface {name} started.")
                else: # Changing to Inactive
                    self.run_command(f"sudo systemctl stop wg-quick@{name}")
                    print(f"[+] Interface {name} stopped.")

            # Perform DB update only if there's data to update
            if update_data:
                self.db.update('interfaces', update_data, {'wg': wg_id})

            # Reload only if config file was changed and service wasn't explicitly started/stopped
            if reload_needed and not service_action_needed:
                self._reload_wireguard(wg_id)

            return True, f"Interface {name} edited successfully."
        except Exception as e:
            return False, f"Error editing interface {name}: {e}"

    def _delete_interface(self, wg_id: int) -> tuple[bool, str]:
        """
        Deletes a WireGuard interface, stops its service, removes config files,
        and deletes associated clients and the interface from the database.
        """
        interface_name = f"wg{wg_id}"
        interface = self.db.get('interfaces', where={'wg': wg_id})
        if not interface:
            return False, f"Interface {interface_name} not found."

        try:
            # 1. Stop and disable the WireGuard service
            self.run_command(f"sudo systemctl stop wg-quick@{interface_name}", check=False)
            self.run_command(f"sudo systemctl disable wg-quick@{interface_name}", check=False)
            print(f"[+] WireGuard service wg-quick@{interface_name} stopped and disabled.")

            # 2. Remove WireGuard configuration files and keys
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

            # 3. Delete all clients associated with this interface from the database
            clients_to_delete = self.db.select('clients', where={'wg': wg_id})
            for client in clients_to_delete:
                self.db.delete('clients', {'name': client['name']})
                print(f"[+] Deleted associated client: {client['name']}")

            # 4. Delete the interface record from the database
            self.db.delete('interfaces', {'wg': wg_id})
            print(f"[+] Interface {interface_name} deleted from database.")

            return True, f"Interface {interface_name} and all associated clients deleted successfully."
        except Exception as e:
            return False, f"Error deleting interface {interface_name}: {e}"


    def _get_client_config(self, name: str) -> tuple[bool, str]:
        """
        Generates and returns the WireGuard client configuration for a given client name, with IPv6 support.
        """
        client = self.db.get('clients', where={'name': name})
        if not client:
            return False, 'Client not found.'

        interface = self.db.get('interfaces', where={'wg': client['wg']})
        if not interface:
            return False, f"Associated WireGuard interface wg{client['wg']} not found."

        dns = self.db.get('settings', where={'key': 'dns'})['value']
        ipv6_dns_setting = self.db.get('settings', where={'key': 'ipv6_dns'})
        mtu = self.db.get('settings', where={'key': 'mtu'})
        mtu_value = mtu['value'] if mtu else '1420' # Default MTU if not found
        server_ip = self.db.get('settings', where={'key': 'custom_endpont'})['value']

        address_line = f"Address = {client['address']}/32"
        if client.get('ipv6_address'):
            address_line += f", {client['ipv6_address']}/128"

        dns_line = f"DNS = {dns}"
        if ipv6_dns_setting and ipv6_dns_setting['value']:
            dns_line += f", {ipv6_dns_setting['value']}"

        client_config = f"""
[Interface]
PrivateKey = {client['private_key']}
{address_line}
{dns_line}
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
    def _generate_unique_short_code(self, length=7): #
        """
        Generates a unique short alphanumeric code for a URL.
        """
        characters = string.ascii_letters + string.digits
        while True:
            short_code = generate(characters, length) #
            if not self.db.has('shortlinks', {'short_code': short_code}): #
                return short_code
    def _get_client_by_name_and_public_key(self, name: str, public_key: str) -> dict | None:
        """
        Retrieves a client record by its name AND public key.
        This is used for public-facing client detail pages.
        """
        client = self.db.get('clients', where={'name': name, 'public_key': public_key})
        if not client:
            return None

        # Parse used_trafic JSON string into a dict, handling potential errors
        try:
            used_traffic_raw = client.get('used_trafic', '{"download":0,"upload":0}')
            client['used_trafic'] = json.loads(used_traffic_raw)
        except (json.JSONDecodeError, TypeError):
            print(f"[!] Warning: Invalid JSON in used_trafic for client '{name}'. Resetting to defaults.")
            client['used_trafic'] = {"download": 0, "upload": 0}

        client.pop('wg', None)

        # Fetch relevant interface details
        interface = self.db.get('interfaces', where={'wg': client.get('wg', 0)}) # Use .get with default in case 'wg' was popped
        if interface:
            client['interface_public_key'] = interface['public_key']
            client['interface_port'] = interface['port']
        else:
            client['interface_public_key'] = None
            client['interface_port'] = None

        # Add server endpoint details from settings
        client['server_endpoint_ip'] = self.db.get('settings', where={'key': 'custom_endpont'})['value']
        client['server_dns'] = self.db.get('settings', where={'key': 'dns'})['value']
        client['server_mtu'] = self.db.get('settings', where={'key': 'mtu'})['value']
        return client
    def _is_telegram_bot_running(self, pid: int) -> bool:
        """
        Checks if the Telegram bot process with the given PID is running.
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
        """
        pid_setting = self.db.get('settings', where={'key': 'telegram_bot_pid'})
        current_pid = int(pid_setting['value']) if pid_setting and pid_setting['value'].isdigit() else 0

        is_running = self._is_telegram_bot_running(current_pid)

        # Get the path to the virtual environment's python interpreter
        current_script_dir = os.path.dirname(os.path.abspath(__file__))
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
                ap_port_setting = self.db.get('settings', where={'key': 'ap_port'}) # Get AP_PORT

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

                # Verify venv python path exists
                if not os.path.exists(venv_python_path):
                    print(f"[!] Error: Virtual environment Python interpreter not found at {venv_python_path}. Please ensure the virtual environment is correctly set up.")
                    return False

                env = os.environ.copy()
                env["TELEGRAM_API_ID"] = api_id_setting['value']
                env["TELEGRAM_API_HASH"] = api_hash_setting['value']
                if ap_port_setting and ap_port_setting['value'].isdigit():
                    env["AP_PORT"] = ap_port_setting['value']
                else:
                    env["AP_PORT"] = '3446' # Default if not set in DB

                log_file_path = "/var/log/candy-telegram-bot.log"
                with open(log_file_path, "a") as log_file:
                    process = subprocess.Popen(
                        [venv_python_path, bot_script_path], # Use venv's python
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

    def _calculate_and_update_traffic(self):
        """
        Calculates and updates cumulative traffic for all clients.
        This replaces the old traffic.json logic.
        """
        print("[*] Calculating and updating client traffic statistics...")

        # Get current traffic from all interfaces
        current_wg_traffic = {}
        for interface_row in self.db.select('interfaces'):
            wg_id = interface_row['wg']
            current_wg_traffic.update(self._get_current_wg_peer_traffic(wg_id))

        # Total bandwidth consumed by all clients in this cycle
        total_bandwidth_consumed_this_cycle = 0

        # Iterate through all clients in the database
        all_clients_in_db = self.db.select('clients')
        for client in all_clients_in_db:
            client_public_key = client['public_key']
            client_name = client['name']

            # Get the current readings from 'wg show dump'
            current_rx = current_wg_traffic.get(client_public_key, {}).get('rx', 0)
            current_tx = current_wg_traffic.get(client_public_key, {}).get('tx', 0)

            try:
                # Parse existing used_trafic data (which now includes last_wg_rx/tx)
                used_traffic_data = json.loads(client.get('used_trafic', '{"download":0,"upload":0,"last_wg_rx":0,"last_wg_tx":0}'))

                cumulative_download = used_traffic_data.get('download', 0)
                cumulative_upload = used_traffic_data.get('upload', 0)
                last_wg_rx = used_traffic_data.get('last_wg_rx', 0)
                last_wg_tx = used_traffic_data.get('last_wg_tx', 0)

                # Calculate delta for this sync cycle
                # Handle WireGuard counter resets: If current < last, assume reset and add current as delta.
                delta_rx = current_rx - last_wg_rx
                if delta_rx < 0:
                    print(f"[*] Detected RX counter reset for client '{client_name}'. Adding current RX ({current_rx} bytes) as delta.")
                    delta_rx = current_rx

                delta_tx = current_tx - last_wg_tx
                if delta_tx < 0:
                    print(f"[*] Detected TX counter reset for client '{client_name}'. Adding current TX ({current_tx} bytes) as delta.")
                    delta_tx = current_tx

                delta_rx = max(0, delta_rx) # Ensure non-negative
                delta_tx = max(0, delta_tx) # Ensure non-negative

                # Update cumulative totals
                cumulative_download += delta_rx
                cumulative_upload += delta_tx

                # Prepare updated JSON for DB
                updated_used_traffic = {
                    'download': cumulative_download,
                    'upload': cumulative_upload,
                    'last_wg_rx': current_rx, # Store current readings for next cycle's delta calculation
                    'last_wg_tx': current_tx
                }

                self.db.update('clients', {'used_trafic': json.dumps(updated_used_traffic)}, {'name': client_name})

                total_bandwidth_consumed_this_cycle += (delta_rx + delta_tx)

            except (json.JSONDecodeError, ValueError, TypeError) as e:
                print(f"[!] Error processing traffic for client '{client_name}': {e}. Skipping this client's traffic update.")

        # Update overall server bandwidth in settings
        old_bandwidth_setting = self.db.get('settings', where={'key': 'bandwidth'})
        current_total_bandwidth = int(old_bandwidth_setting['value']) if old_bandwidth_setting and old_bandwidth_setting['value'].isdigit() else 0
        new_total_bandwidth = current_total_bandwidth + total_bandwidth_consumed_this_cycle
        self.db.update('settings', {'value': str(new_total_bandwidth)}, {'key': 'bandwidth'})
        print("[*] Client traffic statistics updated.")


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

        # --- Client Expiration and Traffic Limit Enforcement (Disable, not Delete) ---
        current_time = datetime.now()
        # FIX: Fetch all clients to disable into a list first, BEFORE iterating and updating
        clients_to_disable = []
        active_clients = self.db.select('clients', where={'status': True})
        for client in active_clients: # Iterating over fetched results
            should_disable = False
            disable_reason = ""

            # Check expiration
            try:
                expires_dt = datetime.fromisoformat(client['expires'])
                if current_time >= expires_dt:
                    should_disable = True
                    disable_reason = "expired"
            except (ValueError, TypeError):
                print(f"[!] Warning: Invalid expires date format for client '{client['name']}'. Skipping expiration check.")

            # Check traffic limit (only if not already marked for disabling by expiration)
            if not should_disable:
                try:
                    traffic_limit = int(client['traffic']) # Expected total traffic quota in bytes
                    used_traffic_data = json.loads(client['used_trafic'])
                    total_used_traffic = used_traffic_data.get('download', 0) + used_traffic_data.get('upload', 0)

                    if traffic_limit > 0 and total_used_traffic >= traffic_limit:
                        should_disable = True
                        disable_reason = "exceeded traffic limit"
                except (ValueError, TypeError, json.JSONDecodeError) as e:
                    print(f"[!] Warning: Invalid traffic data for client '{client['name']}'. Skipping traffic limit check. Error: {e}")

            if should_disable:
                clients_to_disable.append(client['name']) # Collect names to disable

        # Now, iterate over the collected names and perform the database updates
        for client_name_to_disable in clients_to_disable:
            print(f"[!] Client '{client_name_to_disable}' needs disabling. Disabling...")
            self._disable_client(client_name_to_disable)
        # --- Update Traffic Statistics ---
        self._calculate_and_update_traffic()

        # --- Update Uptime ---
        # Get system boot time and calculate uptime
        boot_time_timestamp = psutil.boot_time() # Returns UTC timestamp
        current_timestamp = time.time()
        calculated_uptime_seconds = int(current_timestamp - boot_time_timestamp)
        self.db.update('settings', {'value': str(calculated_uptime_seconds)}, {'key': 'uptime'})
        print("[*] Uptime updated.")

        # --- Ensure AP_PORT setting is in sync with environment (for display purposes) ---
        # This just updates the DB with what the system is actually running on, not
        # to trigger a change in the running port which needs a Flask app restart.
        actual_ap_port = os.environ.get('AP_PORT', '3446')
        stored_ap_port = self.db.get('settings', where={'key': 'ap_port'})
        if not stored_ap_port or stored_ap_port['value'] != actual_ap_port:
            self.db.update('settings', {'value': actual_ap_port}, {'key': 'ap_port'})
            print(f"[*] Updated ap_port in settings to reflect environment variable: {actual_ap_port}")

        print("[*] Synchronization process completed.")


# Custom exception for command execution errors
class CommandExecutionError(Exception):
    pass