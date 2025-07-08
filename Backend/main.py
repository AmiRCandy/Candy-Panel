# main_flask.py
from flask import Flask, request, jsonify, abort, g, send_from_directory
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
app.config['SECRET_KEY'] = 'your_super_secret_key'  # Replace with a strong, random key in production
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

# --- API Endpoints ---

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
    Handles both login and installation based on the 'action' field.
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
            wg_dns = data.get('wg_dns', "8.8.8.8")
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
            admin_password
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
    Unified endpoint for creating/updating/deleting clients, interfaces, and settings.
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
                port = data.get('port')
                if not all([address_range, port]):
                    return error_response("Missing address_range or port for interface creation", 400)
                success, message = await asyncio.to_thread(candy_panel._new_interface_wg, address_range, port)
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
