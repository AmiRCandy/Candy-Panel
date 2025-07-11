import time
import httpx
import json
import os
import re
from pyrogram import Client, filters 
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message

# --- Configuration ---
UNIFIED_API_URL = F"http://127.0.0.1:{os.environ.get('AP_PORT',3446)}"


user_states = {} # {telegram_id: {"step": "await_amount_type" | "await_quantity" | "await_custom_plan_input" | "await_order_id", "purchase_type": "gb" | "month" | "custom", "quantity": int | float, "time_quantity": int | float, "traffic_quantity": int | float, "calculated_price": float }}

# --- Helper Functions for API Calls ---
async def call_unified_api(endpoint: str, payload: dict):
    """Makes an asynchronous POST request to the unified API."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{UNIFIED_API_URL}{endpoint}", json=payload, timeout=30)
            response.raise_for_status() # Raise an exception for 4xx/5xx responses
            return response.json()
    except httpx.HTTPStatusError as e:
        print(f"[-] HTTP error calling unified API {endpoint}: {e.response.status_code} - {e.response.text}")
        return {"success": False, "message": f"API error: {e.response.text}"}
    except httpx.RequestError as e:
        print(f"[-] Network error calling unified API {endpoint}: {e}")
        return {"success": False, "message": f"Network error: {e}"}
    except Exception as e:
        print(f"[-] Unexpected error calling unified API {endpoint}: {e}")
        return {"success": False, "message": f"Unexpected error: {e}"}

def get_bot_token_api_from_unified_api():
    """Fetches the bot token from the unified API's settings."""
    try:
        from db import SQLite
        db = SQLite()
        token_setting = db.get('settings', where={'key': 'telegram_bot_token'})
        api_id = db.get('settings', where={'key': 'telegram_api_id'})
        api_hash = db.get('settings', where={'key': 'telegram_api_hash'})
        return token_setting['value'] if token_setting else None , api_id['value'] if api_id else None, api_hash['value'] if api_hash else None
    except Exception as e:
        print(f"Error fetching bot token from unified API: {e}")
        return None

# --- Pyrogram Client Initialization ---
btoken,bapiid,bapihash = get_bot_token_api_from_unified_api()
if (not btoken or btoken == 'YOUR_TELEGRAM_BOT_TOKEN') or (not bapiid or bapiid == 'YOUR_TELEGRAM_API_ID') or (not bapihash or bapihash == 'YOUR_TELEGRAM_API_HASH') :
    print("ERROR: Telegram bot token not found or is default. Please configure it in CandyPanel.db via main.py settings.")
    exit(1)
app = Client(
    "candy_panel_bot",
    api_id=bapiid,
    api_hash=bapihash,
    bot_token=btoken
)

# Initialize the client outside of main() to make it accessible to handlers
app = None # Will be initialized in main

# --- Keyboards ---
user_menu_keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("💰 Buy Traffic", callback_data="buy_traffic")],
    [InlineKeyboardButton("🔑 Get License", callback_data="get_license")],
    [InlineKeyboardButton("📊 Account Status", callback_data="account_status")],
    [InlineKeyboardButton("📞 Call Support", callback_data="call_support")]
])

admin_menu_keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("👥 Manage Users", callback_data="admin_manage_users")],
    [InlineKeyboardButton("💲 Manage Transactions", callback_data="admin_manage_transactions")],
    [InlineKeyboardButton("📢 Send Broadcast", callback_data="admin_send_broadcast")],
    [InlineKeyboardButton("⚙️ Server Control", callback_data="admin_server_control")]
])

buy_traffic_type_keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("Buy by GB", callback_data="buy_by_gb")],
    [InlineKeyboardButton("Buy by Month", callback_data="buy_by_month")],
    [InlineKeyboardButton("Custom Plan", callback_data="buy_custom_plan")] # New: Custom Plan
])

# --- Handlers ---

@Client.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    telegram_id = message.from_user.id
    username = message.from_user.username if message.from_user.username else message.from_user.first_name

    # Register user with unified API
    response = await call_unified_api("/bot_api/user/register", {"telegram_id": telegram_id})

    if response.get('success'):
        await message.reply_text(
            f"Hello {username}! Welcome to CandyPanel Bot.\n\n"
            "Please choose an option:",
            reply_markup=user_menu_keyboard
        )
    else:
        await message.reply_text(f"Error registering you: {response.get('message', 'Unknown error')}")

