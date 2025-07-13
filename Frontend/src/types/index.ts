export interface Client {
  name: string;
  wg?: number;
  public_key: string;
  private_key?: string;
  address: string;
  created_at: string;
  expires: string;
  note: string;
  traffic: string; // Traffic limit in bytes (as string)
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
  server_id?: number; // New: Link to the server it belongs to
}

export interface Interface {
  wg: number;
  private_key: string;
  public_key: string;
  port: number;
  address_range: string;
  status: boolean;
  server_id?: number; // New: Link to the server it belongs to
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
  bandwidth: string; // Total bandwidth used (as string representation of bytes)
  uptime: string;
  net: {
    download: string;
    upload: string;
  };
}

export interface Server {
  server_id: number;
  name: string;
  ip_address: string;
  agent_port: number;
  api_key?: string; // Optional for security, might not be returned after creation
  status: string; // e.g., 'active', 'inactive', 'unreachable', 'error'
  last_synced: string | null;
  description: string;
  dashboard_cache?: DashboardStats; // New: Cached dashboard stats from the server
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

export interface ApiTokens {
  [key: string]: string; // A dictionary where key is token name, value is the token string
}

export interface AllData {
  dashboard: DashboardStats;
  clients: Client[];
  interfaces: Interface[];
  settings: Record<string, string>;
}