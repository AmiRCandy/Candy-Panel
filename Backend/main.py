# main_flask.py
from flask import Flask, request, jsonify, abort, g , send_from_directory
from functools import wraps
from flask_cors import CORS
import asyncio
import json
from datetime import datetime
import os

# Import your CandyPanel logic
from core import CandyPanel, CommandExecutionError

# --- Initialize CandyPanel ---
candy_panel = CandyPanel()

# --- Flask Application Setup ---
app = Flask(__name__, static_folder=os.path.join(os.getcwd(), '..', 'Frontend', 'dist'), static_url_path='/')
app.config['SECRET_KEY'] = 'your_super_secret_key' # Replace with a strong, random key in production
CORS(app)
# --- Authentication Decorator ---
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
        settings = await asyncio.to_thread(candy_panel.db.get, 'settings', where={'key': 'session_token'})
        if not settings or settings['value'] != token:
            abort(401, description="Invalid authentication credentials")

        return await f(*args, **kwargs)
    return decorated_function

# --- Helper for common responses ---
def success_response(message: str, data = None, status_code: int = 200):
    return jsonify({"message": message, "success": True, "data": data}), status_code

def error_response(message: str, status_code: int = 400):
    return jsonify({"message": message, "success": False}), status_code

# --- API Endpoints ---

@app.post("/api/login")
async def login():
    """
    Authenticates an admin user and returns a session token.
    """
    typeofcheck = await asyncio.to_thread(candy_panel.db.get, 'settings', '*', {'key': 'install'})
    if bool(typeofcheck['value']):
        # If already installed, expect login credentials
        data = request.json
        if not data or 'username' not in data or 'password' not in data:
            return error_response("Missing username or password", 400)

        success, message = await asyncio.to_thread(candy_panel._admin_login, data['username'], data['password'])
        if not success:
            return error_response(message, 401)
        return success_response("Login successful!", data={"access_token": message, "token_type": "bearer"})
    else:
        # If not installed, indicate installation is needed
        return jsonify({"type": "install"})


@app.post("/api/install")
async def install_candypanel():
    """
    Performs the initial installation of WireGuard and CandyPanel configuration.
    This endpoint should ideally be run only once.
    """
    data = request.json
    if not data:
        return error_response("Missing installation data", 400)

    try:
        server_ip = data['server_ip']
        wg_port = data['wg_port']
        wg_address_range = data.get('wg_address_range', "10.0.0.1/24")
        wg_dns = data.get('wg_dns', "8.8.8.8")
        admin_user = data.get('admin_user', "admin")
        admin_password = data.get('admin_password', "admin")
    except KeyError as e:
        return error_response(f"Missing required field: {e}", 400)

    success, message = await asyncio.to_thread(
        candy_panel._install_candy_panel,
        server_ip,
        wg_port,
        wg_address_range,
        wg_dns,
        admin_user,
        admin_password
    )
    if not success:
        return error_response(message, 400)
    return success_response(message)

@app.get("/api/dashboard")
@authenticate_admin
async def get_dashboard_stats():
    """
    Retrieves system and application statistics for the dashboard.
    Requires authentication.
    """
    stats = await asyncio.to_thread(candy_panel._dashboard_stats)
    return jsonify(stats)

@app.post("/api/sync")
@authenticate_admin
async def trigger_sync():
    """
    Manually triggers the CandyPanel synchronization process.
    This process updates traffic, checks expirations, and performs backups.
    Requires authentication.
    """
    try:
        await asyncio.to_thread(candy_panel._sync)
        return success_response("Synchronization process initiated successfully.")
    except Exception as e:
        return error_response(f"Synchronization failed: {e}", 500)

# --- Client Management ---

@app.get("/api/clients")
@authenticate_admin
async def get_all_clients():
    """
    Retrieves a list of all WireGuard clients.
    Requires authentication.
    """
    clients_data = await asyncio.to_thread(candy_panel._get_all_clients)
    # Manually parse 'used_trafic' and prepare response
    for client in clients_data:
        try:
            client['used_trafic'] = json.loads(client['used_trafic'])
        except (json.JSONDecodeError, TypeError):
            client['used_trafic'] = {"download": 0, "upload": 0}
    return jsonify(clients_data)

@app.post("/api/clients")
@authenticate_admin
async def create_new_client():
    """
    Creates a new WireGuard client.
    Requires authentication.
    """
    data = request.json
    if not data:
        return error_response("Missing client data", 400)

    try:
        name = data['name']
        expires = data['expires']
        traffic = data['traffic']
        wg_id = data.get('wg_id', 0)
        note = data.get('note', '')
    except KeyError as e:
        return error_response(f"Missing required field: {e}", 400)

    success, message = await asyncio.to_thread(
        candy_panel._new_client,
        name,
        expires,
        traffic,
        wg_id,
        note
    )
    if not success:
        return error_response(message, 400)
    return success_response("Client created successfully!", data={"client_config": message})

@app.get("/api/clients/<string:client_name>")
@authenticate_admin
async def get_client_by_name(client_name: str):
    """
    Retrieves details of a specific client by name.
    Requires authentication.
    """
    client_data = await asyncio.to_thread(candy_panel.db.get, 'clients', where={'name': client_name})
    if not client_data:
        return error_response(f"Client '{client_name}' not found.", 404)
    try:
        client_data['used_trafic'] = json.loads(client_data['used_trafic'])
    except (json.JSONDecodeError, TypeError):
        client_data['used_trafic'] = {"download": 0, "upload": 0}
    return jsonify(client_data)