@Client.on_message(filters.command("adminlogin"))
async def admin_login_command(client: Client, message: Message):
    telegram_id = message.from_user.id
    
    # Get admin ID from unified API
    admin_check_resp = await call_unified_api("/bot_api/admin/check_admin", {"telegram_id": telegram_id}) 
    admin_telegram_id = admin_check_resp.get('data', {}).get('admin_telegram_id')

    if str(telegram_id) == admin_telegram_id:
        # Fetch dashboard data
        dashboard_resp = await call_unified_api("/api/data", {}) # /api/data is a GET, but call_unified_api uses POST, so empty payload is fine.
        
        status_message = "You are logged in as admin.\n\n"
        if dashboard_resp.get('success') and 'dashboard' in dashboard_resp.get('data', {}):
            dashboard = dashboard_resp['data']['dashboard']
            
            status_message += "📊 **Server Status Overview:**\n"
            status_message += f"CPU Usage: `{dashboard.get('cpu', 'N/A')}`\n"
            status_message += f"Memory Usage: `{dashboard.get('mem', {}).get('usage', 'N/A')}`\n"
            status_message += f"Clients Connected: `{dashboard.get('clients_count', 'N/A')}`\n"
            status_message += f"Server Uptime: `{dashboard.get('uptime', 'N/A')}`\n"
            status_message += f"Download Speed: `{dashboard.get('net', {}).get('download', 'N/A')}`\n"
            status_message += f"Upload Speed: `{dashboard.get('net', {}).get('upload', 'N/A')}`\n"
            status_message += f"Overall Status: `{dashboard.get('status', 'N/A')}`\n"
            
            if dashboard.get('alert'):
                try:
                    alerts = json.loads(dashboard['alert'])
                    if alerts:
                        status_message += "\n🚨 **Alerts:**\n" + "\n".join(alerts)
                except (json.JSONDecodeError, TypeError):
                    status_message += f"\n🚨 **Alert:** {dashboard['alert']}\n"
            
        else:
            status_message += "Failed to fetch server status. Please check API connectivity."

        await message.reply_text(status_message, reply_markup=admin_menu_keyboard)
    else:
        await message.reply_text("You are not authorized to use admin commands.")

