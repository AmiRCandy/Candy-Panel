import time
import httpx
import json
import os
import re
from pyrogram import Client, filters 
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message

# --- Configuration ---
UNIFIED_API_URL = F"http://127.0.0.1:{os.environ.get('AP_PORT',3446)}"

# Dictionaries for multi-language support
# English translations
LANGUAGES = {
    "en": {
        "welcome": "Hello {username}! Welcome to CandyPanel Bot.\n\n"
                   "Please choose your preferred language:",
        "main_menu_prompt": "Please choose an option:",
        "menu_buy_traffic": "💰 Buy Traffic",
        "menu_get_license": "🔑 Get License",
        "menu_account_status": "📊 Account Status",
        "menu_call_support": "📞 Call Support",
        "menu_change_language": "🌐 Change Language",
        "choose_language": "Please choose your language:",
        "language_changed": "Language changed to English.",
        "error_fetching_details": "Error fetching payment details: {message}. Please try again later.",
        "purchase_card_info": "To buy traffic, please transfer the desired amount to this card number:\n"
                              "💳 **Card Number:** `{admin_card_number}`\n\n"
                              "**Available Plans (Prices in Toman):**\n{price_text}\n\n"
                              "Please choose how you'd like to buy:",
        "buy_type_gb": "Buy by GB",
        "buy_type_month": "Buy by Month",
        "buy_type_custom": "Custom Plan",
        "prompt_gb_quantity": "How many **GB** do you want to buy? (e.g., `10`, `20`)",
        "prompt_month_quantity": "How many **months** do you want to buy? (e.g., `1`, `3`)",
        "prompt_custom_plan": "Please enter your desired plan in the format: `[time]month [traffic]gb`\n"
                              "Examples: `1 month 10gb`, `5gb 2months`, `10gb`, `3months`",
        "invalid_quantity": "Invalid quantity. Please enter a number (e.g., `10` or `1.5`).",
        "invalid_custom_format": "I couldn't understand your custom plan. Please use the format `[time]month [traffic]gb`.\n"
                                 "Examples: `1 month 10gb`, `5gb 2months`, `10gb`, `3months`",
        "price_summary": "You want to buy `{quantity} {purchase_type}` for `{calculated_amount:.2f}` Toman.\n\n"
                         "Please proceed with the payment to the admin's card number (provided earlier).\n"
                         "After transfer, reply with your **Order ID** (the reference number from your transaction) "
                         "using the command: `/bought <ORDER_ID>`",
        "price_summary_custom": "You want a custom plan: `{time_qty} months, {traffic_qty} GB` for `{calculated_amount:.2f}` Toman.\n\n"
                                "Please proceed with the payment to the admin's card number (provided earlier).\n"
                                "After transfer, reply with your **Order ID** (the reference number from your transaction) "
                                "using the command: `/bought <ORDER_ID>`",
        "license_config_ready": "Here is your WireGuard configuration:\n\n```\n{config}\n```\n\n"
                                "Save this as a `.conf` file and import it into your WireGuard client.",
        "license_not_active": "You don't have an active license yet. Please purchase one using the 'Buy Traffic' option.",
        "license_error": "Error getting license: {message}. Please try again later or contact support.",
        "account_status_title": "**Account Status:**\n",
        "status_line": "Status: `{status}`",
        "client_name_line": "Client Name: `{candy_client_name}`",
        "bought_traffic_line": "Bought Traffic: `{traffic_bought_gb:.2f} GB`",
        "used_traffic_line": "Used Traffic: `{used_traffic_gb:.2f} GB` (out of `{traffic_limit_gb:.2f} GB`)",
        "bought_time_line": "Bought Time: `{time_bought_days} days`",
        "expires_line": "Expires: `{expires}`",
        "note_line": "Note: {note}",
        "error_account_status": "Error getting account status: {message}. Please try again later.",
        "support_prompt": "Please type your support message after the `/support` command.\n"
                          "Example: `/support My internet is slow.`",
        "support_sent": "Your support message has been sent to the admin.",
        "error_support_send": "Error sending support message: {message}. Please try again later.",
        "bought_usage": "Usage: `/bought <ORDER_ID>`",
        "bought_start_purchase": "Please start a purchase process first by clicking 'Buy Traffic'.",
        "bought_submit_success": "Your purchase request has been submitted. The admin will review it shortly.",
        "bought_error_submit": "Error submitting request: {message}. Please try again later.",
        "admin_login_success": "You are logged in as admin.",
        "admin_server_status": "📊 **Server Status Overview:**",
        "admin_cpu_usage": "CPU Usage: `{cpu}`",
        "admin_mem_usage": "Memory Usage: `{mem_usage}`",
        "admin_clients_count": "Clients Connected: `{clients_count}`",
        "admin_uptime": "Server Uptime: `{uptime}`",
        "admin_download": "Download Speed: `{download}`",
        "admin_upload": "Upload Speed: `{upload}`",
        "admin_overall_status": "Overall Status: `{status}`",
        "admin_alerts": "🚨 **Alerts:**\n{alerts}",
        "admin_error_status": "Failed to fetch server status. Please check API connectivity.",
        "admin_unauthorized": "You are not authorized to use admin commands.",
        "admin_manage_users_title": "📊 **All Bot Users:**\n\n",
        "admin_user_details": "ID: `{telegram_id}`\nClient Name: `{candy_client_name}`\nStatus: `{status}`\n"
                              "Traffic Bought: `{traffic_bought_gb:.2f} GB`\n"
                              "Time Bought: `{time_bought_days} days`\nCreated At: `{created_at}`\n--------------------",
        "admin_no_users": "No users found.",
        "admin_manage_users_cmds": "To manage a user, use commands:\n"
                                   "`/ban <TELEGRAM_ID>`\n"
                                   "`/unban <TELEGRAM_ID>`\n"
                                   "`/update_traffic <TELEGRAM_ID> <GB>`\n"
                                   "`/update_time <TELEGRAM_ID> <DAYS>`",
        "admin_error_users": "Error fetching users: {message}. Please try again later.",
        "admin_pending_transactions_title": "💲 **Pending Transactions:**\n\n",
        "admin_trans_details_simple": "Type: `{purchase_type}`, Quantity: `{quantity}`",
        "admin_trans_details_custom": "Time: `{time_quantity} months`, Traffic: `{traffic_quantity} GB`",
        "admin_trans_item": "Order ID: `{order_id}`\nUser ID: `{telegram_id}`\nAmount: `{amount}`\n"
                            "{purchase_details}\nCard Sent: `{card_number_sent}`\nRequested At: `{requested_at}`\n--------------------",
        "admin_no_transactions": "No pending transactions.",
        "admin_manage_trans_cmds": "To approve/reject:\n"
                                   "`/approve <ORDER_ID> [ADMIN_NOTE]`\n"
                                   "`/reject <ORDER_ID> [ADMIN_NOTE]`",
        "admin_error_transactions": "Error fetching transactions: {message}. Please try again later.",
        "admin_broadcast_prompt": "Please type the message you want to broadcast after the `/broadcast` command.\n"
                                  "Example: `/broadcast Server maintenance tonight.`",
        "admin_broadcast_sent": "Broadcast sent to {sent_count} users.",
        "admin_error_broadcast": "Error preparing broadcast: {message}. Please try again later.",
        "admin_server_control_info": "⚙️ **Server Control Options (via CandyPanel API):**\n"
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
                                     "**Example:** `/cp_new_client testuser 2025-12-31T23:59:59 10737418240 0 This is a test` (10GB traffic)",
        "cmd_usage_error": "Usage: `{command_name} {expected_args}`",
        "invalid_id_format": "Invalid ID format. Must be an integer.",
        "invalid_num_format": "Invalid number format. Please enter a number.",
        "unexpected_error": "An unexpected error occurred: {error_message}. Please try again or contact support.",
        "transaction_approved": "Transaction {order_id} approved. Client '{client_name}' created/updated. "
                                "Bought: {new_traffic_gb:.2f} GB and {new_time_days} days.",
        "transaction_approved_no_config": "Transaction {order_id} approved. Your client name is `{client_name}`. You can get your config using /get_license.",
        "purchase_approved_user": "🎉 **Your purchase has been approved!**\n\n",
        "purchase_rejected_user": "😔 **Your purchase request (Order ID: {order_id}) has been rejected.**\n"
                                  "Admin Note: {admin_note}",
        "user_banned": "User {target_telegram_id} has been banned.",
        "user_unbanned": "User {target_telegram_id} has been unbanned.",
        "user_traffic_updated": "User {target_telegram_id} traffic updated to {new_traffic_gb} GB.",
        "user_time_updated": "User {target_telegram_id} time updated to {new_time_days} days.",
        "user_not_found": "Target user not found.",
        "telegram_bot_payment_req": "🚨 **New Payment Request!**\n\n"
                                    "User: `{username} (ID: {telegram_id})`\n"
                                    "Order ID: `{order_id}`\n"
                                    "Amount: `{amount:.2f}` Toman\n"
                                    "{purchase_summary}\n"
                                    "Status: `Pending`\n\n"
                                    "Please verify the payment and use `/approve {order_id} [ADMIN_NOTE]` or `/reject {order_id} [ADMIN_NOTE]`",
        "bot_already_stopped": "Telegram bot is already stopped (or PID is stale).",
        "bot_already_running": "Telegram bot is already running.",
        "bot_start_fail_token": "Telegram bot token/API credentials not configured. Cannot start bot.",
        "bot_start_fail_venv": "Error: Virtual environment Python interpreter not found. Please ensure the virtual environment is correctly set up.",
        "bot_start_fail_script": "Error: bot.py script not found. Cannot start bot.",
        "bot_start_unexpected": "Failed to start Telegram bot: {error}",
        "bot_stop_unexpected": "Error stopping Telegram bot: {error}",
        "broadcast_msg_prefix": "📢 **Broadcast Message:**\n\n",
        "contact_support_price_config": "Price for this plan is not configured. Please contact support."
    },
    "fa": { # Persian translations
        "welcome": "سلام {username}! به ربات CandyPanel خوش آمدید.\n\n"
                   "لطفاً زبان مورد نظر خود را انتخاب کنید:",
        "main_menu_prompt": "لطفا یک گزینه را انتخاب کنید:",
        "menu_buy_traffic": "💰 خرید ترافیک",
        "menu_get_license": "🔑 دریافت لایسنس",
        "menu_account_status": "📊 وضعیت حساب",
        "menu_call_support": "📞 پشتیبانی",
        "menu_change_language": "🌐 تغییر زبان",
        "choose_language": "لطفا زبان خود را انتخاب کنید:",
        "language_changed": "زبان به فارسی تغییر یافت.",
        "error_fetching_details": "خطا در دریافت جزئیات پرداخت: {message}. لطفا دوباره تلاش کنید.",
        "purchase_card_info": "برای خرید ترافیک، لطفا مبلغ مورد نظر را به شماره کارت زیر واریز کنید:\n"
                              "💳 **شماره کارت:** `{admin_card_number}`\n\n"
                              "**پلن‌های موجود (قیمت به تومان):**\n{price_text}\n\n"
                              "لطفا نحوه خرید خود را انتخاب کنید:",
        "buy_type_gb": "خرید بر اساس گیگابایت",
        "buy_type_month": "خرید بر اساس ماه",
        "buy_type_custom": "پلن سفارشی",
        "prompt_gb_quantity": "چند **گیگابایت** می‌خواهید بخرید؟ (مثال: `10`, `20`)",
        "prompt_month_quantity": "چند **ماه** می‌خواهید بخرید؟ (مثال: `1`, `3`)",
        "prompt_custom_plan": "لطفاً پلن مورد نظر خود را در قالب: `[مدت]ماه [ترافیک]گیگ` وارد کنید.\n"
                              "مثال‌ها: `1 ماه 10گیگ`, `5گیگ 2ماه`, `10گیگ`, `3ماه`",
        "invalid_quantity": "مقدار نامعتبر است. لطفا یک عدد وارد کنید (مثال: `10` یا `1.5`).",
        "invalid_custom_format": "پلن سفارشی شما قابل درک نیست. لطفا از قالب `[مدت]ماه [ترافیک]گیگ` استفاده کنید.\n"
                                 "مثال‌ها: `1 ماه 10گیگ`, `5گیگ 2ماه`, `10گیگ`, `3ماه`",
        "price_summary": "شما می‌خواهید `{quantity} {purchase_type}` را با قیمت `{calculated_amount:.2f}` تومان خریداری کنید.\n\n"
                         "لطفاً پرداخت را به شماره کارت ادمین (که قبلاً ارائه شد) انجام دهید.\n"
                         "پس از انتقال، **شماره پیگیری** (شماره مرجع تراکنش خود) را با دستور: `/bought <ORDER_ID>` ارسال کنید.",
        "price_summary_custom": "شما یک پلن سفارشی: `{time_qty} ماه، {traffic_qty} گیگابایت` را با قیمت `{calculated_amount:.2f}` تومان می‌خواهید.\n\n"
                                "لطفاً پرداخت را به شماره کارت ادمین (که قبلاً ارائه شد) انجام دهید.\n"
                                "پس از انتقال، **شماره پیگیری** (شماره مرجع تراکنش خود) را با دستور: `/bought <ORDER_ID>` ارسال کنید.",
        "license_config_ready": "پیکربندی WireGuard شما:\n\n```\n{config}\n```\n\n"
                                "این را به عنوان یک فایل `.conf` ذخیره کرده و آن را در کلاینت WireGuard خود وارد کنید.",
        "license_not_active": "شما هنوز لایسنس فعال ندارید. لطفا با استفاده از گزینه 'خرید ترافیک' یک لایسنس خریداری کنید.",
        "license_error": "خطا در دریافت لایسنس: {message}. لطفا دوباره تلاش کنید یا با پشتیبانی تماس بگیرید.",
        "account_status_title": "**وضعیت حساب:**\n",
        "status_line": "وضعیت: `{status}`",
        "client_name_line": "نام کلاینت: `{candy_client_name}`",
        "bought_traffic_line": "ترافیک خریداری شده: `{traffic_bought_gb:.2f} GB`",
        "used_traffic_line": "ترافیک استفاده شده: `{used_traffic_gb:.2f} GB` (از `{traffic_limit_gb:.2f} GB`)",
        "bought_time_line": "زمان خریداری شده: `{time_bought_days} روز`",
        "expires_line": "منقضی در: `{expires}`",
        "note_line": "توضیحات: {note}",
        "error_account_status": "خطا در دریافت وضعیت حساب: {message}. لطفا دوباره تلاش کنید.",
        "support_prompt": "لطفا پیام پشتیبانی خود را بعد از دستور `/support` تایپ کنید.\n"
                          "مثال: `/support اینترنت من کند است.`",
        "support_sent": "پیام پشتیبانی شما برای ادمین ارسال شد.",
        "error_support_send": "خطا در ارسال پیام پشتیبانی: {message}. لطفا دوباره تلاش کنید.",
        "bought_usage": "نحوه استفاده: `/bought <ORDER_ID>`",
        "bought_start_purchase": "لطفا ابتدا با کلیک روی 'خرید ترافیک' یک فرآیند خرید را شروع کنید.",
        "bought_submit_success": "درخواست خرید شما ثبت شد. ادمین به زودی آن را بررسی خواهد کرد.",
        "bought_error_submit": "خطا در ثبت درخواست: {message}. لطفا دوباره تلاش کنید.",
        "admin_login_success": "شما به عنوان ادمین وارد شده‌اید.",
        "admin_server_status": "📊 **بررسی اجمالی وضعیت سرور:**",
        "admin_cpu_usage": "مصرف CPU: `{cpu}`",
        "admin_mem_usage": "مصرف حافظه: `{mem_usage}`",
        "admin_clients_count": "کلاینت‌های متصل: `{clients_count}`",
        "admin_uptime": "آپتایم سرور: `{uptime}`",
        "admin_download": "سرعت دانلود: `{download}`",
        "admin_upload": "سرعت آپلود: `{upload}`",
        "admin_overall_status": "وضعیت کلی: `{status}`",
        "admin_alerts": "🚨 **هشدارها:**\n{alerts}",
        "admin_error_status": "دریافت وضعیت سرور ناموفق بود. لطفا اتصال API را بررسی کنید.",
        "admin_unauthorized": "شما مجاز به استفاده از دستورات ادمین نیستید.",
        "admin_manage_users_title": "📊 **همه کاربران ربات:**\n\n",
        "admin_user_details": "شناسه: `{telegram_id}`\nنام کلاینت: `{candy_client_name}`\nوضعیت: `{status}`\n"
                              "ترافیک خریداری شده: `{traffic_bought_gb:.2f} GB`\n"
                              "زمان خریداری شده: `{time_bought_days} روز`\nتاریخ ایجاد: `{created_at}`\n--------------------",
        "admin_no_users": "کاربری یافت نشد.",
        "admin_manage_users_cmds": "برای مدیریت کاربر، از دستورات زیر استفاده کنید:\n"
                                   "`/ban <TELEGRAM_ID>`\n"
                                   "`/unban <TELEGRAM_ID>`\n"
                                   "`/update_traffic <TELEGRAM_ID> <GB>`\n"
                                   "`/update_time <TELEGRAM_ID> <DAYS>`",
        "admin_error_users": "خطا در دریافت کاربران: {message}. لطفا دوباره تلاش کنید.",
        "admin_pending_transactions_title": "💲 **تراکنش‌های در انتظار تایید:**\n\n",
        "admin_trans_details_simple": "نوع: `{purchase_type}`، مقدار: `{quantity}`",
        "admin_trans_details_custom": "زمان: `{time_quantity} ماه`، ترافیک: `{traffic_quantity} GB`",
        "admin_trans_item": "شناسه سفارش: `{order_id}`\nشناسه کاربر: `{telegram_id}`\nمبلغ: `{amount}`\n"
                            "{purchase_details}\nشماره کارت ارسالی: `{card_number_sent}`\nدرخواست در تاریخ: `{requested_at}`\n--------------------",
        "admin_no_transactions": "تراکنش در انتظار تاییدی وجود ندارد.",
        "admin_manage_trans_cmds": "برای تایید/رد:\n"
                                   "`/approve <ORDER_ID> [ADMIN_NOTE]`\n"
                                   "`/reject <ORDER_ID> [ADMIN_NOTE]`",
        "admin_error_transactions": "خطا در دریافت تراکنش‌ها: {message}. لطفا دوباره تلاش کنید.",
        "admin_broadcast_prompt": "لطفا پیامی که می‌خواهید پخش کنید را بعد از دستور `/broadcast` تایپ کنید.\n"
                                  "مثال: `/broadcast سرور امشب برای نگهداری از دسترس خارج می‌شود.`",
        "admin_broadcast_sent": "پیام برای {sent_count} کاربر ارسال شد.",
        "admin_error_broadcast": "خطا در آماده‌سازی پیام: {message}. لطفا دوباره تلاش کنید.",
        "admin_server_control_info": "⚙️ **گزینه‌های کنترل سرور (از طریق API CandyPanel):**\n"
                                     "از دستورات زیر استفاده کنید:\n\n"
                                     "**کلاینت‌ها:**\n"
                                     "`/cp_new_client <نام> <تاریخ_انقضا_ISO> <ترافیک_بایت> [شناسه_WG] [یادداشت]`\n"
                                     "`/cp_edit_client <نام> [تاریخ_انقضا_ISO] [ترافیک_بایت] [وضعیت_بولین] [یادداشت]`\n"
                                     "`/cp_delete_client <نام>`\n"
                                     "`/cp_get_config <نام>`\n\n"
                                     "**اینترفیس‌ها:**\n"
                                     "`/cp_new_interface <محدوده_آدرس> <پورت>`\n"
                                     "`/cp_edit_interface <نام_WGX> [آدرس] [پورت] [وضعیت_بولین]`\n"
                                     "`/cp_delete_interface <شناسه_WG>`\n\n"
                                     "**تنظیمات:**\n"
                                     "`/cp_change_setting <کلید> <مقدار>`\n\n"
                                     "**همگام‌سازی:**\n"
                                     "`/cp_trigger_sync`\n\n"
                                     "**مثال:** `/cp_new_client testuser 2025-12-31T23:59:59 10737418240 0 این یک تست است` (10 گیگابایت ترافیک)",
        "cmd_usage_error": "نحوه استفاده: `{command_name} {expected_args}`",
        "invalid_id_format": "قالب شناسه نامعتبر است. باید عدد صحیح باشد.",
        "invalid_num_format": "قالب عدد نامعتبر است. لطفا یک عدد وارد کنید.",
        "unexpected_error": "خطای غیرمنتظره‌ای رخ داد: {error_message}. لطفا دوباره تلاش کنید یا با پشتیبانی تماس بگیرید.",
        "transaction_approved": "تراکنش {order_id} تایید شد. کلاینت '{client_name}' ایجاد/به‌روزرسانی شد. "
                                "خریداری شده: {new_traffic_gb:.2f} گیگابایت و {new_time_days} روز.",
        "transaction_approved_no_config": "تراکنش {order_id} تایید شد. نام کلاینت شما `{client_name}` است. می‌توانید پیکربندی خود را با استفاده از /get_license دریافت کنید.",
        "purchase_approved_user": "🎉 **خرید شما تایید شد!**\n\n",
        "purchase_rejected_user": "😔 **درخواست خرید شما (شناسه سفارش: {order_id}) رد شد.**\n"
                                  "یادداشت ادمین: {admin_note}",
        "user_banned": "کاربر {target_telegram_id} مسدود شد.",
        "user_unbanned": "کاربر {target_telegram_id} از حالت مسدودی خارج شد.",
        "user_traffic_updated": "ترافیک کاربر {target_telegram_id} به {new_traffic_gb} گیگابایت به‌روزرسانی شد.",
        "user_time_updated": "زمان کاربر {target_telegram_id} به {new_time_days} روز به‌روزرسانی شد.",
        "user_not_found": "کاربر مورد نظر یافت نشد.",
        "telegram_bot_payment_req": "🚨 **درخواست پرداخت جدید!**\n\n"
                                    "کاربر: `{username} (شناسه: {telegram_id})`\n"
                                    "شناسه سفارش: `{order_id}`\n"
                                    "مبلغ: `{amount:.2f}` تومان\n"
                                    "{purchase_summary}\n"
                                    "وضعیت: `در انتظار تایید`\n\n"
                                    "لطفاً پرداخت را تایید کنید و از `/approve {order_id} [ADMIN_NOTE]` یا `/reject {order_id} [ADMIN_NOTE]` استفاده کنید.",
        "bot_already_stopped": "ربات تلگرام از قبل متوقف شده است (یا PID قدیمی است).",
        "bot_already_running": "ربات تلگرام از قبل در حال اجرا است.",
        "bot_start_fail_token": "توکن ربات تلگرام/اعتبارنامه API پیکربندی نشده است. نمی‌توان ربات را شروع کرد.",
        "bot_start_fail_venv": "خطا: مفسر پایتون محیط مجازی یافت نشد. لطفا مطمئن شوید که محیط مجازی به درستی تنظیم شده است.",
        "bot_start_fail_script": "خطا: اسکریپت bot.py یافت نشد. نمی‌توان ربات را شروع کرد.",
        "bot_start_unexpected": "شروع ربات تلگرام ناموفق بود: {error}",
        "bot_stop_unexpected": "خطا در توقف ربات تلگرام: {error}",
        "broadcast_msg_prefix": "📢 **پیام همگانی:**\n\n",
        "contact_support_price_config": "قیمت برای این پلن پیکربندی نشده است. لطفا با پشتیبانی تماس بگیرید."
    }
}

