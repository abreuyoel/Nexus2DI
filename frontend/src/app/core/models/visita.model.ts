export interface Visita {
  id: number;
  mercaderista_id: number;
  punto_id: number;
  ruta_id: number;
  fecha: string;
  estado: string;
  observaciones?: string;
  hora_inicio?: string;
  hora_fin?: string;
  latitud_inicio?: number;
  longitud_inicio?: number;
  balance_inicial?: number;
  balance_final?: number;
  created_at?: string;
  // Relaciones cargadas
  punto?: PuntoInteres;
  mercaderista?: Mercaderista;
}

export interface Foto {
  id: number;
  visita_id: number;
  id_tipo_foto: number;
  tipo_nombre?: string;
  blob_path?: string;
  url?: string;
  estado: string;
  motivo_rechazo?: string;
  latitud?: number;
  longitud?: number;
  exif_timestamp?: string;
  camera_model?: string;
  created_at?: string;
}

export interface Balance {
  id: number;
  id_cliente?: number;
  fecha_balance?: string;
  identificador_pdv?: string;
  mercaderista?: string;
  producto?: string;
  categoria?: string;
  fabricante?: string;
  inv_inicial?: number;
  inv_final?: number;
  inv_deposito?: number;
  caras?: number;
  precio_bs?: number;
  precio_ds?: number;
  visita_id?: number;
}

export interface ChatMensajeLector {
  id_usuario: number;
  username?: string;
  fecha_lectura?: string;
}

export interface ChatMensaje {
  id: number;
  visita_id?: number;
  conversacion_id?: number;
  foto_id?: number;
  foto_adjunta?: string;
  sender_type: string;
  sender_id?: number;
  sender_nombre?: string;
  mensaje: string;
  leido: boolean;
  leido_por?: ChatMensajeLector[];
  created_at?: string;
}

export interface Mercaderista {
  id: number;
  cedula: string;
  nombre: string;
  apellido?: string;
  nombre_completo: string;
  email?: string;
  telefono?: string;
  tipo: string;
  activo: boolean;
  is_auditor: boolean;
}

export interface PuntoInteres {
  id: string;
  nombre?: string;
  direccion?: string;
  departamento?: string;
  region?: string;
  ciudad?: string;
  cadena?: string;
  jerarquia_n2?: string;
  jerarquia_n2_2?: string;
  nivel_de_alcance?: string;
  latitud?: string;
  longitud?: string;
  rif?: string;
  radio?: string;
}