@Client.on_callback_query()
async def callback_query_handler(client: Client, callback_query):
    data = callback_query.data
    telegram_id = callback_query.from_user.id
    message = callback_query.message

    # Clear user state if they click a main menu button after being in a multi-step flow
    if data in ["buy_traffic", "get_license", "account_status", "call_support",
                "admin_manage_users", "admin_manage_transactions", "admin_send_broadcast", "admin_server_control"]:
        if telegram_id in user_states:
            del user_states[telegram_id]

    # Check admin status for admin actions
    is_admin_resp = await call_unified_api("/bot_api/admin/check_admin", {"telegram_id": telegram_id})
    is_admin = is_admin_resp.get('data', {}).get('is_admin', False)

    if data == "buy_traffic":
        # Initial request to get prices and card number (dummy values for purchase_type/quantity)
        response = await call_unified_api("/bot_api/user/buy_traffic_request", {
            "telegram_id": telegram_id,
            "purchase_type": "gb", # Default to GB for initial price display
            "quantity": 1, # Default quantity for initial price display
            "order_id": "dummy",
            "card_number_sent": "dummy"
        })
        if response.get('success'):
            admin_card_number = response['data']['admin_card_number']
            prices = response['data']['prices']
            price_text = "\n".join([f"- {k}: {v} (Toman)" for k, v in prices.items()])
            
            await message.edit_text(
                f"To buy traffic, please transfer the desired amount to this card number:\n"
                f"💳 **Card Number:** `{admin_card_number}`\n\n"
                f"**Available Plans (Prices in Toman):**\n{price_text}\n\n"
                f"Please choose how you'd like to buy:",
                reply_markup=buy_traffic_type_keyboard
            )
            user_states[telegram_id] = {"step": "await_amount_type"}
        else:
            await message.edit_text(f"Error fetching payment details: {response.get('message', 'Unknown error')}")

    elif data == "buy_by_gb":
        user_states[telegram_id] = {"step": "await_quantity", "purchase_type": "gb"}
        await message.edit_text("How many **GB** do you want to buy? (e.g., `10`, `20`)")
    
    elif data == "buy_by_month":
        user_states[telegram_id] = {"step": "await_quantity", "purchase_type": "month"}
        await message.edit_text("How many **months** do you want to buy? (e.g., `1`, `3`)")

    elif data == "buy_custom_plan":
        user_states[telegram_id] = {"step": "await_custom_plan_input", "purchase_type": "custom"}
        await message.edit_text(
            "Please enter your desired plan in the format: `[time]month [traffic]gb`\n"
            "Examples: `1 month 10gb`, `5gb 2months`, `10gb`, `3months`"
        )

    elif data == "get_license":
        response = await call_unified_api("/bot_api/user/get_license", {"telegram_id": telegram_id})
        if response.get('success'):
            config = response['data']['config']
            await message.edit_text(
                "Here is your WireGuard configuration:\n\n"
                f"```\n{config}\n```\n\n"
                "Save this as a `.conf` file and import it into your WireGuard client."
            )
        else:
            await message.edit_text(f"Error getting license: {response.get('message', 'Unknown error')}")

    elif data == "account_status":
        response = await call_unified_api("/bot_api/user/account_status", {"telegram_id": telegram_id})
        if response.get('success'):
            status_data = response['data']
            used_traffic_bytes = status_data.get('used_traffic_bytes', 0)
            traffic_limit_bytes = status_data.get('traffic_limit_bytes', 0)
            
            used_traffic_gb = used_traffic_bytes / (1024**3)
            traffic_limit_gb = traffic_limit_bytes / (1024**3)

            status_text = (
                f"**Account Status:**\n"
                f"Status: `{status_data['status']}`\n"
                f"Client Name: `{status_data.get('candy_client_name', 'N/A')}`\n"
                f"Bought Traffic: `{status_data['traffic_bought_gb']:.2f} GB`\n"
                f"Used Traffic: `{used_traffic_gb:.2f} GB` (out of `{traffic_limit_gb:.2f} GB`)\n"
                f"Bought Time: `{status_data['time_bought_days']} days`\n"
                f"Expires: `{status_data.get('expires', 'N/A')}`\n"
            )
            if status_data.get('note'):
                status_text += f"\nNote: {status_data['note']}"
            await message.edit_text(status_text)
        else:
            await message.edit_text(f"Error getting account status: {response.get('message', 'Unknown error')}")

    elif data == "call_support":
        await message.edit_text(
            "Please type your support message after the `/support` command.\n"
            "Example: `/support My internet is slow.`"
        )
    
    # --- Admin Callbacks ---
    elif is_admin:
        if data == "admin_manage_users":
            response = await call_unified_api("/bot_api/admin/get_all_users", {"telegram_id": telegram_id})
            if response.get('success'):
                users = response['data']['users']
                if not users:
                    await message.edit_text("No users found.")
                    return
                
                user_list_text = "📊 **All Bot Users:**\n\n"
                for user in users:
                    user_list_text += (
                        f"ID: `{user['telegram_id']}`\n"
                        f"Client Name: `{user.get('candy_client_name', 'N/A')}`\n"
                        f"Status: `{user['status']}`\n"
                        f"Traffic Bought: `{user['traffic_bought_gb']:.2f} GB`\n"
                        f"Time Bought: `{user['time_bought_days']} days`\n"
                        f"Created At: `{user['created_at']}`\n"
                        f"--------------------\n"
                    )
                await message.edit_text(user_list_text)
                await message.reply_text(
                    "To manage a user, use commands:\n"
                    "`/ban <TELEGRAM_ID>`\n"
                    "`/unban <TELEGRAM_ID>`\n"
                    "`/update_traffic <TELEGRAM_ID> <GB>`\n"
                    "`/update_time <TELEGRAM_ID> <DAYS>`"
                )
            else:
                await message.edit_text(f"Error fetching users: {response.get('message', 'Unknown error')}")

        elif data == "admin_manage_transactions":
            response = await call_unified_api("/bot_api/admin/get_transactions", {"telegram_id": telegram_id, "status_filter": "pending"})
            if response.get('success'):
                transactions = response['data']['transactions']
                if not transactions:
                    await message.edit_text("No pending transactions.")
                    return
                
                trans_list_text = "💲 **Pending Transactions:**\n\n"
                for trans in transactions:
                    purchase_details = ""
                    if trans.get('purchase_type') == 'custom':
                        purchase_details = f"Time: `{trans.get('time_quantity', 0)} months`, Traffic: `{trans.get('traffic_quantity', 0)} GB`"
                    else:
                        purchase_details = f"Type: `{trans.get('purchase_type', 'N/A')}`, Quantity: `{trans.get('quantity', 'N/A')}`"

                    trans_list_text += (
                        f"Order ID: `{trans['order_id']}`\n"
                        f"User ID: `{trans['telegram_id']}`\n"
                        f"Amount: `{trans['amount']}`\n"
                        f"{purchase_details}\n"
                        f"Card Sent: `{trans['card_number_sent']}`\n"
                        f"Requested At: `{trans['requested_at']}`\n"
                        f"--------------------\n"
                    )
                await message.edit_text(trans_list_text)
                await message.reply_text(
                    "To approve/reject:\n"
                    "`/approve <ORDER_ID> [ADMIN_NOTE]`\n"
                    "`/reject <ORDER_ID> [ADMIN_NOTE]`"
                )
            else:
                await message.edit_text(f"Error fetching transactions: {response.get('message', 'Unknown error')}")

        elif data == "admin_send_broadcast":
            await message.edit_text(
                "Please type the message you want to broadcast after the `/broadcast` command.\n"
                "Example: `/broadcast Server maintenance tonight.`"
            )

        elif data == "admin_server_control":
            await message.edit_text(
                "⚙️ **Server Control Options (via CandyPanel API):**\n"
                "Use the following commands:\n\n"
                "**Clients:**\n"
                "`/cp_new_client <name> <expires_iso> <traffic_bytes> [wg_id] [note]`\n"
                "`/cp_edit_client <name> [expires_iso] [traffic_bytes] [status_bool] [note]`\n"
                "`/cp_delete_client <name>`\n"
                "`/cp_get_config <name>`\n\n"
                "**Interfaces:**\n"
                "`/cp_new_interface <address_range> <port>`\n"
                "`/cp_edit_interface <name_wgX> [address] [port] [status_bool]`\n"
                "`/cp_delete_interface <wg_id>`\n\n"
                "**Settings:**\n"
                "`/cp_change_setting <key> <value>`\n\n"
                "**Sync:**\n"
                "`/cp_trigger_sync`\n\n"
                "**Example:** `/cp_new_client testuser 2025-12-31T23:59:59 10737418240 0 This is a test` (10GB traffic)"
            )
    else:
        await message.edit_text("You are not authorized to perform this action.")


