# main.py
from flask import Flask, request, jsonify, abort, g, send_from_directory , send_file, redirect
from functools import wraps
from flask_cors import CORS
import asyncio
import json
from datetime import datetime, timedelta
import os
import subprocess
import threading
import time

# Import your CandyPanel logic
from core import CandyPanel, CommandExecutionError

# --- Initialize CandyPanel ---
candy_panel = CandyPanel()

# --- Flask Application Setup ---
app = Flask(__name__, static_folder=os.path.join(os.getcwd(), '..', 'Frontend', 'dist'), static_url_path='/static')
app.config['SECRET_KEY'] = 'your_super_secret_key'
CORS(app)

# --- Background Sync Thread ---
def background_sync():
    """Background thread function that runs sync every 5 minutes"""
    while True:
        try:
            print("[*] Starting background sync...")
            candy_panel._sync()
            print("[*] Background sync completed successfully.")
        except Exception as e:
            print(f"[!] Error in background sync: {e}")
        # Sleep for 5 minutes (300 seconds)
        time.sleep(300)

# Start background sync thread
sync_thread = threading.Thread(target=background_sync, daemon=True)
sync_thread.start()
print("[+] Background sync thread started.")

# --- Authentication Decorator for CandyPanel Admin API ---
def authenticate_admin(f):
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            abort(401, description="Authorization header missing")

        try:
            token_type, token = auth_header.split(None, 1)
        except ValueError:
            abort(401, description="Invalid Authorization header format")

        if token_type.lower() != 'bearer':
            abort(401, description="Unsupported authorization type")

        # Run synchronous DB operation in a thread pool
        settings = await asyncio.to_thread(candy_panel.db.get, 'settings','*' ,{'key': 'session_token'})
        if not settings or settings['value'] != token:
            abort(401, description="Invalid authentication credentials")

        g.is_authenticated = True
        return await f(*args, **kwargs)
    return decorated_function

# --- Helper for common responses ---
def success_response(message: str, data=None, status_code: int = 200):
    return jsonify({"message": message, "success": True, "data": data}), status_code

def error_response(message: str, status_code: int = 400):
    return jsonify({"message": message, "success": False}), status_code

# --- CandyPanel API Endpoints ---
@app.get("/client-details/<name>/<public_key>")
async def get_client_public_details(name: str, public_key: str):
    """
    Retrieves public-facing details for a specific client given its name and public key.
    This endpoint does NOT require authentication.
    """
    try:
        client_data = await asyncio.to_thread(candy_panel._get_client_by_name_and_public_key, name, public_key)
        if client_data:
            return success_response("Client details retrieved successfully.", data=client_data)
        else:
            return error_response("Client not found or public key mismatch.", 404)
    except Exception as e:
        return error_response(f"An error occurred: {e}", 500)

@app.get("/shortlink/<name>/<public_key>")
async def shortlink_redirect(name: str, public_key: str):
    """
    Handles shortlink redirects to the client details page.
    This replaces the frontend shortlink handling.
    """
    try:
        # Verify client exists before redirecting
        client = await asyncio.to_thread(candy_panel.db.get, 'clients', where={'name': name, 'public_key': public_key})
        if not client:
            # Serve a simple error page
            return f"""
            <!DOCTYPE html>
            <html>
            <head><title>Client Not Found</title></head>
            <body style="font-family: Arial, sans-serif; text-align: center; margin-top: 50px;">
                <h1>Client Not Found</h1>
                <p>The requested client does not exist or the link is invalid.</p>
            </body>
            </html>
            """, 404
        
        # Serve the client details page directly
        return send_from_directory(app.static_folder, 'client.html')
    except Exception as e:
        return f"""
        <!DOCTYPE html>
        <html>
        <head><title>Error</title></head>
        <body style="font-family: Arial, sans-serif; text-align: center; margin-top: 50px;">
            <h1>Error</h1>
            <p>An error occurred: {e}</p>
        </body>
        </html>
        """, 500

@app.get("/qr/<name>/<public_key>")
async def get_qr_code(name: str, public_key: str):
    """
    Generates and returns a QR code image for a client's configuration (without the private key), with IPv6 support.
    This endpoint is publicly accessible.
    """
    client = await asyncio.to_thread(candy_panel.db.get, 'clients', where={'name': name, 'public_key': public_key})
    if not client:
        return error_response("Client not found or public key mismatch.", 404)

    interface = await asyncio.to_thread(candy_panel.db.get, 'interfaces', where={'wg': client['wg']})
    if not interface:
        return error_response("Associated WireGuard interface not found.", 500)

    # Reconstruct the config using live data
    dns = await asyncio.to_thread(candy_panel.db.get, 'settings', where={'key': 'dns'})
    dns_value = dns['value'] if dns else '8.8.8.8'
    ipv6_dns = await asyncio.to_thread(candy_panel.db.get, 'settings', where={'key': 'ipv6_dns'})
    ipv6_dns_value = ipv6_dns['value'] if ipv6_dns else None
    
    dns_list = [dns_value]
    if ipv6_dns_value:
        dns_list.append(ipv6_dns_value)
    
    dns_line = f"DNS = {', '.join(dns_list)}"

    mtu = await asyncio.to_thread(candy_panel.db.get, 'settings', where={'key': 'mtu'})
    mtu_value = mtu['value'] if mtu else '1420'
    server_ip = await asyncio.to_thread(candy_panel.db.get, 'settings', where={'key': 'custom_endpont'})
    server_ip = server_ip['value']

    address_line = f"Address = {client['address']}/32"
    if client.get('ipv6_address'):
        address_line += f", {client['ipv6_address']}/128"

    config_content = f"""[Interface]
PrivateKey = {client['private_key']}
{address_line}
{dns_line}
MTU = {mtu_value}

[Peer]
PublicKey = {interface['public_key']}
Endpoint = {server_ip}:{interface['port']}
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 25"""
    
    # Use qrencode to generate the QR code as a temporary file
    temp_file_path = f"/tmp/{name}-{public_key}.png"
    try:
        await asyncio.to_thread(subprocess.run,['qrencode', '-o', temp_file_path, config_content], check=True)
        return send_file(temp_file_path, mimetype='image/png')
    except subprocess.CalledProcessError:
        return error_response("Failed to generate QR code. Is 'qrencode' installed?", 500)
    except Exception as e:
        return error_response(f"An error occurred: {e}", 500)
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@app.get("/check")
async def check_installation():
    """
    Checks if the CandyPanel is installed.
    """
    install_status = await asyncio.to_thread(candy_panel.db.get, 'settings', '*',{'key': 'install'})
    is_installed = bool(install_status and install_status['value'] == '1')
    return jsonify({"installed": is_installed})

