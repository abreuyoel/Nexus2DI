import app.db.all_models
from app.db.session import SessionLocal
from app.models.user import Usuario
from app.core.security import get_password_hash

db = SessionLocal()
user = db.query(Usuario).filter(Usuario.username == 'Dev').first()
if user:
    user.password = get_password_hash('DevPassword123')
    db.commit()
    print("Updated Dev password successfully!")
else:
    print("Dev user not found!")
