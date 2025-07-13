from flask import Flask, request, jsonify, abort, g, send_from_directory , send_file
from functools import wraps
from flask_cors import CORS
import asyncio
import json
from datetime import datetime, timedelta
import os
import uuid
# Import your CandyPanel logic
from core import CandyPanel, CommandExecutionError

# --- Initialize CandyPanel ---
# This is the central panel instance, so it uses 'CandyPanel.db'
# AP_PORT for the main Flask app, AGENT_PORT for its internal agent
candy_panel = CandyPanel(db_path='CandyPanel.db')

# --- Flask Application Setup ---
app = Flask(__name__, static_folder=os.path.join(os.getcwd(), '..', 'Frontend', 'dist'), static_url_path='/static')
app.config['SECRET_KEY'] = 'your_super_secret_key'
CORS(app)

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

# Modified: /client-details to handle multi-server by calling core.py which will search
@app.get("/client-details/<name>/<public_key>")
async def get_client_public_details(name: str, public_key: str):
    """
    Retrieves public-facing details for a specific client given its name and public key.
    This endpoint does NOT require authentication. It attempts to find the client across all servers.
    """
    try:
        # Pass server_id=None to indicate that core.py should search across all managed servers.
        # This will be handled by core._get_client_by_name_and_public_key
        client_data = await asyncio.to_thread(candy_panel._get_client_by_name_and_public_key, name, public_key, server_id=None)
        if client_data:
            return success_response("Client details retrieved successfully.", data=client_data)
        else:
            return error_response("Client not found or public key mismatch.", 404)
    except Exception as e:
        return error_response(f"An error occurred: {e}", 500)

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
    Handles both login and initial CandyPanel installation (for the central panel).
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
            server_ip = data['server_ip'] # This refers to the central panel's own IP
            wg_port = data['wg_port'] # This refers to the central panel's WireGuard interface port (if it runs WG too)
            wg_address_range = data.get('wg_address_range', "10.0.0.1/24")
            wg_dns = data.get('wg_dns', "8.8.8.8")
            admin_user = data.get('admin_user', "admin")
            admin_password = data.get('admin_password', "admin")
        except KeyError as e:
            return error_response(f"Missing required field for installation: {e}", 400)

        # Pass AP_PORT and AGENT_PORT from environment to core._install_candy_panel
        # to ensure it can set up UFW correctly and self-register with correct ports.
        os.environ['AP_PORT'] = os.environ.get('AP_PORT', '3446')
        os.environ['AGENT_PORT'] = os.environ.get('AGENT_PORT', '1212')
        os.environ['AGENT_API_KEY_CENTRAL'] = os.environ.get('AGENT_API_KEY_CENTRAL', str(uuid.uuid4())) # Ensure this is generated/available

        success, message = await candy_panel._install_candy_panel(server_ip,wg_port,wg_address_range,wg_dns,admin_user,admin_password)
        
        if not success:
            return error_response(message, 400)
        return success_response(message)
    else:
        return error_response("Invalid action specified. Must be 'login' or 'install'.", 400)

# New: Server Management Endpoints
@app.get("/api/servers")
@authenticate_admin
async def get_all_servers():
    """
    Retrieves a list of all configured remote servers.
    """
    try:
        servers = await asyncio.to_thread(candy_panel.get_all_servers)
        # It's better not to send API keys in this response.
        for server in servers:
            server.pop('api_key', None)
            # Parse dashboard_cache if it exists and is a string
            if 'dashboard_cache' in server and isinstance(server['dashboard_cache'], str):
                try:
                    server['dashboard_cache'] = json.loads(server['dashboard_cache'])
                except json.JSONDecodeError:
                    server['dashboard_cache'] = {} # Default to empty if invalid JSON
        return success_response("Servers retrieved successfully.", data={"servers": servers})
    except Exception as e:
        return error_response(f"Failed to retrieve servers: {e}", 500)

@app.post("/api/servers")
@authenticate_admin
async def add_server():
    """
    Adds a new remote server configuration to the central panel.
    """
    data = request.json
    try:
        name = data['name']
        ip_address = data['ip_address']
        agent_port = data['agent_port']
        api_key = data['api_key']
        description = data.get('description', '')
    except KeyError as e:
        return error_response(f"Missing required field: {e}", 400)

    try:
        success, message, server_id = await candy_panel.add_server( name, ip_address, int(agent_port), api_key, description)
        if success:
            return success_response(message, data={"server_id": server_id})
        return error_response(message, 400)
    except Exception as e:
        return error_response(f"Failed to add server: {e}", 500)