@Client.on_message(filters.text & filters.private & ~filters.command(["start", "adminlogin", "bought", "support", "approve", "reject", "ban", "unban", "update_traffic", "update_time", "broadcast", "cp_new_client", "cp_edit_client", "cp_delete_client", "cp_get_config", "cp_new_interface", "cp_edit_interface", "cp_delete_interface", "cp_change_setting", "cp_trigger_sync"]))
async def handle_quantity_input(client: Client, message: Message):
    telegram_id = message.from_user.id
    current_state = user_states.get(telegram_id)

    if current_state and current_state["step"] == "await_quantity":
        try:
            quantity = float(message.text.strip())
            if quantity <= 0:
                await message.reply_text("Quantity must be a positive number. Please try again.")
                return

            current_state["quantity"] = quantity
            purchase_type = current_state["purchase_type"]

            # Call unified API to get the calculated price
            response = await call_unified_api("/bot_api/user/buy_traffic_request", {
                "telegram_id": telegram_id,
                "purchase_type": purchase_type,
                "quantity": quantity,
                "order_id": "dummy", # Still dummy for price calculation
                "card_number_sent": "dummy" # Still dummy for price calculation
            })

            if response.get('success'):
                calculated_amount = response['data']['calculated_amount']
                current_state["calculated_price"] = calculated_amount
                current_state["step"] = "await_order_id"
                
                await message.reply_text(
                    f"You want to buy `{quantity} {purchase_type.upper()}` for `{calculated_amount:.2f}` Toman.\n\n"
                    f"Please proceed with the payment to the admin's card number (provided earlier).\n"
                    f"After transfer, reply with your **Order ID** (the reference number from your transaction) "
                    f"using the command: `/bought <ORDER_ID>`"
                )
            else:
                await message.reply_text(f"Error calculating price: {response.get('message', 'Unknown error')}")
                if telegram_id in user_states:
                    del user_states[telegram_id] # Clear state on error
        except ValueError:
            await message.reply_text("Invalid quantity. Please enter a number (e.g., `10` or `1.5`).")
        except Exception as e:
            await message.reply_text(f"An unexpected error occurred: {e}")
            if telegram_id in user_states:
                del user_states[telegram_id] # Clear state on error
    
    elif current_state and current_state["step"] == "await_custom_plan_input":
        text_input = message.text.strip().lower()
        time_match = re.search(r'(\d+)\s*(month|months)', text_input)
        traffic_match = re.search(r'(\d+)\s*(gb|gigs)', text_input)

        time_qty = float(time_match.group(1)) if time_match else 0
        traffic_qty = float(traffic_match.group(1)) if traffic_match else 0

        if time_qty == 0 and traffic_qty == 0:
            await message.reply_text(
                "I couldn't understand your custom plan. Please use the format `[time]month [traffic]gb`.\n"
                "Examples: `1 month 10gb`, `5gb 2months`, `10gb`, `3months`"
            )
            return

        current_state["time_quantity"] = time_qty
        current_state["traffic_quantity"] = traffic_qty
        current_state["purchase_type"] = "custom" # Ensure type is set to custom

        # Call unified API to get the calculated price for custom plan
        response = await call_unified_api("/bot_api/user/buy_traffic_request", {
            "telegram_id": telegram_id,
            "purchase_type": "custom",
            "time_quantity": time_qty,
            "traffic_quantity": traffic_qty,
            "order_id": "dummy", # Still dummy for price calculation
            "card_number_sent": "dummy" # Still dummy for price calculation
        })

        if response.get('success'):
            calculated_amount = response['data']['calculated_amount']
            current_state["calculated_price"] = calculated_amount
            current_state["step"] = "await_order_id"
            
            await message.reply_text(
                f"You want a custom plan: `{time_qty} months, {traffic_qty} GB` for `{calculated_amount:.2f}` Toman.\n\n"
                f"Please proceed with the payment to the admin's card number (provided earlier).\n"
                f"After transfer, reply with your **Order ID** (the reference number from your transaction) "
                f"using the command: `/bought <ORDER_ID>`"
            )
        else:
            await message.reply_text(f"Error calculating price for custom plan: {response.get('message', 'Unknown error')}")
            if telegram_id in user_states:
                del user_states[telegram_id] # Clear state on error
    else:
        # If not in a multi-step flow, or not the expected step, just ignore or prompt main menu
        await message.reply_text("I'm not sure how to respond to that. Please use the menu buttons or /start.", reply_markup=user_menu_keyboard)


