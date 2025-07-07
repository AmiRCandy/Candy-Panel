# main.py
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import asyncio
import json
from datetime import datetime

# Import your CandyPanel logic
from core import CandyPanel, CommandExecutionError

# --- Initialize CandyPanel ---
# This will ensure the database is connected and tables are initialized on startup
candy_panel = CandyPanel()

# --- Pydantic Models for Request/Response Bodies ---

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class ClientBase(BaseModel):
    name: str
    expires: str = Field(..., description="Expiration date/time in ISO format (e.g., '2025-12-31T23:59:59')")
    traffic: str = Field(..., description="Total traffic quota in bytes (e.g., '1073741824' for 1GB)")
    wg_id: int = Field(0, description="WireGuard interface ID (default is 0)")
    note: Optional[str] = ""

class ClientCreate(ClientBase):
    pass

class ClientUpdate(BaseModel):
    expires: Optional[str] = Field(None, description="Expiration date/time in ISO format (e.g., '2025-12-31T23:59:59')")
    traffic: Optional[str] = Field(None, description="Total traffic quota in bytes (e.g., '1073741824' for 1GB)")
    status: Optional[bool] = None
    note: Optional[str] = None

class ClientResponse(ClientBase):
    public_key: str
    private_key: str # Sensitive, consider if this should be returned
    address: str
    created_at: str
    used_trafic: Dict[str, int] # Parsed JSON
    connected_now: bool
    status: bool

    class Config:
        json_encoders = {
            # Handle potential datetime objects if they somehow get into the dict
            datetime: lambda v: v.isoformat()
        }
        # Allow population from attributes, useful when converting DB rows (dict) to Pydantic model
        from_attributes = True


class InterfaceBase(BaseModel):
    address_range: str = Field(..., description="CIDR address range (e.g., '10.0.0.1/24')")
    port: int = Field(..., description="Listen port for the WireGuard interface")

class InterfaceCreate(InterfaceBase):
    pass

class InterfaceUpdate(BaseModel):
    address: Optional[str] = Field(None, description="New CIDR address range (e.g., '10.0.1.1/24')")
    port: Optional[int] = Field(None, description="New listen port")
    status: Optional[bool] = None

class InterfaceResponse(InterfaceBase):
    wg: int
    private_key: str # Sensitive, consider if this should be returned
    public_key: str
    status: bool

    class Config:
        from_attributes = True

class SettingsUpdate(BaseModel):
    value: str

class ApiTokenCreate(BaseModel):
    name: str
    token: str

class ApiTokenResponse(BaseModel):
    name: str
    token: str # Sensitive, consider if this should be returned

class InstallRequest(BaseModel):
    server_ip: str
    wg_port: str
    wg_address_range: str = "10.0.0.1/24"
    wg_dns: str = "8.8.8.8"
    admin_user: str = "admin"
    admin_password: str = "admin"

class MessageResponse(BaseModel):
    message: str
    success: bool = True
    data: Optional[Any] = None

# --- FastAPI Application Setup ---
app = FastAPI(
    title="CandyPanel API",
    description="Backend API for managing WireGuard VPN server and clients.",
    version="1.0.0",
)

# OAuth2 for token-based authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# --- Dependency for Authentication ---
async def get_current_admin(token: str = Depends(oauth2_scheme)):
    """
    Authenticates the user based on the provided session token.
    """
    # Run synchronous DB operation in a thread pool
    settings = await asyncio.to_thread(candy_panel.db.get, 'settings', where={'key': 'session_token'})
    if not settings or settings['value'] != token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return True # Authentication successful

# --- API Endpoints ---

@app.post("/login", response_model=MessageResponse, summary="Admin Login")
async def login():
    """
    Authenticates an admin user and returns a session token.
    """
    typeofcheck = await asyncio.to_thread(candy_panel.db.get,'settings','*',{'key':'install'})
    if bool(typeofcheck['value']) :
        return {"type":"admin"}
    else :
        return {"type":"install"}

@app.get("/check", response_model=TokenResponse, summary="check")
async def login(request: LoginRequest):
    """
    Authenticates an admin user and returns a session token.
    """
    success, message = await asyncio.to_thread(candy_panel._admin_login, request.username, request.password)
    if not success:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message)
    return {"access_token": message, "token_type": "bearer"}

