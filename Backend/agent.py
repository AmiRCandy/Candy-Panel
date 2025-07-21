# Candy-Panel/Agent/agent.py
from flask import Flask, request, jsonify, abort
from functools import wraps
import os , json
import sys
import asyncio

try:
    from core import CandyPanel, CommandExecutionError
    from db import SQLite
except ImportError as e:
    print(f"Error importing core modules: {e}")
    print("Please ensure 'core.py' and 'db.py' are accessible in the agent's environment.")
    sys.exit(1)


app = Flask(__name__)

agent_candy_panel = CandyPanel(db_path='CandyPanel.db')
AGENT_API_KEY = os.environ.get("AGENT_API_KEY", "DEBUG_AGENT_API_KEY_CHANGE_ME")

def authenticate_agent(f):
    """
    Decorator to authenticate incoming requests to the agent API using a shared API key.
    """
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key != AGENT_API_KEY:
            # For security, avoid giving too much detail on why authentication failed.
            abort(401, description="Unauthorized: Invalid Agent API Key")
        return await f(*args, **kwargs)
    return decorated_function

# Helper for common responses (similar to main.py)
def success_response(message: str, data=None, status_code: int = 200):
    return jsonify({"message": message, "success": True, "data": json.dumps(data)}), status_code

def error_response(message: str, status_code: int = 400):
    return jsonify({"message": message, "success": False}), status_code

# --- Agent Endpoints ---
# These endpoints wrap the local core.py functions, executing them on the agent's machine.

@app.post("/agent_api/dashboard")
@authenticate_agent
async def agent_get_dashboard_stats():
    """
    Retrieves local dashboard statistics for this WireGuard server.
    """
    try:
        # Calls the local CandyPanel instance's _dashboard_stats method
        stats = await asyncio.to_thread(agent_candy_panel._dashboard_stats)
        return success_response("Dashboard stats retrieved.", data=stats)
    except Exception as e:
        return error_response(f"Failed to get local dashboard stats: {e}", 500)

@app.post("/agent_api/client/create")
@authenticate_agent
async def agent_create_client():
    """
    Creates a new WireGuard client on this server.
    """
    data = request.json
    name = data.get('name')
    expires = data.get('expires')
    traffic = data.get('traffic')
    wg_id = data.get('wg_id', 0) # Default to wg0 if not specified
    note = data.get('note', '')

    if not all([name, expires, traffic]):
        return error_response("Missing required fields (name, expires, traffic) for client creation.", 400)

    try:
        # Calls the local CandyPanel instance's _new_client method
        success, config_or_message = await asyncio.to_thread(agent_candy_panel._new_client, name, expires, traffic, wg_id, note)
        if success:
            # Need to return public_key, private_key, address for central panel to store
            client_details = await asyncio.to_thread(agent_candy_panel.db.get, 'clients', {'name': name})
            if client_details:
               #return success_response("Client created locally.", data={
               #    "client_config": config_or_message,
               #    "public_key": client_details['public_key'],
               #    "private_key": client_details['private_key'],
               #    "address": client_details['address']
               #})
               return {
                  "client_config": config_or_message,
                   "public_key": client_details['public_key'],
                   "private_key": client_details['private_key'],
                   "address": client_details['address']
               }
            else:
                return error_response("Client created but details not found in local DB.", 500)
        return error_response(config_or_message, 400)
    except CommandExecutionError as e:
        return error_response(f"Agent failed to create client (command error): {e}", 500)
    except Exception as e:
        return error_response(f"Agent failed to create client: {e}", 500)

@app.post("/agent_api/client/update")
@authenticate_agent
async def agent_update_client():
    """
    Updates an existing WireGuard client on this server.
    """
    data = request.json
    name = data.get('name')
    expires = data.get('expires')
    traffic = data.get('traffic')
    status = data.get('status') # boolean
    note = data.get('note')

    if not name:
        return error_response("Missing client name for update.", 400)

    try:
        success, message = await asyncio.to_thread(agent_candy_panel._edit_client, name, expires, traffic, status, note)
        if success:
            return success_response(message)
        return error_response(message, 400)
    except CommandExecutionError as e:
        return error_response(f"Agent failed to update client (command error): {e}", 500)
    except Exception as e:
        return error_response(f"Agent failed to update client: {e}", 500)

@app.post("/agent_api/client/delete")
@authenticate_agent
async def agent_delete_client():
    """
    Deletes a WireGuard client from this server.
    """
    data = request.json
    name = data.get('name')

    if not name:
        return error_response("Missing client name for deletion.", 400)

    try:
        success, message = await asyncio.to_thread(agent_candy_panel._delete_client, name)
        if success:
            return success_response(message)
        return error_response(message, 400)
    except CommandExecutionError as e:
        return error_response(f"Agent failed to delete client (command error): {e}", 500)
    except Exception as e:
        return error_response(f"Agent failed to delete client: {e}", 500)