# In-memory dictionary to store user's chosen language
user_languages = {}

# Helper function to get translated text
def _(telegram_id: int, key: str, **kwargs) -> str:
    lang = user_languages.get(telegram_id, "en") # Default to English
    text = LANGUAGES[lang].get(key, LANGUAGES["en"].get(key, f"Translation missing for '{key}'"))
    return text.format(**kwargs)

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
        return {"success": False, "message": e.response.text} # Return only the text for better parsing
    except httpx.RequestError as e:
        print(f"[-] Network error calling unified API {endpoint}: {e}")
        return {"success": False, "message": f"Network error: {e}"}
    except Exception as e:
        print(f"[-] Unexpected error calling unified API {endpoint}: {e}")
        return {"success": False, "message": f"Unexpected error: {e}"}

def get_bot_token_api_from_unified_api():
    """Fetches the bot token from the unified API's settings."""
    try:
        # Import here to avoid circular dependency
        from db import SQLite 
        db = SQLite()
        token_setting = db.get('settings', where={'key': 'telegram_bot_token'})
        api_id = db.get('settings', where={'key': 'telegram_api_id'})
        api_hash = db.get('settings', where={'key': 'telegram_api_hash'})
        return (token_setting['value'] if token_setting else None, 
                api_id['value'] if api_id else None, 
                api_hash['value'] if api_hash else None)
    except Exception as e:
        print(f"Error fetching bot token from unified API: {e}")
        return None, None, None

