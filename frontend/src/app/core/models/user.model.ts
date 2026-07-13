export interface User {
  id: number;
  username: string;
  rol: string;
  rol_nombre?: string;
  email?: string;
  id_rol?: number;
  id_perfil?: number;
  is_admin: boolean;
  is_analyst: boolean;
  is_supervisor: boolean;
  is_client: boolean;
  is_mercaderista: boolean;
  is_coordinador_exclusivo: boolean;
  is_coordinador_tradex: boolean;
  permisos: Permission[];
}

export interface Permission {
  module: string;
  can_read: boolean;
  can_write: boolean;
  can_delete: boolean;
  can_see_all: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  rol: string;
  username: string;
  user_id: number;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginMercaderistaRequest {
  cedula: string;
  password: string;
}