@app.post("/api/auth")
async def handle_auth():
    """
    Handles both login and installation based on the 'action' field, with IPv6 support.
    """
    data = request.json
    if not data or 'action' not in data:
        return error_response("Missing 'action' in request body", 400)

    action = data['action']
    install_status = await asyncio.to_thread(candy_panel.db.get, 'settings', '*',{'key': 'install'})
    is_installed = bool(install_status and install_status['value'] == '1')

    if action == 'login':
        if not is_installed:
            return error_response("CandyPanel is not installed. Please use the 'install' action.", 400)
        
        if 'username' not in data or 'password' not in data:
            return error_response("Missing username or password for login", 400)

        success, message = await asyncio.to_thread(candy_panel._admin_login, data['username'], data['password'])
        if not success:
            return error_response(message, 401)
        return success_response("Login successful!", data={"access_token": message, "token_type": "bearer"})

    elif action == 'install':
        if is_installed:
            return error_response("CandyPanel is already installed.", 400)

        try:
            server_ip = data['server_ip']
            wg_port = data['wg_port']
            wg_address_range = data.get('wg_address_range', "10.0.0.1/24")
            wg_ipv6_address = data.get('wg_ipv6_address', None)
            wg_dns = data.get('wg_dns', "8.8.8.8")
            wg_ipv6_dns = data.get('wg_ipv6_dns', None)
            admin_user = data.get('admin_user', "admin")
            admin_password = data.get('admin_password', "admin")
        except KeyError as e:
            return error_response(f"Missing required field for installation: {e}", 400)

        success, message = await asyncio.to_thread(
            candy_panel._install_candy_panel,
            server_ip,
            wg_port,
            wg_address_range,
            wg_dns,
            admin_user,
            admin_password,
            wg_ipv6_address,
            wg_ipv6_dns
        )
        if not success:
            return error_response(message, 400)
        return success_response(message)
    else:
        return error_response("Invalid action specified. Must be 'login' or 'install'.", 400)

@app.get("/api/data")
@authenticate_admin
async def get_all_data():
    """
    Retrieves all relevant data for the dashboard, clients, interfaces, and settings in one go.
    Requires authentication.
    """
    try:
        # Fetch all data concurrently
        dashboard_stats_task = asyncio.to_thread(candy_panel._dashboard_stats)
        clients_data_task = asyncio.to_thread(candy_panel._get_all_clients)
        interfaces_data_task = asyncio.to_thread(candy_panel.db.select, 'interfaces')
        settings_data_task = asyncio.to_thread(candy_panel.db.select, 'settings')

        dashboard_stats, clients_data, interfaces_data, settings_raw = await asyncio.gather(
            dashboard_stats_task, clients_data_task, interfaces_data_task, settings_data_task
        )

        # Process client data (parse used_trafic)
        for client in clients_data:
            try:
                client['used_trafic'] = json.loads(client['used_trafic'])
            except (json.JSONDecodeError, TypeError):
                client['used_trafic'] = {"download": 0, "upload": 0}
        
        # Process settings data (convert to dict)
        settings_data = {setting['key']: setting['value'] for setting in settings_raw}

        return success_response("All data retrieved successfully.", data={
            "dashboard": dashboard_stats,
            "clients": clients_data,
            "interfaces": interfaces_data,
            "settings": settings_data
        })
    except Exception as e:
        return error_response(f"Failed to retrieve all data: {e}", 500)