@app.post("/agent_api/client/get_config")
@authenticate_agent
async def agent_get_client_config():
    """
    Retrieves WireGuard configuration for a specific client on this server.
    """
    data = request.json
    name = data.get('name')

    if not name:
        return error_response("Missing client name to get config.", 400)

    try:
        success, config_content = await asyncio.to_thread(agent_candy_panel._get_client_config, name)
        if success:
            return success_response("Client config retrieved.", data={"config": config_content})
        return error_response(config_content, 404)
    except Exception as e:
        return error_response(f"Agent failed to get client config: {e}", 500)

@app.post("/agent_api/interface/create")
@authenticate_agent
async def agent_create_interface():
    """
    Creates a new WireGuard interface on this server.
    Modifies response to return wg_id, private_key, public_key.
    """
    data = request.json
    address_range = data.get('address_range')
    port = data.get('port')
    server_id = data.get('server_id')
    if not all([address_range, port]):
        return error_response("Missing address_range or port for interface creation.", 400)

    try:
        # The _new_interface_wg function in core.py (when called locally by agent)
        # now returns a JSON string with the new interface details.
        success, message_json_str = await asyncio.to_thread(agent_candy_panel._new_interface_wg, address_range, port,server_id)
        if success:
            # Parse the JSON string returned by _new_interface_wg
            interface_details = json.loads(message_json_str)
            return success_response(
                interface_details.get("message", "New Interface Created!"),
                data={
                    "wg_id": interface_details["wg_id"],
                    "private_key": interface_details["private_key"],
                    "public_key": interface_details["public_key"],
                    "server_id":server_id
                }
            )
        return error_response(message_json_str, 400) # message_json_str here would be an error string if not success
    except CommandExecutionError as e:
        return error_response(f"Agent failed to create interface (command error): {e}", 500)
    except Exception as e:
        return error_response(f"Agent failed to create interface: {e}", 500)


@app.post("/agent_api/interface/update")
@authenticate_agent
async def agent_update_interface():
    """
    Updates an existing WireGuard interface on this server.
    """
    data = request.json
    name = data.get('name') # e.g., 'wg0'
    address = data.get('address')
    port = data.get('port')
    status = data.get('status') # boolean

    if not name:
        return error_response("Missing interface name for update.", 400)

    try:
        success, message = await asyncio.to_thread(agent_candy_panel._edit_interface, name, address, port, status)
        if success:
            return success_response(message)
        return error_response(message, 400)
    except CommandExecutionError as e:
        return error_response(f"Agent failed to update interface (command error): {e}", 500)
    except Exception as e:
        return error_response(f"Agent failed to update interface: {e}", 500)

@app.post("/agent_api/interface/delete")
@authenticate_agent
async def agent_delete_interface():
    """
    Deletes a WireGuard interface from this server.
    """
    data = request.json
    wg_id = data.get('wg_id')

    if wg_id is None:
        return error_response("Missing wg_id for interface deletion.", 400)

    try:
        success, message = await asyncio.to_thread(agent_candy_panel._delete_interface, wg_id)
        if success:
            return success_response(message)
        return error_response(message, 400)
    except CommandExecutionError as e:
        return error_response(f"Agent failed to delete interface (command error): {e}", 500)
    except Exception as e:
        return error_response(f"Agent failed to delete interface: {e}", 500)

@app.post("/agent_api/sync")
@authenticate_agent
async def agent_trigger_sync():
    """
    Triggers a local sync process on this server.
    """
    try:
        await asyncio.to_thread(agent_candy_panel._sync)
        return success_response("Local synchronization initiated successfully.")
    except Exception as e:
        return error_response(f"Agent failed to trigger sync: {e}", 500)

@app.post("/agent_api/traffic/dump")
@authenticate_agent
async def agent_get_traffic_dump():
    """
    Retrieves raw WireGuard peer traffic data for all interfaces on this server.
    """
    try:
        all_interfaces = await asyncio.to_thread(agent_candy_panel.db.select, 'interfaces')
        full_traffic_data = {}
        for iface in all_interfaces:
            wg_id = iface['wg']
            x = await asyncio.to_thread(agent_candy_panel._get_current_wg_peer_traffic, wg_id)
            full_traffic_data.update(x)
        return success_response("Traffic dump retrieved.", data={"traffic_data": full_traffic_data})
    except Exception as e:
        return error_response(f"Failed to retrieve traffic dump: {e}", 500)

@app.post("/agent_api/client/get_details")
@authenticate_agent
async def agent_get_client_details():
    """
    Retrieves full client details (including live stats) for a specific client.
    This is what the central panel needs to populate its UI.
    """
    data = request.json
    name = data.get('name')
    public_key = data.get('public_key')

    if not all([name, public_key]):
        return error_response("Missing name or public_key for client details.", 400)

    try:
        # Call the local method to get client details
        client_data = await asyncio.to_thread(agent_candy_panel._get_client_by_name_and_public_key, name, public_key)
        if client_data:
            # Ensure sensitive info like private_key is removed before sending back
            client_data.pop('private_key', None)
            return success_response("Client details retrieved.", data=client_data)
        return error_response("Client not found.", 404)
    except Exception as e:
        return error_response(f"Failed to get client details: {e}", 500)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=1212)