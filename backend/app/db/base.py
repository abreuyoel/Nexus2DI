from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Register all domain entities in SQLAlchemy Base metadata
import app.modules.auth.entities
import app.modules.clients.entities
import app.modules.routes.entities
import app.modules.merchandisers.entities
import app.modules.sellers.entities
import app.modules.visits.entities
import app.modules.auditors.entities
import app.modules.catalogues.entities
import app.modules.customer_service.entities
import app.modules.chat.entities
import app.modules.analysts.entities