# --- Pyrogram Client Initialization ---
btoken, bapiid, bapihash = get_bot_token_api_from_unified_api()
if (not btoken or btoken == 'YOUR_TELEGRAM_BOT_TOKEN') or \
   (not bapiid or bapiid == 'YOUR_TELEGRAM_API_ID') or \
   (not bapihash or bapihash == 'YOUR_TELEGRAM_API_HASH'):
    print("ERROR: Telegram bot token or API credentials not found or are default. Please configure them in CandyPanel.db via main.py settings.")
    exit(1)

app = Client(
    "candy_panel_bot",
    api_id=bapiid,
    api_hash=bapihash,
    bot_token=btoken
)

# --- Keyboards ---
def get_user_menu_keyboard(telegram_id: int):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(_(telegram_id, "menu_buy_traffic"), callback_data="buy_traffic")],
        [InlineKeyboardButton(_(telegram_id, "menu_get_license"), callback_data="get_license")],
        [InlineKeyboardButton(_(telegram_id, "menu_account_status"), callback_data="account_status")],
        [InlineKeyboardButton(_(telegram_id, "menu_call_support"), callback_data="call_support")],
        [InlineKeyboardButton(_(telegram_id, "menu_change_language"), callback_data="change_language")]
    ])

admin_menu_keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("👥 Manage Users", callback_data="admin_manage_users")],
    [InlineKeyboardButton("💲 Manage Transactions", callback_data="admin_manage_transactions")],
    [InlineKeyboardButton("📢 Send Broadcast", callback_data="admin_send_broadcast")],
    [InlineKeyboardButton("⚙️ Server Control", callback_data="admin_server_control")]
])