@Client.on_message(filters.command("bought") & filters.private)
async def handle_bought_command(client: Client, message: Message):
    telegram_id = message.from_user.id
    
    if telegram_id not in user_states or user_states[telegram_id]["step"] != "await_order_id":
        await message.reply_text("Please start a purchase process first by clicking 'Buy Traffic'.")
        return

    try:
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.reply_text("Usage: `/bought <ORDER_ID>`")
            return
        order_id = parts[1]
        
        # Retrieve purchase details from user_states
        purchase_type = user_states[telegram_id]["purchase_type"]
        calculated_amount = user_states[telegram_id]["calculated_price"]
        
        # Prepare payload based on purchase type
        payload_data = {
            "telegram_id": telegram_id,
            "amount": calculated_amount,
            "order_id": order_id,
            "card_number_sent": "User confirmed payment",
            "purchase_type": purchase_type
        }

        if purchase_type == 'gb' or purchase_type == 'month':
            payload_data["quantity"] = user_states[telegram_id]["quantity"]
        elif purchase_type == 'custom':
            payload_data["time_quantity"] = user_states[telegram_id]["time_quantity"]
            payload_data["traffic_quantity"] = user_states[telegram_id]["traffic_quantity"]

        response = await call_unified_api("/bot_api/user/buy_traffic_request", payload_data)

        if response.get('success'):
            admin_telegram_id = response['data']['admin_telegram_id']
            
            purchase_summary = ""
            if purchase_type == 'gb' or purchase_type == 'month':
                purchase_summary = f"Type: `{purchase_type.upper()}`, Quantity: `{user_states[telegram_id]['quantity']}`"
            elif purchase_type == 'custom':
                purchase_summary = f"Type: `Custom`, Time: `{user_states[telegram_id]['time_quantity']} months`, Traffic: `{user_states[telegram_id]['traffic_quantity']} GB`"

            if admin_telegram_id != '0':
                await client.send_message(
                    chat_id=int(admin_telegram_id),
                    text=f"🚨 **New Payment Request!**\n\n"
                         f"User: `{message.from_user.first_name} (ID: {telegram_id})`\n"
                         f"Order ID: `{order_id}`\n"
                         f"Amount: `{calculated_amount:.2f}` Toman\n"
                         f"{purchase_summary}\n"
                         f"Status: `Pending`\n\n"
                         f"Please verify the payment and use `/approve {order_id} [ADMIN_NOTE]` or `/reject {order_id} [ADMIN_NOTE]`"
                )
            await message.reply_text(
                "Your purchase request has been submitted. The admin will review it shortly."
            )
        else:
            await message.reply_text(f"Error submitting request: {response.get('message', 'Unknown error')}")
    except Exception as e:
        await message.reply_text(f"An unexpected error occurred: {e}")
    finally:
        if telegram_id in user_states:
            del user_states[telegram_id] # Always clear state after /bought command

@Client.on_message(filters.command("support") & filters.private)
async def handle_support_command(client: Client, message: Message):
    telegram_id = message.from_user.id
    support_message = message.text.split(maxsplit=1)
    if len(support_message) < 2:
        await message.reply_text("Please provide a message for support. Example: `/support My connection is slow.`")
        return

    response = await call_unified_api("/bot_api/user/call_support", {
        "telegram_id": telegram_id,
        "message": support_message[1]
    })

    if response.get('success'):
        admin_telegram_id = response['data']['admin_telegram_id']
        support_text_to_admin = response['data']['support_message']
        if admin_telegram_id != '0':
            await client.send_message(chat_id=int(admin_telegram_id), text=support_text_to_admin)
        await message.reply_text("Your support message has been sent to the admin.")
    else:
        await message.reply_text(f"Error sending support message: {response.get('message', 'Unknown error')}")

@Client.on_message(filters.command("approve") & filters.private)
async def admin_approve_transaction_command(client: Client, message: Message):
    telegram_id = message.from_user.id
    parts = message.text.split(maxsplit=2)
    if len(parts) < 2:
        await message.reply_text("Usage: `/approve <ORDER_ID> [ADMIN_NOTE]`")
        return

    try:
        order_id = parts[1]
        admin_note = parts[2] if len(parts) > 2 else ""

        response = await call_unified_api("/bot_api/admin/approve_transaction", {
            "telegram_id": telegram_id,
            "order_id": order_id,
            "admin_note": admin_note
        })

        if response.get('success'):
            target_telegram_id = response['data']['telegram_id']
            client_config = response['data'].get('client_config')
            client_name = response['data'].get('client_name') # Get client name from API response
            await message.reply_text(f"Transaction {order_id} approved. Client '{client_name}' created.")
            
            # Send config to user
            if client_config:
                await client.send_message(
                    chat_id=target_telegram_id,
                    text=f"🎉 **Your purchase has been approved!**\n\n"
                         f"Here is your WireGuard configuration:\n\n"
                         f"```\n{client_config}\n```\n\n"
                         f"Save this as a `.conf` file and import it into your WireGuard client."
                )
            else:
                await client.send_message(
                    chat_id=target_telegram_id,
                    text=f"🎉 **Your purchase has been approved!**\n"
                         f"Your client name is `{client_name}`. You can get your config using /license."
                )
        else:
            await message.reply_text(f"Error approving transaction: {response.get('message', 'Unknown error')}")
    except Exception as e:
        await message.reply_text(f"An unexpected error occurred: {e}")

