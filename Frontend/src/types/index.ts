export interface Client {
  name: string;
  wg: number;
  public_key: string;
  private_key: string;
  address: string;
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
}

export interface Interface {
  wg: number;
  private_key: string;
  public_key: string;
  port: number;
  address_range: string;
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

export interface AllData {
  dashboard: DashboardStats;
  clients: Client[];
  interfaces: Interface[];
  settings: Record<string, string>;
}