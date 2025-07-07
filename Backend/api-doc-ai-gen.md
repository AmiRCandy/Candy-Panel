
-----

# CandyPanel API Documentation

This document provides a comprehensive overview of the CandyPanel RESTful API, which allows for the management of WireGuard VPN servers and clients.

## Base URL

The base URL for all API endpoints is typically `http://your-server-ip:8000` (or `http://127.0.0.1:8000` if running locally).

## Authentication

Most endpoints require authentication. The API uses a simple token-based authentication mechanism.

  * **Authentication Method:** Bearer Token

  * **Token Acquisition:** Obtain an `access_token` by successfully logging in via the `/login` endpoint.

  * **Usage:** Include the `access_token` in the `Authorization` header of your requests, prefixed with `Bearer`.

    **Example Header:**
    `Authorization: Bearer YOUR_ACCESS_TOKEN_HERE`

## API Endpoints

-----

### 1\. Admin Login

  * **HTTP Method:** `POST`

  * **Path:** `/login`

  * **Summary:** Authenticates an admin user and returns a session token.

  * **Description:** Use this endpoint to log in as an administrator. Upon successful authentication, a unique session token will be provided, which must be used for subsequent authenticated requests.

  * **Request Body (`application/json`):**

    ```json
    {
      "username": "string",
      "password": "string"
    }
    ```

  * **Response Body (Success - `200 OK`):**

    ```json
    {
      "access_token": "string",
      "token_type": "bearer"
    }
    ```

  * **Response Body (Error - `401 Unauthorized`):**

    ```json
    {
      "detail": "Wrong username or password!"
    }
    ```

  * **Authentication Required:** No

-----

### 2\. Install CandyPanel

  * **HTTP Method:** `POST`

  * **Path:** `/install`

  * **Summary:** Install CandyPanel (Run Once)

  * **Description:** Performs the initial installation of WireGuard and CandyPanel configuration on the server. This endpoint should ideally be run only once during the initial setup of the CandyPanel system. It sets up the default WireGuard interface (`wg0`) and initial admin credentials.

  * **Request Body (`application/json`):**

    ```json
    {
      "server_ip": "string",
      "wg_port": "string",
      "wg_address_range": "10.0.0.1/24",
      "wg_dns": "8.8.8.8",
      "admin_user": "admin",
      "admin_password": "admin"
    }
    ```

      * `server_ip`: The public IP address of your server.
      * `wg_port`: The WireGuard listen port (e.g., "51820").
      * `wg_address_range`: The internal IP range for the WireGuard interface.
      * `wg_dns`: DNS server for clients.
      * `admin_user`: Desired admin username.
      * `admin_password`: Desired admin password.

  * **Response Body (Success - `200 OK`):**

    ```json
    {
      "message": "Installed successfully!",
      "success": true,
      "data": null
    }
    ```

  * **Response Body (Error - `400 Bad Request`):**

    ```json
    {
      "detail": "IP INCORRECT"
    }
    ```

    (or other error messages from the backend)

  * **Authentication Required:** No

-----

### 3\. Get Dashboard Statistics

  * **HTTP Method:** `GET`

  * **Path:** `/dashboard`

  * **Summary:** Get Dashboard Statistics

  * **Description:** Retrieves various system and application statistics for the dashboard, including CPU usage, memory, client count, server status, alerts, bandwidth, uptime, and network speeds.

  * **Response Body (Success - `200 OK`):**

    ```json
    {
      "cpu": "string",
      "mem": {
        "total": "string",
        "available": "string",
        "usage": "string"
      },
      "clients_count": 0,
      "status": "string",
      "alert": [],
      "bandwidth": "string",
      "uptime": "string",
      "net": {
        "download": "string",
        "upload": "string"
      }
    }
    ```

  * **Authentication Required:** Yes

-----

### 4\. Trigger Synchronization Process

  * **HTTP Method:** `POST`

  * **Path:** `/sync`

  * **Summary:** Trigger Synchronization Process

  * **Description:** Manually triggers the CandyPanel synchronization process. This process updates traffic statistics for clients, checks for client expirations and traffic limit breaches (and deletes clients if necessary), and performs automatic backups of WireGuard configurations if enabled. This is the same process run by the `corn.py` cron job.

  * **Response Body (Success - `200 OK`):**

    ```json
    {
      "message": "Synchronization process initiated successfully.",
      "success": true,
      "data": null
    }
    ```

  * **Response Body (Error - `500 Internal Server Error`):**

    ```json
    {
      "detail": "Synchronization failed: [error message]"
    }
    ```

  * **Authentication Required:** Yes