@Client.on_message(filters.command("reject") & filters.private)
async def admin_reject_transaction_command(client: Client, message: Message):
    telegram_id = message.from_user.id
    parts = message.text.split(maxsplit=2)
    if len(parts) < 2:
        await message.reply_text("Usage: `/reject <ORDER_ID> [ADMIN_NOTE]`")
        return

    try:
        order_id = parts[1]
        admin_note = parts[2] if len(parts) > 2 else ""

        response = await call_unified_api("/bot_api/admin/reject_transaction", {
            "telegram_id": telegram_id,
            "order_id": order_id,
            "admin_note": admin_note
        })

        if response.get('success'):
            target_telegram_id = response['data']['telegram_id']
            await message.reply_text(f"Transaction {order_id} rejected.")
            await client.send_message(
                chat_id=target_telegram_id,
                text=f"😔 **Your purchase request (Order ID: {order_id}) has been rejected.**\n"
                     f"Admin Note: {admin_note if admin_note else 'No specific reason provided.'}"
            )
        else:
            await message.reply_text(f"Error rejecting transaction: {response.get('message', 'Unknown error')}")
    except Exception as e:
        await message.reply_text(f"An unexpected error occurred: {e}")

@Client.on_message(filters.command("ban") & filters.private)
async def admin_ban_user_command(client: Client, message: Message):
    telegram_id = message.from_user.id
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply_text("Usage: `/ban <TELEGRAM_ID>`")
        return
    try:
        target_telegram_id = int(parts[1])
        response = await call_unified_api("/bot_api/admin/manage_user", {
            "admin_telegram_id": telegram_id,
            "target_telegram_id": target_telegram_id,
            "action": "ban"
        })
        await message.reply_text(response.get('message', 'Unknown error'))
    except ValueError:
        await message.reply_text("Invalid Telegram ID. Must be an integer.")
    except Exception as e:
        await message.reply_text(f"An unexpected error occurred: {e}")

@Client.on_message(filters.command("unban") & filters.private)
async def admin_unban_user_command(client: Client, message: Message):
    telegram_id = message.from_user.id
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply_text("Usage: `/unban <TELEGRAM_ID>`")
        return
    try:
        target_telegram_id = int(parts[1])
        response = await call_unified_api("/bot_api/admin/manage_user", {
            "admin_telegram_id": telegram_id,
            "target_telegram_id": target_telegram_id,
            "action": "unban"
        })
        await message.reply_text(response.get('message', 'Unknown error'))
    except ValueError:
        await message.reply_text("Invalid Telegram ID. Must be an integer.")
    except Exception as e:
        await message.reply_text(f"An unexpected error occurred: {e}")

@Client.on_message(filters.command("update_traffic") & filters.private)
async def admin_update_traffic_command(client: Client, message: Message):
    telegram_id = message.from_user.id
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.reply_text("Usage: `/update_traffic <TELEGRAM_ID> <GB>`")
        return
    try:
        target_telegram_id = int(parts[1])
        traffic_gb = float(parts[2])
        response = await call_unified_api("/bot_api/admin/manage_user", {
            "admin_telegram_id": telegram_id,
            "target_telegram_id": target_telegram_id,
            "action": "update_traffic",
            "value": traffic_gb
        })
        await message.reply_text(response.get('message', 'Unknown error'))
    except ValueError:
        await message.reply_text("Invalid Telegram ID or traffic amount. Traffic must be a number.")
    except Exception as e:
        await message.reply_text(f"An unexpected error occurred: {e}")

@Client.on_message(filters.command("update_time") & filters.private)
async def admin_update_time_command(client: Client, message: Message):
    telegram_id = message.from_user.id
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.reply_text("Usage: `/update_time <TELEGRAM_ID> <DAYS>`")
        return
    try:
        target_telegram_id = int(parts[1])
        time_days = int(parts[2])
        response = await call_unified_api("/bot_api/admin/manage_user", {
            "admin_telegram_id": telegram_id,
            "target_telegram_id": target_telegram_id,
            "action": "update_time",
            "value": time_days
        })
        await message.reply_text(response.get('message', 'Unknown error'))
    except ValueError:
        await message.reply_text("Invalid Telegram ID or time in days. Time must be an integer.")
    except Exception as e:
        await message.reply_text(f"An unexpected error occurred: {e}")