@app.post("/install", response_model=MessageResponse, summary="Install CandyPanel (Run Once)")
async def install_candypanel(request: InstallRequest):
    """
    Performs the initial installation of WireGuard and CandyPanel configuration.
    This endpoint should ideally be run only once.
    """
    success, message = await asyncio.to_thread(
        candy_panel._install_candy_panel,
        request.server_ip,
        request.wg_port,
        request.wg_address_range,
        request.wg_dns,
        request.admin_user,
        request.admin_password
    )
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    return MessageResponse(message=message, success=True)

@app.get("/dashboard", response_model=Dict[str, Any], summary="Get Dashboard Statistics")
async def get_dashboard_stats(authenticated: bool = Depends(get_current_admin)):
    """
    Retrieves system and application statistics for the dashboard.
    Requires authentication.
    """
    stats = await asyncio.to_thread(candy_panel._dashboard_stats)
    return stats

@app.post("/sync", response_model=MessageResponse, summary="Trigger Synchronization Process")
async def trigger_sync(authenticated: bool = Depends(get_current_admin)):
    """
    Manually triggers the CandyPanel synchronization process.
    This process updates traffic, checks expirations, and performs backups.
    Requires authentication.
    """
    try:
        await asyncio.to_thread(candy_panel._sync)
        return MessageResponse(message="Synchronization process initiated successfully.", success=True)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Synchronization failed: {e}")

# --- Client Management ---

@app.get("/clients", response_model=List[ClientResponse], summary="Get All Clients")
async def get_all_clients(authenticated: bool = Depends(get_current_admin)):
    """
    Retrieves a list of all WireGuard clients.
    Requires authentication.
    """
    clients_data = await asyncio.to_thread(candy_panel._get_all_clients)
    # Parse 'used_trafic' JSON string into a dictionary for each client
    for client in clients_data:
        try:
            client['used_trafic'] = json.loads(client['used_trafic'])
        except (json.JSONDecodeError, TypeError):
            client['used_trafic'] = {"download": 0, "upload": 0} # Default if parsing fails
    return [ClientResponse.model_validate(client) for client in clients_data]


@app.post("/clients", response_model=MessageResponse, summary="Create New Client")
async def create_new_client(client: ClientCreate, authenticated: bool = Depends(get_current_admin)):
    """
    Creates a new WireGuard client.
    Requires authentication.
    """
    success, message = await asyncio.to_thread(
        candy_panel._new_client,
        client.name,
        client.expires,
        client.traffic,
        client.wg_id,
        client.note
    )
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    return MessageResponse(message=message, success=True, data={"client_config": message}) # client_config is returned in message


@app.get("/clients/{client_name}", response_model=ClientResponse, summary="Get Client by Name")
async def get_client_by_name(client_name: str, authenticated: bool = Depends(get_current_admin)):
    """
    Retrieves details of a specific client by name.
    Requires authentication.
    """
    client_data = await asyncio.to_thread(candy_panel.db.get, 'clients', where={'name': client_name})
    if not client_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Client '{client_name}' not found.")
    try:
        client_data['used_trafic'] = json.loads(client_data['used_trafic'])
    except (json.JSONDecodeError, TypeError):
        client_data['used_trafic'] = {"download": 0, "upload": 0}
    return ClientResponse.model_validate(client_data)

@app.put("/clients/{client_name}", response_model=MessageResponse, summary="Update Client Details")
async def update_client_details(client_name: str, client_update: ClientUpdate, authenticated: bool = Depends(get_current_admin)):
    """
    Updates details for an existing WireGuard client.
    Requires authentication.
    """
    success, message = await asyncio.to_thread(
        candy_panel._edit_client,
        client_name,
        client_update.expires,
        client_update.traffic,
        client_update.status,
        client_update.note
    )
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    return MessageResponse(message=message, success=True)

@app.delete("/clients/{client_name}", response_model=MessageResponse, summary="Delete Client")
async def delete_client(client_name: str, authenticated: bool = Depends(get_current_admin)):
    """
    Deletes a WireGuard client.
    Requires authentication.
    """
    success, message = await asyncio.to_thread(candy_panel._delete_client, client_name)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    return MessageResponse(message=message, success=True)