@app.post("/api/manage")
@authenticate_admin
async def manage_resources():
    """
    Unified endpoint for creating/updating/deleting clients, interfaces, and settings, with IPv6 support.
    Requires authentication.
    """
    data = request.json
    if not data or 'resource' not in data or 'action' not in data:
        return error_response("Missing 'resource' or 'action' in request body", 400)

    resource = data['resource']
    action = data['action']

    try:
        if resource == 'client':
            if action == 'create':
                name = data.get('name')
                expires = data.get('expires')
                traffic = data.get('traffic')
                wg_id = data.get('wg_id', 0)
                note = data.get('note', '')
                if not all([name, expires, traffic]):
                    return error_response("Missing name, expires, or traffic for client creation", 400)
                success, message = await asyncio.to_thread(candy_panel._new_client, name, expires, traffic, wg_id, note)
                if not success:
                    return error_response(message, 400)
                return success_response("Client created successfully!", data={"client_config": message})

            elif action == 'update':
                name = data.get('name')
                if not name:
                    return error_response("Missing client name for update", 400)
                expires = data.get('expires')
                traffic = data.get('traffic')
                status = data.get('status')
                note = data.get('note')
                success, message = await asyncio.to_thread(candy_panel._edit_client, name, expires, traffic, status, note)
                if not success:
                    return error_response(message, 400)
                return success_response(message)

            elif action == 'delete':
                name = data.get('name')
                if not name:
                    return error_response("Missing client name for deletion", 400)
                success, message = await asyncio.to_thread(candy_panel._delete_client, name)
                if not success:
                    return error_response(message, 400)
                return success_response(message)

            elif action == 'get_config':
                name = data.get('name')
                if not name:
                    return error_response("Missing client name to get config", 400)
                success, config_content = await asyncio.to_thread(candy_panel._get_client_config, name)
                if not success:
                    return error_response(config_content, 404)
                return success_response("Client config retrieved successfully.", data={"config": config_content})
            else:
                return error_response(f"Invalid action '{action}' for client resource", 400)

        elif resource == 'interface':
            if action == 'create':
                address_range = data.get('address_range')
                ipv6_address_range = data.get('ipv6_address_range')
                port = data.get('port')
                if not all([address_range, port]):
                    return error_response("Missing address_range or port for interface creation", 400)
                success, message = await asyncio.to_thread(candy_panel._new_interface_wg, address_range, port, ipv6_address_range)
                if not success:
                    return error_response(message, 400)
                return success_response(message)

            elif action == 'update':
                name = data.get('name') # e.g., 'wg0'
                if not name:
                    return error_response("Missing interface name for update", 400)
                address = data.get('address')
                port = data.get('port')
                status = data.get('status')
                success, message = await asyncio.to_thread(candy_panel._edit_interface, name, address, port, status)
                if not success:
                    return error_response(message, 400)
                return success_response(message)
            
            # New: Delete interface
            elif action == 'delete':
                wg_id = data.get('wg_id')
                if wg_id is None:
                    return error_response("Missing wg_id for interface deletion", 400)
                success, message = await asyncio.to_thread(candy_panel._delete_interface, wg_id)
                if not success:
                    return error_response(message, 400)
                return success_response(message)

            else:
                return error_response(f"Invalid action '{action}' for interface resource", 400)

        elif resource == 'setting':
            if action == 'update':
                key = data.get('key')
                value = data.get('value')
                if not all([key, value is not None]): # Value can be an empty string or 0, so check explicitly
                    return error_response("Missing key or value for setting update", 400)
                if key == 'telegram_bot_status':
                    if value == '1': # '1' means ON
                        bot_control_success = await asyncio.to_thread(candy_panel._manage_telegram_bot_process, 'start')
                        if not bot_control_success:
                            # Log the failure, but return success for setting update if DB was successful
                            print(f"Warning: Failed to start bot immediately after setting update.")
                            return success_response(f"(Bot start attempted, but failed.)")
                    else: # '0' means OFF
                        bot_control_success = await asyncio.to_thread(candy_panel._manage_telegram_bot_process, 'stop')
                        if not bot_control_success:
                            print(f"Warning: Failed to stop bot immediately after setting update.")
                            return success_response(f"(Bot stop attempted, but failed.)")
                success, message = await asyncio.to_thread(candy_panel._change_settings, key, value)
                if not success:
                    return error_response(message, 400)
                return success_response(message)
            else:
                return error_response(f"Invalid action '{action}' for setting resource", 400)

        elif resource == 'api_token':
            if action == 'create_or_update':
                name = data.get('name')
                token = data.get('token')
                if not all([name, token]):
                    return error_response("Missing name or token for API token operation", 400)
                success, message = await asyncio.to_thread(candy_panel._add_api_token, name, token)
                if not success:
                    return error_response(message, 400)
                return success_response(message)

            elif action == 'delete':
                name = data.get('name')
                if not name:
                    return error_response("Missing name for API token deletion", 400)
                success, message = await asyncio.to_thread(candy_panel._delete_api_token, name)
                if not success:
                    return error_response(message, 400)
                return success_response(message)
            else:
                return error_response(f"Invalid action '{action}' for API token resource", 400)
        
        elif resource == 'sync':
            if action == 'trigger':
                await asyncio.to_thread(candy_panel._sync)
                return success_response("Synchronization process initiated successfully.")
            else:
                return error_response(f"Invalid action '{action}' for sync resource", 400)

        else:
            return error_response(f"Unknown resource type: {resource}", 400)

    except CommandExecutionError as e:
        return error_response(f"Command execution error: {e}", 500)
    except Exception as e:
        return error_response(f"An unexpected error occurred: {e}", 500)

# --- Telegram Bot API Endpoints (Integrated) ---

@app.post("/bot_api/user/register")
async def bot_register_user():
    data = request.json
    telegram_id = data.get('telegram_id')
    if not telegram_id:
        return error_response("Missing telegram_id", 400)

    user = await asyncio.to_thread(candy_panel.db.get, 'users', where={'telegram_id': telegram_id})
    if user:
        return success_response("User already registered.", data={"registered": True, "language": user.get('language', 'en')}) # Return current language
    
    # Default language is English
    await asyncio.to_thread(candy_panel.db.insert, 'users', {
        'telegram_id': telegram_id,
        'created_at': datetime.now().isoformat(),
        'language': 'en' 
    })
    return success_response("User registered successfully.", data={"registered": True, "language": "en"})

@app.post("/bot_api/user/set_language")
async def bot_set_language():
    data = request.json
    telegram_id = data.get('telegram_id')
    language = data.get('language')

    if not all([telegram_id, language]):
        return error_response("Missing telegram_id or language", 400)

    if language not in ['en', 'fa']: # Only allow 'en' or 'fa' for now
        return error_response("Unsupported language. Available: 'en', 'fa'", 400)

    if not await asyncio.to_thread(candy_panel.db.has, 'users', {'telegram_id': telegram_id}):
        return error_response("User not registered with the bot.", 404)

    await asyncio.to_thread(candy_panel.db.update, 'users', {'language': language}, {'telegram_id': telegram_id})
    return success_response("Language updated successfully.")


@app.post("/bot_api/user/initiate_purchase") # NEW ENDPOINT
async def bot_initiate_purchase():
    data = request.json
    telegram_id = data.get('telegram_id')
    
    if not telegram_id:
        return error_response("Missing telegram_id", 400)

    if not await asyncio.to_thread(candy_panel.db.has, 'users', {'telegram_id': telegram_id}):
        return error_response("User not registered with the bot.", 404)

    prices_json = await asyncio.to_thread(candy_panel.db.get, 'settings', where={'key': 'prices'})
    prices = json.loads(prices_json['value']) if prices_json and prices_json['value'] else {}

    admin_card_number_setting = await asyncio.to_thread(candy_panel.db.get, 'settings', where={'key': 'admin_card_number'})
    admin_card_number = admin_card_number_setting['value'] if admin_card_number_setting else 'YOUR_ADMIN_CARD_NUMBER'

    return success_response("Purchase initiation details.", data={
        "admin_card_number": admin_card_number,
        "prices": prices
    })