-----

### 5\. Get All Clients

  * **HTTP Method:** `GET`

  * **Path:** `/clients`

  * **Summary:** Get All Clients

  * **Description:** Retrieves a list of all WireGuard client records stored in the database.

  * **Response Body (Success - `200 OK`):**

    ```json
    [
      {
        "name": "string",
        "expires": "2025-12-31T23:59:59",
        "traffic": "string",
        "wg_id": 0,
        "note": "string",
        "public_key": "string",
        "private_key": "string",
        "address": "string",
        "created_at": "string",
        "used_trafic": {
          "download": 0,
          "upload": 0
        },
        "connected_now": false,
        "status": true
      }
    ]
    ```

  * **Authentication Required:** Yes

-----

### 6\. Create New Client

  * **HTTP Method:** `POST`

  * **Path:** `/clients`

  * **Summary:** Create New Client

  * **Description:** Creates a new WireGuard client, generates its configuration, and adds it to the database. The client's WireGuard configuration content is returned in the response data.

  * **Request Body (`application/json`):**

    ```json
    {
      "name": "string",
      "expires": "2025-12-31T23:59:59",
      "traffic": "1073741824",
      "wg_id": 0,
      "note": "string"
    }
    ```

      * `name`: Unique name for the client.
      * `expires`: Expiration date/time in ISO format (e.g., `'YYYY-MM-DDTHH:MM:SS'`).
      * `traffic`: Total traffic quota in bytes (e.g., `'1073741824'` for 1GB).
      * `wg_id`: WireGuard interface ID to associate the client with (default is `0`).
      * `note`: Optional note for the client.

  * **Response Body (Success - `200 OK`):**

    ```json
    {
      "message": "Client created successfully.",
      "success": true,
      "data": {
        "client_config": "[Interface]\\nPrivateKey = ...\\nAddress = ...\\n..."
      }
    }
    ```

  * **Response Body (Error - `400 Bad Request`):**

    ```json
    {
      "detail": "Client with this name already exists."
    }
    ```

    (or "No available IP addresses in the subnet.", etc.)

  * **Authentication Required:** Yes

-----

### 7\. Get Client by Name

  * **HTTP Method:** `GET`

  * **Path:** `/clients/{client_name}`

  * **Summary:** Get Client by Name

  * **Description:** Retrieves details of a specific client by their unique name.

  * **Path Parameters:**

      * `client_name` (string): The name of the client.

  * **Response Body (Success - `200 OK`):**

    ```json
    {
      "name": "string",
      "expires": "2025-12-31T23:59:59",
      "traffic": "string",
      "wg_id": 0,
      "note": "string",
      "public_key": "string",
      "private_key": "string",
      "address": "string",
      "created_at": "string",
      "used_trafic": {
        "download": 0,
        "upload": 0
      },
      "connected_now": false,
      "status": true
    }
    ```

  * **Response Body (Error - `404 Not Found`):**

    ```json
    {
      "detail": "Client 'client_name' not found."
    }
    ```

  * **Authentication Required:** Yes

-----

### 8\. Update Client Details

  * **HTTP Method:** `PUT`

  * **Path:** `/clients/{client_name}`

  * **Summary:** Update Client Details

  * **Description:** Updates details for an existing WireGuard client. Only provided fields will be updated.

  * **Path Parameters:**

      * `client_name` (string): The name of the client to update.

  * **Request Body (`application/json`):**

    ```json
    {
      "expires": "2026-01-01T00:00:00",
      "traffic": "2147483648",
      "status": true,
      "note": "Updated note"
    }
    ```

      * All fields are optional.

  * **Response Body (Success - `200 OK`):**

    ```json
    {
      "message": "Client 'client_name' edited successfully.",
      "success": true,
      "data": null
    }
    ```

  * **Response Body (Error - `400 Bad Request`):**

    ```json
    {
      "detail": "Client 'client_name' not found."
    }
    ```

    (or "No update data provided.")

  * **Authentication Required:** Yes