@app.put("/api/servers/<int:server_id>")
@authenticate_admin
async def update_server(server_id: int):
    """
    Updates an existing remote server configuration.
    """
    data = request.json
    try:
        success, message = await asyncio.to_thread(candy_panel.update_server,
                                                  server_id,
                                                  name=data.get('name'),
                                                  ip_address=data.get('ip_address'),
                                                  agent_port=data.get('agent_port'),
                                                  api_key=data.get('api_key'),
                                                  description=data.get('description'),
                                                  status=data.get('status'))
        if success:
            return success_response(message)
        return error_response(message, 400)
    except Exception as e:
        return error_response(f"Failed to update server: {e}", 500)

@app.delete("/api/servers/<int:server_id>")
@authenticate_admin
async def delete_server(server_id: int):
    """
    Deletes a remote server configuration and all its associated clients/interfaces.
    """
    try:
        success, message = await asyncio.to_thread(candy_panel.delete_server, server_id)
        if success:
            return success_response(message)
        return error_response(message, 400)
    except Exception as e:
        return error_response(f"Failed to delete server: {e}", 500)


# Modified: /api/data endpoint to fetch specific server data
@app.get("/api/data/server/<int:server_id>")
@authenticate_admin
async def get_server_data(server_id: int):
    """
    Retrieves dashboard, clients, and interfaces data for a specific server.
    Requires authentication.
    """
    try:
        # Fetch individual data types from the specified agent via core.py
        dashboard_stats_response = await candy_panel._dashboard_stats_for_server(server_id) # New helper in core to get live dashboard
        if not dashboard_stats_response.get('success'):
            return error_response(f"Failed to get dashboard stats from server {server_id}: {dashboard_stats_response.get('message', 'Unknown error')}", 500)

        clients_data = await candy_panel._get_all_clients(server_id) # Filter clients by server_id
        interfaces_data = await asyncio.to_thread(candy_panel.db.select, 'interfaces', where={'server_id': server_id}) # Filter interfaces by server_id

        # Process client data (parse used_trafic)
        for client in clients_data:
            try:
                client['used_trafic'] = json.loads(client['used_trafic'])
            except (json.JSONDecodeError, TypeError):
                client['used_trafic'] = {"download": 0, "upload": 0}

        # Get central settings (not server-specific settings)
        settings_raw = await asyncio.to_thread(candy_panel.db.select, 'settings')
        settings_data = {setting['key']: setting['value'] for setting in settings_raw}


        return success_response("Server data retrieved successfully.", data={
            "dashboard": dashboard_stats_response['data'], # Get actual data from response
            "clients": clients_data,
            "interfaces": interfaces_data,
            "settings": settings_data # Central settings, not server-specific
        })
    except Exception as e:
        return error_response(f"Failed to retrieve server data: {e}", 500)

