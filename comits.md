# Commits in origin/main since July 23, 2026

List of commits on the `origin/main` branch starting from **Thursday, July 23, 2026 at 10:10:37 AM -0400** to the present day, using first-parent history (to show direct mainline integrations).

* **5a8fdc9** - 2026-08-13 - abreuyoel - fix: resolver errores de compilacion de angular por merge
* **f354ea2** - 2026-08-13 - abreuyoel - Merge remote-tracking branch 'origin/changesmain'
* **3056caf** - 2026-08-12 - abreuyoel - fix: use epran-qa Azure container in QA configmap
* **a0412e7** - 2026-08-12 - abreuyoel - feat: add QA k8s manifests and GitHub Actions CI/CD workflows to main
* **daf35ec** - 2026-08-11 - abreuyoel - fix(ventas-dashboard): gráfico crecía infinito al hacer hover
* **fbe9acc** - 2026-08-11 - abreuyoel - feat(ventas): pantalla de gestión de Pedidos -- listar/detalle/workflow/firma
* **c3abb60** - 2026-08-11 - abreuyoel - docs(sql): guarda el DDL del módulo de Ventas 2.0 para referencia
* **98f6cc1** - 2026-08-11 - abreuyoel - feat(ventas): módulo de Ventas 2.0 -- catálogo real, pedidos con líneas, OCR/IA, dashboard, crédito
* **8a27b89** - 2026-08-11 - abreuyoel - fix: assert GeoJSON types as const to fix compilation error
* **6f1bd72** - 2026-08-11 - abreuyoel - feat: add MapLibre clustering and coordinates on survey BI map
* **10e9e9b** - 2026-08-11 - abreuyoel - feat: add Ejecutivo role, table, users jsalazar and ymorillo, and permissions
* **54a0d7d** - 2026-08-10 - abreuyoel - fix(redis_pubsub): fuga de conexiones por wait_for externo sin pool acotado
* **02243da** - 2026-08-09 - abreuyoel - feat(encuestador): columnas de ubicacion de cierre en JORNADAS_ENCUESTADOR
* **c6953dc** - 2026-08-09 - abreuyoel - Implement offline queue backups and server idempotency for retry reliability
* **d871f3a** - 2026-08-09 - abreuyoel - Fix encuestador offline sync, UI validations, and duplicate doctors
* **3af8675** - 2026-08-08 - abreuyoel - fix(revision-visitas): filas de Auto-cierre se veian como fotos rotas
* **1534302** - 2026-08-08 - abreuyoel - fix(chat): modal "Chat de la visita" ilegible segun el tema
* **7ddf527** - 2026-08-08 - abreuyoel - fix(revision-visitas): visitas inalcanzables y tarjetas duplicadas indistinguibles
* **26db894** - 2026-08-08 - abreuyoel - fix(centro-mando): "Completas" inalcanzable en PDVs multi-cliente
* **36a3a43** - 2026-08-08 - abreuyoel - fix(revision-visitas): pares Antes/Despues rotos al filtrar por estado
* **0b61dfb** - 2026-08-07 - abreuyoel - feat(encuestador): editar medico despues de registrarlo
* **a5589e5** - 2026-08-07 - abreuyoel - fix(encuestador): condicion de carrera causando medicos/encuestas duplicados
* **d035658** - 2026-08-07 - Deltalove2330 - fix: eliminar medicos duplicados en BI encuestador (ROW_NUMBER dedup) recordar eelimnar duplicados despues
* **f3f8530** - 2026-08-07 - abreuyoel - feat(cliente-encuestador): acceso a BI por permiso individual, no solo por rol
* **10eedf5** - 2026-08-07 - abreuyoel - feat(chat): nombres reales, admins/miembros extra en el grupo, CRUD de admin
* **fbb335d** - 2026-08-07 - abreuyoel - feat(chat): grupo unico "Equipo Encuestadores" para roles 12/13
* **ba6b288** - 2026-08-07 - abreuyoel - feat(encuestador): modelo Encuestador + nombre real en listado de usuarios
* **8cd2723** - 2026-08-06 - abreuyoel - feat(IQVIA): habilitar acceso real al modulo Encuestador para id_rol=13
* **ba5e71f** - 2026-08-06 - abreuyoel - feat(IQVIA/cliente-encuestador): export a Excel, especialidades en barras, chat sin pestana Cliente
* **3f85da4** - 2026-08-06 - abreuyoel - feat(encuestador): proteger la cola offline en dispositivos de gama baja
* **f441db4** - 2026-08-06 - abreuyoel - feat(encuestador): modo offline real -- deja de perder data con senal debil
* **ec7d526** - 2026-08-06 - abreuyoel - feat(BI Encuestas): cross-filter estilo Power BI + grafico de horas de consulta
* **655abcf** - 2026-08-06 - abreuyoel - fix(encuestador): BI Encuestas quedaba en blanco tras el refactor de consultorios dinamicos
* **069d5e5** - 2026-08-06 - abreuyoel - fix(encuestador): pre-llenar nombre de clinica del Consultorio 1 con el centro activo
* **8d300ea** - 2026-08-06 - abreuyoel - fix(encuestador): corregir orden de inicializacion de propiedades en formulario medico
* **ff878df** - 2026-08-06 - abreuyoel - feat(encuestador): consultorios dinamicos, mapa maplibre y mejoras de rendimiento
* **3d4f733** - 2026-08-06 - abreuyoel - Mejora de rendimiento en Centro de Mando: se reemplaza auto-refresh excesivo por WS con indicador visual (pulse), badge de eventos, sonido de notificación y auto-refresh a los 60s.
* **ddca46a** - 2026-08-05 - abreuyoel - Fix: Centro de Mando se quedaba refrescando activaciones/visitas en loop
* **78a61a1** - 2026-08-05 - abreuyoel - Rechazar foto reabre la visita para el mercaderista (estado 'Rechazada')
* **8b46d6b** - 2026-08-05 - abreuyoel - Fix: Todas las Visitas se refrescaba en cascada + default a hoy en vez de 7 dias
* **d16a74b** - 2026-08-04 - abreuyoel - Segundo intento: --workers 2 con limits.cpu subido a 4 (2 por worker)
* **dfe797c** - 2026-08-04 - abreuyoel - Revierte --workers a 1: empeoro bajo carga real, falta subir CPU limit primero
* **69768ad** - 2026-08-04 - abreuyoel - Fase C: sube --workers a 2 (ultimo eje) y baja el pool de conexiones por proceso
* **9f921af** - 2026-08-04 - abreuyoel - Fix real del 500 al eliminar ruta: RutaActivada.id mapeaba a columna inexistente
* **a728316** - 2026-08-04 - abreuyoel - Rutas: conecta crear/editar/eliminar/duplicar al canal de eventos en vivo
* **585a9e2** - 2026-08-04 - abreuyoel - Incidente hora pico: sube DB_POOL_SIZE/DB_MAX_OVERFLOW (5/10 -> 20/30)
* **f493dea** - 2026-08-04 - abreuyoel - Fix: crear/editar ruta rompia con 500 (id_analista no es columna de Ruta)
* **7fac101** - 2026-08-04 - abreuyoel - Fase C: sube replicas a 2 (workers sigue en 1)
* **50b9e1b** - 2026-08-03 - abreuyoel - Fase A: cablea Redis pub/sub para WebSockets (sigue en workers=1/replicas=1)
* **7828874** - 2026-08-03 - abreuyoel - Fix real del 500 al eliminar PDV: la tabla ACTIVACIONES no existe en la BD
* **278005f** - 2026-08-03 - abreuyoel - Perf: aliviar saturacion en hora pico (login lento/caido bajo carga)
* **31fb572** - 2026-08-03 - abreuyoel - Fix: eliminar PDV segue crasheando (500) por RUTA_PROGRAMACION sin validar
* **6292450** - 2026-08-03 - abreuyoel - Diagnostico: referencias a APZ0020/FTD0067 en todas las tablas antes de fusionar el PDV duplicado
* **2e324ba** - 2026-08-03 - abreuyoel - Fix bugs pre-existentes reportados: crear cliente, regiones/ciudades de PDV, eliminar PDV
* **4381e80** - 2026-08-03 - abreuyoel - Rediseno del sistema de permisos: conecta Plan de Accion, SKU vs SKU, Centro de Mando Auditoria, Frecuencias PDVs y Catalogos de Productos al control de accesos real (antes solo points/users/routes/products tenian enforcement)
* **c0d3c4b** - 2026-08-03 - abreuyoel - Diagnostico: volcar contenido completo de MODULOS para rediseno de permisos
* **f39f86f** - 2026-08-03 - abreuyoel - Fix: Productos no filtraba por analista (veia el catalogo completo)
* **fc9bcf0** - 2026-08-03 - abreuyoel - Asignacion Mercaderistas: buscar tambien por numero de ruta (ej. E164)
* **cd1b7dd** - 2026-08-03 - abreuyoel - Fix: Frecuencias PDVs no filtraba por analista (veia TODOS los clientes)
* **1ca957b** - 2026-08-03 - abreuyoel - Plan de Accion: boton para descargar la ficha tecnica del modulo (PDF)
* **032dbc8** - 2026-08-03 - abreuyoel - Plan de Accion Fase 4: confirmar propuesta crea la ruta BCK de verdad
* **0313d2b** - 2026-08-03 - abreuyoel - Plan de Accion Fase 3: partir cada zona geografica en rutas del tamano de una jornada
* **9c8d26a** - 2026-08-03 - abreuyoel - Plan de Accion Fase 3: matematica de capacidad por cluster (backups sugeridos)
* **ba86b8e** - 2026-08-03 - abreuyoel - Plan de Accion Fase 3 (primer incremento): geo-clustering de pendientes criticos
* **e13eaf8** - 2026-08-02 - abreuyoel - Fix diagnostico Fase 3: la columna PK de SERVICIOS es 'id', no 'id_servicio'
* **cc1b9b1** - 2026-08-02 - abreuyoel - Diagnostico previo a Fase 3: servicios BCK, join horas promedio, completitud de coordenadas
* **b14a9a2** - 2026-08-02 - abreuyoel - Plan de Accion: excluir combinaciones que nunca arrancaron (piloto en curso)
* **156441b** - 2026-08-02 - abreuyoel - Diagnostico: tamano real del universo de combinaciones activas en RUTA_PROGRAMACION
* **aa2d407** - 2026-08-02 - abreuyoel - Fix diagnostico: reemplaza EXISTS dentro de SUM por COUNT(DISTINCT CASE) (SQL Server rechazaba el anidado)
* **901a464** - 2026-08-02 - abreuyoel - Diagnostico: uso real de fotos tipo activacion/desactivacion en visitas del mes
* **4ef1693** - 2026-08-02 - abreuyoel - Plan de Accion: contar visita como completa sin exigir aprobacion del analista
* **72b8756** - 2026-08-02 - abreuyoel - Fix Plan de Accion: usar GETDATE() del servidor en vez de date.today() del contenedor
* **4d11a82** - 2026-08-02 - abreuyoel - Fix real de fondo: fast_executemany en el INSERT de Plan de Accion
* **4e3e40e** - 2026-08-02 - abreuyoel - Plan de Accion: timeout tambien en GET /pendientes + script de validacion de indices
* **b9f82a1** - 2026-08-02 - abreuyoel - Fix Plan de Accion: timeout en las queries + recalcular corre en background
* **949493e** - 2026-08-02 - abreuyoel - Fix Plan de Accion: fecha_visita es DATETIME en la base real, no DATE
* **6fbcb66** - 2026-08-02 - abreuyoel - Plan de Accion: mover a 4to lugar en el sidebar, junto a los otros centros de mando
* **2e4bc91** - 2026-08-02 - abreuyoel - Plan de Accion: pantalla minima de lectura en el sidebar
* **e4b3920** - 2026-08-02 - abreuyoel - Plan de Accion Fase 2: job en background que calcula visitas pendientes con score