-----

### 9\. Delete Client

  * **HTTP Method:** `DELETE`

  * **Path:** `/clients/{client_name}`

  * **Summary:** Delete Client

  * **Description:** Deletes a WireGuard client from the configuration and database.

  * **Path Parameters:**

      * `client_name` (string): The name of the client to delete.

  * **Response Body (Success - `200 OK`):**

    ```json
    {
      "message": "Client 'client_name' deleted successfully.",
      "success": true,
      "data": null
    }
    ```

  * **Response Body (Error - `400 Bad Request`):**

    ```json
    {
      "detail": "Client 'client_name' not found."
    }
    ```

  * **Authentication Required:** Yes

-----

### 10\. Get Client Configuration

  * **HTTP Method:** `GET`

  * **Path:** `/clients/{client_name}/config`

  * **Summary:** Get Client Configuration

  * **Description:** Retrieves the raw WireGuard client configuration file content for a specific client. This content can be directly used in a WireGuard client application.

  * **Path Parameters:**

      * `client_name` (string): The name of the client.

  * **Response Body (Success - `200 OK`):**

    ```json
    {
      "message": "Client config retrieved successfully.",
      "success": true,
      "data": {
        "config": "[Interface]\\nPrivateKey = ...\\nAddress = ...\\n..."
      }
    }
    ```

  * **Response Body (Error - `404 Not Found`):**

    ```json
    {
      "detail": "Client not found."
    }
    ```

    (or "Associated WireGuard interface wgX not found.")

  * **Authentication Required:** Yes

-----

### 11\. Get All Interfaces

  * **HTTP Method:** `GET`

  * **Path:** `/interfaces`

  * **Summary:** Get All Interfaces

  * **Description:** Retrieves a list of all WireGuard interfaces configured on the server.

  * **Response Body (Success - `200 OK`):**

    ```json
    [
      {
        "address_range": "10.0.0.1/24",
        "port": 51820,
        "wg": 0,
        "private_key": "string",
        "public_key": "string",
        "status": true
      }
    ]
    ```

  * **Authentication Required:** Yes

-----

### 12\. Create New Interface

  * **HTTP Method:** `POST`

  * **Path:** `/interfaces`

  * **Summary:** Create New Interface

  * **Description:** Creates a new WireGuard interface configuration and adds it to the database. A new `wg` ID will be automatically assigned.

  * **Request Body (`application/json`):**

    ```json
    {
      "address_range": "10.0.1.1/24",
      "port": 51821
    }
    ```

      * `address_range`: CIDR address range for the new interface.
      * `port`: Listen port for the new interface.

  * **Response Body (Success - `200 OK`):**

    ```json
    {
      "message": "New Interface Created!",
      "success": true,
      "data": null
    }
    ```

  * **Response Body (Error - `400 Bad Request`):**

    ```json
    {
      "detail": "An interface with port 51821 already exists."
    }
    ```

    (or "An interface with address range 10.0.1.1/24 already exists.", "Interface with this name already exists", etc.)

  * **Authentication Required:** Yes

-----

### 13\. Update Interface Details

  * **HTTP Method:** `PUT`

  * **Path:** `/interfaces/{interface_name}`

  * **Summary:** Update Interface Details

  * **Description:** Updates details for an existing WireGuard interface (e.g., 'wg0'). Only provided fields will be updated.

  * **Path Parameters:**

      * `interface_name` (string): The name of the interface to update (e.g., "wg0", "wg1").

  * **Request Body (`application/json`):**

    ```json
    {
      "address": "10.0.0.1/24",
      "port": 51820,
      "status": true
    }
    ```

      * All fields are optional.

  * **Response Body (Success - `200 OK`):**

    ```json
    {
      "message": "Interface wg0 edited successfully.",
      "success": true,
      "data": null
    }
    ```

  * **Response Body (Error - `400 Bad Request`):**

    ```json
    {
      "detail": "Interface wg0 does not exist."
    }
    ```

    (or other error messages)

  * **Authentication Required:** Yes

-----