@app.post("/api/manage")
@authenticate_admin
async def manage_resources():
    """
    Unified endpoint for creating/updating/deleting clients, interfaces, and settings on a specific server.
    Requires authentication and `server_id` in payload.
    """
    data = request.json
    if not data or 'resource' not in data or 'action' not in data or 'server_id' not in data:
        return error_response("Missing 'resource', 'action', or 'server_id' in request body", 400)

    server_id = data['server_id']
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
                success, message = await asyncio.to_thread(candy_panel._new_client, name, expires, traffic, wg_id, note, server_id=server_id)
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
                success, message = await asyncio.to_thread(candy_panel._edit_client, name, expires, traffic, status, note, server_id=server_id)
                if not success:
                    return error_response(message, 400)
                return success_response(message)

            elif action == 'delete':
                name = data.get('name')
                if not name:
                    return error_response("Missing client name for deletion", 400)
                success, message = await asyncio.to_thread(candy_panel._delete_client, name, server_id=server_id)
                if not success:
                    return error_response(message, 400)
                return success_response(message)

            elif action == 'get_config':
                name = data.get('name')
                if not name:
                    return error_response("Missing client name to get config", 400)
                success, config_content = await asyncio.to_thread(candy_panel._get_client_config, name, server_id=server_id)
                if not success:
                    return error_response(config_content, 404)
                return success_response("Client config retrieved successfully.", data={"config": config_content})
            else:
                return error_response(f"Invalid action '{action}' for client resource", 400)

        elif resource == 'interface':
            if action == 'create':
                address_range = data.get('address_range')
                port = data.get('port')
                if not all([address_range, port]):
                    return error_response("Missing address_range or port for interface creation", 400)
                success, message = await asyncio.to_thread(candy_panel._new_interface_wg, address_range, port, server_id=server_id)
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
                success, message = await asyncio.to_thread(candy_panel._edit_interface, name, address, port, status, server_id=server_id)
                if not success:
                    return error_response(message, 400)
                return success_response(message)

            elif action == 'delete':
                wg_id = data.get('wg_id')
                if wg_id is None:
                    return error_response("Missing wg_id for interface deletion", 400)
                success, message = await asyncio.to_thread(candy_panel._delete_interface, wg_id, server_id=server_id)
                if not success:
                    return error_response(message, 400)
                return success_response(message)

            else:
                return error_response(f"Invalid action '{action}' for interface resource", 400)

        elif resource == 'setting':
            # Settings here apply to the central panel's settings
            key = data.get('key')
            value = data.get('value')
            if not all([key, value is not None]):
                return error_response("Missing key or value for setting update", 400)
            if key == 'telegram_bot_status':
                if value == '1':
                    bot_control_success = await asyncio.to_thread(candy_panel._manage_telegram_bot_process, 'start')
                    if not bot_control_success:
                        print(f"Warning: Failed to start bot immediately after setting update.")
                        # This particular setting might require a different handling in a multi-server setup,
                        # if the bot itself is considered server-specific or central.
                        # For now, it manages the central panel's bot process.
                        return success_response(f"(Bot start attempted, but failed.)")
                else:
                    bot_control_success = await asyncio.to_thread(candy_panel._manage_telegram_bot_process, 'stop')
                    if not bot_control_success:
                        print(f"Warning: Failed to stop bot immediately after setting update.")
                        return success_response(f"(Bot stop attempted, but failed.)")
            success, message = await asyncio.to_thread(candy_panel._change_settings, key, value)
            if not success:
                return error_response(message, 400)
            return success_response(message)
            # NOTE: If settings need to be applied per-server, a separate API for agent settings or
            # a different structure for this endpoint would be needed.
            # Current `_change_settings` only affects central DB.

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
                # This sync action now triggers a sync on the *specified* remote server.
                await asyncio.to_thread(candy_panel._sync, server_id=server_id)
                return success_response(f"Synchronization process initiated successfully on server {server_id}.")
            else:
                return error_response(f"Invalid action '{action}' for sync resource", 400)

        else:
            return error_response(f"Unknown resource type: {resource}", 400)

    except CommandExecutionError as e:
        return error_response(f"Command execution error: {e}", 500)
    except Exception as e:
        return error_response(f"An unexpected error occurred: {e}", 500)

# --- Telegram Bot API Endpoints (Integrated) ---
# These endpoints generally operate on the central panel's DB (users, transactions)
# and delegate to CandyPanel core functions which are now multi-server aware.

@app.post("/bot_api/user/register")
async def bot_register_user():
    data = request.json
    telegram_id = data.get('telegram_id')
    if not telegram_id:
        return error_response("Missing telegram_id", 400)

    user = await asyncio.to_thread(candy_panel.db.get, 'users', where={'telegram_id': telegram_id})
    if user:
        return success_response("User already registered.", data={"registered": True, "language": user.get('language', 'en')})
    
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

    if language not in ['en', 'fa']:
        return error_response("Unsupported language. Available: 'en', 'fa'", 400)

    if not await asyncio.to_thread(candy_panel.db.has, 'users', {'telegram_id': telegram_id}):
        return error_response("User not registered with the bot.", 404)

    await asyncio.to_thread(candy_panel.db.update, 'users', {'language': language}, {'telegram_id': telegram_id})
    return success_response("Language updated successfully.")


@app.post("/bot_api/user/initiate_purchase")
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