* **f7b54db** - 2026-08-02 - abreuyoel - feat: nuevo módulo SKU vs SKU (Fase 1 -- solo definición, admin)
* **4161316** - 2026-08-02 - abreuyoel - feat: nuevo módulo Centro de Mando Auditoría
* **d89d9b1** - 2026-08-02 - abreuyoel - fix: admin no podía probar Auditoría de Campo fuera del día programado












* **3b7a661** - 2026-08-02 - abreuyoel - fix: filtros cascada en Productos + dropdown de Categorías Cliente cortado
* **daf5503** - 2026-08-02 - abreuyoel - feat: tanda de ajustes de UI/permisos pedidos sobre la marcha
* **7269d27** - 2026-08-02 - abreuyoel - fix: el timeout de execute_query rompía ANTES de correr la query
* **8e8b437** - 2026-08-02 - abreuyoel - fix: horas-trabajadas daba 524 (Cloudflare, >100s) con datos reales
* **fa1b294** - 2026-08-02 - abreuyoel - perf: Centro de Mando más rápido + tiempo de traslado + bundle móvil más liviano
* **72f9ec3** - 2026-07-31 - abreuyoel - fix: liveness probe seguía matando el pod bajo carga real (100s no alcanzaba)
* **bc87108** - 2026-07-31 - abreuyoel - fix: analista veía balances/productos de clientes que no tiene asignados
* **6f22045** - 2026-07-31 - abreuyoel - fix: Horas Trabajadas no respetaba el filtro de Cliente
* **28105bd** - 2026-07-31 - abreuyoel - feat: tab de Horas Trabajadas en Centro de Mando
* **9df6b42** - 2026-07-31 - abreuyoel - fix: reinicios en cascada del backend bajo picos de tráfico real
* **cf81775** - 2026-07-31 - abreuyoel - feat: roster de mercaderistas por defecto ordenado por sin_revisar
* **102b0b5** - 2026-07-31 - abreuyoel - fix: 500 en review-list (GROUP BY sin id_mercaderista) + roster escopado por cliente
* **53a5d9b** - 2026-07-31 - abreuyoel - feat: Revisión de Fotos muestra mercaderistas primero, no tarjetas de visitas
* **e173c92** - 2026-07-31 - abreuyoel - fix: servidor lento / 502 de Cloudflare -- print bloqueante en cada request + pool de conexiones agotado
* **2509da1** - 2026-07-31 - abreuyoel - feat: Fase 2 del portal Mercaderista -- chat dentro de la visita activa, limpieza de scaffold huérfano
* **231db4e** - 2026-07-30 - abreuyoel - feat: completa el flujo esencial del portal Mercaderista (activar PDV + fotos + balance + finalizar), offline-first
* **badc109** - 2026-07-29 - abreuyoel - fix: error al cargar fotos de una visita se tragaba en silencio
* **3dfc1a8** - 2026-07-29 - abreuyoel - fix: ATC no podía crear/editar/eliminar PDV; agrega filtros de Jerarquía N2_2, Nivel de Alcance y Clasificación de Canal
* **65f842d** - 2026-07-29 - abreuyoel - fix: la tabla de Productos no mostraba la Productora
* **289b4df** - 2026-07-29 - abreuyoel - feat: catálogo de Servicios con prefijo -- correlativo de rutas ya no depende de una whitelist fija E/A/T