### 14\. Get All Settings

  * **HTTP Method:** `GET`

  * **Path:** `/settings`

  * **Summary:** Get All Settings

  * **Description:** Retrieves all application settings stored in the database.
    **WARNING:** This endpoint exposes all settings, including potentially sensitive ones like the admin password (if not hashed). In a production environment, consider filtering sensitive data before returning it.

  * **Response Body (Success - `200 OK`):**

    ```json
    {
      "server_ip": "192.168.1.100",
      "session_token": "YOUR_SESSION_TOKEN",
      "dns": "8.8.8.8",
      "admin": "{\"user\":\"admin\",\"password\":\"admin\"}",
      "status": "1",
      "alert": "[\"Welcome To Candy Panel - by AmiRCandy\"]",
      "reset_time": "0",
      "mtu": "1420",
      "bandwidth": "0",
      "uptime": "0",
      "telegram_bot_status": "0",
      "telegram_bot_admin_id": "0",
      "telegram_bot_token": "0",
      "telegram_bot_prices": "{\"per_month\":75000,\"per_gb\":4000}",
      "api_tokens": "{}",
      "auto_backup": "1"
    }
    ```

    (Values will vary based on your configuration)

  * **Authentication Required:** Yes

-----

### 15\. Update Specific Setting

  * **HTTP Method:** `PUT`

  * **Path:** `/settings/{key}`

  * **Summary:** Update Specific Setting

  * **Description:** Updates the value of a specific application setting by its key.

  * **Path Parameters:**

      * `key` (string): The key of the setting to update (e.g., "server\_ip", "dns", "reset\_time").

  * **Request Body (`application/json`):**

    ```json
    {
      "value": "new_value"
    }
    ```

      * `value`: The new value for the setting.

  * **Response Body (Success - `200 OK`):**

    ```json
    {
      "message": "Changed!",
      "success": true,
      "data": null
    }
    ```

  * **Response Body (Error - `400 Bad Request`):**

    ```json
    {
      "detail": "Invalid Key"
    }
    ```

  * **Authentication Required:** Yes

-----

### 16\. Create or Update API Token

  * **HTTP Method:** `POST`

  * **Path:** `/api-tokens`

  * **Summary:** Create or Update API Token

  * **Description:** Creates a new API token or updates the value of an existing API token.

  * **Request Body (`application/json`):**

    ```json
    {
      "name": "string",
      "token": "string"
    }
    ```

      * `name`: The name of the API token (e.g., "telegram\_bot\_api").
      * `token`: The actual token string.

  * **Response Body (Success - `200 OK`):**

    ```json
    {
      "message": "API token 'name' added/updated successfully.",
      "success": true,
      "data": null
    }
    ```

  * **Response Body (Error - `400 Bad Request`):**

    ```json
    {
      "detail": "Failed to add/update API token: [error message]"
    }
    ```

  * **Authentication Required:** Yes

-----

### 17\. Delete API Token

  * **HTTP Method:** `DELETE`

  * **Path:** `/api-tokens/{name}`

  * **Summary:** Delete API Token

  * **Description:** Deletes an API token by its name.

  * **Path Parameters:**

      * `name` (string): The name of the API token to delete.

  * **Response Body (Success - `200 OK`):**

    ```json
    {
      "message": "API token 'name' deleted successfully.",
      "success": true,
      "data": null
    }
    ```

  * **Response Body (Error - `400 Bad Request`):**

    ```json
    {
      "detail": "API token 'name' not found."
    }
    ```

    (or "API tokens setting not found or is empty.", etc.)

  * **Authentication Required:** Yes

-----

### 18\. Get Specific API Token

  * **HTTP Method:** `GET`

  * **Path:** `/api-tokens/{name}`

  * **Summary:** Get Specific API Token

  * **Description:** Retrieves the value of a specific API token by its name.

  * **Path Parameters:**

      * `name` (string): The name of the API token to retrieve.

  * **Response Body (Success - `200 OK`):**

    ```json
    {
      "message": "API token retrieved.",
      "success": true,
      "data": {
        "token": "string"
      }
    }
    ```

  * **Response Body (Error - `404 Not Found`):**

    ```json
    {
      "detail": "API token 'name' not found."
    }
    ```

    (or "API tokens setting not found or is empty.", etc.)

  * **Authentication Required:** Yes

-----