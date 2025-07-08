# CandyPanel Unified API Documentation

This document provides a comprehensive overview of the CandyPanel unified API. This API serves as the backend for both the CandyPanel web interface and the Telegram bot, managing WireGuard clients, interfaces, server settings, and user/transaction data for the bot.

## Base URL

All API endpoints are relative to your server's address and port where `main.py` is running.
**Example:** `http://your-server-ip:3446`

## Authentication

Admin-level endpoints (both for the CandyPanel web UI and the Telegram bot's admin functions) require authentication using a Bearer Token.

### Obtaining an Access Token

To obtain an access token, send a `POST` request to the `/api/auth` endpoint with the `action` set to `login` and your admin `username` and `password`.

  * **Endpoint:** `/api/auth`
  * **Method:** `POST`
  * **Request Body (JSON):**
    ```json
    {
        "action": "login",
        "username": "your_admin_username",
        "password": "your_admin_password"
    }
    ```
  * **Success Response (200 OK):**
    ```json
    {
        "message": "Login successful!",
        "success": true,
        "data": {
            "access_token": "YOUR_GENERATED_SESSION_TOKEN",
            "token_type": "bearer"
        }
    }
    ```
  * **Error Response (401 Unauthorized / 400 Bad Request):**
    ```json
    {
        "message": "Invalid authentication credentials",
        "success": false
    }
    ```

### Using the Access Token

Once you have an `access_token`, include it in the `Authorization` header of subsequent requests as a Bearer token:

`Authorization: Bearer YOUR_GENERATED_SESSION_TOKEN`

## General Endpoints

### 1\. Check Installation Status

Checks if the CandyPanel is installed on the server.

  * **Endpoint:** `/check`
  * **Method:** `GET`
  * **Authentication:** None
  * **Success Response (200 OK):**
    ```json
    {
        "installed": true
    }
    ```
    or
    ```json
    {
        "installed": false
    }
    ```

### 2\. Handle Authentication and Installation

This endpoint is used for both admin login and initial CandyPanel installation.

  * **Endpoint:** `/api/auth`
  * **Method:** `POST`
  * **Authentication:** None
  * **Actions:**
      * **`login`**: Authenticates an existing admin user.
      * **`install`**: Performs the initial setup of WireGuard and CandyPanel. This action can only be performed once.

#### Request Body (JSON)

**For `action: "login"`:**

```json
{
    "action": "login",
    "username": "your_admin_username",
    "password": "your_admin_password"
}
```

**For `action: "install"`:**

```json
{
    "action": "install",
    "server_ip": "YOUR_SERVER_PUBLIC_IP",
    "wg_port": "WIREGUARD_PORT",
    "wg_address_range": "10.0.0.1/24",
    "wg_dns": "8.8.8.8",
    "admin_user": "new_admin_username",
    "admin_password": "new_admin_password"
}
```

  * `server_ip`: The public IP address of your server.

  * `wg_port`: The port WireGuard will listen on (e.g., `51820`).

  * `wg_address_range`: (Optional) The internal IP range for WireGuard clients. Default: `10.0.0.1/24`.

  * `wg_dns`: (Optional) DNS server for clients. Default: `8.8.8.8`.

  * `admin_user`: (Optional) Username for the initial admin account. Default: `admin`.

  * `admin_password`: (Optional) Password for the initial admin account. Default: `admin`.

  * **Success Response (200 OK):**

      * For `login`: See "Obtaining an Access Token" above.
      * For `install`:
        ```json
        {
            "message": "Installed successfully!",
            "success": true
        }
        ```

  * **Error Response (400 Bad Request / 401 Unauthorized):**

    ```json
    {
        "message": "Error message details",
        "success": false
    }
    ```

## CandyPanel Admin Endpoints (`/api/manage`)

This endpoint is a unified interface for managing various CandyPanel resources.

  * **Endpoint:** `/api/manage`
  * **Method:** `POST`
  * **Authentication:** Required (Bearer Token)
  * **Request Body (JSON):** Must include `resource` and `action` fields, plus `data` specific to the action.

### 1\. Client Management (`resource: "client"`)

#### a. Create Client (`action: "create"`)

Creates a new WireGuard client.

  * **Request Body `data`:**
    ```json
    {
        "name": "client_name",
        "expires": "YYYY-MM-DDTHH:MM:SS",
        "traffic": "TOTAL_TRAFFIC_BYTES",
        "wg_id": 0,
        "note": "Optional client note"
    }
    ```
      * `name`: Unique name for the client.
      * `expires`: ISO formatted datetime string (e.g., `2025-12-31T23:59:59`).
      * `traffic`: Total traffic quota in bytes (as a string).
      * `wg_id`: (Optional) WireGuard interface ID (default: `0`).
      * `note`: (Optional) A note for the client.
  * **Success Response (200 OK):**
    ```json
    {
        "message": "Client created successfully!",
        "success": true,
        "data": {
            "client_config": "[Interface]..." // The generated WireGuard client config
        }
    }
    ```

#### b. Update Client (`action: "update"`)

Modifies an existing WireGuard client. Provide only the fields you wish to update.

  * **Request Body `data`:**
    ```json
    {
        "name": "client_name",
        "expires": "YYYY-MM-DDTHH:MM:SS",
        "traffic": "NEW_TOTAL_TRAFFIC_BYTES",
        "status": true, // or false to enable/disable
        "note": "Updated client note"
    }
    ```
      * `name`: **Required**. Name of the client to update.
      * `expires`: (Optional) New expiry date.
      * `traffic`: (Optional) New total traffic quota in bytes (as a string).
      * `status`: (Optional) `true` to activate, `false` to deactivate.
      * `note`: (Optional) New note.
  * **Success Response (200 OK):**
    ```json
    {
        "message": "Client 'client_name' edited successfully.",
        "success": true
    }
    ```

#### c. Delete Client (`action: "delete"`)

Deletes a WireGuard client.

  * **Request Body `data`:**
    ```json
    {
        "name": "client_name"
    }
    ```
      * `name`: Name of the client to delete.
  * **Success Response (200 OK):**
    ```json
    {
        "message": "Client 'client_name' deleted successfully.",
        "success": true
    }
    ```

#### d. Get Client Config (`action: "get_config"`)

Retrieves the WireGuard client configuration for a specific client.

  * **Request Body `data`:**
    ```json
    {
        "name": "client_name"
    }
    ```
      * `name`: Name of the client.
  * **Success Response (200 OK):**
    ```json
    {
        "message": "Client config retrieved successfully.",
        "success": true,
        "data": {
            "config": "[Interface]..." // The WireGuard client config
        }
    }
    ```

### 2\. Interface Management (`resource: "interface"`)

#### a. Create Interface (`action: "create"`)

Creates a new WireGuard interface (e.g., `wg1`, `wg2`).

  * **Request Body `data`:**
    ```json
    {
        "address_range": "10.0.1.1/24",
        "port": 51821
    }
    ```
      * `address_range`: The internal IP range for the new interface.
      * `port`: The listening port for the new interface.
  * **Success Response (200 OK):**
    ```json
    {
        "message": "New Interface Created!",
        "success": true
    }
    ```

#### b. Update Interface (`action: "update"`)

Modifies an existing WireGuard interface.

  * **Request Body `data`:**
    ```json
    {
        "name": "wg0", // e.g., 'wg0', 'wg1'
        "address": "10.0.0.1/24", // Optional
        "port": 51820, // Optional
        "status": true // Optional (true to activate, false to deactivate)
    }
    ```
      * `name`: **Required**. The name of the interface (e.g., `wg0`).
      * `address`: (Optional) New address range.
      * `port`: (Optional) New listening port.
      * `status`: (Optional) `true` to start, `false` to stop the interface.
  * **Success Response (200 OK):**
    ```json
    {
        "message": "Interface 'wg0' edited successfully.",
        "success": true
    }
    ```

#### c. Delete Interface (`action: "delete"`)

Deletes a WireGuard interface and all its associated clients.

  * **Request Body `data`:**
    ```json
    {
        "wg_id": 1 // The numeric ID of the interface (e.g., 0 for wg0, 1 for wg1)
    }
    ```
      * `wg_id`: The numeric ID of the interface to delete.
  * **Success Response (200 OK):**
    ```json
    {
        "message": "Interface wg1 and all associated clients deleted successfully.",
        "success": true
    }
    ```

### 3\. Setting Management (`resource: "setting"`)

#### a. Update Setting (`action: "update"`)

Changes a specific setting in the database.

  * **Request Body `data`:**
    ```json
    {
        "key": "server_ip",
        "value": "NEW_SERVER_IP"
    }
    ```
      * `key`: The key of the setting to update (e.g., `server_ip`, `dns`, `mtu`, `reset_time`, `auto_backup`, `telegram_bot_admin_id`, `telegram_bot_token`, `admin_card_number`, `prices`).
      * `value`: The new value for the setting. For `prices`, this should be a JSON string (e.g., `"{\"1GB\": 5000, \"1Month\": 80000}"`).
  * **Success Response (200 OK):**
    ```json
    {
        "message": "Changed!",
        "success": true
    }
    ```

### 4\. API Token Management (`resource: "api_token"`)

#### a. Create or Update API Token (`action: "create_or_update"`)

Adds a new API token or updates an existing one.

  * **Request Body `data`:**
    ```json
    {
        "name": "my_app_token",
        "token": "a_long_random_string_for_api_access"
    }
    ```
      * `name`: A name for the API token (e.g., `android_app_token`).
      * `token`: The actual token string.
  * **Success Response (200 OK):**
    ```json
    {
        "message": "API token 'my_app_token' added/updated successfully.",
        "success": true
    }
    ```

#### b. Delete API Token (`action: "delete"`)

Deletes an API token.

  * **Request Body `data`:**
    ```json
    {
        "name": "my_app_token"
    }
    ```
      * `name`: The name of the API token to delete.
  * **Success Response (200 OK):**
    ```json
    {
        "message": "API token 'my_app_token' deleted successfully.",
        "success": true
    }
    ```

### 5\. Synchronization (`resource: "sync"`)

#### a. Trigger Synchronization (`action: "trigger"`)

Manually triggers the CandyPanel's synchronization process (traffic updates, client expiry checks, etc.).

  * **Request Body `data`:** (Empty or `{}`)
    ```json
    {}
    ```
  * **Success Response (200 OK):**
    ```json
    {
        "message": "Synchronization process initiated successfully.",
        "success": true
    }
    ```

## CandyPanel Admin Endpoints (`/api/data`)

This endpoint provides a consolidated view of various CandyPanel data.

  * **Endpoint:** `/api/data`
  * **Method:** `GET`
  * **Authentication:** Required (Bearer Token)
  * **Success Response (200 OK):**
    ```json
    {
        "message": "All data retrieved successfully.",
        "success": true,
        "data": {
            "dashboard": {
                "cpu": "...",
                "mem": { "total": "...", "available": "...", "usage": "..." },
                "clients_count": ...,
                "status": "...",
                "alert": [...],
                "bandwidth": "...",
                "uptime": "...",
                "net": { "download": "...", "upload": "..." }
            },
            "clients": [
                {
                    "name": "client1",
                    "wg": 0,
                    "public_key": "...",
                    "private_key": "...",
                    "address": "...",
                    "created_at": "...",
                    "expires": "...",
                    "note": "...",
                    "traffic": "...",
                    "used_trafic": { "download": ..., "upload": ... },
                    "connected_now": false,
                    "status": true
                }
                // ... more clients
            ],
            "interfaces": [
                {
                    "wg": 0,
                    "private_key": "...",
                    "public_key": "...",
                    "port": ...,
                    "address_range": "...",
                    "status": true
                }
                // ... more interfaces
            ],
            "settings": {
                "server_ip": "...",
                "session_token": "...",
                "dns": "...",
                "admin": "{\"user\":\"admin\",\"password\":\"admin\"}",
                "status": "...",
                "alert": "[\"...\"]",
                "reset_time": "...",
                "mtu": "...",
                "bandwidth": "...",
                "uptime": "...",
                "telegram_bot_status": "...",
                "telegram_bot_admin_id": "...",
                "telegram_bot_token": "...",
                "admin_card_number": "...",
                "prices": "{\"1GB\": 4000, \"1Month\": 75000}",
                "api_tokens": "{}",
                "auto_backup": "...",
                "install": "..."
            }
        }
    }
    ```

## Telegram Bot API Endpoints (`/bot_api/*`)

These endpoints are primarily used by the Telegram bot itself, but can also be accessed by other applications (e.g., Android/Windows apps) for user-specific functionalities.

  * **Endpoint:** `/bot_api/...`
  * **Method:** `POST`
  * **Authentication:** For admin endpoints, the `telegram_id` in the request body must match the `telegram_bot_admin_id` set in the `settings` table.

### 1\. User Endpoints (`/bot_api/user/*`)

#### a. Register User (`/bot_api/user/register`)

Registers a new Telegram user in the bot's database.

  * **Request Body (JSON):**
    ```json
    {
        "telegram_id": 123456789
    }
    ```
  * **Success Response (200 OK):**
    ```json
    {
        "message": "User registered successfully.",
        "success": true,
        "data": {
            "registered": true
        }
    }
    ```

#### b. Buy Traffic Request (`/bot_api/user/buy_traffic_request`)

Handles requests for buying traffic, including price calculation and submitting payment requests.

  * **Request Body (JSON):**
    ```json
    {
        "telegram_id": 123456789,
        "purchase_type": "gb",    // "gb" or "month"
        "quantity": 10,           // e.g., 10 GB or 3 months
        "order_id": "UNIQUE_ORDER_ID", // Required for final payment submission
        "card_number_sent": "User confirmed payment" // Required for final payment submission
    }
    ```
      * `order_id` and `card_number_sent` are optional for the initial request (to get prices), but required for the final submission after payment.
  * **Success Response (200 OK):**
    ```json
    {
        "message": "Purchase request submitted. Admin will review.",
        "success": true,
        "data": {
            "admin_card_number": "YOUR_ADMIN_CARD_NUMBER",
            "prices": {
                "1GB": 4000,
                "1Month": 75000
            },
            "admin_telegram_id": "YOUR_ADMIN_TELEGRAM_ID",
            "calculated_amount": 40000.0 // Price in Toman for 10GB
        }
    }
    ```

#### c. Get License (`/bot_api/user/get_license`)

Retrieves the WireGuard configuration for the user's assigned client.

  * **Request Body (JSON):**
    ```json
    {
        "telegram_id": 123456789
    }
    ```
  * **Success Response (200 OK):**
    ```json
    {
        "message": "Your WireGuard configuration:",
        "success": true,
        "data": {
            "config": "[Interface]..." // WireGuard client config
        }
    }
    ```

#### d. Account Status (`/bot_api/user/account_status`)

Retrieves the user's account status, including traffic and expiry details.

  * **Request Body (JSON):**
    ```json
    {
        "telegram_id": 123456789
    }
    ```
  * **Success Response (200 OK):**
    ```json
    {
        "message": "Your account status:",
        "success": true,
        "data": {
            "status": "active",
            "traffic_bought_gb": 10.0,
            "time_bought_days": 365,
            "candy_client_name": "user_123456789_1678888888",
            "used_traffic_bytes": 1234567890,
            "expires": "2025-12-31T23:59:59",
            "traffic_limit_bytes": 10737418240,
            "note": "Optional note if client data is outdated"
        }
    }
    ```

#### e. Call Support (`/bot_api/user/call_support`)

Sends a support message to the admin.

  * **Request Body (JSON):**
    ```json
    {
        "telegram_id": 123456789,
        "message": "My internet is very slow."
    }
    ```
  * **Success Response (200 OK):**
    ```json
    {
        "message": "Your message has been sent to support.",
        "success": true,
        "data": {
            "admin_telegram_id": "YOUR_ADMIN_TELEGRAM_ID",
            "support_message": "Support request from User 123456789 (ID: 123456789):\n\nMy internet is very slow."
        }
    }
    ```

### 2\. Admin Endpoints (`/bot_api/admin/*`)

These endpoints require the `telegram_id` in the request body to match the `telegram_bot_admin_id` setting.

#### a. Check Admin Status (`/bot_api/admin/check_admin`)

Checks if a given Telegram ID is configured as the bot admin.

  * **Request Body (JSON):**
    ```json
    {
        "telegram_id": 987654321
    }
    ```
  * **Success Response (200 OK):**
    ```json
    {
        "message": "Admin status checked.",
        "success": true,
        "data": {
            "is_admin": true, // or false
            "admin_telegram_id": "YOUR_ADMIN_TELEGRAM_ID"
        }
    }
    ```

#### b. Get All Users (`/bot_api/admin/get_all_users`)

Retrieves a list of all registered bot users.

  * **Request Body (JSON):**
    ```json
    {
        "telegram_id": 987654321 // Admin's Telegram ID
    }
    ```
  * **Success Response (200 OK):**
    ```json
    {
        "message": "All bot users retrieved.",
        "success": true,
        "data": {
            "users": [
                {
                    "telegram_id": 123456789,
                    "candy_client_name": "user_123456789_1678888888",
                    "traffic_bought_gb": 10.0,
                    "time_bought_days": 365,
                    "status": "active",
                    "is_admin": 0,
                    "created_at": "2023-01-01T10:00:00"
                }
                // ... more users
            ]
        }
    }
    ```

#### c. Get Transactions (`/bot_api/admin/get_transactions`)

Retrieves a list of transactions, with optional status filtering.

  * **Request Body (JSON):**
    ```json
    {
        "telegram_id": 987654321, // Admin's Telegram ID
        "status_filter": "pending" // Optional: "pending", "approved", "rejected", "all"
    }
    ```
  * **Success Response (200 OK):**
    ```json
    {
        "message": "Transactions retrieved.",
        "success": true,
        "data": {
            "transactions": [
                {
                    "order_id": "ORDER123",
                    "telegram_id": 123456789,
                    "amount": 40000.0,
                    "card_number_sent": "User confirmed payment",
                    "status": "pending",
                    "requested_at": "2023-01-05T11:30:00",
                    "approved_at": null,
                    "admin_note": null,
                    "purchase_type": "gb",
                    "quantity": 10.0
                }
                // ... more transactions
            ]
        }
    }
    ```

#### d. Approve Transaction (`/bot_api/admin/approve_transaction`)

Approves a pending transaction, creates a WireGuard client, and updates user/transaction records.

  * **Request Body (JSON):**
    ```json
    {
        "telegram_id": 987654321, // Admin's Telegram ID
        "order_id": "ORDER123",
        "admin_note": "Payment confirmed, client created." // Optional
    }
    ```
  * **Success Response (200 OK):**
    ```json
    {
        "message": "Transaction ORDER123 approved. Client 'user_123456789_1678888888' created in CandyPanel.",
        "success": true,
        "data": {
            "client_config": "[Interface]...", // The generated WireGuard client config
            "telegram_id": 123456789, // Telegram ID of the user whose transaction was approved
            "client_name": "user_123456789_1678888888"
        }
    }
    ```

#### e. Reject Transaction (`/bot_api/admin/reject_transaction`)

Rejects a pending transaction.

  * **Request Body (JSON):**
    ```json
    {
        "telegram_id": 987654321, // Admin's Telegram ID
        "order_id": "ORDER123",
        "admin_note": "Insufficient funds." // Optional
    }
    ```
  * **Success Response (200 OK):**
    ```json
    {
        "message": "Transaction ORDER123 rejected.",
        "success": true,
        "data": {
            "telegram_id": 123456789 // Telegram ID of the user whose transaction was rejected
        }
    }
    ```

#### f. Manage User (`/bot_api/admin/manage_user`)

Performs actions like banning, unbanning, updating traffic, or updating time for a user.

  * **Request Body (JSON):**
    ```json
    {
        "admin_telegram_id": 987654321,
        "target_telegram_id": 123456789,
        "action": "ban", // "ban", "unban", "update_traffic", "update_time"
        "value": 50 // Required for "update_traffic" (GB) or "update_time" (DAYS)
    }
    ```
  * **Success Response (200 OK):**
    ```json
    {
        "message": "User 123456789 has been banned.",
        "success": true
    }
    ```

#### g. Send Message to All (`/bot_api/admin/send_message_to_all`)

Prepares a broadcast message to be sent to all bot users by the Telegram bot.

  * **Request Body (JSON):**
    ```json
    {
        "telegram_id": 987654321, // Admin's Telegram ID
        "message": "Important announcement: Server maintenance at 2 AM UTC."
    }
    ```
  * **Success Response (200 OK):**
    ```json
    {
        "message": "Broadcast message prepared.",
        "success": true,
        "data": {
            "target_user_ids": [123456789, 123456790, ...], // List of Telegram IDs
            "message": "Important announcement: Server maintenance at 2 AM UTC."
        }
    }
    ```

#### h. Server Control (`/bot_api/admin/server_control`)

A passthrough endpoint for admin Telegram commands to interact with the core CandyPanel functionalities. This mirrors the `/api/manage` endpoint's structure but is accessed by the bot.

  * **Request Body (JSON):**
    ```json
    {
        "admin_telegram_id": 987654321, // Admin's Telegram ID
        "resource": "client", // e.g., "client", "interface", "setting", "sync"
        "action": "create",   // e.g., "create", "update", "delete", "get_config", "trigger"
        "data": {
            // Data specific to the resource and action, same as /api/manage
            "name": "new_client",
            "expires": "2025-01-01T00:00:00",
            "traffic": "10737418240"
        }
    }
    ```
  * **Success Response (200 OK):**
    ```json
    {
        "message": "CandyPanel: Client created successfully!",
        "success": true,
        "data": {
            "client_config": "[Interface]..." // Or other data depending on the action
        }
    }
    ```
  * **Error Response (500 Internal Server Error / 400 Bad Request):**
    ```json
    {
        "message": "CandyPanel Error: Failed to create client in CandyPanel: Client with this name already exists.",
        "success": false
    }
    ```

## Response Formats

### Success Response

All successful API responses follow this format:

```json
{
    "message": "A descriptive success message.",
    "success": true,
    "data": {
        // Optional: Any relevant data returned by the endpoint
    }
}
```

### Error Response

All error API responses follow this format:

```json
{
    "message": "A descriptive error message explaining what went wrong.",
    "success": false
}
```