def get_buy_traffic_type_keyboard(telegram_id: int):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(_(telegram_id, "buy_type_gb"), callback_data="buy_by_gb")],
        [InlineKeyboardButton(_(telegram_id, "buy_type_month"), callback_data="buy_by_month")],
        [InlineKeyboardButton(_(telegram_id, "buy_type_custom"), callback_data="buy_custom_plan")]
    ])

language_selection_keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("English 🇬🇧", callback_data="lang_en")],
    [InlineKeyboardButton("فارسی 🇮🇷", callback_data="lang_fa")]
])

# --- Handlers ---

@app.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    telegram_id = message.from_user.id
    username = message.from_user.username if message.from_user.username else message.from_user.first_name

    # Register user with unified API and get initial language
    response = await call_unified_api("/bot_api/user/register", {"telegram_id": telegram_id})

    if response.get('success'):
        user_lang = response['data'].get('language', 'en')
        user_languages[telegram_id] = user_lang # Store language in memory
        await message.reply_text(
            _(telegram_id, "welcome", username=username),
            reply_markup=language_selection_keyboard # Always ask for language on start for flexibility
        )
    else:
        # Fallback to English if registration fails for some reason
        user_languages[telegram_id] = 'en' 
        await message.reply_text(f"Error registering you: {response.get('message', 'Unknown error')}")


@app.on_message(filters.command("adminlogin"))
async def admin_login_command(client: Client, message: Message):
    telegram_id = message.from_user.id
    
    # Get admin ID from unified API
    admin_check_resp = await call_unified_api("/bot_api/admin/check_admin", {"telegram_id": telegram_id}) 
    admin_telegram_id = admin_check_resp.get('data', {}).get('admin_telegram_id')

    if str(telegram_id) == admin_telegram_id:
        # Fetch dashboard data
        dashboard_resp = await call_unified_api("/api/data", {}) 
        
        status_message = _(telegram_id, "admin_login_success") + "\n\n"
        if dashboard_resp.get('success') and 'dashboard' in dashboard_resp.get('data', {}):
            dashboard = dashboard_resp['data']['dashboard']
            
            status_message += _(telegram_id, "admin_server_status") + "\n"
            status_message += _(telegram_id, "admin_cpu_usage", cpu=dashboard.get('cpu', 'N/A')) + "\n"
            status_message += _(telegram_id, "admin_mem_usage", mem_usage=dashboard.get('mem', {}).get('usage', 'N/A')) + "\n"
            status_message += _(telegram_id, "admin_clients_count", clients_count=dashboard.get('clients_count', 'N/A')) + "\n"
            status_message += _(telegram_id, "admin_uptime", uptime=dashboard.get('uptime', 'N/A')) + "\n"
            status_message += _(telegram_id, "admin_download", download=dashboard.get('net', {}).get('download', 'N/A')) + "\n"
            status_message += _(telegram_id, "admin_upload", upload=dashboard.get('net', {}).get('upload', 'N/A')) + "\n"
            status_message += _(telegram_id, "admin_overall_status", status=dashboard.get('status', 'N/A')) + "\n"
            
            if dashboard.get('alert'):
                try:
                    # Alerts from core.py are now a JSON list of strings
                    alerts = json.loads(dashboard['alert']) 
                    if alerts:
                        status_message += "\n" + _(telegram_id, "admin_alerts", alerts="\n".join(alerts))
                except (json.JSONDecodeError, TypeError):
                    status_message += f"\n🚨 **Alert:** {dashboard['alert']}\n" # Fallback if not valid JSON
            
        else:
            status_message += _(telegram_id, "admin_error_status")

        await message.reply_text(status_message, reply_markup=admin_menu_keyboard)
    else:
        await message.reply_text(_(telegram_id, "admin_unauthorized"))

