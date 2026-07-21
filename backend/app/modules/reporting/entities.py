# Reporting module entity references and definitions
from app.modules.visits.entities import Visita, Foto, Balance
from app.modules.routes.entities import Ruta, RutaProgramacion, PuntoInteres, RutaActivada, AnalistaRuta
from app.modules.merchandisers.entities import Mercaderista, MercaderistaRuta
from app.modules.clients.entities import Cliente, DashboardClient
from app.modules.auth.entities import Usuario
from app.modules.analysts.entities import AnalistaCliente

__all__ = [
    "Visita",
    "Foto",
    "Balance",
    "Ruta",
    "RutaProgramacion",
    "PuntoInteres",
    "RutaActivada",
    "AnalistaRuta",
    "Mercaderista",
    "MercaderistaRuta",
    "Cliente",
    "DashboardClient",
    "Usuario",
    "AnalistaCliente",
]