@app.put("/api/clients/<string:client_name>")
@authenticate_admin
async def update_client_details(client_name: str):
    """
    Updates details for an existing WireGuard client.
    Requires authentication.
    """
    data = request.json
    if not data:
        return error_response("Missing update data", 400)

    expires = data.get('expires')
    traffic = data.get('traffic')
    status = data.get('status')
    note = data.get('note')

    success, message = await asyncio.to_thread(
        candy_panel._edit_client,
        client_name,
        expires,
        traffic,
        status,
        note
    )
    if not success:
        return error_response(message, 400)
    return success_response(message)

@app.delete("/api/clients/<string:client_name>")
@authenticate_admin
async def delete_client(client_name: str):
    """
    Deletes a WireGuard client.
    Requires authentication.
    """
    success, message = await asyncio.to_thread(candy_panel._delete_client, client_name)
    if not success:
        return error_response(message, 400)
    return success_response(message)

@app.get("/api/clients/<string:client_name>/config")
@authenticate_admin
async def get_client_config(client_name: str):
    """
    Retrieves the WireGuard client configuration file content for a specific client.
    Requires authentication.
    """
    success, config_content = await asyncio.to_thread(candy_panel._get_client_config, client_name)
    if not success:
        return error_response(config_content, 404)
    return success_response("Client config retrieved successfully.", data={"config": config_content})

# --- Interface Management ---

@app.get("/api/interfaces")
@authenticate_admin
async def get_all_interfaces():
    """
    Retrieves a list of all WireGuard interfaces.
    Requires authentication.
    """
    interfaces_data = await asyncio.to_thread(candy_panel.db.select, 'interfaces')
    return jsonify(interfaces_data)

@app.post("/api/interfaces")
@authenticate_admin
async def create_new_interface():
    """
    Creates a new WireGuard interface.
    Requires authentication.
    """
    data = request.json
    if not data:
        return error_response("Missing interface data", 400)
    try:
        address_range = data['address_range']
        port = data['port']
    except KeyError as e:
        return error_response(f"Missing required field: {e}", 400)

    success, message = await asyncio.to_thread(
        candy_panel._new_interface_wg,
        address_range,
        port
    )
    if not success:
        return error_response(message, 400)
    return success_response(message)

@app.put("/api/interfaces/<string:interface_name>")
@authenticate_admin
async def update_interface_details(interface_name: str):
    """
    Updates details for an existing WireGuard interface (e.g., 'wg0').
    Requires authentication.
    """
    data = request.json
    if not data:
        return error_response("Missing update data", 400)

    address = data.get('address')
    port = data.get('port')
    status = data.get('status')

    success, message = await asyncio.to_thread(
        candy_panel._edit_interface,
        interface_name,
        address,
        port,
        status
    )
    if not success:
        return error_response(message, 400)
    return success_response(message)

# --- Settings Management ---

@app.get("/api/settings")
@authenticate_admin
async def get_all_settings():
    """
    Retrieves all application settings.
    Requires authentication.
    """
    settings_data = await asyncio.to_thread(candy_panel.db.select, 'settings')
    # Convert list of dicts to a single dict for easier consumption
    return jsonify({setting['key']: setting['value'] for setting in settings_data})

@app.put("/api/settings/<string:key>")
@authenticate_admin
async def update_setting(key: str):
    """
    Updates a specific application setting by its key.
    Requires authentication.
    """
    data = request.json
    if not data or 'value' not in data:
        return error_response("Missing 'value' in request body", 400)

    value = data['value']
    success, message = await asyncio.to_thread(candy_panel._change_settings, key, value)
    if not success:
        return error_response(message, 400)
    return success_response(message)

# --- API Token Management ---

@app.post("/api/api-tokens")
@authenticate_admin
async def create_or_update_api_token():
    """
    Creates a new API token or updates an existing one.
    Requires authentication.
    """
    data = request.json
    if not data or 'name' not in data or 'token' not in data:
        return error_response("Missing 'name' or 'token' in request body", 400)

    name = data['name']
    token = data['token']
    success, message = await asyncio.to_thread(candy_panel._add_api_token, name, token)
    if not success:
        return error_response(message, 400)
    return success_response(message)

@app.delete("/api/api-tokens/<string:name>")
@authenticate_admin
async def delete_api_token(name: str):
    """
    Deletes an API token by its name.
    Requires authentication.
    """
    success, message = await asyncio.to_thread(candy_panel._delete_api_token, name)
    if not success:
        return error_response(message, 400)
    return success_response(message)

@app.get("/api/api-tokens/<string:name>")
@authenticate_admin
async def get_api_token(name: str):
    """
    Retrieves a specific API token by its name.
    Requires authentication.
    """
    success, token_value = await asyncio.to_thread(candy_panel._get_api_token, name)
    if not success:
        return error_response(token_value, 404)
    return success_response("API token retrieved.", data={"token": token_value})
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')
# This is for development purposes only. For production, use a WSGI server like Gunicorn.
if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=3446)