@Client.on_message(filters.command("broadcast") & filters.private)
async def admin_broadcast_command(client: Client, message: Message):
    telegram_id = message.from_user.id
    broadcast_message = message.text.split(maxsplit=1)
    if len(broadcast_message) < 2:
        await message.reply_text("Please provide a message to broadcast. Example: `/broadcast Server will be down for maintenance.`")
        return

    response = await call_unified_api("/bot_api/admin/send_message_to_all", {
        "telegram_id": telegram_id,
        "message": broadcast_message[1]
    })

    if response.get('success'):
        target_user_ids = response['data']['target_user_ids']
        message_to_send = response['data']['message']
        
        sent_count = 0
        for user_id in target_user_ids:
            try:
                await client.send_message(chat_id=user_id, text=f"📢 **Broadcast Message:**\n\n{message_to_send}")
                sent_count += 1
                time.sleep(0.2) # Small delay to avoid hitting Telegram API limits
            except Exception as e:
                print(f"Error sending broadcast to user {user_id}: {e}")
        await message.reply_text(f"Broadcast sent to {sent_count} users.")
    else:
        await message.reply_text(f"Error preparing broadcast: {response.get('message', 'Unknown error')}")


# --- CandyPanel API Passthrough Commands (Admin Only) ---
@Client.on_message(filters.command("cp_new_client") & filters.private)
async def cp_new_client_command(client: Client, message: Message):
    telegram_id = message.from_user.id
    is_admin_resp = await call_unified_api("/bot_api/admin/check_admin", {"telegram_id": telegram_id})
    if not is_admin_resp.get('data', {}).get('is_admin', False):
        await message.reply_text("You are not authorized to use this command.")
        return

    parts = message.text.split(maxsplit=6)
    if len(parts) < 5:
        await message.reply_text("Usage: `/cp_new_client <name> <expires_iso> <traffic_bytes> <wg_id> [note]`")
        return
    try:
        name = parts[1]
        expires = parts[2]
        traffic = parts[3]
        wg_id = int(parts[4])
        note = parts[5] if len(parts) > 5 else ""

        response = await call_unified_api("/bot_api/admin/server_control", {
            "admin_telegram_id": telegram_id,
            "resource": "client",
            "action": "create",
            "data": {"name": name, "expires": expires, "traffic": traffic, "wg_id": wg_id, "note": note}
        })
        await message.reply_text(response.get('message', 'Unknown error'))
        if response.get('success') and response['data'].get('client_config'):
            await message.reply_text(f"Client config for {name}:\n```\n{response['data']['client_config']}\n```")
    except ValueError:
        await message.reply_text("Invalid wg_id. Must be an integer.")
    except Exception as e:
        await message.reply_text(f"An unexpected error occurred: {e}")

@Client.on_message(filters.command("cp_edit_client") & filters.private)
async def cp_edit_client_command(client: Client, message: Message):
    telegram_id = message.from_user.id
    is_admin_resp = await call_unified_api("/bot_api/admin/check_admin", {"telegram_id": telegram_id})
    if not is_admin_resp.get('data', {}).get('is_admin', False):
        await message.reply_text("You are not authorized to use this command.")
        return

    parts = message.text.split(maxsplit=5)
    if len(parts) < 2:
        await message.reply_text("Usage: `/cp_edit_client <name> [expires_iso] [traffic_bytes] [status_bool] [note]`")
        return
    try:
        name = parts[1]
        edit_data = {"name": name}
        if len(parts) > 2: edit_data["expires"] = parts[2]
        if len(parts) > 3: edit_data["traffic"] = parts[3]
        if len(parts) > 4: edit_data["status"] = True if parts[4].lower() == 'true' else False
        if len(parts) > 5: edit_data["note"] = parts[5]

        response = await call_unified_api("/bot_api/admin/server_control", {
            "admin_telegram_id": telegram_id,
            "resource": "client",
            "action": "update",
            "data": edit_data
        })
        await message.reply_text(response.get('message', 'Unknown error'))
    except Exception as e:
        await message.reply_text(f"An unexpected error occurred: {e}")

@Client.on_message(filters.command("cp_delete_client") & filters.private)
async def cp_delete_client_command(client: Client, message: Message):
    telegram_id = message.from_user.id
    is_admin_resp = await call_unified_api("/bot_api/admin/check_admin", {"telegram_id": telegram_id})
    if not is_admin_resp.get('data', {}).get('is_admin', False):
        await message.reply_text("You are not authorized to use this command.")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply_text("Usage: `/cp_delete_client <name>`")
        return
    
    name = parts[1]
    response = await call_unified_api("/bot_api/admin/server_control", {
        "admin_telegram_id": telegram_id,
        "resource": "client",
        "action": "delete",
        "data": {"name": name}
    })
    await message.reply_text(response.get('message', 'Unknown error'))

@Client.on_message(filters.command("cp_get_config") & filters.private)
async def cp_get_config_command(client: Client, message: Message):
    telegram_id = message.from_user.id
    is_admin_resp = await call_unified_api("/bot_api/admin/check_admin", {"telegram_id": telegram_id})
    if not is_admin_resp.get('data', {}).get('is_admin', False):
        await message.reply_text("You are not authorized to use this command.")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply_text("Usage: `/cp_get_config <name>`")
        return
    
    name = parts[1]
    response = await call_unified_api("/bot_api/admin/server_control", {
        "admin_telegram_id": telegram_id,
        "resource": "client",
        "action": "get_config",
        "data": {"name": name}
    })
    await message.reply_text(response.get('message', 'Unknown error'))
    if response.get('success') and response['data'].get('config'):
        await message.reply_text(f"Client config for {name}:\n```\n{response['data']['config']}\n```")