@app.on_callback_query()
async def callback_query_handler(client: Client, callback_query):
    data = callback_query.data
    telegram_id = callback_query.from_user.id
    message = callback_query.message

    # Handle language selection first
    if data.startswith("lang_"):
        chosen_lang = data.split("_")[1]
        response = await call_unified_api("/bot_api/user/set_language", {"telegram_id": telegram_id, "language": chosen_lang})
        if response.get('success'):
            user_languages[telegram_id] = chosen_lang
            await message.edit_text(
                _(telegram_id, "language_changed") if chosen_lang == 'en' else LANGUAGES['fa']['language_changed'], 
                reply_markup=get_user_menu_keyboard(telegram_id)
            )
        else:
            await message.edit_text(f"Error changing language: {response.get('message', 'Unknown error')}", reply_markup=get_user_menu_keyboard(telegram_id))
        return

    # Clear user state if they click a main menu button after being in a multi-step flow
    if data in ["buy_traffic", "get_license", "account_status", "call_support", "change_language",
                "admin_manage_users", "admin_manage_transactions", "admin_send_broadcast", "admin_server_control"]:
        if telegram_id in user_states:
            del user_states[telegram_id]
        
        # If it's a main menu button, refresh the keyboard
        if data in ["buy_traffic", "get_license", "account_status", "call_support", "change_language"]:
            await message.edit_reply_markup(reply_markup=get_user_menu_keyboard(telegram_id))


    # Check admin status for admin actions
    is_admin_resp = await call_unified_api("/bot_api/admin/check_admin", {"telegram_id": telegram_id})
    is_admin = is_admin_resp.get('data', {}).get('is_admin', False)

    if data == "buy_traffic":
        response = await call_unified_api("/bot_api/user/initiate_purchase", {"telegram_id": telegram_id})
        if response.get('success'):
            admin_card_number = response['data']['admin_card_number']
            prices = response['data']['prices']
            price_text = "\n".join([f"- {k}: {v} (Toman)" for k, v in prices.items()])
            
            await message.edit_text(
                _(telegram_id, "purchase_card_info", admin_card_number=admin_card_number, price_text=price_text),
                reply_markup=get_buy_traffic_type_keyboard(telegram_id)
            )
            user_states[telegram_id] = {"step": "await_amount_type"}
        else:
            await message.edit_text(_(telegram_id, "error_fetching_details", message=response.get('message', 'Unknown error')))

    elif data == "buy_by_gb":
        user_states[telegram_id] = {"step": "await_quantity", "purchase_type": "gb"}
        await message.edit_text(_(telegram_id, "prompt_gb_quantity"))
    
    elif data == "buy_by_month":
        user_states[telegram_id] = {"step": "await_quantity", "purchase_type": "month"}
        await message.edit_text(_(telegram_id, "prompt_month_quantity"))

    elif data == "buy_custom_plan":
        user_states[telegram_id] = {"step": "await_custom_plan_input", "purchase_type": "custom"}
        await message.edit_text(_(telegram_id, "prompt_custom_plan"))

    elif data == "get_license":
        response = await call_unified_api("/bot_api/user/get_license", {"telegram_id": telegram_id})
        if response.get('success'):
            config = response['data']['config']
            await message.edit_text(_(telegram_id, "license_config_ready", config=config))
        else:
            # Provide more user-friendly messages for license errors
            if "You don't have an active license yet" in response.get('message', ''):
                await message.edit_text(_(telegram_id, "license_not_active"), reply_markup=get_user_menu_keyboard(telegram_id))
            else:
                await message.edit_text(_(telegram_id, "license_error", message=response.get('message', 'Unknown error')), reply_markup=get_user_menu_keyboard(telegram_id))

    elif data == "account_status":
        response = await call_unified_api("/bot_api/user/account_status", {"telegram_id": telegram_id})
        if response.get('success'):
            status_data = response['data']
            used_traffic_bytes = status_data.get('used_traffic_bytes', 0)
            traffic_limit_bytes = status_data.get('traffic_limit_bytes', 0)
            
            used_traffic_gb = used_traffic_bytes / (1024**3)
            traffic_limit_gb = traffic_limit_bytes / (1024**3)

            status_text = _(telegram_id, "account_status_title")
            status_text += _(telegram_id, "status_line", status=status_data['status']) + "\n"
            status_text += _(telegram_id, "client_name_line", candy_client_name=status_data.get('candy_client_name', _(telegram_id, "N/A"))) + "\n"
            status_text += _(telegram_id, "bought_traffic_line", traffic_bought_gb=status_data['traffic_bought_gb']) + "\n"
            status_text += _(telegram_id, "used_traffic_line", used_traffic_gb=used_traffic_gb, traffic_limit_gb=traffic_limit_gb) + "\n"
            status_text += _(telegram_id, "bought_time_line", time_bought_days=status_data['time_bought_days']) + "\n"
            status_text += _(telegram_id, "expires_line", expires=status_data.get('expires', _(telegram_id, "N/A"))) + "\n"
            
            if status_data.get('note'):
                status_text += _(telegram_id, "note_line", note=status_data['note'])

            await message.edit_text(status_text)
        else:
            await message.edit_text(_(telegram_id, "error_account_status", message=response.get('message', 'Unknown error')))

    elif data == "call_support":
        await message.edit_text(_(telegram_id, "support_prompt"))

    elif data == "change_language":
        await message.edit_text(_(telegram_id, "choose_language"), reply_markup=language_selection_keyboard)
    
    # --- Admin Callbacks ---
    elif is_admin:
        if data == "admin_manage_users":
            response = await call_unified_api("/bot_api/admin/get_all_users", {"telegram_id": telegram_id})
            if response.get('success'):
                users = response['data']['users']
                if not users:
                    await message.edit_text(_(telegram_id, "admin_no_users"))
                    return
                
                user_list_text = _(telegram_id, "admin_manage_users_title")
                for user in users:
                    user_list_text += _(telegram_id, "admin_user_details", 
                                        telegram_id=user['telegram_id'],
                                        candy_client_name=user.get('candy_client_name', _(telegram_id, "N/A")),
                                        status=user['status'],
                                        traffic_bought_gb=user['traffic_bought_gb'],
                                        time_bought_days=user['time_bought_days'],
                                        created_at=user['created_at']) + "\n"
                await message.edit_text(user_list_text)
                await message.reply_text(_(telegram_id, "admin_manage_users_cmds"))
            else:
                await message.edit_text(_(telegram_id, "admin_error_users", message=response.get('message', 'Unknown error')))

        elif data == "admin_manage_transactions":
            response = await call_unified_api("/bot_api/admin/get_transactions", {"telegram_id": telegram_id, "status_filter": "pending"})
            if response.get('success'):
                transactions = response['data']['transactions']
                if not transactions:
                    await message.edit_text(_(telegram_id, "admin_no_transactions"))
                    return
                
                trans_list_text = _(telegram_id, "admin_pending_transactions_title")
                for trans in transactions:
                    purchase_details = ""
                    if trans.get('purchase_type') == 'custom':
                        purchase_details = _(telegram_id, "admin_trans_details_custom", 
                                             time_quantity=trans.get('time_quantity', 0), 
                                             traffic_quantity=trans.get('traffic_quantity', 0))
                    else:
                        purchase_details = _(telegram_id, "admin_trans_details_simple", 
                                             purchase_type=trans.get('purchase_type', _(telegram_id, "N/A")).upper(), 
                                             quantity=trans.get('quantity', _(telegram_id, "N/A")))

                    trans_list_text += _(telegram_id, "admin_trans_item",
                                        order_id=trans['order_id'],
                                        telegram_id=trans['telegram_id'],
                                        amount=trans['amount'],
                                        purchase_details=purchase_details,
                                        card_number_sent=trans['card_number_sent'],
                                        requested_at=trans['requested_at']) + "\n"
                await message.edit_text(trans_list_text)
                await message.reply_text(_(telegram_id, "admin_manage_trans_cmds"))
            else:
                await message.edit_text(_(telegram_id, "admin_error_transactions", message=response.get('message', 'Unknown error')))

        elif data == "admin_send_broadcast":
            await message.edit_text(_(telegram_id, "admin_broadcast_prompt"))

        elif data == "admin_server_control":
            await message.edit_text(_(telegram_id, "admin_server_control_info"))
    else:
        await message.edit_text(_(telegram_id, "admin_unauthorized"))


