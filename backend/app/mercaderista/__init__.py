"""
Portal Mercaderista - Módulo modular con ORM SQLAlchemy.

Estructura:
  schemas.py       → Pydantic models (request/response)
  services/        → Lógica de negocio con SQLAlchemy ORM
  endpoints/       → Routers FastAPI (thin, solo llaman services)
  router.py        → Router principal que agrega todos los sub-routers

Endpoints:
  /api/merc/me                    → Perfil del mercaderista
  /api/merc/rutas                 → Rutas del día con PDVs y clientes
  /api/merc/pdv-activos           → PDVs activos con trabajo pendiente
  /api/merc/visitas/iniciar       → Iniciar visita
  /api/merc/visitas               → Historial de visitas
  /api/merc/visitas/{id}/fotos    → GET fotos | POST upload
  /api/merc/visitas/{id}/balances → Guardar balances
  /api/merc/visitas/{id}/finalizar→ Finalizar visita
  /api/merc/visitas/{id}/productos→ Productos para balance
  /api/merc/pdv/activar           → Activar PDV
  /api/merc/pdv/desactivar        → Desactivar PDV
  /api/merc/pdv/{id}/validar-cierre → Validar que todos los clientes estén visitados
  /api/merc/chat/inbox            → Bandeja de chat
  /api/merc/chat/visitas/{id}     → Mensajes de chat por visita
  /api/merc/chat/enviar           → Enviar mensaje
"""
