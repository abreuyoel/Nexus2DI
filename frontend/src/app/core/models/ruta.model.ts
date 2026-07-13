export interface Ruta {
  id: number;
  nombre: string;
  tipo?: string;
  servicio?: string;
  cuadrante?: string;
  coordinador_1?: string;
  coordinador_2?: string;
  activa: boolean;
  analista_id?: number;
  cliente_id?: number;
  created_at?: string;
  // Enriquecidos por el backend (lista de rutas)
  id_cliente_exclusivo?: number | null;
  cliente_exclusivo_nombre?: string | null;
  puntos_count?: number;
  region?: string | null;
  clientes?: string[];
}

export interface RutaProgramacion {
  id: number;
  ruta_id: number;
  punto_id?: string;
  dia?: string;
  prioridad?: string;
  activo?: boolean;
  punto?: { id: string; nombre?: string; direccion?: string };
  cliente?: { id: number; nombre?: string };
}

export interface CambioFuturo {
  id: number;
  ruta_id?: number;
  id_programacion?: number;
  punto_interes_nombre?: string;
  cliente_nombre?: string;
  dia?: string;
  prioridad?: string;
  tipo_cambio?: string;
  fecha_ejecucion?: string;
  estado?: string;
  observaciones?: string;
  creado_por?: string;
  created_at?: string;
}