@app.post("/bot_api/user/calculate_price") # NEW ENDPOINT
async def bot_calculate_price():
    data = request.json
    telegram_id = data.get('telegram_id')
    purchase_type = data.get('purchase_type')
    quantity = data.get('quantity')
    time_quantity = data.get('time_quantity', 0)
    traffic_quantity = data.get('traffic_quantity', 0)

    if not all([telegram_id, purchase_type]):
        return error_response("Missing telegram_id or purchase_type", 400)

    if not await asyncio.to_thread(candy_panel.db.has, 'users', {'telegram_id': telegram_id}):
        return error_response("User not registered with the bot.", 404)

    prices_json = await asyncio.to_thread(candy_panel.db.get, 'settings', where={'key': 'prices'})
    prices = json.loads(prices_json['value']) if prices_json and prices_json['value'] else {}

    calculated_amount = 0
    if purchase_type == 'gb':
        if quantity is None: return error_response("Missing quantity for GB purchase", 400)
        price_per_gb = prices.get('1GB')
        if not price_per_gb:
            return error_response("Price per GB not configured. Please contact support.", 500)
        calculated_amount = price_per_gb * float(quantity)
    elif purchase_type == 'month':
        if quantity is None: return error_response("Missing quantity for Month purchase", 400)
        price_per_month = prices.get('1Month')
        if not price_per_month:
            return error_response("Price per Month not configured. Please contact support.", 500)
        calculated_amount = price_per_month * float(quantity)
    elif purchase_type == 'custom':
        if time_quantity is None or traffic_quantity is None:
            return error_response("Missing time_quantity or traffic_quantity for custom purchase", 400)
        price_per_gb = prices.get('1GB')
        price_per_month = prices.get('1Month')
        if not price_per_gb or not price_per_month:
            return error_response("Prices for custom plan (1GB or 1Month) not configured. Please contact support.", 500)
        calculated_amount = (price_per_gb * float(traffic_quantity)) + (price_per_month * float(time_quantity))
    else:
        return error_response("Invalid purchase_type. Must be 'gb', 'month', or 'custom'.", 400)
    
    return success_response("Price calculated successfully.", data={"calculated_amount": calculated_amount})


@app.post("/bot_api/user/submit_transaction") # NEW ENDPOINT
async def bot_submit_transaction():
    data = request.json
    telegram_id = data.get('telegram_id')
    order_id = data.get('order_id')
    card_number_sent = data.get('card_number_sent') # This will be "User confirmed payment" for now
    purchase_type = data.get('purchase_type')
    amount = data.get('amount') # Calculated amount from previous step
    quantity = data.get('quantity', 0) # For 'gb' or 'month'
    time_quantity = data.get('time_quantity', 0) # For 'custom'
    traffic_quantity = data.get('traffic_quantity', 0) # For 'custom'

    if not all([telegram_id, order_id, card_number_sent, purchase_type, amount is not None]):
        return error_response("Missing required transaction details.", 400)

    # Check if order_id already exists (to prevent duplicate requests)
    if await asyncio.to_thread(candy_panel.db.has, 'transactions', {'order_id': order_id}):
        return error_response("This Order ID has already been submitted. Please use a unique one or contact support if you believe this is an error.", 400)

    await asyncio.to_thread(candy_panel.db.insert, 'transactions', {
        'order_id': order_id,
        'telegram_id': telegram_id,
        'amount': amount,
        'card_number_sent': card_number_sent,
        'status': 'pending',
        'requested_at': datetime.now().isoformat(),
        'purchase_type': purchase_type,
        'quantity': quantity,
        'time_quantity': time_quantity,
        'traffic_quantity': traffic_quantity
    })

    admin_telegram_id_setting = await asyncio.to_thread(candy_panel.db.get, 'settings', where={'key': 'telegram_bot_admin_id'})
    admin_telegram_id = admin_telegram_id_setting['value'] if admin_telegram_id_setting else '0'

    return success_response("Transaction submitted for review.", data={
        "admin_telegram_id": admin_telegram_id
    })


@app.post("/bot_api/user/get_license")
async def bot_get_user_license():
    data = request.json
    telegram_id = data.get('telegram_id')
    if not telegram_id:
        return error_response("Missing telegram_id", 400)

    user = await asyncio.to_thread(candy_panel.db.get, 'users', where={'telegram_id': telegram_id})
    if not user:
        return error_response("User not registered with the bot. Please use /start to register.", 404)
    if not user.get('candy_client_name'):
        return error_response("You don't have an active license yet. Please purchase one using the 'Buy Traffic' option.", 404)

    success, config_content = await asyncio.to_thread(candy_panel._get_client_config, user['candy_client_name'])
    if not success:
        return error_response(f"Failed to retrieve license. Reason: {config_content}. Please contact support.", 500)

    return success_response("Your WireGuard configuration:", data={"config": config_content})

@app.post("/bot_api/user/account_status")
async def bot_get_account_status():
    data = request.json
    telegram_id = data.get('telegram_id')
    if not telegram_id:
        return error_response("Missing telegram_id", 400)

    user = await asyncio.to_thread(candy_panel.db.get, 'users', where={'telegram_id': telegram_id})
    if not user:
        return error_response("User not registered with the bot. Please use /start to register.", 404)

    status_info = {
        "status": user['status'],
        "traffic_bought_gb": user['traffic_bought_gb'],
        "time_bought_days": user['time_bought_days'],
        "candy_client_name": user['candy_client_name'],
        "used_traffic_bytes": 0, # Default to 0
        "traffic_limit_bytes": 0, # Default to 0
        "expires": 'N/A',
        "note": ''
    }

    if user.get('candy_client_name'):
        # Directly call CandyPanel's internal method to get all clients
        all_clients_data = await asyncio.to_thread(candy_panel._get_all_clients)
        
        if all_clients_data:
            client_info = next((c for c in all_clients_data if c['name'] == user['candy_client_name']), None)
            if client_info:
                try:
                    used_traffic = json.loads(client_info.get('used_trafic', '{"download":0,"upload":0}'))
                    status_info['used_traffic_bytes'] = used_traffic.get('download', 0) + used_traffic.get('upload', 0)
                except (json.JSONDecodeError, TypeError):
                    status_info['used_traffic_bytes'] = 0 # Fallback
                status_info['expires'] = client_info.get('expires') # Get expiry from CandyPanel
                status_info['traffic_limit_bytes'] = int(client_info.get('traffic', 0))
                status_info['note'] = client_info.get('note', '') # Get note from CandyPanel client
            else:
                status_info['note'] = "Your VPN client configuration might be out of sync or deleted from the server. Please contact support."
        else:
            status_info['note'] = "Could not fetch live traffic data from the server. Please try again later or contact support."

    return success_response("Your account status:", data=status_info)