@app.get("/clients/{client_name}/config", response_model=MessageResponse, summary="Get Client Configuration")
async def get_client_config(client_name: str, authenticated: bool = Depends(get_current_admin)):
    """
    Retrieves the WireGuard client configuration file content for a specific client.
    Requires authentication.
    """
    success, config_content = await asyncio.to_thread(candy_panel._get_client_config, client_name)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=config_content)
    return MessageResponse(message="Client config retrieved successfully.", success=True, data={"config": config_content})

# --- Interface Management ---

@app.get("/interfaces", response_model=List[InterfaceResponse], summary="Get All Interfaces")
async def get_all_interfaces(authenticated: bool = Depends(get_current_admin)):
    """
    Retrieves a list of all WireGuard interfaces.
    Requires authentication.
    """
    interfaces_data = await asyncio.to_thread(candy_panel.db.select, 'interfaces')
    return [InterfaceResponse.model_validate(interface) for interface in interfaces_data]

@app.post("/interfaces", response_model=MessageResponse, summary="Create New Interface")
async def create_new_interface(interface: InterfaceCreate, authenticated: bool = Depends(get_current_admin)):
    """
    Creates a new WireGuard interface.
    Requires authentication.
    """
    success, message = await asyncio.to_thread(
        candy_panel._new_interface_wg,
        interface.address_range,
        interface.port
    )
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    return MessageResponse(message=message, success=True)

@app.put("/interfaces/{interface_name}", response_model=MessageResponse, summary="Update Interface Details")
async def update_interface_details(interface_name: str, interface_update: InterfaceUpdate, authenticated: bool = Depends(get_current_admin)):
    """
    Updates details for an existing WireGuard interface (e.g., 'wg0').
    Requires authentication.
    """
    success, message = await asyncio.to_thread(
        candy_panel._edit_interface,
        interface_name,
        interface_update.address,
        interface_update.port,
        interface_update.status
    )
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    return MessageResponse(message=message, success=True)

# --- Settings Management ---

@app.get("/settings", response_model=Dict[str, str], summary="Get All Settings")
async def get_all_settings(authenticated: bool = Depends(get_current_admin)):
    """
    Retrieves all application settings.
    Requires authentication.
    WARNING: This endpoint exposes all settings, including sensitive ones like admin password (if not hashed).
    Consider filtering sensitive data before returning.
    """
    settings_data = await asyncio.to_thread(candy_panel.db.select, 'settings')
    # Convert list of dicts to a single dict for easier consumption
    return {setting['key']: setting['value'] for setting in settings_data}

@app.put("/settings/{key}", response_model=MessageResponse, summary="Update Specific Setting")
async def update_setting(key: str, setting_update: SettingsUpdate, authenticated: bool = Depends(get_current_admin)):
    """
    Updates a specific application setting by its key.
    Requires authentication.
    """
    success, message = await asyncio.to_thread(candy_panel._change_settings, key, setting_update.value)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    return MessageResponse(message=message, success=True)

# --- API Token Management ---

@app.post("/api-tokens", response_model=MessageResponse, summary="Create or Update API Token")
async def create_or_update_api_token(token_data: ApiTokenCreate, authenticated: bool = Depends(get_current_admin)):
    """
    Creates a new API token or updates an existing one.
    Requires authentication.
    """
    success, message = await asyncio.to_thread(candy_panel._add_api_token, token_data.name, token_data.token)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    return MessageResponse(message=message, success=True)

@app.delete("/api-tokens/{name}", response_model=MessageResponse, summary="Delete API Token")
async def delete_api_token(name: str, authenticated: bool = Depends(get_current_admin)):
    """
    Deletes an API token by its name.
    Requires authentication.
    """
    success, message = await asyncio.to_thread(candy_panel._delete_api_token, name)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    return MessageResponse(message=message, success=True)

@app.get("/api-tokens/{name}", response_model=MessageResponse, summary="Get Specific API Token")
async def get_api_token(name: str, authenticated: bool = Depends(get_current_admin)):
    """
    Retrieves a specific API token by its name.
    Requires authentication.
    """
    success, token_value = await asyncio.to_thread(candy_panel._get_api_token, name)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=token_value)
    return MessageResponse(message="API token retrieved.", success=True, data={"token": token_value})
