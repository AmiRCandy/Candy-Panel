# db.py
import sqlite3
import time
import json , os
from datetime import datetime

class SQLite:
    def __init__(self, db_path='CandyPanel.db'):
        """
        Initializes the SQLite database connection.
        """
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(script_dir, db_path)
        self.conn = None
        self.cursor = None
        self._connect()
        self._initialize_tables()

    def _connect(self):
        """
        Establishes a connection to the SQLite database.
        """
        try:
            self.conn = sqlite3.connect(self.db_path, timeout=30, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            self.cursor.execute("PRAGMA journal_mode=WAL;")
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")
            raise ConnectionError(f"Database connection error: {e}")

    def _initialize_tables(self):
        """
        Creates necessary tables if they don't exist and inserts default settings.
        Includes tables for CandyPanel and Telegram Bot.
        """
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS `interfaces` (
                    `wg` INTEGER PRIMARY KEY,
                    `private_key` TEXT NOT NULL,
                    `public_key` TEXT NOT NULL,
                    `port` INTEGER NOT NULL UNIQUE,
                    `address_range` TEXT NOT NULL UNIQUE,
                    `ipv6_address_range` TEXT UNIQUE,
                    `status` BOOLEAN DEFAULT 1
                );
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS `clients` (
                    `name` TEXT NOT NULL UNIQUE, 
                    `wg` INTEGER NOT NULL,
                    `public_key` TEXT NOT NULL UNIQUE, 
                    `private_key` TEXT NOT NULL,
                    `address` TEXT NOT NULL UNIQUE,
                    `ipv6_address` TEXT UNIQUE,
                    `created_at` TEXT NOT NULL,
                    `expires` TEXT NOT NULL,
                    `note` TEXT DEFAULT '',
                    `traffic` TEXT NOT NULL, 
                    `used_trafic` TEXT NOT NULL DEFAULT '{"download":0,"upload":0, "last_wg_rx":0, "last_wg_tx":0}',
                    `connected_now` BOOLEAN NOT NULL DEFAULT 0,
                    `status` BOOLEAN NOT NULL DEFAULT 1
                );
            """)

            # Add IPv6 columns if they don't exist (migration for existing DBs)
            self.cursor.execute("PRAGMA table_info(interfaces);")
            interfaces_cols = [col[1] for col in self.cursor.fetchall()]
            if 'ipv6_address_range' not in interfaces_cols:
                self.cursor.execute("ALTER TABLE `interfaces` ADD COLUMN `ipv6_address_range` TEXT UNIQUE;")

            self.cursor.execute("PRAGMA table_info(clients);")
            clients_cols = [col[1] for col in self.cursor.fetchall()]
            if 'ipv6_address' not in clients_cols:
                self.cursor.execute("ALTER TABLE `clients` ADD COLUMN `ipv6_address` TEXT UNIQUE;")
            
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS `settings` (
                    `key` TEXT PRIMARY KEY,
                    `value` TEXT NOT NULL
                );
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS `users` (
                    `telegram_id` INTEGER PRIMARY KEY,
                    `candy_client_name` TEXT UNIQUE, 
                    `traffic_bought_gb` REAL DEFAULT 0,
                    `time_bought_days` INTEGER DEFAULT 0,
                    `status` TEXT DEFAULT 'active',
                    `is_admin` BOOLEAN DEFAULT 0,
                    `created_at` TEXT NOT NULL,
                    `language` TEXT DEFAULT 'en'
                );
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS `transactions` (
                    `order_id` TEXT PRIMARY KEY,
                    `telegram_id` INTEGER NOT NULL,
                    `amount` REAL NOT NULL, 
                    `card_number_sent` TEXT,
                    `status` TEXT DEFAULT 'pending', 
                    `requested_at` TEXT NOT NULL,
                    `approved_at` TEXT,
                    `admin_note` TEXT,
                    `purchase_type` TEXT, 
                    `quantity` REAL, 
                    `time_quantity` REAL DEFAULT 0,
                    `traffic_quantity` REAL DEFAULT 0,
                    FOREIGN KEY (`telegram_id`) REFERENCES `users`(`telegram_id`)
                );
            """)
            self.conn.commit()

            # Insert default settings if the settings table is empty
            if self.count('settings') == 0:
                self._insert_default_settings()

        except sqlite3.Error as e:
            print(f"Database table initialization error: {e}")
            raise RuntimeError(f"Database table initialization error: {e}")

    def _insert_default_settings(self):
        """
        Inserts initial default settings into the 'settings' table.
        Includes settings for CandyPanel and Telegram Bot.
        """
        default_settings = [
            {'key': 'server_ip', 'value': '192.168.1.100'},
            {'key': 'custom_endpont', 'value': '192.168.1.100'},
            {'key': 'session_token', 'value': 'NONE'},
            {'key': 'dns', 'value': '8.8.8.8'},
            {'key': 'ipv6_dns', 'value': '2001:4860:4860::8888'},
            {'key': 'admin', 'value': '{"user":"admin","password":"admin"}'},
            {'key': 'status', 'value': '1'},
            {'key': 'alert', 'value': '["Welcome To Candy Panel - by AmiRCandy"]'},
            {'key': 'reset_time', 'value': '0'},
            {'key': 'mtu', 'value': '1420'}, 
            {'key': 'bandwidth', 'value': '0'},
            {'key': 'uptime', 'value': '0'},
            {'key': 'telegram_bot_status', 'value': '0'},
            {'key': 'telegram_bot_admin_id', 'value': '0'},
            {'key': 'telegram_bot_token', 'value': 'YOUR_TELEGRAM_BOT_TOKEN'}, 
            {'key': 'telegram_api_hash', 'value': 'YOUR_TELEGRAM_API_HASH'}, 
            {'key': 'telegram_api_id', 'value': 'YOUR_TELEGRAM_API_ID'}, 
            {'key': 'admin_card_number', 'value': 'YOUR_ADMIN_CARD_NUMBER'}, 
            {'key': 'prices', 'value': '{"1GB": 4000, "1Month": 75000}'}, 
            {'key': 'api_tokens', 'value': '{}'},
            {'key': 'auto_backup', 'value': '1'},
            {'key': 'install', 'value': '0'},
            {'key': 'telegram_bot_pid', 'value': '0'},
            {'key': 'ap_port', 'value': '3446'},
        ]
        for setting in default_settings:
            self.insert('settings', setting)
        print("Default settings inserted.")

    def _execute_query(self, query: str, params: tuple = (), fetch_type: str = None):
        """
        Executes a SQL query with given parameters.
        'fetch_type' can be 'all' (for fetchall), 'one' (for fetchone), or None (for DML operations).
        """
        try:
            self.cursor.execute(query, params)
            if fetch_type == 'all':
                return [dict(row) for row in self.cursor.fetchall()]
            elif fetch_type == 'one':
                row = self.cursor.fetchone()
                return dict(row) if row else None
            else:
                self.conn.commit()
                if 'INSERT' in query.upper():
                    return self.cursor.lastrowid
                return self.cursor.rowcount
        except sqlite3.Error as e:
            print(f"Database query failed: {e}\nQuery: {query}\nParams: {params}")
            raise 

    def select(self, table: str, columns: str | list[str] = '*', where: dict = None) -> list[dict]:
        """
        Selects data from a table.
        'columns' can be a string (e.g., '*') or a list of column names.
        'where' is a dictionary for filtering (e.g., {'id': 1}).
        """
        cols = ', '.join(f"`{c}`" for c in columns) if isinstance(columns, list) else columns
        query = f"SELECT {cols} FROM `{table}`"
        params = []
        if where:
            query += " WHERE " + " AND ".join(f"`{k}`=?" for k in where)
            params = list(where.values())
        return self._execute_query(query, tuple(params), 'all')

    def get(self, table: str, columns: str | list[str] = '*', where: dict = None) -> dict | None:
        """
        Retrieves a single row from a table.
        Returns None if no row is found.
        """
        rows = self.select(table, columns, where)
        return rows[0] if rows else None

    def has(self, table: str, where: dict) -> bool:
        """
        Checks if a record exists in a table based on the where clause.
        """
        return self.count(table, where) > 0

    def count(self, table: str, where: dict = None) -> int:
        """
        Counts the number of rows in a table, optionally with a where clause.
        """
        query = f"SELECT COUNT(*) as count FROM `{table}`"
        params = []
        if where:
            query += " WHERE " + " AND ".join(f"`{k}`=?" for k in where)
            params = list(where.values())
        result = self._execute_query(query, tuple(params), 'one')
        return result["count"] if result else 0

    def insert(self, table: str, data: dict):
        """
        Inserts a new row into a table.
        'data' is a dictionary of column-value pairs.
        """
        keys = ', '.join(f"`{k}`" for k in data.keys())
        placeholders = ', '.join(['?'] * len(data))
        query = f"INSERT INTO `{table}` ({keys}) VALUES ({placeholders})"
        return self._execute_query(query, tuple(data.values()))

    def update(self, table: str, data: dict, where: dict):
        """
        Updates existing rows in a table.
        'data' is a dictionary of column-value pairs to update.
        'where' is a dictionary for filtering which rows to update.
        """
        set_clause = ', '.join(f"`{k}`=?" for k in data)
        where_clause = ' AND '.join(f"`{k}`=?" for k in where)
        query = f"UPDATE `{table}` SET {set_clause} WHERE {where_clause}"
        return self._execute_query(query, tuple(data.values()) + tuple(where.values()))

    def delete(self, table: str, where: dict):
        """
        Deletes rows from a table.
        'where' is a dictionary for filtering which rows to delete.
        """
        where_clause = ' AND '.join(f"`{k}`=?" for k in where)
        query = f"DELETE FROM `{table}` WHERE {where_clause}"
        return self._execute_query(query, tuple(where.values()))

    def close(self):
        """
        Closes the database connection.
        """
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None