@app.post("/bot_api/user/calculate_price")
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


@app.post("/bot_api/user/submit_transaction")
async def bot_submit_transaction():
    data = request.json
    telegram_id = data.get('telegram_id')
    order_id = data.get('order_id')
    card_number_sent = data.get('card_number_sent')
    purchase_type = data.get('purchase_type')
    amount = data.get('amount')
    quantity = data.get('quantity', 0)
    time_quantity = data.get('time_quantity', 0)
    traffic_quantity = data.get('traffic_quantity', 0)

    if not all([telegram_id, order_id, card_number_sent, purchase_type, amount is not None]):
        return error_response("Missing required transaction details.", 400)

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

    client_name = user['candy_client_name']
    
    # Try to find the client to get its server_id
    client_record = await asyncio.to_thread(candy_panel.db.get, 'clients', where={'name': client_name})
    if not client_record or 'server_id' not in client_record:
        return error_response("Associated client or server information not found.", 500)

    server_id = client_record['server_id']
    success, config_content = await asyncio.to_thread(candy_panel._get_client_config, client_name, server_id=server_id)
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
        "used_traffic_bytes": 0,
        "traffic_limit_bytes": 0,
        "expires": 'N/A',
        "note": ''
    }

    if user.get('candy_client_name'):
        client_name = user['candy_client_name']
        # Find the client's server_id first
        client_record_central = await asyncio.to_thread(candy_panel.db.get, 'clients', where={'name': client_name})

        if client_record_central and 'server_id' in client_record_central:
            server_id = client_record_central['server_id']
            # Now call _get_client_by_name_and_public_key with server_id to get live data from agent
            live_client_data = await asyncio.to_thread(candy_panel._get_client_by_name_and_public_key,
                                                        client_name,
                                                        client_record_central['public_key'], # Pass public key for lookup
                                                        server_id=server_id)
            if live_client_data:
                try:
                    used_traffic = live_client_data.get('used_trafic', '{"download":0,"upload":0}')
                    if isinstance(used_traffic, str):
                         used_traffic = json.loads(used_traffic)
                    status_info['used_traffic_bytes'] = used_traffic.get('download', 0) + used_traffic.get('upload', 0)
                except (json.JSONDecodeError, TypeError):
                    status_info['used_traffic_bytes'] = 0
                status_info['expires'] = live_client_data.get('expires')
                status_info['traffic_limit_bytes'] = int(live_client_data.get('traffic', 0))
                status_info['note'] = live_client_data.get('note', '')
            else:
                status_info['note'] = "Your VPN client configuration might be out of sync or deleted from the server. Please contact support."
        else:
            status_info['note'] = "Could not find associated client information in central panel. Please contact support."


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
    
    # New: Choose a server for the client. For simplicity, pick the first active server available.
    available_servers = await asyncio.to_thread(candy_panel.db.select, 'servers', where={'status': 'active'})
    if not available_servers:
        return error_response("No active servers available to create clients.", 500)
    
    target_server_id = available_servers[0]['server_id']
    target_server_name = available_servers[0]['name']

    current_expires_str = None
    current_traffic_str = None
    candy_client_exists = False
    
    # Check if client exists in CandyPanel DB (on the target server)
    existing_candy_client = await asyncio.to_thread(candy_panel.db.get, 'clients', where={'name': client_name, 'server_id': target_server_id})
    if existing_candy_client:
        candy_client_exists = True
        current_expires_str = existing_candy_client.get('expires')
        current_traffic_str = existing_candy_client.get('traffic')
        current_used_traffic = json.loads(existing_candy_client.get('used_trafic', '{"download":0,"upload":0,"last_wg_rx":0,"last_wg_tx":0}'))
        current_total_used_bytes = current_used_traffic.get('download',0) + current_used_traffic.get('upload',0)
    else:
        if not client_name:
             client_name = f"tguser_{transaction['telegram_id']}"
             if await asyncio.to_thread(candy_panel.db.has, 'clients', {'name': client_name, 'server_id': target_server_id}):
                 client_name = f"tguser_{transaction['telegram_id']}_{int(datetime.now().timestamp())}"

    new_expires_dt = datetime.now()
    if current_expires_str:
        try:
            current_expires_dt = datetime.fromisoformat(current_expires_str)
            if current_expires_dt > new_expires_dt:
                new_expires_dt = current_expires_dt
        except ValueError:
            print(f"Warning: Invalid existing expiry date format for client '{client_name}'. Recalculating from now.")
    
    new_expires_dt += timedelta(days=expire_days_for_candy)
    new_expires_iso = new_expires_dt.isoformat()

    new_total_traffic_bytes_for_candy = quantity_for_candy
    if candy_client_exists and current_traffic_str:
        try:
            previous_traffic_limit_bytes = int(current_traffic_str)
            if purchase_type == 'gb' or (purchase_type == 'custom' and traffic_quantity_gb > 0):
                new_total_traffic_bytes_for_candy += previous_traffic_limit_bytes
            elif purchase_type == 'month' and previous_traffic_limit_bytes < 1024 * (1024**3):
                 new_total_traffic_bytes_for_candy = int(1024 * (1024**3))
        except ValueError:
            print(f"Warning: Invalid existing traffic limit format for client '{client_name}'. Overwriting.")
    
    if candy_client_exists and new_total_traffic_bytes_for_candy < current_total_used_bytes:
        new_total_traffic_bytes_for_candy = current_total_used_bytes + quantity_for_candy

    client_config = None

    if not candy_client_exists:
        success_cp, message_cp = await asyncio.to_thread(
            candy_panel._new_client,
            client_name,
            new_expires_iso,
            str(new_total_traffic_bytes_for_candy),
            0,
            f"Bot User: {transaction['telegram_id']} - Order: {order_id}",
            server_id=target_server_id
        )
        if not success_cp:
            return error_response(f"Failed to create client on server {target_server_name}: {message_cp}", 500)
        client_config = message_cp
    else:
        success_cp, message_cp = await asyncio.to_thread(
            candy_panel._edit_client,
            client_name,
            expires=new_expires_iso,
            traffic=str(new_total_traffic_bytes_for_candy),
            status=True,
            server_id=target_server_id
        )
        if not success_cp:
            return error_response(f"Failed to update client on server {target_server_name}: {message_cp}", 500)
        success_config, fetched_config = await asyncio.to_thread(
            candy_panel._get_client_config, client_name, server_id=target_server_id
        )
        if success_config:
            client_config = fetched_config
        else:
            print(f"Warning: Could not fetch updated config for existing client {client_name} on server {target_server_id}: {fetched_config}")
    
    user_update_data = {
        'traffic_bought_gb': user_in_bot_db.get('traffic_bought_gb', 0) + user_traffic_bought_gb,
        'time_bought_days': user_in_bot_db.get('time_bought_days', 0) + user_time_bought_days,
        'status': 'active'
    }
    if user_in_bot_db.get('candy_client_name') != client_name:
        user_update_data['candy_client_name'] = client_name
    
    await asyncio.to_thread(candy_panel.db.update, 'users', user_update_data, {'telegram_id': transaction['telegram_id']})

    await asyncio.to_thread(candy_panel.db.update, 'transactions', {
        'status': 'approved',
        'approved_at': datetime.now().isoformat(),
        'admin_note': admin_note
    }, {'order_id': order_id})

    return success_response(f"Transaction {order_id} approved. Client '{client_name}' {'created' if not candy_client_exists else 'updated'} on server {target_server_name}.", data={
        "client_config": client_config,
        "telegram_id": transaction['telegram_id'],
        "client_name": client_name,
        "new_traffic_gb": user_traffic_bought_gb,
        "new_time_days": user_time_bought_days
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
        "telegram_id": transaction['telegram_id']
    })

