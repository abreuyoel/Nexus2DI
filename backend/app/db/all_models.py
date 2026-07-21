from app.modules.auth.entities import Usuario, UserPermission, SesionActiva  # noqa: F401
from app.modules.merchandisers.entities import Mercaderista, MercaderistaRuta  # noqa: F401
from app.modules.clients.entities import Cliente, CategoriaCliente, ClienteRuta  # noqa: F401
from app.modules.catalogues.entities import Categoria, Producto, TipoNegocio, SubtipoNegocio, Alcance, CanalVenta, DepartamentoGeo, Ciudad, Cuadrante, Servicio  # noqa: F401
from app.modules.routes.entities import Ruta, RutaProgramacion, RutaCambioFuturo, RutaActivada, AnalistaRuta, PuntoInteres  # noqa: F401
from app.modules.analysts.entities import Analista, AnalistaCliente  # noqa: F401
from app.modules.supervisors.entities import Supervisor, SupervisorRuta, SupervisorCliente  # noqa: F401
from app.modules.visits.entities import Visita, Foto, NotificacionRechazoFoto, PushSubscription, FotoRazonRechazo, Activacion, Balance  # noqa: F401
from app.modules.chat.entities import ChatMensaje  # noqa: F401
from app.models.chat import ChatMensajeLectura  # noqa: F401
from app.models.chat_grupos import (  # noqa: F401
    ChatGrupo, ChatGrupoMensaje, ChatGrupoLectura, ChatGrupoMensajeLectura,
    ChatMensajeGrupoVisita, ChatGrupoVisitaLectura,
)
from app.modules.customer_service.entities import Solicitud  # noqa: F401
from app.modules.auditors.entities import AuditLog  # noqa: F401
from app.modules.surveyors.entities import JornadaEncuestador, CentroSalud, EncuestaCentro, Medico, MedicoCentroEncuesta  # noqa: F401
from app.modules.frequencies.entities import FrecuenciaPdvCliente, HorasPromedioEjecucion  # noqa: F401

