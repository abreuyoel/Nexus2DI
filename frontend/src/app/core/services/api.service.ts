import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { Ruta, RutaProgramacion, CambioFuturo } from '../models/ruta.model';
import { Visita, Foto, Mercaderista, PuntoInteres, ChatMensaje, Balance } from '../models/visita.model';
import { User } from '../models/user.model';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private base = environment.apiUrl;

  constructor(private http: HttpClient) { }

  private params(obj: Record<string, any>): HttpParams {
    let p = new HttpParams();
    for (const [k, v] of Object.entries(obj)) {
      if (v !== undefined && v !== null && (typeof v === 'string' || typeof v === 'number' || typeof v === 'boolean')) {
        p = p.set(k, String(v));
      }
    }
    return p;
  }

  getUsers(limit = 150, search?: string, id_rol?: number, rol?: string): Observable<User[]> {
    const params: any = { limit };
    if (search) params.q = search;
    if (id_rol) params.id_rol = id_rol;
    if (rol) params.rol = rol;
    return this.http.get<User[]>(`${this.base}/api/users`, { params });
  }

  /** Lista ligera para selectores/dropdowns — sin JOINs, mucho más rápido */
  getUsersSlim(limit = 300, search?: string, rol?: string, id_rol?: number): Observable<{id: number; username: string; id_rol: number; rol_nombre: string; activo: boolean}[]> {
    const params: any = { limit };
    if (search) params.q = search;
    if (rol) params.rol = rol;
    if (id_rol) params.id_rol = id_rol;
    return this.http.get<any[]>(`${this.base}/api/users/slim`, { params });
  }
  createUser(data: object): Observable<User> { return this.http.post<User>(`${this.base}/api/users`, data); }
  updateUser(id: number, data: object): Observable<User> { return this.http.patch<User>(`${this.base}/api/users/${id}`, data); }
  deleteUser(id: number): Observable<object> { return this.http.delete<object>(`${this.base}/api/users/${id}`); }
  getAnalysts(): Observable<User[]> { return this.http.get<User[]>(`${this.base}/api/users/analysts`); }
  getSupervisors(): Observable<User[]> { return this.http.get<User[]>(`${this.base}/api/users/supervisors`); }
  getEncuestadores(): Observable<any[]> { return this.http.get<any[]>(`${this.base}/api/users/encuestadores`); }
  createEncuestador(data: object): Observable<any> { return this.http.post<any>(`${this.base}/api/users/encuestadores`, data); }
  updateEncuestador(id: number, data: object): Observable<any> { return this.http.put<any>(`${this.base}/api/users/encuestadores/${id}`, data); }
  deleteEncuestador(id: number): Observable<any> { return this.http.delete<any>(`${this.base}/api/users/encuestadores/${id}`); }
  getModulos(): Observable<any[]> { return this.http.get<any[]>(`${this.base}/api/modulos`); }
  getUserPermissions(userId: number): Observable<any[]> { return this.http.get<any[]>(`${this.base}/api/users/${userId}/permissions`); }
  updateUserPermissions(userId: number, permissions: any[]): Observable<any> { return this.http.post<any>(`${this.base}/api/users/${userId}/permissions`, { permissions }); }

  // --- MERCADERISTAS ---
  getMercaderistas(): Observable<Mercaderista[]> { return this.http.get<Mercaderista[]>(`${this.base}/api/merchandisers`); }
  getMercaderista(id: number): Observable<Mercaderista> { return this.http.get<Mercaderista>(`${this.base}/api/merchandisers/${id}`); }
  createMercaderista(data: object): Observable<Mercaderista> { return this.http.post<Mercaderista>(`${this.base}/api/merchandisers`, data); }
  updateMercaderista(id: number, data: object): Observable<Mercaderista> { return this.http.patch<Mercaderista>(`${this.base}/api/merchandisers/${id}`, data); }
  deleteMercaderista(id: number): Observable<object> { return this.http.delete<object>(`${this.base}/api/merchandisers/${id}`); }
  uploadPhoto(formData: FormData): Observable<object> { return this.http.post<object>(`${this.base}/api/merchandisers/upload-photo`, formData); }
  getActivePoints(cedula: string): Observable<object[]> { return this.http.get<object[]>(`${this.base}/api/merchandisers/${cedula}/active-points`); }
  getFotoMetadatos(fotoId: number): Observable<object> { return this.http.get<object>(`${this.base}/api/merchandisers/foto/${fotoId}/metadatos`); }

  // --- PUNTOS DE INTERÉS ---
  getPoints(opts: { region?: string; ciudad?: string; jerarquia_n2?: string; jerarquia_n2_2?: string; nivel_de_alcance?: string; cadena?: string; search?: string; skip?: number; limit?: number } = {}): Observable<PuntoInteres[]> {
    return this.http.get<PuntoInteres[]>(`${this.base}/api/points`, { params: this.params(opts) });
  }
  createPoint(data: object): Observable<PuntoInteres> { return this.http.post<PuntoInteres>(`${this.base}/api/points`, data); }
  updatePoint(id: string, data: object): Observable<PuntoInteres> { return this.http.put<PuntoInteres>(`${this.base}/api/points/${id}`, data); }
  getRegions(): Observable<string[]> { return this.http.get<string[]>(`${this.base}/api/points/regions/list`); }
  getCities(departamento?: string): Observable<string[]> {
    return this.http.get<string[]>(`${this.base}/api/points/cities/list`, { params: this.params({ departamento }) });
  }
  getChains(): Observable<string[]> { return this.http.get<string[]>(`${this.base}/api/points/chains/list`); }
  deletePoint(id: string): Observable<object> { return this.http.delete<object>(`${this.base}/api/points/${id}`); }
  getJerarquiaN2(): Observable<string[]> { return this.http.get<string[]>(`${this.base}/api/points/jerarquia_n2/list`); }
  getJerarquiaN2_2(): Observable<string[]> { return this.http.get<string[]>(`${this.base}/api/points/jerarquia_n2_2/list`); }
  getNivelesAlcance(): Observable<string[]> { return this.http.get<string[]>(`${this.base}/api/points/nivel_alcance/list`); }
  getPointsCount(opts: { region?: string; ciudad?: string; jerarquia_n2?: string; jerarquia_n2_2?: string; nivel_de_alcance?: string; cadena?: string; search?: string } = {}): Observable<{ total: number }> {
    return this.http.get<{ total: number }>(`${this.base}/api/points/count`, { params: this.params(opts) });
  }
  getPointPhotos(pointId: number, estado?: string): Observable<object[]> {
    return this.http.get<object[]>(`${this.base}/api/points/${pointId}/photos`, { params: this.params({ estado }) });
  }

  // --- CATÁLOGOS PDV ---
  // catalog ∈ 'tipo-negocio' | 'subtipo-negocio' | 'alcance' | 'canal-venta' | 'departamentos'
  listCatalog(catalog: string, activo?: boolean): Observable<{ id: number; nombre: string; activo: boolean }[]> {
    return this.http.get<{ id: number; nombre: string; activo: boolean }[]>(
      `${this.base}/api/catalogos/${catalog}`,
      { params: this.params({ activo }) }
    );
  }
  createCatalogItem(catalog: string, data: { nombre: string; activo?: boolean }): Observable<{ id: number; nombre: string; activo: boolean }> {
    return this.http.post<{ id: number; nombre: string; activo: boolean }>(`${this.base}/api/catalogos/${catalog}`, data);
  }
  updateCatalogItem(catalog: string, id: number, data: { nombre?: string; activo?: boolean }): Observable<{ id: number; nombre: string; activo: boolean }> {
    return this.http.put<{ id: number; nombre: string; activo: boolean }>(`${this.base}/api/catalogos/${catalog}/${id}`, data);
  }
  deleteCatalogItem(catalog: string, id: number, force = false): Observable<object> {
    return this.http.delete<object>(`${this.base}/api/catalogos/${catalog}/${id}`, { params: this.params({ force }) });
  }

  // Servicios — endpoints específicos (extienden el genérico con "prefijo",
  // la sigla usada para el correlativo de nombre de ruta)
  listServicios(activo?: boolean): Observable<{ id: number; nombre: string; prefijo: string | null; activo: boolean }[]> {
    return this.http.get<any[]>(`${this.base}/api/catalogos/servicios`, { params: this.params({ activo }) });
  }
  createServicio(data: { nombre: string; prefijo: string; activo?: boolean }): Observable<any> {
    return this.http.post<any>(`${this.base}/api/catalogos/servicios`, data);
  }
  updateServicio(id: number, data: { nombre?: string; prefijo?: string; activo?: boolean }): Observable<any> {
    return this.http.put<any>(`${this.base}/api/catalogos/servicios/${id}`, data);
  }
  deleteServicio(id: number, force = false): Observable<object> {
    return this.http.delete<object>(`${this.base}/api/catalogos/servicios/${id}`, { params: this.params({ force }) });
  }

  // Ciudades — endpoints específicos
  listCiudades(opts: { departamento_id?: number; departamento?: string; activo?: boolean } = {}): Observable<{ id: number; nombre: string; activo: boolean; departamento_id: number; departamento_nombre: string | null }[]> {
    return this.http.get<any[]>(`${this.base}/api/catalogos/ciudades`, { params: this.params(opts) });
  }
  createCiudad(data: { nombre: string; departamento_id: number; activo?: boolean }): Observable<any> {
    return this.http.post<any>(`${this.base}/api/catalogos/ciudades`, data);
  }
  updateCiudad(id: number, data: { nombre?: string; departamento_id?: number; activo?: boolean }): Observable<any> {
    return this.http.put<any>(`${this.base}/api/catalogos/ciudades/${id}`, data);
  }
  deleteCiudad(id: number, force = false): Observable<object> {
    return this.http.delete<object>(`${this.base}/api/catalogos/ciudades/${id}`, { params: this.params({ force }) });
  }

  // --- RUTAS ---
  getRoutes(activa?: boolean): Observable<Ruta[]> {
    return this.http.get<Ruta[]>(`${this.base}/api/routes`, { params: this.params({ activa }) });
  }
  createRoute(data: object): Observable<Ruta> { return this.http.post<Ruta>(`${this.base}/api/routes`, data); }
  updateRoute(id: number, data: object): Observable<Ruta> { return this.http.patch<Ruta>(`${this.base}/api/routes/${id}`, data); }
  deleteRoute(id: number): Observable<void> { return this.http.delete<void>(`${this.base}/api/routes/${id}`); }
  duplicateRoute(id: number): Observable<Ruta> { return this.http.post<Ruta>(`${this.base}/api/routes/${id}/duplicate`, {}); }
  getRoutePoints(routeId: number, includeInactive = false): Observable<RutaProgramacion[]> {
    return this.http.get<RutaProgramacion[]>(`${this.base}/api/routes/${routeId}/points`, { params: this.params({ include_inactive: includeInactive }) });
  }
  addPointToRoute(routeId: number, data: object): Observable<RutaProgramacion> { return this.http.post<RutaProgramacion>(`${this.base}/api/routes/${routeId}/add-point`, data); }
  removePointFromRoute(programacionId: number): Observable<void> { return this.http.delete<void>(`${this.base}/api/routes/points/${programacionId}`); }
  setPointActive(programacionId: number, activa: boolean): Observable<object> {
    return this.http.patch<object>(`${this.base}/api/routes/points/${programacionId}/active`, {}, { params: this.params({ activa }) });
  }
  bulkApply(routeId: number, body: { inserts?: any[]; updates?: any[]; deletes?: any[] }): Observable<any> {
    return this.http.post<any>(`${this.base}/api/routes/${routeId}/bulk-apply`, body);
  }
  scheduleChange(routeId: number, data: object): Observable<CambioFuturo> { return this.http.post<CambioFuturo>(`${this.base}/api/routes/${routeId}/schedule-change`, data); }
  getFutureChanges(routeId: number): Observable<CambioFuturo[]> { return this.http.get<CambioFuturo[]>(`${this.base}/api/routes/${routeId}/future-changes`); }
  getActivatedRoutes(): Observable<object[]> { return this.http.get<object[]>(`${this.base}/api/routes/activated/today`); }
  getRouteOptions(): Observable<{ servicios: string[] }> { return this.http.get<{ servicios: string[] }>(`${this.base}/api/routes/options`); }
  getNextRouteNumber(servicio: string): Observable<{ next_number: number; prefijo: string }> {
    return this.http.get<{ next_number: number; prefijo: string }>(`${this.base}/api/routes/next-number`, { params: { servicio } });
  }

  // --- CLIENTES ---
  getClients(): Observable<any[]> { return this.http.get<any[]>(`${this.base}/api/clients`); }
  createClient(data: object): Observable<any> { return this.http.post<any>(`${this.base}/api/clients`, data); }
  updateClient(id: number, data: object): Observable<any> { return this.http.put<any>(`${this.base}/api/clients/${id}`, data); }
  deleteClient(id: number): Observable<object> { return this.http.delete<object>(`${this.base}/api/clients/${id}`); }

  // --- ANALISTAS ---
  getAnalystsList(): Observable<any[]> { return this.http.get<any[]>(`${this.base}/api/analysts`); }
  createAnalyst(data: object): Observable<any> { return this.http.post<any>(`${this.base}/api/analysts`, data); }
  updateAnalyst(id: number, data: object): Observable<any> { return this.http.put<any>(`${this.base}/api/analysts/${id}`, data); }
  deleteAnalyst(id: number): Observable<object> { return this.http.delete<object>(`${this.base}/api/analysts/${id}`); }
  // Asignaciones de analista (Fase 2)
  getAnalystsWithAssignments(): Observable<any[]> { return this.http.get<any[]>(`${this.base}/api/analysts/with-assignments`); }
  getAnalystRoutes(id: number): Observable<any[]> { return this.http.get<any[]>(`${this.base}/api/analysts/${id}/routes`); }
  syncAnalystRoutes(id: number, ids: number[]): Observable<object> { return this.http.post<object>(`${this.base}/api/analysts/${id}/sync-routes`, { ids }); }
  getAnalystClients(id: number): Observable<any[]> { return this.http.get<any[]>(`${this.base}/api/analysts/${id}/clients`); }
  getAnalystRouteClients(id: number): Observable<any[]> { return this.http.get<any[]>(`${this.base}/api/analysts/${id}/route-clients`); }
  syncAnalystClients(id: number, ids: number[]): Observable<object> { return this.http.post<object>(`${this.base}/api/analysts/${id}/sync-clients`, { ids }); }

  // --- SUPERVISORES (asignaciones, tablas dedicadas) ---
  createSupervisor(data: { nombre: string }): Observable<any> { return this.http.post<any>(`${this.base}/api/supervisores`, data); }
  updateSupervisor(id: number, data: { nombre: string }): Observable<any> { return this.http.put<any>(`${this.base}/api/supervisores/${id}`, data); }
  deleteSupervisor(id: number): Observable<void> { return this.http.delete<void>(`${this.base}/api/supervisores/${id}`); }
  getSupervisorsWithAssignments(): Observable<any[]> { return this.http.get<any[]>(`${this.base}/api/supervisores/with-assignments`); }
  getSupervisorRoutes(id: number): Observable<any[]> { return this.http.get<any[]>(`${this.base}/api/supervisores/${id}/routes`); }
  syncSupervisorRoutes(id: number, ids: number[]): Observable<object> { return this.http.post<object>(`${this.base}/api/supervisores/${id}/sync-routes`, { ids }); }
  getSupervisorClients(id: number): Observable<any[]> { return this.http.get<any[]>(`${this.base}/api/supervisores/${id}/clients`); }
  getSupervisorRouteClients(id: number): Observable<any[]> { return this.http.get<any[]>(`${this.base}/api/supervisores/${id}/route-clients`); }
  syncSupervisorClients(id: number, ids: number[]): Observable<object> { return this.http.post<object>(`${this.base}/api/supervisores/${id}/sync-clients`, { ids }); }

  // --- VISITAS ---
  getVisits(opts: { estado?: string; ruta_id?: number; fecha?: string } = {}): Observable<Visita[]> {
    return this.http.get<Visita[]>(`${this.base}/api/visits`, { params: this.params(opts) });
  }
  createVisit(data: object): Observable<Visita> { return this.http.post<Visita>(`${this.base}/api/visits`, data); }
  updateVisit(id: number, data: object): Observable<Visita> { return this.http.patch<Visita>(`${this.base}/api/visits/${id}`, data); }
  getPendingVisits(): Observable<Visita[]> { return this.http.get<Visita[]>(`${this.base}/api/visits/pending`); }
  getVisitPhotos(visitId: number, tipo?: number): Observable<Foto[]> {
    return this.http.get<Foto[]>(`${this.base}/api/visits/${visitId}/photos`, { params: this.params({ tipo }) });
  }
  approvePhotos(fotoIds: number[]): Observable<object> { return this.http.post<object>(`${this.base}/api/visits/approve-photos`, { foto_ids: fotoIds }); }
  rejectPhoto(fotoId: number, motivo: string, razonesIds?: number[]): Observable<object> { return this.http.post<object>(`${this.base}/api/visits/reject-photo`, { foto_id: fotoId, motivo, razones_ids: razonesIds }); }
  savePhotoDecisions(decisions: object[]): Observable<object> { return this.http.post<object>(`${this.base}/api/visits/save-decisions`, { decisions }); }

  // --- REVISIÓN / CENTRO DE MANDO (re-aplicado tras restauración) ---
  getReviewList(opts: { desde?: string; hasta?: string; cliente_id?: number } = {}): Observable<any[]> { return this.http.get<any[]>(`${this.base}/api/visits/review-list`, { params: this.params(opts) }); }
  getReviewMercaderistas(opts: { cliente_id?: number } = {}): Observable<any[]> { return this.http.get<any[]>(`${this.base}/api/visits/review-mercaderistas`, { params: this.params(opts) }); }
  markVisitReviewed(visitId: number, revisada = true): Observable<any> { return this.http.post<any>(`${this.base}/api/visits/${visitId}/mark-reviewed`, null, { params: this.params({ revisada }) }); }
  getRejectReasons(): Observable<any[]> { return this.http.get<any[]>(`${this.base}/api/visits/reject-reasons`); }
  getCentroMandoClientes(): Observable<any> { return this.http.get<any>(`${this.base}/api/centro-mando/clientes`); }
  getCentroMandoResumenDia(opts: any = {}): Observable<any> { return this.http.get<any>(`${this.base}/api/centro-mando/resumen-dia`, { params: this.params(opts) }); }
  getCentroMandoActivaciones(opts: any = {}): Observable<any> { return this.http.get<any>(`${this.base}/api/centro-mando/activaciones`, { params: this.params(opts) }); }
  getCentroMandoHorasTrabajadas(opts: { desde?: string; hasta?: string; cliente_id?: number } = {}): Observable<any> { return this.http.get<any>(`${this.base}/api/centro-mando/horas-trabajadas`, { params: this.params(opts) }); }
  getCentroMandoAuditoriaFiltros(): Observable<any> { return this.http.get<any>(`${this.base}/api/centro-mando-auditoria/filtros`); }
  getCentroMandoAuditoriaResumen(opts: { desde?: string; hasta?: string; id_auditor?: number; id_ruta?: number; id_cliente?: number; id_categoria?: number } = {}): Observable<any> { return this.http.get<any>(`${this.base}/api/centro-mando-auditoria/resumen`, { params: this.params(opts) }); }
  getAuditoriaUsuarios(opts: { skip?: number; limit?: number; accion?: string; ejecutor?: string; search?: string; fecha_inicio?: string; fecha_fin?: string } = {}): Observable<any> { return this.http.get<any>(`${this.base}/api/auditoria-usuarios`, { params: this.params(opts) }); }
  getCentroMandoAuditoriaTendenciaCompetencia(opts: { semanas?: number; id_ruta?: number; id_cliente?: number; id_categoria?: number } = {}): Observable<any> { return this.http.get<any>(`${this.base}/api/centro-mando-auditoria/tendencia-competencia`, { params: this.params(opts) }); }
  deleteMercFoto(fotoId: number): Observable<any> { return this.http.delete<any>(`${this.base}/api/merc/foto/${fotoId}`); }

  // --- DATA / BALANCES ---
  getVisitsWithBalances(opts: { fecha_inicio?: string; fecha_fin?: string; cliente_id?: number; mercaderista_id?: number; punto_id?: string } = {}): Observable<Visita[]> {
    return this.http.get<Visita[]>(`${this.base}/api/visits/with-balances`, { params: this.params(opts) });
  }
  getVisitBalances(visitId: number): Observable<Balance[]> { return this.http.get<Balance[]>(`${this.base}/api/visits/${visitId}/balances`); }
  saveBalances(data: { visita_id: number; balances: any[] }): Observable<object> {
    return this.http.post<object>(`${this.base}/api/visits/update-balances`, data);
  }

  // --- CLIENT DATA ---
  getClientDataFilters(): Observable<any> {
    return this.http.get<any>(`${this.base}/api/client-data/filters`);
  }

  // Paginado en el servidor -- ver client-data.component.ts. { total, items }
  // en vez de un array plano: la tabla puede mostrar "X de Y" sin traer Y
  // filas completas.
  getClientDataBalances(filters: any): Observable<{ total: number; items: any[] }> {
    return this.http.get<{ total: number; items: any[] }>(`${this.base}/api/client-data/balances`, { params: this.params(filters) });
  }

  // --- REPORTE DE EXCEL ---
  downloadExcelReport(startDate: string, endDate: string): Observable<Blob> {
    const params = this.params({ fecha_inicio: startDate, fecha_fin: endDate });
    return this.http.get(`${this.base}/api/reporteria/excel`, { params, responseType: 'blob' });
  }

  exportVisitasExcel(opts: { id_cliente: number; fecha_inicio: string; fecha_fin: string; cuadrante?: string; departamento?: string; categoria?: string }): Observable<Blob> {
    const params = this.params(opts);
    return this.http.get(`${this.base}/api/reports/export-visitas`, { params, responseType: 'blob' });
  }
  getExportVisitasFiltros(opts: { id_cliente: number; fecha_inicio?: string; fecha_fin?: string }): Observable<{ cuadrantes: string[]; departamentos: string[]; categorias: string[] }> {
    return this.http.get<{ cuadrantes: string[]; departamentos: string[]; categorias: string[] }>(
      `${this.base}/api/reports/export-visitas-filtros`, { params: this.params(opts) });
  }

  // --- REPORTERÍA ---
  getReportSummary(opts: { fecha_inicio?: string; fecha_fin?: string; ruta_id?: number } = {}): Observable<object> {
    return this.http.get<object>(`${this.base}/api/reports/summary`, { params: this.params(opts) });
  }
  getChartData(tipo: string, opts: Record<string, string> = {}): Observable<object> {
    return this.http.get<object>(`${this.base}/api/reports/chart-data`, { params: this.params({ tipo, ...opts }) });
  }
  getActivatedRoutesReport(): Observable<object[]> { return this.http.get<object[]>(`${this.base}/api/reports/activated-routes`); }

  // --- CHAT ---
  getChatInbox(clienteId?: number): Observable<any[]> {
    return this.http.get<any[]>(`${this.base}/api/chat/inbox`, { params: this.params({ cliente_id: clienteId }) });
  }
  searchChatVisits(q: string): Observable<any[]> { return this.http.get<any[]>(`${this.base}/api/chat/search-visits`, { params: this.params({ q }) }); }
  getMessagesByPhoto(fotoId: number): Observable<ChatMensaje[]> { return this.http.get<ChatMensaje[]>(`${this.base}/api/chat/messages/${fotoId}`); }
  getMessagesByVisit(visitId: number): Observable<ChatMensaje[]> { return this.http.get<ChatMensaje[]>(`${this.base}/api/chat/visit/${visitId}/messages`); }
  sendMessage(data: object): Observable<ChatMensaje> { return this.http.post<ChatMensaje>(`${this.base}/api/chat/send`, data); }

  // --- CHAT — CONVERSACIONES (grupos ad-hoc de mercaderistas: region/pdv;
  // el chat de equipo/visita vive en CHAT — GRUPOS más abajo) ---
  getChatRecipients(clienteId?: number): Observable<any> {
    return this.http.get<any>(`${this.base}/api/chat/recipients`, { params: this.params({ cliente_id: clienteId }) });
  }
  listConversations(clienteId?: number): Observable<any[]> {
    return this.http.get<any[]>(`${this.base}/api/chat/conversations`, { params: this.params({ cliente_id: clienteId }) });
  }
  createConversation(body: {
    tipo: 'group_region' | 'group_pdv';
    cliente_id?: number;
    region?: string;
    punto_interes_id?: string;
    titulo?: string;
    primer_mensaje?: string;
  }): Observable<any> {
    return this.http.post<any>(`${this.base}/api/chat/conversations`, body);
  }
  getConversation(convId: number): Observable<any> {
    return this.http.get<any>(`${this.base}/api/chat/conversations/${convId}`);
  }
  getConversationMessages(convId: number): Observable<ChatMensaje[]> {
    return this.http.get<ChatMensaje[]>(`${this.base}/api/chat/conversations/${convId}/messages`);
  }
  sendConversationMessage(convId: number, mensaje: string): Observable<ChatMensaje> {
    return this.http.post<ChatMensaje>(`${this.base}/api/chat/conversations/${convId}/messages`, { mensaje });
  }

  // --- CHAT — GRUPOS (equipo operativo / equipo+cliente + sub-hilo por
  // visita) — mismas tablas que AppWeb v1 y la APK del mercaderista ---
  getMisGrupos(): Observable<any[]> {
    return this.http.get<any[]>(`${this.base}/api/chat/grupos/mis-grupos`);
  }
  getMercMisGrupos(): Observable<any[]> {
    return this.http.get<any[]>(`${this.base}/api/merc/chat/grupos/mis-grupos`);
  }
  getMensajesGrupo(idGrupo: number, beforeId?: number, limit = 50): Observable<any[]> {
    return this.http.get<any[]>(`${this.base}/api/chat/grupos/${idGrupo}/mensajes`,
      { params: this.params({ before_id: beforeId, limit }) });
  }
  enviarMensajeGrupo(idGrupo: number, mensaje: string): Observable<any> {
    return this.http.post<any>(`${this.base}/api/chat/grupos/${idGrupo}/mensajes`, { mensaje });
  }
  getMiembrosGrupo(idGrupo: number): Observable<any[]> {
    return this.http.get<any[]>(`${this.base}/api/chat/grupos/${idGrupo}/miembros`);
  }

  // ── Admin: Grupos de Chat ──────────────────────────────────────────────
  adminListarGruposChat(q: string = '', page: number = 1, limit: number = 10): Observable<any> {
    return this.http.get<any>(`${this.base}/api/admin/chat-grupos`, { params: this.params({ q, page, limit }) });
  }
  adminListarClientesParaGrupos(q: string = ''): Observable<any[]> {
    return this.http.get<any[]>(`${this.base}/api/admin/chat-grupos/clientes`, { params: this.params({ q }) });
  }
  adminAsegurarGruposCliente(idCliente: number): Observable<any> {
    return this.http.post<any>(`${this.base}/api/admin/chat-grupos/asegurar/${idCliente}`, {});
  }
  adminMiembrosGrupo(idGrupo: number): Observable<any[]> {
    return this.http.get<any[]>(`${this.base}/api/admin/chat-grupos/${idGrupo}/miembros`);
  }
  adminBuscarUsuarios(q: string = ''): Observable<any[]> {
    return this.http.get<any[]>(`${this.base}/api/admin/chat-grupos/usuarios`, { params: this.params({ q }) });
  }
  adminAgregarMiembroExtra(idGrupo: number, idUsuario: number): Observable<any> {
    return this.http.post<any>(`${this.base}/api/admin/chat-grupos/${idGrupo}/miembros-extra`, { id_usuario: idUsuario });
  }
  adminQuitarMiembroExtra(idGrupo: number, idUsuario: number): Observable<any> {
    return this.http.delete<any>(`${this.base}/api/admin/chat-grupos/${idGrupo}/miembros-extra/${idUsuario}`);
  }
  marcarLeidoGrupo(idGrupo: number): Observable<any> {
    return this.http.post<any>(`${this.base}/api/chat/grupos/${idGrupo}/marcar-leido`, {});
  }
  getVisitasConChat(idCliente: number, tipoGrupo: 'operativo' | 'operativo_cliente'): Observable<any[]> {
    return this.http.get<any[]>(`${this.base}/api/chat/grupos/visitas-chat/${idCliente}/${tipoGrupo}`);
  }
  getMensajesGrupoVisita(idCliente: number, tipoGrupo: 'operativo' | 'operativo_cliente', idVisita: number): Observable<any[]> {
    return this.http.get<any[]>(`${this.base}/api/chat/grupos/visita-mensajes/${idCliente}/${tipoGrupo}/${idVisita}`);
  }
  enviarMensajeGrupoVisita(idCliente: number, tipoGrupo: 'operativo' | 'operativo_cliente', idVisita: number, mensaje: string): Observable<any> {
    return this.http.post<any>(`${this.base}/api/chat/grupos/visita-mensajes/${idCliente}/${tipoGrupo}/${idVisita}`, { mensaje });
  }
  marcarLeidoGrupoVisita(idCliente: number, tipoGrupo: 'operativo' | 'operativo_cliente', idVisita: number): Observable<any> {
    return this.http.post<any>(`${this.base}/api/chat/grupos/visita-marcar-leido/${idCliente}/${tipoGrupo}/${idVisita}`, {});
  }
  getInfoGrupoCliente(idCliente: number, tipoGrupo: 'operativo' | 'operativo_cliente'): Observable<any> {
    return this.http.get<any>(`${this.base}/api/chat/grupos/info-cliente/${idCliente}/${tipoGrupo}`);
  }
  getOrCreateVisitaThread(visitaId: number, tipoGrupo: 'operativo' | 'operativo_cliente'): Observable<any> {
    return this.http.post<any>(`${this.base}/api/chat/grupos/visita-thread`, { visita_id: visitaId, tipo_grupo: tipoGrupo });
  }

  // --- NOTIFICACIONES ---
  getRejectionNotifications(cedula?: string): Observable<object[]> {
    return this.http.get<object[]>(`${this.base}/api/notifications/rejection`, { params: this.params({ cedula }) });
  }
  markNotifRead(id: number): Observable<object> { return this.http.post<object>(`${this.base}/api/notifications/mark-read/${id}`, {}); }
  markAllNotifsRead(cedula?: string): Observable<object> {
    return this.http.post<object>(`${this.base}/api/notifications/mark-all-read`, {}, { params: this.params({ cedula }) });
  }

  // --- SUPERVISOR ---
  getRejectedPhotos(): Observable<Foto[]> { return this.http.get<Foto[]>(`${this.base}/api/supervisor/rejected-photos`); }
  replacePhoto(formData: FormData): Observable<object> { return this.http.post<object>(`${this.base}/api/supervisor/replace-photo`, formData); }

  // --- MERCADERISTA RUTAS ---
  getMercaderistasConRutas(): Observable<any[]> { return this.http.get<any[]>(`${this.base}/api/mercaderista-rutas`); }
  getMercaderistaRoutes(mercaderistaId: number): Observable<any[]> { return this.http.get<any[]>(`${this.base}/api/mercaderista-rutas/mercaderista/${mercaderistaId}/routes`); }
  syncMercaderistaRoutes(mercaderistaId: number, assignments: { ruta_id: number; tipo_ruta: string }[]): Observable<object> {
    return this.http.post<object>(`${this.base}/api/mercaderista-rutas/mercaderista/${mercaderistaId}/sync-routes`, assignments);
  }
  assignRoute(mercaderistaId: number, rutaId: number): Observable<object> {
    return this.http.post<object>(`${this.base}/api/mercaderista-rutas/assign`, null, { params: this.params({ mercaderista_id: mercaderistaId, ruta_id: rutaId }) });
  }

  // --- ADMIN SESIONES ---
  getActiveSessions(): Observable<object[]> { return this.http.get<object[]>(`${this.base}/api/admin/sessions/active`); }
  killSession(id: number): Observable<object> { return this.http.post<object>(`${this.base}/api/admin/sessions/kill/${id}`, {}); }
  killUserSessions(userId: number): Observable<object> { return this.http.post<object>(`${this.base}/api/admin/sessions/kill-user/${userId}`, {}); }
  invalidateSession(id: number): Observable<object> { return this.http.post<object>(`${this.base}/api/admin/sessions/invalidate`, null, { params: this.params({ session_id: id }) }); }
  cleanupSessions(): Observable<object> { return this.http.post<object>(`${this.base}/api/admin/sessions/cleanup`, {}); }
  getSessionHistory(userId: number): Observable<object[]> { return this.http.get<object[]>(`${this.base}/api/admin/sessions/history/${userId}`); }

  // --- AUDITORÍA ---
  getAuditLogs(opts: { username?: string; action?: string; entity_type?: string; from_date?: string; to_date?: string; limit?: number; offset?: number } = {}): Observable<object> {
    return this.http.get<object>(`${this.base}/api/audit/logs`, { params: this.params(opts) });
  }
  getAuditEntityTypes(): Observable<object> { return this.http.get<object>(`${this.base}/api/audit/entity-types`); }

  // --- PRODUCTOS / PDV / SOLICITUDES ---

  // === PRODUCTOS - Con paginación y búsqueda ===
  getProductos(opts: { skip?: number; limit?: number; busqueda?: string; id_departamento?: number; id_categoria?: number; id_subcategoria?: number; id_marca?: number; id_productora?: number; id_presentacion?: number; id_clasificacion_tamano?: number; inagotable?: boolean; categoria?: string; fabricante?: string; tipo_servicio?: string } = {}): Observable<{ total: number; pagina: number; items: any[] }> {
    return this.http.get<{ total: number; pagina: number; items: any[] }>(`${this.base}/api/productos-catalogos/productos`, { params: this.params(opts) });
  }
  getProductosFiltrosDisponibles(opts: { busqueda?: string; id_departamento?: number; id_categoria?: number; id_subcategoria?: number; id_marca?: number; id_productora?: number; id_presentacion?: number; id_clasificacion_tamano?: number; inagotable?: boolean } = {}): Observable<{ departamentos: any[]; categorias: any[]; subcategorias: any[]; marcas: any[]; productoras: any[]; presentaciones: any[]; tamanos: any[] }> {
    return this.http.get<any>(`${this.base}/api/productos-catalogos/productos/filtros-disponibles`, { params: this.params(opts) });
  }

  getProducto(id: number): Observable<any> {
    return this.http.get<any>(`${this.base}/api/productos-catalogos/productos/${id}`);
  }

  createProducto(data: object): Observable<object> {
    return this.http.post<object>(`${this.base}/api/productos-catalogos/productos`, data);
  }

  updateProducto(id: number, data: object): Observable<object> {
    return this.http.put<object>(`${this.base}/api/productos-catalogos/productos/${id}`, data);
  }

  deleteProducto(id: number): Observable<object> {
    return this.http.delete<object>(`${this.base}/api/productos-catalogos/productos/${id}`);
  }

  // catálogos para dropdowns del formulario de producto
  getCatMarcas(idProductora?: number): Observable<any[]> {
    return this.http.get<any[]>(`${this.base}/api/productos-catalogos/marcas`, { params: idProductora ? { id_productora: idProductora } : {} });
  }
  getCatProductoras(): Observable<any[]> { return this.http.get<any[]>(`${this.base}/api/productos-catalogos/productoras`); }
  getCatPresentaciones(): Observable<any[]> { return this.http.get<any[]>(`${this.base}/api/productos-catalogos/presentaciones`); }
  getCatDepartamentos(): Observable<any[]> { return this.http.get<any[]>(`${this.base}/api/productos-catalogos/departamentos`); }
  getCatTamanos(): Observable<any[]> { return this.http.get<any[]>(`${this.base}/api/productos-catalogos/tamanos`); }
  // ABM de catálogos (crear/borrar) — categorías/subcategorías ya tienen sus métodos arriba
  createCatDepartamento(data: any): Observable<any> { return this.http.post<any>(`${this.base}/api/productos-catalogos/departamentos`, data); }
  updateCatDepartamento(id: number, data: any): Observable<any> { return this.http.put<any>(`${this.base}/api/productos-catalogos/departamentos/${id}`, data); }
  deleteCatDepartamento(id: number): Observable<any> { return this.http.delete<any>(`${this.base}/api/productos-catalogos/departamentos/${id}`); }
  createCatMarca(data: any): Observable<any> { return this.http.post<any>(`${this.base}/api/productos-catalogos/marcas`, data); }
  updateCatMarca(id: number, data: any): Observable<any> { return this.http.put<any>(`${this.base}/api/productos-catalogos/marcas/${id}`, data); }
  deleteCatMarca(id: number): Observable<any> { return this.http.delete<any>(`${this.base}/api/productos-catalogos/marcas/${id}`); }
  createCatPresentacion(data: any): Observable<any> { return this.http.post<any>(`${this.base}/api/productos-catalogos/presentaciones`, data); }
  updateCatPresentacion(id: number, data: any): Observable<any> { return this.http.put<any>(`${this.base}/api/productos-catalogos/presentaciones/${id}`, data); }
  deleteCatPresentacion(id: number): Observable<any> { return this.http.delete<any>(`${this.base}/api/productos-catalogos/presentaciones/${id}`); }
  createCatTamano(data: any): Observable<any> { return this.http.post<any>(`${this.base}/api/productos-catalogos/tamanos`, data); }
  updateCatTamano(id: number, data: any): Observable<any> { return this.http.put<any>(`${this.base}/api/productos-catalogos/tamanos/${id}`, data); }
  deleteCatTamano(id: number): Observable<any> { return this.http.delete<any>(`${this.base}/api/productos-catalogos/tamanos/${id}`); }

  getProductosCategorias(): Observable<string[]> {
    return this.http.get<string[]>(`${this.base}/api/atencion-cliente/productos/listado/categorias`);
  }

  // --- CATALOGOS DE PRODUCTOS (SNOWFLAKE) ---
  getCatalogosCategorias(): Observable<any[]> {
    return this.http.get<any[]>(`${this.base}/api/productos-catalogos/categorias`);
  }
  createCatalogosCategoria(data: any): Observable<any> {
    return this.http.post<any>(`${this.base}/api/productos-catalogos/categorias`, data);
  }
  updateCatalogosCategoria(id: number, data: any): Observable<any> {
    return this.http.put<any>(`${this.base}/api/productos-catalogos/categorias/${id}`, data);
  }
  deleteCatalogosCategoria(id: number): Observable<any> {
    return this.http.delete<any>(`${this.base}/api/productos-catalogos/categorias/${id}`);
  }

  getCatalogosSubCategorias(idCategoria?: number): Observable<any[]> {
    let params = {};
    if (idCategoria) params = { id_categoria: idCategoria };
    return this.http.get<any[]>(`${this.base}/api/productos-catalogos/subcategorias`, { params });
  }
  createCatalogosSubCategoria(data: any): Observable<any> {
    return this.http.post<any>(`${this.base}/api/productos-catalogos/subcategorias`, data);
  }
  updateCatalogosSubCategoria(id: number, data: any): Observable<any> {
    return this.http.put<any>(`${this.base}/api/productos-catalogos/subcategorias/${id}`, data);
  }
  deleteCatalogosSubCategoria(id: number): Observable<any> {
    return this.http.delete<any>(`${this.base}/api/productos-catalogos/subcategorias/${id}`);
  }


  getProductosFabricantes(): Observable<string[]> {
    return this.http.get<string[]>(`${this.base}/api/atencion-cliente/productos/listado/fabricantes`);
  }

  getProductosTiposServicio(): Observable<string[]> {
    return this.http.get<string[]>(`${this.base}/api/atencion-cliente/productos/listado/tipos-servicio`);
  }

  getProductosTiposFabricante(): Observable<string[]> {
    return this.http.get<string[]>(`${this.base}/api/atencion-cliente/productos/listado/tipos-fabricante`);
  }

  getCategorias(): Observable<object[]> { return this.http.get<object[]>(`${this.base}/api/atencion-cliente/categorias`); }
  getPDVList(opts: { activo?: boolean; region?: string } = {}): Observable<PuntoInteres[]> {
    return this.http.get<PuntoInteres[]>(`${this.base}/api/atencion-cliente/pdv`, { params: this.params(opts) });
  }
  createPDV(data: object): Observable<PuntoInteres> { return this.http.post<PuntoInteres>(`${this.base}/api/atencion-cliente/pdv`, data); }
  updatePDV(id: number, data: object): Observable<PuntoInteres> { return this.http.put<PuntoInteres>(`${this.base}/api/atencion-cliente/pdv/${id}`, data); }
  getSolicitudes(estado?: string, tipo?: string): Observable<object[]> {
    return this.http.get<object[]>(`${this.base}/api/atencion-cliente/solicitudes`, { params: this.params({ estado, tipo }) });
  }
  crearSolicitud(data: { tipo: string; descripcion: string }): Observable<object> {
    return this.http.post<object>(`${this.base}/api/atencion-cliente/solicitudes`, data);
  }
  aprobarSolicitud(id: number, completar: object = {}): Observable<object> { return this.http.post<object>(`${this.base}/api/atencion-cliente/solicitudes/${id}/aprobar`, completar); }
  rechazarSolicitud(id: number): Observable<object> { return this.http.post<object>(`${this.base}/api/atencion-cliente/solicitudes/${id}/rechazar`, {}); }

  // --- FRECUENCIAS PDVs CLIENTE ---
  getFrecuenciasPdvsCliente(opts: { id_cliente?: number; id_punto_interes?: string; activo?: boolean } = {}): Observable<any[]> {
    return this.http.get<any[]>(`${this.base}/api/frecuencias-pdvs-cliente`, { params: this.params(opts) });
  }
  createFrecuenciaPdvCliente(data: object): Observable<any> { return this.http.post<any>(`${this.base}/api/frecuencias-pdvs-cliente`, data); }
  updateFrecuenciaPdvCliente(id: number, data: object): Observable<any> { return this.http.put<any>(`${this.base}/api/frecuencias-pdvs-cliente/${id}`, data); }
  deleteFrecuenciaPdvCliente(id: number): Observable<any> { return this.http.delete<any>(`${this.base}/api/frecuencias-pdvs-cliente/${id}`); }
  getPdvsDisponiblesParaFrecuencia(idCliente: number): Observable<any[]> {
    return this.http.get<any[]>(`${this.base}/api/frecuencias-pdvs-cliente/pdvs-disponibles/${idCliente}`);
  }
  bulkUpsertFrecuenciasPdvCliente(data: { id_cliente: number; items: object[] }): Observable<any> {
    return this.http.post<any>(`${this.base}/api/frecuencias-pdvs-cliente/bulk`, data);
  }
  importFrecuenciasExcel(idCliente: number, file: File): Observable<any> {
    const fd = new FormData();
    fd.append('id_cliente', String(idCliente));
    fd.append('file', file, file.name);
    return this.http.post<any>(`${this.base}/api/frecuencias-pdvs-cliente/importar-excel`, fd);
  }

  // --- HORAS PROMEDIO EJECUCIÓN ---
  getHorasPromedioEjecucion(opts: { id_cliente?: number; id_tipo_negocio?: number } = {}): Observable<any[]> {
    return this.http.get<any[]>(`${this.base}/api/horas-promedio-ejecucion`, { params: this.params(opts) });
  }
  createHorasPromedioEjecucion(data: object): Observable<any> { return this.http.post<any>(`${this.base}/api/horas-promedio-ejecucion`, data); }
  updateHorasPromedioEjecucion(id: number, data: object): Observable<any> { return this.http.put<any>(`${this.base}/api/horas-promedio-ejecucion/${id}`, data); }
  deleteHorasPromedioEjecucion(id: number): Observable<any> { return this.http.delete<any>(`${this.base}/api/horas-promedio-ejecucion/${id}`); }

  // --- CLIENTE - MIS FOTOS & VISITAS ---
  // El query param cliente_id es OPCIONAL: solo lo usa el Coordinador Exclusivo
  // para indicar de qué cliente quiere ver los datos. Para clientes normales se ignora.
  getExclusiveClients(): Observable<{ id_cliente: number; cliente: string; id_tipo_cliente: number }[]> {
    return this.http.get<any[]>(`${this.base}/api/client/exclusive-clients`);
  }
  getClientRegions(clienteId?: number): Observable<any[]> {
    return this.http.get<any[]>(`${this.base}/api/client/regions`, { params: this.params({ cliente_id: clienteId }) });
  }
  getClientChains(region: string, clienteId?: number): Observable<any[]> {
    return this.http.get<any[]>(`${this.base}/api/client/chains/${encodeURIComponent(region)}`, { params: this.params({ cliente_id: clienteId }) });
  }
  getClientPoints(region: string, clienteId?: number): Observable<any[]> {
    return this.http.get<any[]>(`${this.base}/api/client/points/${encodeURIComponent(region)}`, { params: this.params({ cliente_id: clienteId }) });
  }
  getClientPointVisits(pointId: string, clienteId?: number): Observable<any[]> {
    return this.http.get<any[]>(`${this.base}/api/client/point/${encodeURIComponent(pointId)}/visits`, { params: this.params({ cliente_id: clienteId }) });
  }
  getClientMisVisitas(opts: { fecha_inicio?: string; fecha_fin?: string; region?: string; cadena?: string; punto_id?: string; cliente_id?: number } = {}): Observable<any> {
    return this.http.get<any>(`${this.base}/api/client/mis-visitas`, { params: this.params(opts) });
  }
  getClientDashboard(clienteId?: number, idDashboard?: number): Observable<any> {
    return this.http.get<any>(`${this.base}/api/client/dashboard`, { params: this.params({ cliente_id: clienteId, id_dashboard: idDashboard }) });
  }
  getClientSummary(opts: { clienteId?: number; fecha_inicio?: string; fecha_fin?: string } = {}): Observable<any> {
    return this.http.get<any>(`${this.base}/api/client/summary`, { params: this.params({ cliente_id: opts.clienteId, fecha_inicio: opts.fecha_inicio, fecha_fin: opts.fecha_fin }) });
  }

  // --- CARGAS DE POWER BI ---
  getPowerBiSummary(): Observable<any[]> {
    return this.http.get<any[]>(`${this.base}/api/cargas-powerbi/summary`);
  }
  getPowerBisByClient(clientId: number): Observable<any[]> {
    return this.http.get<any[]>(`${this.base}/api/cargas-powerbi/client/${clientId}`);
  }
  createPowerBi(payload: { id_cliente: number; nombre?: string; url_html: string; tipo?: string }): Observable<any> {
    return this.http.post<any>(`${this.base}/api/cargas-powerbi`, payload);
  }
  updatePowerBi(id: number, payload: { nombre?: string; url_html?: string; activo?: boolean }): Observable<any> {
    return this.http.put<any>(`${this.base}/api/cargas-powerbi/${id}`, payload);
  }
  deletePowerBi(id: number): Observable<any> {
    return this.http.delete<any>(`${this.base}/api/cargas-powerbi/${id}`);
  }

  // --- PORTAL MERCADERISTA ---
  getMercMiPerfil(): Observable<any> { return this.http.get<any>(`${this.base}/api/merc/me`); }
  getMercMiRuta(): Observable<any> { return this.http.get<any>(`${this.base}/api/merc/rutas`); }
  activarRuta(idRuta: number): Observable<{ success: boolean; id_activacion?: number; ya_activado?: boolean }> {
    return this.http.post<{ success: boolean; id_activacion?: number; ya_activado?: boolean }>(`${this.base}/api/merc/ruta/activar`, { id_ruta: idRuta });
  }
  finalizarRuta(idRuta: number): Observable<{ success: boolean; mensaje?: string }> {
    return this.http.post<{ success: boolean; mensaje?: string }>(`${this.base}/api/merc/ruta/finalizar`, { id_ruta: idRuta });
  }
  desactivarPdv(idPunto: string): Observable<{ success: boolean; mensaje?: string }> {
    return this.http.post<{ success: boolean; mensaje?: string }>(`${this.base}/api/merc/pdv/desactivar`, { id_punto: idPunto });
  }
  getMercMisVisitas(opts: { fecha_inicio?: string; fecha_fin?: string } = {}): Observable<any[]> {
    return this.http.get<any[]>(`${this.base}/api/merc/visitas`, { params: this.params(opts) });
  }
  getMercRutaPdvs(idRuta: number): Observable<any> {
    return this.http.get<any>(`${this.base}/api/merc/ruta/${idRuta}/pdvs`);
  }
  iniciarVisita(data: { id_punto: string; id_cliente: number }): Observable<any> {
    return this.http.post<any>(`${this.base}/api/merc/visitas/iniciar`, data);
  }
  getFotosVisita(visitaId: number): Observable<any> {
    return this.http.get<any>(`${this.base}/api/merc/visitas/${visitaId}/fotos`);
  }
  getMercProductosCliente(idCliente: number): Observable<{ categorias: any[]; total_productos: number }> {
    return this.http.get<{ categorias: any[]; total_productos: number }>(`${this.base}/api/merc/productos`, { params: { id_cliente: idCliente } });
  }
  guardarMercBalances(payload: { visita_id: number; id_cliente: number; productos: any[] }): Observable<any> {
    return this.http.post<any>(`${this.base}/api/merc/visitas/${payload.visita_id}/balances`, payload);
  }
  uploadMercFoto(visitaId: number, tipoFoto: string, file: File | Blob, lat?: number, lon?: number): Observable<any> {
    const fd = new FormData();
    fd.append('tipo_foto', tipoFoto);
    fd.append('file', file, (file as File).name || 'foto.jpg');
    if (lat != null) fd.append('lat', String(lat));
    if (lon != null) fd.append('lon', String(lon));
    return this.http.post<any>(`${this.base}/api/merc/visitas/${visitaId}/fotos`, fd);
  }
  finalizarMercVisita(idVisita: number): Observable<any> {
    return this.http.post<any>(`${this.base}/api/merc/visitas/${idVisita}/finalizar`, { id_visita: idVisita });
  }
  registrarAuditoriaTiempo(payload: { id_visita?: number; identificador_punto_interes?: string; evento: string; detalle?: string; tiempo_restante_segundos: number }): Observable<any> {
    return this.http.post<any>(`${this.base}/api/merc/visitas/auditoria-tiempo`, payload);
  }

  // --- SKU vs SKU ---
  getSkuCompetenciaMapeos(idCliente: number): Observable<any[]> {
    return this.http.get<any[]>(`${this.base}/api/sku-competencia/mapeos`, { params: this.params({ id_cliente: idCliente }) });
  }
  createSkuCompetencia(idCliente: number, idProductoCliente: number, idProductoCompetencia: number): Observable<any> {
    return this.http.post<any>(`${this.base}/api/sku-competencia/mapeos`, { id_cliente: idCliente, id_producto_cliente: idProductoCliente, id_producto_competencia: idProductoCompetencia });
  }
  bulkCreateSkuCompetencia(idCliente: number, idProductoCliente: number, competenciaIds: number[]): Observable<any> {
    return this.http.post<any>(`${this.base}/api/sku-competencia/mapeos/masivo`, { id_cliente: idCliente, id_producto_cliente: idProductoCliente, competencia_ids: competenciaIds });
  }
  deleteSkuCompetencia(id: number): Observable<any> {
    return this.http.delete<any>(`${this.base}/api/sku-competencia/mapeos/${id}`);
  }
  getDerivaPrecio(idCliente: number, umbralPct?: number): Observable<any[]> {
    return this.http.get<any[]>(`${this.base}/api/sku-competencia/deriva-precio`, { params: this.params({ id_cliente: idCliente, umbral_pct: umbralPct }) });
  }

  // --- PLAN DE ACCIÓN ---
  getPlanAccionPendientes(opts: { id_ruta?: number; id_cliente?: number; tipo_pendiente?: string; prioridad_ruta?: string; score_min?: number } = {}): Observable<any> {
    return this.http.get<any>(`${this.base}/api/plan-accion/pendientes`, { params: this.params(opts) });
  }
  recalcularPlanAccion(): Observable<any> {
    return this.http.post<any>(`${this.base}/api/plan-accion/recalcular`, {});
  }
  getPlanAccionClusters(opts: { score_min?: number; radio_km?: number } = {}): Observable<any> {
    return this.http.get<any>(`${this.base}/api/plan-accion/clusters`, { params: this.params(opts) });
  }
  confirmarRutaBck(items: any[], idMercaderista: number): Observable<any> {
    return this.http.post<any>(`${this.base}/api/plan-accion/clusters/confirmar`, { items, id_mercaderista: idMercaderista });
  }
  entrenarModeloPlanAccion(sincrono = false): Observable<any> {
    return this.http.post<any>(`${this.base}/api/plan-accion/modelo/entrenar`, {}, { params: this.params({ sincrono }) });
  }
  getModeloInfoPlanAccion(): Observable<any> {
    return this.http.get<any>(`${this.base}/api/plan-accion/modelo/info`);
  }

  // --- QUIEBRE DINÁMICO (N2) ---
  getQuiebreAlertas(opts: { riesgo?: string; urgente?: boolean; id_cliente?: number; identificador_pdv?: string } = {}): Observable<any> {
    return this.http.get<any>(`${this.base}/api/quiebre/alertas`, { params: this.params(opts) });
  }
  getQuiebreLineaBaseInfo(): Observable<any> {
    return this.http.get<any>(`${this.base}/api/quiebre/linea-base/info`);
  }
  recalcularQuiebreLineaBase(sincrono = false): Observable<any> {
    return this.http.post<any>(`${this.base}/api/quiebre/linea-base/recalcular`, {}, { params: this.params({ sincrono }) });
  }
  recalcularQuiebreAlertas(sincrono = false): Observable<any> {
    return this.http.post<any>(`${this.base}/api/quiebre/alertas/recalcular`, {}, { params: this.params({ sincrono }) });
  }
  getPronosticoQuiebre(opts: { id_cliente?: number; horizonte_semanas?: number } = {}): Observable<any> {
    return this.http.get<any>(`${this.base}/api/quiebre/pronostico`, { params: this.params(opts) });
  }

  // --- QUIEBRE POR CADENA (agregado, sin atribución de marca) ---
  getQuiebrePorCadena(diasVentana = 30): Observable<any> {
    return this.http.get<any>(`${this.base}/api/quiebre-cadena`, { params: this.params({ dias_ventana: diasVentana }) });
  }

  // --- CLIENT CATEGORIES ---
  getClientCategories(clientId: number): Observable<any[]> {
    return this.http.get<any[]>(`${this.base}/api/clients/${clientId}/categorias`);
  }

  addClientCategory(clientId: number, categoryId: number): Observable<any> {
    return this.http.post<any>(`${this.base}/api/clients/${clientId}/categorias`, { id_categoria: categoryId });
  }

  removeClientCategory(clientId: number, categoryId: number): Observable<any> {
    return this.http.delete<any>(`${this.base}/api/clients/${clientId}/categorias/${categoryId}`);
  }
  getClientsByCategory(categoryId: number): Observable<number[]> {
    return this.http.get<number[]>(`${this.base}/api/clients/categorias/${categoryId}/clientes`);
  }
  bulkAssignCategory(categoryId: number, clienteIds: number[]): Observable<any> {
    return this.http.post<any>(`${this.base}/api/clients/categorias/${categoryId}/asignar-masivo`, { cliente_ids: clienteIds });
  }

  // --- CATALOGOS ---
  getEstados(): Observable<any[]> {
    return this.http.get<any[]>(`${this.base}/api/catalogos/estados`);
  }

  // --- GENERIC HTTP METHODS ---
  get<T>(url: string, opts?: { params?: HttpParams | Record<string, string | number | boolean | undefined | null> }): Observable<T> {
    const httpParams = opts?.params instanceof HttpParams ? opts.params : (opts?.params ? this.params(opts.params) : undefined);
    return this.http.get<T>(`${this.base}${url}`, { params: httpParams });
  }

  post<T>(url: string, body: any, opts?: { params?: HttpParams | Record<string, string | number | boolean | undefined | null> }): Observable<T> {
    const httpParams = opts?.params instanceof HttpParams ? opts.params : (opts?.params ? this.params(opts.params) : undefined);
    return this.http.post<T>(`${this.base}${url}`, body, { params: httpParams });
  }

  put<T>(url: string, body: any, opts?: { params?: HttpParams | Record<string, string | number | boolean | undefined | null> }): Observable<T> {
    const httpParams = opts?.params instanceof HttpParams ? opts.params : (opts?.params ? this.params(opts.params) : undefined);
    return this.http.put<T>(`${this.base}${url}`, body, { params: httpParams });
  }

  delete<T>(url: string, opts?: { params?: HttpParams | Record<string, string | number | boolean | undefined | null> }): Observable<T> {
    const httpParams = opts?.params instanceof HttpParams ? opts.params : (opts?.params ? this.params(opts.params) : undefined);
    return this.http.delete<T>(`${this.base}${url}`, { params: httpParams });
  }
}