@app.post("/bot_api/admin/manage_user")
async def bot_admin_manage_user():
    data = request.json
    admin_telegram_id = data.get('admin_telegram_id')
    target_telegram_id = data.get('target_telegram_id')
    action = data.get('action')
    value = data.get('value')

    if not all([admin_telegram_id, target_telegram_id, action]):
        return error_response("Missing required fields.", 400)
    
    admin_telegram_id_setting = await asyncio.to_thread(candy_panel.db.get, 'settings', where={'key': 'telegram_bot_admin_id'})
    admin_telegram_id = admin_telegram_id_setting['value'] if admin_telegram_id_setting else '0'

    if str(admin_telegram_id) != admin_telegram_id:
        return error_response("Unauthorized", 403)

    user = await asyncio.to_thread(candy_panel.db.get, 'users', where={'telegram_id': target_telegram_id})
    if not user:
        return error_response("Target user not found.", 404)

    client_name = user.get('candy_client_name')
    target_server_id = None
    if client_name:
        client_record = await asyncio.to_thread(candy_panel.db.get, 'clients', where={'name': client_name})
        if client_record and 'server_id' in client_record:
            target_server_id = client_record['server_id']

    update_data = {}
    message = ""
    success_status = True

    if action == 'ban':
        update_data['status'] = 'banned'
        message = f"User {target_telegram_id} has been banned."
        if client_name and target_server_id is not None:
            success, msg = await asyncio.to_thread(
                candy_panel._edit_client, client_name, status=False, server_id=target_server_id
            )
            if not success:
                message += f" (Failed to disable client on server {target_server_id}: {msg})"
                success_status = False
    elif action == 'unban':
        update_data['status'] = 'active'
        message = f"User {target_telegram_id} has been unbanned."
        if client_name and target_server_id is not None:
            success, msg = await asyncio.to_thread(
                candy_panel._edit_client, client_name, status=True, server_id=target_server_id
            )
            if not success:
                message += f" (Failed to enable client on server {target_server_id}: {msg})"
                success_status = False
    elif action == 'update_traffic' and value is not None:
        try:
            new_traffic_gb = float(value)
            update_data['traffic_bought_gb'] = new_traffic_gb
            message = f"User {target_telegram_id} traffic updated to {new_traffic_gb} GB."
            if client_name and target_server_id is not None:
                traffic_bytes = int(new_traffic_gb * (1024**3))
                success, msg = await asyncio.to_thread(
                    candy_panel._edit_client, client_name, traffic=str(traffic_bytes), server_id=target_server_id
                )
                if not success:
                    message += f" (Failed to update traffic on server {target_server_id}: {msg})"
                    success_status = False
        except ValueError:
            return error_response("Invalid value for traffic. Must be a number.", 400)
    elif action == 'update_time' and value is not None:
        try:
            new_time_days = int(value)
            update_data['time_bought_days'] = new_time_days
            message = f"User {target_telegram_id} time updated to {new_time_days} days."
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

    return success_response("Broadcast message prepared.", data={"target_user_ids": user_ids, "message": message_text})

