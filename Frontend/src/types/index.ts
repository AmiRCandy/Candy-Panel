export interface Client {
  name: string;
  wg: number;
  public_key: string;
  private_key: string;
  address: string;
  created_at: string;
  expires: string;
  note: string;
  traffic: string; // Total traffic quota in bytes
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

export interface ServerStats {
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

export interface ServerConfig {
  server_ip: string;
  dns: string;
  mtu: string;
  reset_time: string;
  status: string;
}

export interface APIToken {
  name: string;
  token: string;
}

export interface InstallationData {
  server_ip: string;
  wg_port: string;
  wg_address_range: string;
  wg_dns: string;
  admin_user: string;
  admin_password: string;
}