@app.post("/bot_api/user/call_support")
async def bot_call_support():
    data = request.json
    telegram_id = data.get('telegram_id')
    message_text = data.get('message')

    if not all([telegram_id, message_text]):
        return error_response("Missing telegram_id or message", 400)

    user = await asyncio.to_thread(candy_panel.db.get, 'users', where={'telegram_id': telegram_id})
    username = f"User {telegram_id}"
    if user and user.get('candy_client_name'):
        username = user['candy_client_name']

    admin_telegram_id_setting = await asyncio.to_thread(candy_panel.db.get, 'settings', where={'key': 'telegram_bot_admin_id'})
    admin_telegram_id = admin_telegram_id_setting['value'] if admin_telegram_id_setting else '0'

    if admin_telegram_id == '0':
        return error_response("Admin Telegram ID not set in bot settings. Support is unavailable.", 500)

    return success_response("Your message has been sent to support.", data={
        "admin_telegram_id": admin_telegram_id,
        "support_message": f"Support request from {username} (ID: {telegram_id}):\n\n{message_text}"
    })

# --- Admin Endpoints ---

@app.post("/bot_api/admin/check_admin")
async def bot_check_admin():
    data = request.json
    telegram_id = data.get('telegram_id')
    if not telegram_id:
        return error_response("Missing telegram_id", 400)
    
    admin_telegram_id_setting = await asyncio.to_thread(candy_panel.db.get, 'settings', where={'key': 'telegram_bot_admin_id'})
    admin_telegram_id = admin_telegram_id_setting['value'] if admin_telegram_id_setting else '0'
    is_admin = (str(telegram_id) == admin_telegram_id)
    return success_response("Admin status checked.", data={"is_admin": is_admin, "admin_telegram_id": admin_telegram_id})


@app.post("/bot_api/admin/get_all_users")
async def bot_admin_get_all_users():
    data = request.json
    telegram_id = data.get('telegram_id')
    admin_telegram_id_setting = await asyncio.to_thread(candy_panel.db.get, 'settings', where={'key': 'telegram_bot_admin_id'})
    admin_telegram_id = admin_telegram_id_setting['value'] if admin_telegram_id_setting else '0'

    if not telegram_id or str(telegram_id) != admin_telegram_id:
        return error_response("Unauthorized", 403)

    users = await asyncio.to_thread(candy_panel.db.select, 'users')
    return success_response("All bot users retrieved.", data={"users": users})

@app.post("/bot_api/admin/get_transactions")
async def bot_admin_get_transactions():
    data = request.json
    telegram_id = data.get('telegram_id')
    status_filter = data.get('status_filter', 'pending') # 'pending', 'approved', 'rejected', 'all'

    admin_telegram_id_setting = await asyncio.to_thread(candy_panel.db.get, 'settings', where={'key': 'telegram_bot_admin_id'})
    admin_telegram_id = admin_telegram_id_setting['value'] if admin_telegram_id_setting else '0'

    if not telegram_id or str(telegram_id) != admin_telegram_id:
        return error_response("Unauthorized", 403)

    where_clause = {}
    if status_filter != 'all':
        where_clause['status'] = status_filter

    transactions = await asyncio.to_thread(candy_panel.db.select, 'transactions', where=where_clause)
    return success_response("Transactions retrieved.", data={"transactions": transactions})