@app.get("/bot_api/admin/data")
async def bot_admin_data():
    """
    This endpoint retrieves aggregated data for the admin bot.
    It will iterate through all managed servers and fetch their data.
    """
    try:
        all_servers = await asyncio.to_thread(candy_panel.get_all_servers)
        
        # Initialize aggregated dashboard stats (or pick one if only one server exists)
        dashboard_stats = {
            'cpu': 'N/A', 'mem': {'total': 'N/A', 'available': 'N/A', 'usage': 'N/A'},
            'clients_count': 0, 'status': 'N/A', 'alert': [], 'bandwidth': '0', 'uptime': 'N/A',
            'net': {'download': 'N/A', 'upload': 'N/A'}
        }
        total_clients_count = 0
        total_download_speed = 0.0 # in KB/s
        total_upload_speed = 0.0 # in KB/s
        overall_status_list = []
        overall_alerts = []

        if not all_servers:
            return success_response("No servers managed.", data={"dashboard": dashboard_stats, "clients": [], "interfaces": [], "settings": {}})

        # Aggregate data from all active servers
        # Note: This is a simplified aggregation. For a real production system,
        # you might want more sophisticated aggregation logic or a dedicated dashboard server.
        for server in all_servers:
            server_id = server['server_id']
            # Get cached dashboard stats first
            cached_dashboard_str = server.get('dashboard_cache', '{}')
            cached_dashboard = {}
            try:
                cached_dashboard = json.loads(cached_dashboard_str)
            except json.JSONDecodeError:
                print(f"Warning: Invalid JSON in dashboard_cache for server {server_id}.")

            if cached_dashboard:
                if 'clients_count' in cached_dashboard:
                    total_clients_count += int(cached_dashboard['clients_count'])
                if 'net' in cached_dashboard:
                    # Parse speeds and sum them up
                    try:
                        dl_speed = float(cached_dashboard['net']['download'].replace(' KB/s', ''))
                        ul_speed = float(cached_dashboard['net']['upload'].replace(' KB/s', ''))
                        total_download_speed += dl_speed
                        total_upload_speed += ul_speed
                    except ValueError:
                        pass # Ignore if speed format is unexpected

                overall_status_list.append(cached_dashboard.get('status', 'Unknown'))
                if cached_dashboard.get('alert'):
                    try:
                        alerts_from_server = json.loads(cached_dashboard['alert'])
                        overall_alerts.extend(alerts_from_server)
                    except (json.JSONDecodeError, TypeError):
                         overall_alerts.append(str(cached_dashboard['alert']))


            # Live data for first active server to represent overall
            if server['status'] == 'active' and 'cpu' == 'N/A': # Only use first active server for CPU/Mem/Uptime etc.
                dashboard_stats['cpu'] = cached_dashboard.get('cpu', 'N/A')
                dashboard_stats['mem'] = cached_dashboard.get('mem', {'total': 'N/A', 'available': 'N/A', 'usage': 'N/A'})
                dashboard_stats['uptime'] = cached_dashboard.get('uptime', 'N/A')


        dashboard_stats['clients_count'] = total_clients_count
        dashboard_stats['net']['download'] = f"{total_download_speed:.2f} KB/s"
        dashboard_stats['net']['upload'] = f"{total_upload_speed:.2f} KB/s"
        
        # Determine overall status (e.g., if any server is 'error' or 'unreachable', show that)
        if 'unreachable' in overall_status_list:
            dashboard_stats['status'] = 'Partially Unreachable'
        elif 'error' in overall_status_list:
            dashboard_stats['status'] = 'Partially Errored'
        elif all(s == 'active' for s in overall_status_list if s != 'N/A'):
            dashboard_stats['status'] = 'All Active'
        else:
            dashboard_stats['status'] = 'Mixed Status'
        
        dashboard_stats['alert'] = list(set(overall_alerts)) # Remove duplicates

        # For clients and interfaces, fetch all from central DB (which are linked to servers)
        clients_data = await asyncio.to_thread(candy_panel.db.select, 'clients')
        interfaces_data = await asyncio.to_thread(candy_panel.db.select, 'interfaces')

        for client in clients_data:
            try:
                client['used_trafic'] = json.loads(client['used_trafic'])
            except (json.JSONDecodeError, TypeError):
                client['used_trafic'] = {"download": 0, "upload": 0}

        # Central settings
        settings_raw = await asyncio.to_thread(candy_panel.db.select, 'settings')
        settings_data = {setting['key']: setting['value'] for setting in settings_raw}


        return success_response("All aggregated data retrieved successfully.", data={
            "dashboard": dashboard_stats,
            "clients": clients_data,
            "interfaces": interfaces_data,
            "settings": settings_data
        })
    except Exception as e:
        return error_response(f"Failed to retrieve aggregated data: {e}", 500)