@app.on_message(filters.text & filters.private & ~filters.command([
    "start", "adminlogin", "bought", "support", "approve", "reject", "ban", 
    "unban", "update_traffic", "update_time", "broadcast", "cp_new_client", 
    "cp_edit_client", "cp_delete_client", "cp_get_config", "cp_new_interface", 
    "cp_edit_interface", "cp_delete_interface", "cp_change_setting", "cp_trigger_sync"
]))
async def handle_quantity_input(client: Client, message: Message):
    telegram_id = message.from_user.id
    current_state = user_states.get(telegram_id)

    if current_state and current_state["step"] == "await_quantity":
        try:
            quantity = float(message.text.strip())
            if quantity <= 0:
                await message.reply_text(_(telegram_id, "invalid_quantity"))
                return

            current_state["quantity"] = quantity
            purchase_type = current_state["purchase_type"]

            # Call unified API to get the calculated price
            response = await call_unified_api("/bot_api/user/calculate_price", {
                "telegram_id": telegram_id,
                "purchase_type": purchase_type,
                "quantity": quantity
            })

            if response.get('success'):
                calculated_amount = response['data']['calculated_amount']
                current_state["calculated_price"] = calculated_amount
                current_state["step"] = "await_order_id"
                
                await message.reply_text(
                    _(telegram_id, "price_summary", 
                      quantity=quantity, 
                      purchase_type=purchase_type.upper(), 
                      calculated_amount=calculated_amount)
                )
            else:
                # Handle specific price config error from API
                if "Price per" in response.get('message', '') and "not configured" in response.get('message', ''):
                     await message.reply_text(_(telegram_id, "contact_support_price_config"))
                else:
                    await message.reply_text(_(telegram_id, "unexpected_error", error_message=response.get('message', 'Unknown error')))
                if telegram_id in user_states:
                    del user_states[telegram_id] # Clear state on error
        except ValueError:
            await message.reply_text(_(telegram_id, "invalid_quantity"))
        except Exception as e:
            await message.reply_text(_(telegram_id, "unexpected_error", error_message=str(e)))
            if telegram_id in user_states:
                del user_states[telegram_id] # Clear state on error
    
    elif current_state and current_state["step"] == "await_custom_plan_input":
        text_input = message.text.strip().lower()
        time_match = re.search(r'(\d+)\s*(month|months|mah|maah)', text_input) # Added Persian 'mah' and 'maah'
        traffic_match = re.search(r'(\d+)\s*(gb|gigs|gig)', text_input) # Added Persian 'gig'

        time_qty = float(time_match.group(1)) if time_match else 0
        traffic_qty = float(traffic_match.group(1)) if traffic_match else 0

        if time_qty == 0 and traffic_qty == 0:
            await message.reply_text(_(telegram_id, "invalid_custom_format"))
            return

        current_state["time_quantity"] = time_qty
        current_state["traffic_quantity"] = traffic_qty
        current_state["purchase_type"] = "custom" # Ensure type is set to custom

        # Call unified API to get the calculated price for custom plan
        response = await call_unified_api("/bot_api/user/calculate_price", {
            "telegram_id": telegram_id,
            "purchase_type": "custom",
            "time_quantity": time_qty,
            "traffic_quantity": traffic_qty
        })

        if response.get('success'):
            calculated_amount = response['data']['calculated_amount']
            current_state["calculated_price"] = calculated_amount
            current_state["step"] = "await_order_id"
            
            await message.reply_text(
                _(telegram_id, "price_summary_custom", 
                  time_qty=time_qty, 
                  traffic_qty=traffic_qty, 
                  calculated_amount=calculated_amount)
            )
        else:
            # Handle specific price config error from API
            if "Price for" in response.get('message', '') and "not configured" in response.get('message', ''):
                 await message.reply_text(_(telegram_id, "contact_support_price_config"))
            else:
                await message.reply_text(_(telegram_id, "unexpected_error", error_message=response.get('message', 'Unknown error')))
            if telegram_id in user_states:
                del user_states[telegram_id] # Clear state on error
    else:
        # If not in a multi-step flow, or not the expected step, just ignore or prompt main menu
        await message.reply_text(_(telegram_id, "main_menu_prompt"), reply_markup=get_user_menu_keyboard(telegram_id))


@app.on_message(filters.command("bought") & filters.private)
async def handle_bought_command(client: Client, message: Message):
    telegram_id = message.from_user.id
    
    if telegram_id not in user_states or user_states[telegram_id]["step"] != "await_order_id":
        await message.reply_text(_(telegram_id, "bought_start_purchase"))
        return

    try:
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.reply_text(_(telegram_id, "bought_usage", command_name="/bought", expected_args="<ORDER_ID>"))
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
            "card_number_sent": "User confirmed payment via bot", # More descriptive
            "purchase_type": purchase_type
        }

        if purchase_type == 'gb' or purchase_type == 'month':
            payload_data["quantity"] = user_states[telegram_id]["quantity"]
        elif purchase_type == 'custom':
            payload_data["time_quantity"] = user_states[telegram_id]["time_quantity"]
            payload_data["traffic_quantity"] = user_states[telegram_id]["traffic_quantity"]

        response = await call_unified_api("/bot_api/user/submit_transaction", payload_data)

        if response.get('success'):
            admin_telegram_id = response['data']['admin_telegram_id']
            
            purchase_summary = ""
            if purchase_type == 'gb' or purchase_type == 'month':
                purchase_summary = _(telegram_id, "admin_trans_details_simple", 
                                     purchase_type=purchase_type.upper(), 
                                     quantity=user_states[telegram_id]['quantity'])
            elif purchase_type == 'custom':
                purchase_summary = _(telegram_id, "admin_trans_details_custom", 
                                     time_quantity=user_states[telegram_id]['time_quantity'], 
                                     traffic_quantity=user_states[telegram_id]['traffic_quantity'])

            if admin_telegram_id != '0':
                await client.send_message(
                    chat_id=int(admin_telegram_id),
                    text=_(telegram_id, "telegram_bot_payment_req",
                         username=message.from_user.first_name,
                         telegram_id=telegram_id,
                         order_id=order_id,
                         amount=calculated_amount,
                         purchase_summary=purchase_summary
                    )
                )
            await message.reply_text(_(telegram_id, "bought_submit_success"))
        else:
            await message.reply_text(_(telegram_id, "bought_error_submit", message=response.get('message', 'Unknown error')))
    except Exception as e:
        await message.reply_text(_(telegram_id, "unexpected_error", error_message=str(e)))
    finally:
        if telegram_id in user_states:
            del user_states[telegram_id] # Always clear state after /bought command

@app.on_message(filters.command("support") & filters.private)
async def handle_support_command(client: Client, message: Message):
    telegram_id = message.from_user.id
    support_message = message.text.split(maxsplit=1)
    if len(support_message) < 2:
        await message.reply_text(_(telegram_id, "support_prompt"))
        return

    response = await call_unified_api("/bot_api/user/call_support", {
        "telegram_id": telegram_id,
        "message": support_message[1]
    })

    if response.get('success'):
        admin_telegram_id = response['data']['admin_telegram_id']
        support_text_to_admin = response['data']['support_message']
        if admin_telegram_id != '0':
            try:
                await client.send_message(chat_id=int(admin_telegram_id), text=support_text_to_admin)
            except Exception as e:
                print(f"Error sending support message to admin {admin_telegram_id}: {e}")
                await message.reply_text(_(telegram_id, "error_support_send", message="Could not forward message to admin."))
                return
        await message.reply_text(_(telegram_id, "support_sent"))
    else:
        await message.reply_text(_(telegram_id, "error_support_send", message=response.get('message', 'Unknown error')))

@app.on_message(filters.command("approve") & filters.private)
async def admin_approve_transaction_command(client: Client, message: Message):
    telegram_id = message.from_user.id
    is_admin_resp = await call_unified_api("/bot_api/admin/check_admin", {"telegram_id": telegram_id})
    if not is_admin_resp.get('data', {}).get('is_admin', False):
        await message.reply_text(_(telegram_id, "admin_unauthorized"))
        return

    parts = message.text.split(maxsplit=2)
    if len(parts) < 2:
        await message.reply_text(_(telegram_id, "cmd_usage_error", command_name="/approve", expected_args="<ORDER_ID> [ADMIN_NOTE]"))
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
            client_name = response['data'].get('client_name')
            new_traffic_gb = response['data'].get('new_traffic_gb', 0)
            new_time_days = response['data'].get('new_time_days', 0)

            await message.reply_text(_(telegram_id, "transaction_approved", 
                                       order_id=order_id, 
                                       client_name=client_name,
                                       new_traffic_gb=new_traffic_gb,
                                       new_time_days=new_time_days))
            
            # Send config to user
            if client_config:
                await client.send_message(
                    chat_id=target_telegram_id,
                    text=_(target_telegram_id, "purchase_approved_user") + 
                         _(target_telegram_id, "license_config_ready", config=client_config)
                )
            else:
                await client.send_message(
                    chat_id=target_telegram_id,
                    text=_(target_telegram_id, "purchase_approved_user") +
                         _(target_telegram_id, "transaction_approved_no_config", client_name=client_name)
                )
        else:
            await message.reply_text(_(telegram_id, "unexpected_error", error_message=response.get('message', 'Unknown error')))
    except Exception as e:
        await message.reply_text(_(telegram_id, "unexpected_error", error_message=str(e)))