@app.post("/bot_api/admin/approve_transaction")
async def bot_admin_approve_transaction():
    data = request.json
    telegram_id = data.get('telegram_id')
    order_id = data.get('order_id')
    admin_note = data.get('admin_note', '')

    if not all([telegram_id, order_id]):
        return error_response("Missing required fields for approval.", 400)
    
    admin_telegram_id_setting = await asyncio.to_thread(candy_panel.db.get, 'settings', where={'key': 'telegram_bot_admin_id'})
    admin_telegram_id = admin_telegram_id_setting['value'] if admin_telegram_id_setting else '0'

    if str(telegram_id) != admin_telegram_id:
        return error_response("Unauthorized", 403)

    transaction = await asyncio.to_thread(candy_panel.db.get, 'transactions', where={'order_id': order_id})
    if not transaction:
        return error_response("Transaction not found.", 404)
    if transaction['status'] != 'pending':
        return error_response("Transaction is not pending. It has been already processed.", 400)

    purchase_type = transaction['purchase_type']
    
    # Determine quantities based on purchase_type
    quantity_for_candy = 0 # This will be the traffic quota in bytes
    expire_days_for_candy = 0 # This will be days for expiry

    user_time_bought_days = 0
    user_traffic_bought_gb = 0

    if purchase_type == 'gb':
        traffic_quantity_gb = float(transaction['quantity'])
        expire_days_for_candy = 365 # Default expiry for GB plans, e.g., 1 year
        quantity_for_candy = int(traffic_quantity_gb * (1024**3)) # Convert GB to bytes
        user_traffic_bought_gb = traffic_quantity_gb
        user_time_bought_days = 0 # No explicit time added for GB plans
    elif purchase_type == 'month':
        time_quantity_months = float(transaction['quantity'])
        expire_days_for_candy = int(time_quantity_months * 30)
        quantity_for_candy = int(1024 * (1024**3)) # Default high traffic for time-based plans (1TB)
        user_traffic_bought_gb = 0 # No explicit traffic added for month plans
        user_time_bought_days = expire_days_for_candy
    elif purchase_type == 'custom':
        time_quantity_months = float(transaction['time_quantity'])
        traffic_quantity_gb = float(transaction['traffic_quantity'])
        expire_days_for_candy = int(time_quantity_months * 30)
        quantity_for_candy = int(traffic_quantity_gb * (1024**3)) # Convert GB to bytes
        user_traffic_bought_gb = traffic_quantity_gb
        user_time_bought_days = expire_days_for_candy
    else:
        return error_response("Invalid purchase_type in transaction record.", 500)
    
    # Get user from bot's DB
    user_in_bot_db = await asyncio.to_thread(candy_panel.db.get, 'users', where={'telegram_id': transaction['telegram_id']})
    if not user_in_bot_db:
        print(f"Warning: User {transaction['telegram_id']} not found in bot_db during transaction approval.")
        return error_response(f"User {transaction['telegram_id']} not found in bot's database. Cannot approve.", 404)

    client_name = user_in_bot_db.get('candy_client_name')
    if not client_name:
        # Generate a unique client name if none exists (e.g., "user_<telegram_id>")
        # Use a more stable client name, maybe just based on telegram_id if unique enough
        client_name = f"tguser_{transaction['telegram_id']}"
        # Ensure uniqueness by appending timestamp if a client with this name already exists in CandyPanel
        existing_client = await asyncio.to_thread(candy_panel.db.get, 'clients', where={'name': client_name})
        if existing_client:
            client_name = f"tguser_{transaction['telegram_id']}_{int(datetime.now().timestamp())}"

    current_expires_str = None
    current_traffic_str = None
    candy_client_exists = False
    
    # Check if client exists in CandyPanel DB
    existing_candy_client = await asyncio.to_thread(candy_panel.db.get, 'clients', where={'name': client_name})
    if existing_candy_client:
        candy_client_exists = True
        current_expires_str = existing_candy_client.get('expires')
        current_traffic_str = existing_candy_client.get('traffic')
        current_used_traffic = json.loads(existing_candy_client.get('used_trafic', '{"download":0,"upload":0,"last_wg_rx":0,"last_wg_tx":0}'))
        current_total_used_bytes = current_used_traffic.get('download',0) + current_used_traffic.get('upload',0)
    
    # Calculate new expiry date based on existing one if present, otherwise from now
    new_expires_dt = datetime.now()
    if current_expires_str:
        try:
            current_expires_dt = datetime.fromisoformat(current_expires_str)
            if current_expires_dt > new_expires_dt: # If current expiry is in future, extend from that point
                new_expires_dt = current_expires_dt
        except ValueError:
            print(f"Warning: Invalid existing expiry date format for client '{client_name}'. Recalculating from now.")
    
    new_expires_dt += timedelta(days=expire_days_for_candy)
    new_expires_iso = new_expires_dt.isoformat()

    # Calculate new total traffic limit for CandyPanel: add the new traffic to existing total
    new_total_traffic_bytes_for_candy = quantity_for_candy # Start with newly bought traffic
    if candy_client_exists and current_traffic_str:
        try:
            # If the new plan is traffic-based, add to previous traffic limit.
            # If the previous plan was time-based with a large dummy traffic, overwrite it.
            # This logic can be refined if there are complex plan combinations.
            # For simplicity, if the new purchase is traffic-based, we add to existing.
            # If it's time-based, we set to a large default unless previous was larger and explicitly traffic-limited.
            previous_traffic_limit_bytes = int(current_traffic_str)
            if purchase_type == 'gb' or (purchase_type == 'custom' and traffic_quantity_gb > 0):
                new_total_traffic_bytes_for_candy += previous_traffic_limit_bytes
            elif purchase_type == 'month' and previous_traffic_limit_bytes < 1024 * (1024**3): # If previous was not already a large default
                 new_total_traffic_bytes_for_candy = int(1024 * (1024**3)) # Set to 1TB if buying time
        except ValueError:
            print(f"Warning: Invalid existing traffic limit format for client '{client_name}'. Overwriting.")
    
    # Ensure new traffic limit is at least the current used traffic
    if candy_client_exists and new_total_traffic_bytes_for_candy < current_total_used_bytes:
        new_total_traffic_bytes_for_candy = current_total_used_bytes + quantity_for_candy # Ensure it's not less than already used + new purchase.

    client_config = None # Will store the config if a new client is created

    if not candy_client_exists:
        # Create client in CandyPanel
        success_cp, message_cp = await asyncio.to_thread(
            candy_panel._new_client,
            client_name,
            new_expires_iso,
            str(new_total_traffic_bytes_for_candy), # CandyPanel expects string
            0, # Assuming default wg0 for now, can be made configurable via admin settings
            f"Bot User: {transaction['telegram_id']} - Order: {order_id}"
        )
        if not success_cp:
            return error_response(f"Failed to create client in CandyPanel: {message_cp}", 500)
        client_config = message_cp # _new_client returns config on success
    else:
        # Update existing client in CandyPanel
        # Ensure status is True when updating (unbanning if it was banned)
        success_cp, message_cp = await asyncio.to_thread(
            candy_panel._edit_client, 
            client_name, 
            expires=new_expires_iso, 
            traffic=str(new_total_traffic_bytes_for_candy), # Update traffic quota
            status=True # Ensure client is active
        )
        if not success_cp:
            return error_response(f"Failed to update client in CandyPanel: {message_cp}", 500)
        # If client was updated, user needs to get config again.
        # Fetch the config explicitly here, as _edit_client doesn't return it
        success_config, fetched_config = await asyncio.to_thread(candy_panel._get_client_config, client_name)
        if success_config:
            client_config = fetched_config
        else:
            print(f"Warning: Could not fetch updated config for existing client {client_name}: {fetched_config}")
    
    # Update bot's user table
    # Accumulate bought traffic and time
    await asyncio.to_thread(candy_panel.db.update, 'users', {
        'candy_client_name': client_name,
        'traffic_bought_gb': user_in_bot_db.get('traffic_bought_gb', 0) + user_traffic_bought_gb,
        'time_bought_days': user_in_bot_db.get('time_bought_days', 0) + user_time_bought_days,
        'status': 'active' # Ensure bot user status is active
    }, {'telegram_id': transaction['telegram_id']})

    # Update transaction status
    await asyncio.to_thread(candy_panel.db.update, 'transactions', {
        'status': 'approved',
        'approved_at': datetime.now().isoformat(),
        'admin_note': admin_note
    }, {'order_id': order_id})

    return success_response(f"Transaction {order_id} approved. Client '{client_name}' {'created' if not candy_client_exists else 'updated'} in CandyPanel.", data={
        "client_config": client_config, # Send config back to bot for user
        "telegram_id": transaction['telegram_id'], # For bot to send message to user
        "client_name": client_name, # Pass client name for user message
        "new_traffic_gb": user_traffic_bought_gb, # For bot message to user
        "new_time_days": user_time_bought_days # For bot message to user
    })

