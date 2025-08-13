export interface Client {
  name: string;
  wg?: number;
  public_key: string;
  private_key?: string;
  address: string;
  ipv6_address?: string;
  created_at: string;
  expires: string;
  note: string;
  traffic: string;
  used_trafic: {
    download: number;
    upload: number;
  };
  connected_now: boolean;
  status: boolean;
  interface_public_key: string | null;
  interface_port: number | null;
  server_endpoint_ip: string;
  server_dns: string;
  server_mtu: string;
}

export interface Interface {
  wg: number;
  private_key: string;
  public_key: string;
  port: number;
  address_range: string;
  ipv6_address_range?: string;
  status: boolean;
}

export interface DashboardStats {
  cpu: string;
  mem: {
    total: string;
    available: string;
    usage: string;
  };
  clients_count: number;
  status: string;
  alert: string[];
  bandwidth: string;
  uptime: string;
  net: {
    download: string;
    upload: string;
  };
}
export interface ApiResponse<T = any> {
  message: string;
  success: boolean;
  data?: T;
}

export interface AuthData {
  access_token: string;
  token_type: string;
}

// New interfaces for Telegram and API Tokens
export interface TelegramSettings {
  telegram_bot_status: string;
  telegram_bot_admin_id: string;
  telegram_bot_token: string;
  telegram_bot_prices: string; // Stored as JSON string
}

export interface ApiTokens {
  [key: string]: string; // A dictionary where key is token name, value is the token string
}

export interface AllData {
  dashboard: DashboardStats;
  clients: Client[];
  interfaces: Interface[];
  settings: Record<string, string>;
  // Add new fields for Telegram settings and API tokens if they are returned directly by getAllData
  // For now, these are part of 'settings' record, but if backend changes, they can be separate.
}