@Client.on_message(filters.command("cp_new_interface") & filters.private)
async def cp_new_interface_command(client: Client, message: Message):
    telegram_id = message.from_user.id
    is_admin_resp = await call_unified_api("/bot_api/admin/check_admin", {"telegram_id": telegram_id})
    if not is_admin_resp.get('data', {}).get('is_admin', False):
        await message.reply_text("You are not authorized to use this command.")
        return

    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.reply_text("Usage: `/cp_new_interface <address_range> <port>`")
        return
    try:
        address_range = parts[1]
        port = int(parts[2])
        response = await call_unified_api("/bot_api/admin/server_control", {
            "admin_telegram_id": telegram_id,
            "resource": "interface",
            "action": "create",
            "data": {"address_range": address_range, "port": port}
        })
        await message.reply_text(response.get('message', 'Unknown error'))
    except ValueError:
        await message.reply_text("Invalid port. Must be an integer.")
    except Exception as e:
        await message.reply_text(f"An unexpected error occurred: {e}")

@Client.on_message(filters.command("cp_edit_interface") & filters.private)
async def cp_edit_interface_command(client: Client, message: Message):
    telegram_id = message.from_user.id
    is_admin_resp = await call_unified_api("/bot_api/admin/check_admin", {"telegram_id": telegram_id})
    if not is_admin_resp.get('data', {}).get('is_admin', False):
        await message.reply_text("You are not authorized to use this command.")
        return

    parts = message.text.split(maxsplit=4)
    if len(parts) < 2:
        await message.reply_text("Usage: `/cp_edit_interface <name_wgX> [address] [port] [status_bool]`")
        return
    try:
        name = parts[1]
        edit_data = {"name": name}
        if len(parts) > 2: edit_data["address"] = parts[2]
        if len(parts) > 3: edit_data["port"] = int(parts[3])
        if len(parts) > 4: edit_data["status"] = True if parts[4].lower() == 'true' else False

        response = await call_unified_api("/bot_api/admin/server_control", {
            "admin_telegram_id": telegram_id,
            "resource": "interface",
            "action": "update",
            "data": edit_data
        })
        await message.reply_text(response.get('message', 'Unknown error'))
    except ValueError:
        await message.reply_text("Invalid port or status. Port must be integer, status true/false.")
    except Exception as e:
        await message.reply_text(f"An unexpected error occurred: {e}")

@Client.on_message(filters.command("cp_delete_interface") & filters.private)
async def cp_delete_interface_command(client: Client, message: Message):
    telegram_id = message.from_user.id
    is_admin_resp = await call_unified_api("/bot_api/admin/check_admin", {"telegram_id": telegram_id})
    if not is_admin_resp.get('data', {}).get('is_admin', False):
        await message.reply_text("You are not authorized to use this command.")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply_text("Usage: `/cp_delete_interface <wg_id>`")
        return
    try:
        wg_id = int(parts[1])
        response = await call_unified_api("/bot_api/admin/server_control", {
            "admin_telegram_id": telegram_id,
            "resource": "interface",
            "action": "delete",
            "data": {"wg_id": wg_id}
        })
        await message.reply_text(response.get('message', 'Unknown error'))
    except ValueError:
        await message.reply_text("Invalid wg_id. Must be an integer.")
    except Exception as e:
        await message.reply_text(f"An unexpected error occurred: {e}")

@Client.on_message(filters.command("cp_change_setting") & filters.private)
async def cp_change_setting_command(client: Client, message: Message):
    telegram_id = message.from_user.id
    is_admin_resp = await call_unified_api("/bot_api/admin/check_admin", {"telegram_id": telegram_id})
    if not is_admin_resp.get('data', {}).get('is_admin', False):
        await message.reply_text("You are not authorized to use this command.")
        return

    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.reply_text("Usage: `/cp_change_setting <key> <value>`")
        return
    
    key = parts[1]
    value = parts[2]
    response = await call_unified_api("/bot_api/admin/server_control", {
        "admin_telegram_id": telegram_id,
        "resource": "setting",
        "action": "update",
        "data": {"key": key, "value": value}
    })
    await message.reply_text(response.get('message', 'Unknown error'))

@Client.on_message(filters.command("cp_trigger_sync") & filters.private)
async def cp_trigger_sync_command(client: Client, message: Message):
    telegram_id = message.from_user.id
    is_admin_resp = await call_unified_api("/bot_api/admin/check_admin", {"telegram_id": telegram_id})
    if not is_admin_resp.get('data', {}).get('is_admin', False):
        await message.reply_text("You are not authorized to use this command.")
        return
    
    response = await call_unified_api("/bot_api/admin/server_control", {
        "admin_telegram_id": telegram_id,
        "resource": "sync",
        "action": "trigger"
    })
    await message.reply_text(response.get('message', 'Unknown error'))


# --- Main Execution ---


print("Bot started. Press Ctrl+C to exit.")
app.run()