@app.on_message(filters.command("reject") & filters.private)
async def admin_reject_transaction_command(client: Client, message: Message):
    telegram_id = message.from_user.id
    is_admin_resp = await call_unified_api("/bot_api/admin/check_admin", {"telegram_id": telegram_id})
    if not is_admin_resp.get('data', {}).get('is_admin', False):
        await message.reply_text(_(telegram_id, "admin_unauthorized"))
        return

    parts = message.text.split(maxsplit=2)
    if len(parts) < 2:
        await message.reply_text(_(telegram_id, "cmd_usage_error", command_name="/reject", expected_args="<ORDER_ID> [ADMIN_NOTE]"))
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
                text=_(target_telegram_id, "purchase_rejected_user", order_id=order_id, admin_note=admin_note if admin_note else _(target_telegram_id, "No specific reason provided."))
            )
        else:
            await message.reply_text(_(telegram_id, "unexpected_error", error_message=response.get('message', 'Unknown error')))
    except Exception as e:
        await message.reply_text(_(telegram_id, "unexpected_error", error_message=str(e)))

@app.on_message(filters.command("ban") & filters.private)
async def admin_ban_user_command(client: Client, message: Message):
    telegram_id = message.from_user.id
    is_admin_resp = await call_unified_api("/bot_api/admin/check_admin", {"telegram_id": telegram_id})
    if not is_admin_resp.get('data', {}).get('is_admin', False):
        await message.reply_text(_(telegram_id, "admin_unauthorized"))
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply_text(_(telegram_id, "cmd_usage_error", command_name="/ban", expected_args="<TELEGRAM_ID>"))
        return
    try:
        target_telegram_id = int(parts[1])
        response = await call_unified_api("/bot_api/admin/manage_user", {
            "admin_telegram_id": telegram_id,
            "target_telegram_id": target_telegram_id,
            "action": "ban"
        })
        if response.get('success'):
            await message.reply_text(_(telegram_id, "user_banned", target_telegram_id=target_telegram_id))
        else:
            await message.reply_text(_(telegram_id, "unexpected_error", error_message=response.get('message', 'Unknown error')))
    except ValueError:
        await message.reply_text(_(telegram_id, "invalid_id_format"))
    except Exception as e:
        await message.reply_text(_(telegram_id, "unexpected_error", error_message=str(e)))

@app.on_message(filters.command("unban") & filters.private)
async def admin_unban_user_command(client: Client, message: Message):
    telegram_id = message.from_user.id
    is_admin_resp = await call_unified_api("/bot_api/admin/check_admin", {"telegram_id": telegram_id})
    if not is_admin_resp.get('data', {}).get('is_admin', False):
        await message.reply_text(_(telegram_id, "admin_unauthorized"))
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply_text(_(telegram_id, "cmd_usage_error", command_name="/unban", expected_args="<TELEGRAM_ID>"))
        return
    try:
        target_telegram_id = int(parts[1])
        response = await call_unified_api("/bot_api/admin/manage_user", {
            "admin_telegram_id": telegram_id,
            "target_telegram_id": target_telegram_id,
            "action": "unban"
        })
        if response.get('success'):
            await message.reply_text(_(telegram_id, "user_unbanned", target_telegram_id=target_telegram_id))
        else:
            await message.reply_text(_(telegram_id, "unexpected_error", error_message=response.get('message', 'Unknown error')))
    except ValueError:
        await message.reply_text(_(telegram_id, "invalid_id_format"))
    except Exception as e:
        await message.reply_text(_(telegram_id, "unexpected_error", error_message=str(e)))

@app.on_message(filters.command("update_traffic") & filters.private)
async def admin_update_traffic_command(client: Client, message: Message):
    telegram_id = message.from_user.id
    is_admin_resp = await call_unified_api("/bot_api/admin/check_admin", {"telegram_id": telegram_id})
    if not is_admin_resp.get('data', {}).get('is_admin', False):
        await message.reply_text(_(telegram_id, "admin_unauthorized"))
        return

    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.reply_text(_(telegram_id, "cmd_usage_error", command_name="/update_traffic", expected_args="<TELEGRAM_ID> <GB>"))
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
        if response.get('success'):
            await message.reply_text(_(telegram_id, "user_traffic_updated", target_telegram_id=target_telegram_id, new_traffic_gb=traffic_gb))
        else:
            await message.reply_text(_(telegram_id, "unexpected_error", error_message=response.get('message', 'Unknown error')))
    except ValueError:
        await message.reply_text(_(telegram_id, "invalid_num_format"))
    except Exception as e:
        await message.reply_text(_(telegram_id, "unexpected_error", error_message=str(e)))

@app.on_message(filters.command("update_time") & filters.private)
async def admin_update_time_command(client: Client, message: Message):
    telegram_id = message.from_user.id
    is_admin_resp = await call_unified_api("/bot_api/admin/check_admin", {"telegram_id": telegram_id})
    if not is_admin_resp.get('data', {}).get('is_admin', False):
        await message.reply_text(_(telegram_id, "admin_unauthorized"))
        return

    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.reply_text(_(telegram_id, "cmd_usage_error", command_name="/update_time", expected_args="<TELEGRAM_ID> <DAYS>"))
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
        if response.get('success'):
            await message.reply_text(_(telegram_id, "user_time_updated", target_telegram_id=target_telegram_id, new_time_days=time_days))
        else:
            await message.reply_text(_(telegram_id, "unexpected_error", error_message=response.get('message', 'Unknown error')))
    except ValueError:
        await message.reply_text(_(telegram_id, "invalid_num_format"))
    except Exception as e:
        await message.reply_text(_(telegram_id, "unexpected_error", error_message=str(e)))

@app.on_message(filters.command("broadcast") & filters.private)
async def admin_broadcast_command(client: Client, message: Message):
    telegram_id = message.from_user.id
    is_admin_resp = await call_unified_api("/bot_api/admin/check_admin", {"telegram_id": telegram_id})
    if not is_admin_resp.get('data', {}).get('is_admin', False):
        await message.reply_text(_(telegram_id, "admin_unauthorized"))
        return

    broadcast_message = message.text.split(maxsplit=1)
    if len(broadcast_message) < 2:
        await message.reply_text(_(telegram_id, "admin_broadcast_prompt"))
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
                await client.send_message(chat_id=user_id, text=_(user_id, "broadcast_msg_prefix") + message_to_send)
                sent_count += 1
                time.sleep(0.2) # Small delay to avoid hitting Telegram API limits
            except Exception as e:
                print(f"Error sending broadcast to user {user_id}: {e}")
        await message.reply_text(_(telegram_id, "admin_broadcast_sent", sent_count=sent_count))
    else:
        await message.reply_text(_(telegram_id, "admin_error_broadcast", message=response.get('message', 'Unknown error')))


# --- CandyPanel API Passthrough Commands (Admin Only) ---
# Each of these is wrapped with admin check and proper error handling/messages.
@app.on_message(filters.command("cp_new_client") & filters.private)
async def cp_new_client_command(client: Client, message: Message):
    telegram_id = message.from_user.id
    is_admin_resp = await call_unified_api("/bot_api/admin/check_admin", {"telegram_id": telegram_id})
    if not is_admin_resp.get('data', {}).get('is_admin', False):
        await message.reply_text(_(telegram_id, "admin_unauthorized"))
        return

    parts = message.text.split(maxsplit=6)
    if len(parts) < 5:
        await message.reply_text(_(telegram_id, "cmd_usage_error", command_name="/cp_new_client", expected_args="<name> <expires_iso> <traffic_bytes> <wg_id> [note]"))
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
        if response.get('success'):
            await message.reply_text(response.get('message', 'Success'))
            if response['data'].get('client_config'):
                await message.reply_text(f"Client config for {name}:\n```\n{response['data']['client_config']}\n```")
        else:
            await message.reply_text(_(telegram_id, "unexpected_error", error_message=response.get('message', 'Unknown error')))
    except ValueError:
        await message.reply_text(_(telegram_id, "invalid_id_format"))
    except Exception as e:
        await message.reply_text(_(telegram_id, "unexpected_error", error_message=str(e)))