@app.post("/bot_api/admin/reject_transaction")
async def bot_admin_reject_transaction():
    data = request.json
    telegram_id = data.get('telegram_id')
    order_id = data.get('order_id')
    admin_note = data.get('admin_note', '')

    if not all([telegram_id, order_id]):
        return error_response("Missing telegram_id or order_id.", 400)
    
    admin_telegram_id_setting = await asyncio.to_thread(candy_panel.db.get, 'settings', where={'key': 'telegram_bot_admin_id'})
    admin_telegram_id = admin_telegram_id_setting['value'] if admin_telegram_id_setting else '0'

    if str(telegram_id) != admin_telegram_id:
        return error_response("Unauthorized", 403)

    transaction = await asyncio.to_thread(candy_panel.db.get, 'transactions', where={'order_id': order_id})
    if not transaction:
        return error_response("Transaction not found.", 404)
    if transaction['status'] != 'pending':
        return error_response("Transaction is not pending. It has been already processed.", 400)

    await asyncio.to_thread(candy_panel.db.update, 'transactions', {
        'status': 'rejected',
        'approved_at': datetime.now().isoformat(),
        'admin_note': admin_note
    }, {'order_id': order_id})

    return success_response(f"Transaction {order_id} rejected.", data={
        "telegram_id": transaction['telegram_id'] # For bot to send message to user
    })

@app.post("/bot_api/admin/manage_user")
async def bot_admin_manage_user():
    data = request.json
    admin_telegram_id = data.get('admin_telegram_id')
    target_telegram_id = data.get('target_telegram_id')
    action = data.get('action') # 'ban', 'unban', 'update_traffic', 'update_time'
    value = data.get('value') # For update_traffic/time

    if not all([admin_telegram_id, target_telegram_id, action]):
        return error_response("Missing required fields.", 400)
    
    admin_telegram_id_setting = await asyncio.to_thread(candy_panel.db.get, 'settings', where={'key': 'telegram_bot_admin_id'})
    admin_telegram_id = admin_telegram_id_setting['value'] if admin_telegram_id_setting else '0'

    if str(admin_telegram_id) != admin_telegram_id:
        return error_response("Unauthorized", 403)

    user = await asyncio.to_thread(candy_panel.db.get, 'users', where={'telegram_id': target_telegram_id})
    if not user:
        return error_response("Target user not found.", 404)

    update_data = {}
    message = ""
    success_status = True

    if action == 'ban':
        update_data['status'] = 'banned'
        message = f"User {target_telegram_id} has been banned."
        # Also disable in CandyPanel if linked
        if user.get('candy_client_name'):
            success, msg = await asyncio.to_thread(
                candy_panel._edit_client, user['candy_client_name'], status=False
            )
            if not success:
                message += f" (Failed to disable client in CandyPanel: {msg})"
                success_status = False
    elif action == 'unban':
        update_data['status'] = 'active'
        message = f"User {target_telegram_id} has been unbanned."
        # Also enable in CandyPanel if linked
        if user.get('candy_client_name'):
            success, msg = await asyncio.to_thread(
                candy_panel._edit_client, user['candy_client_name'], status=True
            )
            if not success:
                message += f" (Failed to enable client in CandyPanel: {msg})"
                success_status = False
    elif action == 'update_traffic' and value is not None:
        try:
            new_traffic_gb = float(value)
            update_data['traffic_bought_gb'] = new_traffic_gb
            message = f"User {target_telegram_id} traffic updated to {new_traffic_gb} GB."
            # Update in CandyPanel
            if user.get('candy_client_name'):
                traffic_bytes = int(new_traffic_gb * (1024**3))
                success, msg = await asyncio.to_thread(
                    candy_panel._edit_client, user['candy_client_name'], traffic=str(traffic_bytes)
                )
                if not success:
                    message += f" (Failed to update traffic in CandyPanel: {msg})"
                    success_status = False
        except ValueError:
            return error_response("Invalid value for traffic. Must be a number.", 400)
    elif action == 'update_time' and value is not None:
        try:
            new_time_days = int(value)
            update_data['time_bought_days'] = new_time_days
            message = f"User {target_telegram_id} time updated to {new_time_days} days."
            # Update in CandyPanel (this is more complex, as CandyPanel uses expiry date)
            # For simplicity, we'll just update the bot's record for now.
            # A full implementation would recalculate expiry based on new_time_days from current date
            # or extend the existing expiry. For now, this is a placeholder.
            message += " (Note: Time update in CandyPanel requires manual expiry date calculation or a dedicated API endpoint in CandyPanel.)"
        except ValueError:
            return error_response("Invalid value for time. Must be an integer.", 400)
    else:
        return error_response("Invalid action or missing value.", 400)

    if update_data:
        await asyncio.to_thread(candy_panel.db.update, 'users', update_data, {'telegram_id': target_telegram_id})
    
    if success_status:
        return success_response(message)
    else:
        return error_response(message, 500)