=====================================================================================================
* **5c551b5** - 2026-07-29 - abreuyoel - fix: el service worker dejaba deploys nuevos invisibles en pestañas abiertas
* **68fb8b0** - 2026-07-29 - abreuyoel - fix: resumen-dia tiraba 500 al filtrar por cliente_id siendo analista
* **7bef61f** - 2026-07-28 - abreuyoel - fix: mark-reviewed tiraba 500 -- Visita no tiene atributo punto_interes
* **a019382** - 2026-07-28 - abreuyoel - fix: dropdown de usuarios en Permisos solo mostraba los primeros 100
* **af13e8d** - 2026-07-28 - abreuyoel - fix: modal Ver PDVs seguía en 0/0 -- espacios finales de columnas CHAR
* **8e02e5b** - 2026-07-28 - abreuyoel - fix: build de Angular fallaba -- showPicker() no está en los tipos de HTMLSelectElement
* **f9e58a0** - 2026-07-28 - abreuyoel - fix: modal "Ver PDVs" mostraba 0 Activados/Completados pese a la tarjeta
* **5a1a5c2** - 2026-07-28 - abreuyoel - fix: rechazar foto tiraba 500 -- faltaba insertar en FOTOS_RECHAZADAS
* **2d726c8** - 2026-07-26 - abreuyoel - fix: Rutas con Pendientes negativo y Puntos con Activos/Completados en 0
* **748bddf** - 2026-07-24 - abreuyoel - fix: tarjetas Rutas/Puntos del Centro de Mando ignoraban "Activos"
* **76c9951** - 2026-07-24 - abreuyoel - fix: puntos_interes de /resumen-dia exigía foto APROBADA para航空 activo/completo
* **3e64141** - 2026-07-24 - abreuyoel - fix: /activaciones tumbaba con 500 para cualquier analista (alias SQL inexistente)
* **fab83c2** - 2026-07-24 - abreuyoel - fix: /activaciones no mostraba visitas de clientes que comparten PDV ya activado