@app.post("/bot_api/admin/server_control")
async def bot_admin_server_control():
    data = request.json
    admin_telegram_id = data.get('admin_telegram_id')
    resource = data.get('resource')
    action = data.get('action')
    payload_data = data.get('data', {})

    if not all([admin_telegram_id, resource, action]):
        return error_response("Missing admin_telegram_id, resource, or action.", 400)
    
    admin_telegram_id_setting = await asyncio.to_thread(candy_panel.db.get, 'settings', where={'key': 'telegram_bot_admin_id'})
    admin_telegram_id = admin_telegram_id_setting['value'] if admin_telegram_id_setting else '0'

    if str(admin_telegram_id) != admin_telegram_id:
        return error_response("Unauthorized", 403)

    success = False
    message = "Invalid operation."
    candy_data = {}

    target_server_id = payload_data.get('server_id')
    if resource in ['client', 'interface', 'sync'] and target_server_id is None:
        return error_response(f"Missing 'server_id' in data for {resource} {action} operation.", 400)


    if resource == 'client':
        if action == 'create':
            name = payload_data.get('name')
            expires = payload_data.get('expires')
            traffic = payload_data.get('traffic')
            wg_id = payload_data.get('wg_id', 0)
            note = payload_data.get('note', '')
            if all([name, expires, traffic]):
                success, message = await asyncio.to_thread(candy_panel._new_client, name, expires, traffic, wg_id, note, server_id=target_server_id)
                if success:
                    candy_data = {"client_config": message}
        elif action == 'update':
            name = payload_data.get('name')
            expires = payload_data.get('expires')
            traffic = payload_data.get('traffic')
            status = payload_data.get('status')
            note = payload_data.get('note')
            if name:
                success, message = await asyncio.to_thread(candy_panel._edit_client, name, expires, traffic, status, note, server_id=target_server_id)
        elif action == 'delete':
            name = payload_data.get('name')
            if name:
                success, message = await asyncio.to_thread(candy_panel._delete_client, name, server_id=target_server_id)
        elif action == 'get_config':
            name = payload_data.get('name')
            if name:
                success, message = await asyncio.to_thread(candy_panel._get_client_config, name, server_id=target_server_id)
                if success:
                    candy_data = {"config": message}
    elif resource == 'interface':
        if action == 'create':
            address_range = payload_data.get('address_range')
            port = payload_data.get('port')
            if all([address_range, port]):
                success, message = await asyncio.to_thread(candy_panel._new_interface_wg, address_range, port, server_id=target_server_id)
                if success: # message here is json string
                     interface_details = json.loads(message)
                     candy_data = {"wg_id": interface_details["wg_id"], "private_key": interface_details["private_key"], "public_key": interface_details["public_key"]}
                     message = interface_details.get("message", "Interface created.")
        elif action == 'update':
            name = payload_data.get('name')
            address = payload_data.get('address')
            port = payload_data.get('port')
            status = payload_data.get('status')
            if name:
                success, message = await asyncio.to_thread(candy_panel._edit_interface, name, address, port, status, server_id=target_server_id)
        elif action == 'delete':
            wg_id = payload_data.get('wg_id')
            if wg_id is not None:
                success, message = await asyncio.to_thread(candy_panel._delete_interface, wg_id, server_id=target_server_id)
    elif resource == 'setting':
        # These are central panel settings, not server-specific settings via agent
        if action == 'update':
            key = payload_data.get('key')
            value = payload_data.get('value')
            if all([key, value is not None]):
                success, message = await asyncio.to_thread(candy_panel._change_settings, key, value)
    elif resource == 'sync':
        if action == 'trigger':
            await asyncio.to_thread(candy_panel._sync, server_id=target_server_id)
            success = True
            message = "Synchronization process initiated successfully."
    elif resource == 'server': # New resource for managing servers via bot (admin only)
        if action == 'add':
            name = payload_data.get('name')
            ip_address = payload_data.get('ip_address')
            agent_port = payload_data.get('agent_port')
            api_key = payload_data.get('api_key')
            description = payload_data.get('description', '')
            if all([name, ip_address, agent_port, api_key]):
                success, message, server_id = await asyncio.to_thread(candy_panel.add_server, name, ip_address, int(agent_port), api_key, description)
                if success:
                    candy_data = {"server_id": server_id}
        elif action == 'update':
            server_id_to_update = payload_data.get('server_id')
            if server_id_to_update is not None:
                success, message = await asyncio.to_thread(candy_panel.update_server,
                                                            server_id_to_update,
                                                            name=payload_data.get('name'),
                                                            ip_address=payload_data.get('ip_address'),
                                                            agent_port=payload_data.get('agent_port'),
                                                            api_key=payload_data.get('api_key'),
                                                            description=payload_data.get('description'),
                                                            status=payload_data.get('status'))
        elif action == 'delete':
            server_id_to_delete = payload_data.get('server_id')
            if server_id_to_delete is not None:
                success, message = await asyncio.to_thread(candy_panel.delete_server, server_id_to_delete)
        elif action == 'get_all':
            servers = await asyncio.to_thread(candy_panel.get_all_servers)
            for s in servers:
                s.pop('api_key', None) # Don't expose API keys
                if 'dashboard_cache' in s and isinstance(s['dashboard_cache'], str):
                    try: s['dashboard_cache'] = json.loads(s['dashboard_cache'])
                    except json.JSONDecodeError: s['dashboard_cache'] = {}
            success = True
            message = "Servers retrieved."
            candy_data = {"servers": servers}

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