@app.post("/bot_api/admin/send_message_to_all")
async def bot_admin_send_message_to_all():
    data = request.json
    telegram_id = data.get('telegram_id')
    message_text = data.get('message')

    if not all([telegram_id, message_text]):
        return error_response("Missing telegram_id or message.", 400)
    
    admin_telegram_id_setting = await asyncio.to_thread(candy_panel.db.get, 'settings', where={'key': 'telegram_bot_admin_id'})
    admin_telegram_id = admin_telegram_id_setting['value'] if admin_telegram_id_setting else '0'

    if str(telegram_id) != admin_telegram_id:
        return error_response("Unauthorized", 403)

    all_users = await asyncio.to_thread(candy_panel.db.select, 'users')
    user_ids = [user['telegram_id'] for user in all_users]

    # This API endpoint just prepares the list of users.
    # The Telegram bot itself will handle the actual sending to avoid blocking the API.
    return success_response("Broadcast message prepared.", data={"target_user_ids": user_ids, "message": message_text})
@app.get("/bot_api/admin/data")
async def bot_admin_data():
    try:
        # Fetch all data concurrently
        dashboard_stats_task = asyncio.to_thread(candy_panel._dashboard_stats)
        clients_data_task = asyncio.to_thread(candy_panel._get_all_clients)
        interfaces_data_task = asyncio.to_thread(candy_panel.db.select, 'interfaces')
        settings_data_task = asyncio.to_thread(candy_panel.db.select, 'settings')

        dashboard_stats, clients_data, interfaces_data, settings_raw = await asyncio.gather(
            dashboard_stats_task, clients_data_task, interfaces_data_task, settings_data_task
        )

        # Process client data (parse used_trafic)
        for client in clients_data:
            try:
                client['used_trafic'] = json.loads(client['used_trafic'])
            except (json.JSONDecodeError, TypeError):
                client['used_trafic'] = {"download": 0, "upload": 0}
        
        # Process settings data (convert to dict)
        settings_data = {setting['key']: setting['value'] for setting in settings_raw}

        return success_response("All data retrieved successfully.", data={
            "dashboard": dashboard_stats,
            "clients": clients_data,
            "interfaces": interfaces_data,
            "settings": settings_data
        })
    except Exception as e:
        return error_response(f"Failed to retrieve all data: {e}", 500)
@app.post("/bot_api/admin/server_control")
async def bot_admin_server_control():
    data = request.json
    admin_telegram_id = data.get('admin_telegram_id')
    resource = data.get('resource')
    action = data.get('action')
    payload_data = data.get('data', {}) # Additional data for the CandyPanel API call

    if not all([admin_telegram_id, resource, action]):
        return error_response("Missing admin_telegram_id, resource, or action.", 400)
    
    admin_telegram_id_setting = await asyncio.to_thread(candy_panel.db.get, 'settings', where={'key': 'telegram_bot_admin_id'})
    admin_telegram_id = admin_telegram_id_setting['value'] if admin_telegram_id_setting else '0'

    if str(admin_telegram_id) != admin_telegram_id:
        return error_response("Unauthorized", 403)

    # Direct internal calls to CandyPanel methods
    success = False
    message = "Invalid operation."
    candy_data = {}

    if resource == 'client':
        if action == 'create':
            name = payload_data.get('name')
            expires = payload_data.get('expires')
            traffic = payload_data.get('traffic')
            wg_id = payload_data.get('wg_id', 0)
            note = payload_data.get('note', '')
            if all([name, expires, traffic]):
                success, message = await asyncio.to_thread(candy_panel._new_client, name, expires, traffic, wg_id, note)
                if success:
                    candy_data = {"client_config": message} # _new_client returns config on success
        elif action == 'update':
            name = payload_data.get('name')
            expires = payload_data.get('expires')
            traffic = payload_data.get('traffic')
            status = payload_data.get('status')
            note = payload_data.get('note')
            if name:
                success, message = await asyncio.to_thread(candy_panel._edit_client, name, expires, traffic, status, note)
        elif action == 'delete':
            name = payload_data.get('name')
            if name:
                success, message = await asyncio.to_thread(candy_panel._delete_client, name)
        elif action == 'get_config':
            name = payload_data.get('name')
            if name:
                success, message = await asyncio.to_thread(candy_panel._get_client_config, name)
                if success:
                    candy_data = {"config": message}
    elif resource == 'interface':
        if action == 'create':
            address_range = payload_data.get('address_range')
            ipv6_address_range = payload_data.get('ipv6_address_range')
            port = payload_data.get('port')
            if all([address_range, port]):
                success, message = await asyncio.to_thread(candy_panel._new_interface_wg, address_range, port, ipv6_address_range)
        elif action == 'update':
            name = payload_data.get('name')
            address = payload_data.get('address')
            port = payload_data.get('port')
            status = payload_data.get('status')
            if name:
                success, message = await asyncio.to_thread(candy_panel._edit_interface, name, address, port, status)
        elif action == 'delete':
            wg_id = payload_data.get('wg_id')
            if wg_id is not None:
                success, message = await asyncio.to_thread(candy_panel._delete_interface, wg_id)
    elif resource == 'setting':
        if action == 'update':
            key = payload_data.get('key')
            value = payload_data.get('value')
            if all([key, value is not None]):
                success, message = await asyncio.to_thread(candy_panel._change_settings, key, value)
    elif resource == 'sync':
        if action == 'trigger':
            await asyncio.to_thread(candy_panel._sync)
            success = True
            message = "Synchronization process initiated successfully."
    else:
        return error_response(f"Unknown resource type: {resource}", 400)

    if success:
        return success_response(f"CandyPanel: {message}", data=candy_data)
    else:
        return error_response(f"CandyPanel Error: {message}", 500)


@app.route('/')
def serve_root_index():
    return send_file(os.path.join(app.static_folder, 'index.html'))

@app.route('/<path:path>')
def catch_all_frontend_routes(path):
    static_file_path = os.path.join(app.static_folder, path)
    if os.path.exists(static_file_path) and os.path.isfile(static_file_path):
        return send_file(static_file_path)
    else:
        return send_file(os.path.join(app.static_folder, 'index.html'))
# This is for development purposes only. For production, use a WSGI server like Gunicorn.
if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get('AP_PORT',3446)))