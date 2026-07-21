import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { Ruta, RutaProgramacion, CambioFuturo } from '../models/ruta.model';
import { Visita, VisitaPaginatedResponse, Foto, Mercaderista, PuntoInteres, ChatMensaje, Balance } from '../models/visita.model';
import { User } from '../models/user.model';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private base = environment.apiUrl;

  constructor(private http: HttpClient) { }

  private params(obj: Record<string, string | number | boolean | undefined | null>): HttpParams {
    let p = new HttpParams();
    for (const [k, v] of Object.entries(obj)) {
      if (v !== undefined && v !== null) p = p.set(k, String(v));
    }
    return p;
  }

  // --- USUARIOS ---
  getUsers(): Observable<User[]> { return this.http.get<User[]>(`${this.base}/api/users/`); }
  createUser(data: object): Observable<User> { return this.http.post<User>(`${this.base}/api/users/`, data); }
  updateUser(id: number, data: object): Observable<User> { return this.http.patch<User>(`${this.base}/api/users/${id}`, data); }
  deleteUser(id: number): Observable<object> { return this.http.delete<object>(`${this.base}/api/users/${id}`); }
  getAnalysts(): Observable<User[]> { return this.http.get<User[]>(`${this.base}/api/users/analysts`); }
  getSupervisors(): Observable<User[]> { return this.http.get<User[]>(`${this.base}/api/users/supervisors`); }
  getModulos(): Observable<any[]> { return this.http.get<any[]>(`${this.base}/api/modulos`); }
  getUserPermissions(userId: number): Observable<any[]> { return this.http.get<any[]>(`${this.base}/api/users/${userId}/permissions`); }
  updateUserPermissions(userId: number, permissions: any[]): Observable<any> { return this.http.post<any>(`${this.base}/api/users/${userId}/permissions`, { permissions }); }

  // --- MERCADERISTAS ---
  getMercaderistas(): Observable<Mercaderista[]> { return this.http.get<Mercaderista[]>(`${this.base}/api/merchandisers/`); }
  getMercaderista(id: number): Observable<Mercaderista> { return this.http.get<Mercaderista>(`${this.base}/api/merchandisers/${id}`); }
  createMercaderista(data: object): Observable<Mercaderista> { return this.http.post<Mercaderista>(`${this.base}/api/merchandisers/`, data); }
  updateMercaderista(id: number, data: object): Observable<Mercaderista> { return this.http.patch<Mercaderista>(`${this.base}/api/merchandisers/${id}`, data); }
  deleteMercaderista(id: number): Observable<object> { return this.http.delete<object>(`${this.base}/api/merchandisers/${id}`); }
  uploadPhoto(formData: FormData): Observable<object> { return this.http.post<object>(`${this.base}/api/merchandisers/upload-photo`, formData); }
  getActivePoints(cedula: string): Observable<object[]> { return this.http.get<object[]>(`${this.base}/api/merchandisers/${cedula}/active-points`); }
  getFotoMetadatos(fotoId: number): Observable<object> { return this.http.get<object>(`${this.base}/api/merchandisers/foto/${fotoId}/metadatos`); }

  // --- PUNTOS DE INTERÉS ---
  getPoints(opts: { region?: string; ciudad?: string; jerarquia_n2?: string; cadena?: string; search?: string; skip?: number; limit?: number } = {}): Observable<{ items: PuntoInteres[]; total: number }> {
    return this.http.get<{ items: PuntoInteres[]; total: number }>(`${this.base}/api/points/`, { params: this.params({ ...opts, include_total: true }) });
  }
  createPoint(data: object): Observable<PuntoInteres> { return this.http.post<PuntoInteres>(`${this.base}/api/points/`, data); }
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
  getPointsCount(opts: { region?: string; ciudad?: string; jerarquia_n2?: string; cadena?: string; search?: string } = {}): Observable<{ total: number }> {
    return this.http.get<{ total: number }>(`${this.base}/api/points/count`, { params: this.params(opts) });
  }
  getPointPhotos(pointId: number, estado?: string): Observable<object[]> {
    return this.http.get<object[]>(`${this.base}/api/points/${pointId}/photos`, { params: this.params({ estado }) });
  }

  // --- CATÁLOGOS PDV ---
  // catalog ∈ 'tipo-negocio' | 'subtipo-negocio' | 'alcance' | 'canal-venta' | 'departamentos'
  listCatalog(catalog: string, activo?: boolean): Observable<{ id: number; nombre: string; activo: boolean }[]> {
    return this.http.get<{ id: number; nombre: string; activo: boolean }[]>(
      `${this.base}/api/catalogos/${catalog}/`,
      { params: this.params({ activo }) }
    );
  }
  createCatalogItem(catalog: string, data: { nombre: string; activo?: boolean }): Observable<{ id: number; nombre: string; activo: boolean }> {
    return this.http.post<{ id: number; nombre: string; activo: boolean }>(`${this.base}/api/catalogos/${catalog}/`, data);
  }
  updateCatalogItem(catalog: string, id: number, data: { nombre?: string; activo?: boolean }): Observable<{ id: number; nombre: string; activo: boolean }> {
    return this.http.put<{ id: number; nombre: string; activo: boolean }>(`${this.base}/api/catalogos/${catalog}/${id}`, data);
  }
  deleteCatalogItem(catalog: string, id: number, force = false): Observable<object> {
    return this.http.delete<object>(`${this.base}/api/catalogos/${catalog}/${id}`, { params: this.params({ force }) });
  }

  // Ciudades — endpoints específicos
  listCiudades(opts: { departamento_id?: number; departamento?: string; activo?: boolean } = {}): Observable<{ id: number; nombre: string; activo: boolean; departamento_id: number; departamento_nombre: string | null }[]> {
    return this.http.get<any[]>(`${this.base}/api/catalogos/ciudades/`, { params: this.params(opts) });
  }
  createCiudad(data: { nombre: string; departamento_id: number; activo?: boolean }): Observable<any> {
    return this.http.post<any>(`${this.base}/api/catalogos/ciudades/`, data);
  }
  updateCiudad(id: number, data: { nombre?: string; departamento_id?: number; activo?: boolean }): Observable<any> {
    return this.http.put<any>(`${this.base}/api/catalogos/ciudades/${id}`, data);
  }
  deleteCiudad(id: number, force = false): Observable<object> {
    return this.http.delete<object>(`${this.base}/api/catalogos/ciudades/${id}`, { params: this.params({ force }) });
  }

  // --- RUTAS ---
  getRoutes(activa?: boolean): Observable<Ruta[]> {
    return this.http.get<Ruta[]>(`${this.base}/api/routes/`, { params: this.params({ activa }) });
  }
  createRoute(data: object): Observable<Ruta> { return this.http.post<Ruta>(`${this.base}/api/routes/`, data); }
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
  getNextRouteNumber(tipo: string): Observable<{ next_number: number }> { return this.http.get<{ next_number: number }>(`${this.base}/api/routes/next-number`, { params: { tipo } }); }

  // --- CLIENTES ---
  getClients(): Observable<any[]> { return this.http.get<any[]>(`${this.base}/api/clients/`); }
  createClient(data: object): Observable<any> { return this.http.post<any>(`${this.base}/api/clients/`, data); }
  updateClient(id: number, data: object): Observable<any> { return this.http.put<any>(`${this.base}/api/clients/${id}`, data); }
  deleteClient(id: number): Observable<object> { return this.http.delete<object>(`${this.base}/api/clients/${id}`); }

  // --- ANALISTAS ---
  getAnalystsList(): Observable<any[]> { return this.http.get<any[]>(`${this.base}/api/analysts/`); }
  createAnalyst(data: object): Observable<any> { return this.http.post<any>(`${this.base}/api/analysts/`, data); }
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
  createSupervisor(data: { nombre: string }): Observable<any> { return this.http.post<any>(`${this.base}/api/supervisores/`, data); }
  updateSupervisor(id: number, data: { nombre: string }): Observable<any> { return this.http.put<any>(`${this.base}/api/supervisores/${id}`, data); }
  deleteSupervisor(id: number): Observable<void> { return this.http.delete<void>(`${this.base}/api/supervisores/${id}`); }
  getSupervisorsWithAssignments(): Observable<any[]> { return this.http.get<any[]>(`${this.base}/api/supervisores/with-assignments`); }
  getSupervisorRoutes(id: number): Observable<any[]> { return this.http.get<any[]>(`${this.base}/api/supervisores/${id}/routes`); }
  syncSupervisorRoutes(id: number, ids: number[]): Observable<object> { return this.http.post<object>(`${this.base}/api/supervisores/${id}/sync-routes`, { ids }); }
  getSupervisorClients(id: number): Observable<any[]> { return this.http.get<any[]>(`${this.base}/api/supervisores/${id}/clients`); }
  getSupervisorRouteClients(id: number): Observable<any[]> { return this.http.get<any[]>(`${this.base}/api/supervisores/${id}/route-clients`); }
  syncSupervisorClients(id: number, ids: number[]): Observable<object> { return this.http.post<object>(`${this.base}/api/supervisores/${id}/sync-clients`, { ids }); }

  // --- VISITAS ---
  getVisits(opts: { estado?: string; ruta_id?: number; fecha?: string; page?: number; per_page?: number } = {}): Observable<VisitaPaginatedResponse> {
    return this.http.get<VisitaPaginatedResponse>(`${this.base}/api/visits/`, { params: this.params(opts) });
  }
  createVisit(data: object): Observable<Visita> { return this.http.post<Visita>(`${this.base}/api/visits/`, data); }
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
  markVisitReviewed(visitId: number, revisada = true): Observable<any> { return this.http.post<any>(`${this.base}/api/visits/${visitId}/mark-reviewed`, null, { params: this.params({ revisada }) }); }
  getRejectReasons(): Observable<any[]> { return this.http.get<any[]>(`${this.base}/api/visits/reject-reasons`); }
  getCentroMandoClientes(): Observable<any> { return this.http.get<any>(`${this.base}/api/centro-mando/clientes`); }
  getCentroMandoResumenDia(opts: any = {}): Observable<any> { return this.http.get<any>(`${this.base}/api/centro-mando/resumen-dia`, { params: this.params(opts) }); }
  getCentroMandoActivaciones(opts: any = {}): Observable<any> { return this.http.get<any>(`${this.base}/api/centro-mando/activaciones`, { params: this.params(opts) }); }
  getMercRutaPdvs(idRuta: number): Observable<any> { return this.http.get<any>(`${this.base}/api/merc/ruta/${idRuta}/pdvs`); }
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

  getClientDataBalances(filters: any): Observable<any[]> {
    return this.http.get<any[]>(`${this.base}/api/client-data/balances`, { params: this.params(filters) });
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

  // --- CHAT — CONVERSACIONES (chats no atados a visita) ---
  getChatRecipients(clienteId?: number): Observable<any> {
    return this.http.get<any>(`${this.base}/api/chat/recipients`, { params: this.params({ cliente_id: clienteId }) });
  }
  listConversations(clienteId?: number): Observable<any[]> {
    return this.http.get<any[]>(`${this.base}/api/chat/conversations`, { params: this.params({ cliente_id: clienteId }) });
  }
  createConversation(body: {
    tipo: 'direct' | 'group_team' | 'group_region' | 'group_pdv';
    cliente_id?: number;
    destinatario_id?: number;
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

  // --- NOTIFICACIONES ---
  getRejectionNotifications(cedula?: string): Observable<object[]> {
    return this.http.get<object[]>(`${this.base}/api/notifications/rejection`, { params: this.params({ cedula }) });
  }
  markNotifRead(id: number): Observable<object> { return this.http.post<object>(`${this.base}/api/notifications/mark-read/${id}`, {}); }
  markAllNotifsRead(cedula?: string): Observable<object> {
    return this.http.post<object>(`${this.base}/api/notifications/mark-all-read`, {}, { params: this.params({ cedula }) });
  }

  // --- SUPERVISOR ---
  getRejectedPhotoFilters(): Observable<{ mercaderistas: { value: string; label: string }[]; rechazados_por: { value: string; label: string }[] }> {
    return this.http.get<any>(`${this.base}/api/supervisor/rejected-photos/filters`);
  }
  getRejectedPhotos(
    page: number = 1,
    perPage: number = 20,
    filters?: {
      fecha_desde?: string;
      fecha_hasta?: string;
      mercaderista?: string;
      rechazado_por?: string;
      cedula?: string;
    }
  ): Observable<{
    items: Foto[];
    total: number;
    page: number;
    per_page: number;
    total_pages: number;
  }> {
    const params = {
      page,
      per_page: perPage,
      ...(filters || {}),
    };
    return this.http.get<{
      items: Foto[];
      total: number;
      page: number;
      per_page: number;
      total_pages: number;
    }>(`${this.base}/api/supervisor/rejected-photos`, {
      params: this.params(params),
    });
  }
  replacePhoto(formData: FormData): Observable<object> { return this.http.post<object>(`${this.base}/api/supervisor/replace-photo`, formData); }

  // --- MERCADERISTA RUTAS ---
  getMercaderistasConRutas(): Observable<any[]> { return this.http.get<any[]>(`${this.base}/api/mercaderista-rutas/`); }
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
  getProductos(opts: { skip?: number; limit?: number; busqueda?: string; id_categoria?: number; id_subcategoria?: number; id_marca?: number; categoria?: string; fabricante?: string; tipo_servicio?: string } = {}): Observable<{ total: number; pagina: number; items: any[] }> {
    return this.http.get<{ total: number; pagina: number; items: any[] }>(`${this.base}/api/productos-catalogos/productos`, { params: this.params(opts) });
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
  getClientMisVisitas(opts: { fecha_inicio?: string; fecha_fin?: string; region?: string; cadena?: string; punto_id?: string; cliente_id?: number; page?: number; per_page?: number } = {}): Observable<any> {
    return this.http.get<any>(`${this.base}/api/client/mis-visitas`, { params: this.params(opts) });
  }
  getClientDashboard(clienteId?: number): Observable<{ has_dashboard: boolean; url_html: string | null; tipo?: string }> {
    return this.http.get<any>(`${this.base}/api/client/dashboard`, { params: this.params({ cliente_id: clienteId }) });
  }
  getClientSummary(clienteId?: number): Observable<any> {
    return this.http.get<any>(`${this.base}/api/client/summary`, { params: this.params({ cliente_id: clienteId }) });
  }

  // --- PORTAL MERCADERISTA ---
  getMercMiPerfil(): Observable<any> { return this.http.get<any>(`${this.base}/api/merc/mi-perfil`); }
  getMercMiRuta(page: number = 1, perPage: number = 20, tipo?: string): Observable<any> {
    return this.http.get<any>(`${this.base}/api/merc/mi-ruta`, {
      params: this.params({ page, per_page: perPage, tipo })
    });
  }
  getMercMisVisitas(opts: { fecha_inicio?: string; fecha_fin?: string } = {}): Observable<any[]> {
    return this.http.get<any[]>(`${this.base}/api/merc/mis-visitas`, { params: this.params(opts) });
  }
  iniciarVisita(data: { id_punto: string; id_cliente: number }): Observable<any> {
    return this.http.post<any>(`${this.base}/api/merc/iniciar-visita`, data);
  }
  getFotosVisita(visitaId: number): Observable<any> {
    return this.http.get<any>(`${this.base}/api/merc/visita/${visitaId}/fotos`);
  }
  getMercProductosCliente(idCliente: number): Observable<any[]> {
    return this.http.get<any[]>(`${this.base}/api/merc/productos`, { params: { id_cliente: idCliente } });
  }
  guardarMercBalances(payload: { visita_id: number; id_cliente: number; productos: any[] }): Observable<any> {
    return this.http.post<any>(`${this.base}/api/merc/balances`, payload);
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

  // --- CATALOGOS ---
  getEstados(): Observable<any[]> {
    return this.http.get<any[]>(`${this.base}/api/catalogos/estados`);
  }
}
