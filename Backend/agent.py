# Candy-Panel/Agent/agent.py
from flask import Flask, request, jsonify, abort
from functools import wraps
import os , json
import sys
import asyncio

try:
    from core import LocalAgentRunner, CommandExecutionError
except ImportError as e:
    print(f"Error importing core modules: {e}")
    print("Please ensure 'core.py' is accessible in the agent's environment.")
    sys.exit(1)


app = Flask(__name__)

# The agent now uses a stateless runner, not a full CandyPanel instance
local_agent_runner = LocalAgentRunner()
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
    return jsonify({"message": message, "success": True, "data": data}), status_code

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
        stats = await asyncio.to_thread(local_agent_runner._dashboard_stats)
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
    public_key = data.get('public_key')
    private_key = data.get('private_key')
    address = data.get('address')
    wg_id = data.get('wg_id', 0)
    
    if not all([name, public_key, private_key, address]):
        return error_response("Missing required fields for client creation.", 400)

    try:
        # Calls the local runner to create the client config entry
        await asyncio.to_thread(local_agent_runner._add_peer_to_config, wg_id, name, public_key, address)
        return success_response("Client created locally.")
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
    public_key = data.get('public_key')
    address = data.get('address')
    status = data.get('status')
    
    if not name:
        return error_response("Missing client name for update.", 400)

    try:
        # The agent now only needs to know about the name and public key to update the config file
        if status is not None:
            if status:
                await asyncio.to_thread(local_agent_runner._add_peer_to_config, 0, name, public_key, address)
                return success_response("Client enabled successfully.")
            else:
                await asyncio.to_thread(local_agent_runner._remove_peer_from_config, 0, name)
                return success_response("Client disabled successfully.")
        return success_response("Update request received, no action taken.")
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
    wg_id = data.get('wg_id')

    if not all([name, wg_id is not None]):
        return error_response("Missing client name or wg_id for deletion.", 400)

    try:
        await asyncio.to_thread(local_agent_runner._remove_peer_from_config, wg_id, name)
        return success_response("Client deleted locally.")
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
    public_key = data.get('public_key')
    private_key = data.get('private_key')
    address = data.get('address')
    server_endpoint_ip = data.get('server_endpoint_ip')
    interface_port = data.get('interface_port')
    server_dns = data.get('server_dns')
    server_mtu = data.get('server_mtu')
    
    if not all([name, public_key, private_key, address, server_endpoint_ip, interface_port, server_dns, server_mtu]):
        return error_response("Missing required data for config generation.", 400)
        
    try:
        config_content = await asyncio.to_thread(local_agent_runner._get_client_config_string, private_key, address, server_endpoint_ip, interface_port, server_dns, server_mtu)
        return success_response("Client config retrieved.", data={"config": config_content})
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
    
    if not all([address_range, port]):
        return error_response("Missing address_range or port for interface creation.", 400)

    try:
        interface_details = await asyncio.to_thread(local_agent_runner._new_interface_wg, address_range, port)
        return success_response("New Interface Created!", data=interface_details)
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
        success, message = await asyncio.to_thread(local_agent_runner._edit_interface, name, address, port, status)
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
        success, message = await asyncio.to_thread(local_agent_runner._delete_interface, wg_id)
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
        await asyncio.to_thread(local_agent_runner._sync)
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
        full_traffic_data = await asyncio.to_thread(local_agent_runner._get_all_wg_peer_traffic)
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
        client_data = await asyncio.to_thread(local_agent_runner._get_client_by_name_and_public_key, name, public_key)
        if client_data:
            # Ensure sensitive info like private_key is removed before sending back
            client_data.pop('private_key', None)
            return success_response("Client details retrieved.", data=client_data)
        return error_response("Client not found.", 404)
    except Exception as e:
        return error_response(f"Failed to get client details: {e}", 500)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=1212)