@app.on_message(filters.command("cp_edit_client") & filters.private)
async def cp_edit_client_command(client: Client, message: Message):
    telegram_id = message.from_user.id
    is_admin_resp = await call_unified_api("/bot_api/admin/check_admin", {"telegram_id": telegram_id})
    if not is_admin_resp.get('data', {}).get('is_admin', False):
        await message.reply_text(_(telegram_id, "admin_unauthorized"))
        return

    parts = message.text.split(maxsplit=5)
    if len(parts) < 2:
        await message.reply_text(_(telegram_id, "cmd_usage_error", command_name="/cp_edit_client", expected_args="<name> [expires_iso] [traffic_bytes] [status_bool] [note]"))
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
        if response.get('success'):
            await message.reply_text(response.get('message', 'Success'))
        else:
            await message.reply_text(_(telegram_id, "unexpected_error", error_message=response.get('message', 'Unknown error')))
    except Exception as e:
        await message.reply_text(_(telegram_id, "unexpected_error", error_message=str(e)))

@app.on_message(filters.command("cp_delete_client") & filters.private)
async def cp_delete_client_command(client: Client, message: Message):
    telegram_id = message.from_user.id
    is_admin_resp = await call_unified_api("/bot_api/admin/check_admin", {"telegram_id": telegram_id})
    if not is_admin_resp.get('data', {}).get('is_admin', False):
        await message.reply_text(_(telegram_id, "admin_unauthorized"))
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply_text(_(telegram_id, "cmd_usage_error", command_name="/cp_delete_client", expected_args="<name>"))
        return
    
    name = parts[1]
    response = await call_unified_api("/bot_api/admin/server_control", {
        "admin_telegram_id": telegram_id,
        "resource": "client",
        "action": "delete",
        "data": {"name": name}
    })
    if response.get('success'):
        await message.reply_text(response.get('message', 'Success'))
    else:
        await message.reply_text(_(telegram_id, "unexpected_error", error_message=response.get('message', 'Unknown error')))

@app.on_message(filters.command("cp_get_config") & filters.private)
async def cp_get_config_command(client: Client, message: Message):
    telegram_id = message.from_user.id
    is_admin_resp = await call_unified_api("/bot_api/admin/check_admin", {"telegram_id": telegram_id})
    if not is_admin_resp.get('data', {}).get('is_admin', False):
        await message.reply_text(_(telegram_id, "admin_unauthorized"))
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply_text(_(telegram_id, "cmd_usage_error", command_name="/cp_get_config", expected_args="<name>"))
        return
    
    name = parts[1]
    response = await call_unified_api("/bot_api/admin/server_control", {
        "admin_telegram_id": telegram_id,
        "resource": "client",
        "action": "get_config",
        "data": {"name": name}
    })
    if response.get('success'):
        await message.reply_text(response.get('message', 'Success'))
        if response['data'].get('config'):
            await message.reply_text(f"Client config for {name}:\n```\n{response['data']['config']}\n```")
    else:
        await message.reply_text(_(telegram_id, "unexpected_error", error_message=response.get('message', 'Unknown error')))

@app.on_message(filters.command("cp_new_interface") & filters.private)
async def cp_new_interface_command(client: Client, message: Message):
    telegram_id = message.from_user.id
    is_admin_resp = await call_unified_api("/bot_api/admin/check_admin", {"telegram_id": telegram_id})
    if not is_admin_resp.get('data', {}).get('is_admin', False):
        await message.reply_text(_(telegram_id, "admin_unauthorized"))
        return

    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.reply_text(_(telegram_id, "cmd_usage_error", command_name="/cp_new_interface", expected_args="<address_range> <port>"))
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
        if response.get('success'):
            await message.reply_text(response.get('message', 'Success'))
        else:
            await message.reply_text(_(telegram_id, "unexpected_error", error_message=response.get('message', 'Unknown error')))
    except ValueError:
        await message.reply_text(_(telegram_id, "invalid_num_format"))
    except Exception as e:
        await message.reply_text(_(telegram_id, "unexpected_error", error_message=str(e)))

@app.on_message(filters.command("cp_edit_interface") & filters.private)
async def cp_edit_interface_command(client: Client, message: Message):
    telegram_id = message.from_user.id
    is_admin_resp = await call_unified_api("/bot_api/admin/check_admin", {"telegram_id": telegram_id})
    if not is_admin_resp.get('data', {}).get('is_admin', False):
        await message.reply_text(_(telegram_id, "admin_unauthorized"))
        return

    parts = message.text.split(maxsplit=4)
    if len(parts) < 2:
        await message.reply_text(_(telegram_id, "cmd_usage_error", command_name="/cp_edit_interface", expected_args="<name_wgX> [address] [port] [status_bool]"))
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
        if response.get('success'):
            await message.reply_text(response.get('message', 'Success'))
        else:
            await message.reply_text(_(telegram_id, "unexpected_error", error_message=response.get('message', 'Unknown error')))
    except ValueError:
        await message.reply_text(_(telegram_id, "invalid_num_format"))
    except Exception as e:
        await message.reply_text(_(telegram_id, "unexpected_error", error_message=str(e)))

@app.on_message(filters.command("cp_delete_interface") & filters.private)
async def cp_delete_interface_command(client: Client, message: Message):
    telegram_id = message.from_user.id
    is_admin_resp = await call_unified_api("/bot_api/admin/check_admin", {"telegram_id": telegram_id})
    if not is_admin_resp.get('data', {}).get('is_admin', False):
        await message.reply_text(_(telegram_id, "admin_unauthorized"))
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply_text(_(telegram_id, "cmd_usage_error", command_name="/cp_delete_interface", expected_args="<wg_id>"))
        return
    try:
        wg_id = int(parts[1])
        response = await call_unified_api("/bot_api/admin/server_control", {
            "admin_telegram_id": telegram_id,
            "resource": "interface",
            "action": "delete",
            "data": {"wg_id": wg_id}
        })
        if response.get('success'):
            await message.reply_text(response.get('message', 'Success'))
        else:
            await message.reply_text(_(telegram_id, "unexpected_error", error_message=response.get('message', 'Unknown error')))
    except ValueError:
        await message.reply_text(_(telegram_id, "invalid_id_format"))
    except Exception as e:
        await message.reply_text(_(telegram_id, "unexpected_error", error_message=str(e)))

@app.on_message(filters.command("cp_change_setting") & filters.private)
async def cp_change_setting_command(client: Client, message: Message):
    telegram_id = message.from_user.id
    is_admin_resp = await call_unified_api("/bot_api/admin/check_admin", {"telegram_id": telegram_id})
    if not is_admin_resp.get('data', {}).get('is_admin', False):
        await message.reply_text(_(telegram_id, "admin_unauthorized"))
        return

    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.reply_text(_(telegram_id, "cmd_usage_error", command_name="/cp_change_setting", expected_args="<key> <value>"))
        return
    
    key = parts[1]
    value = parts[2]
    response = await call_unified_api("/bot_api/admin/server_control", {
        "admin_telegram_id": telegram_id,
        "resource": "setting",
        "action": "update",
        "data": {"key": key, "value": value}
    })
    if response.get('success'):
        await message.reply_text(response.get('message', 'Success'))
        # Specific handling for telegram_bot_status to reflect immediate change
        if key == 'telegram_bot_status':
            if value == '1':
                await message.reply_text(_(telegram_id, "bot_already_running"))
            else:
                await message.reply_text(_(telegram_id, "bot_already_stopped"))
    else:
        await message.reply_text(_(telegram_id, "unexpected_error", error_message=response.get('message', 'Unknown error')))

@app.on_message(filters.command("cp_trigger_sync") & filters.private)
async def cp_trigger_sync_command(client: Client, message: Message):
    telegram_id = message.from_user.id
    is_admin_resp = await call_unified_api("/bot_api/admin/check_admin", {"telegram_id": telegram_id})
    if not is_admin_resp.get('data', {}).get('is_admin', False):
        await message.reply_text(_(telegram_id, "admin_unauthorized"))
        return
    
    response = await call_unified_api("/bot_api/admin/server_control", {
        "admin_telegram_id": telegram_id,
        "resource": "sync",
        "action": "trigger"
    })
    if response.get('success'):
        await message.reply_text(response.get('message', 'Success'))
    else:
        await message.reply_text(_(telegram_id, "unexpected_error", error_message=response.get('message', 'Unknown error')))

# --- Main Execution ---
print("Bot started. Press Ctrl+C to exit.")
# This is a blocking call, so it should be the last thing in the script.
app.run()
