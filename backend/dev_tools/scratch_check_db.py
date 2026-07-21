from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

with engine.connect() as conn:
    # 1. Contar balances
    res = conn.execute(text("SELECT COUNT(*) FROM BALANCES_TOTALES"))
    print(f"Total Balances: {res.scalar()}")

    # 2. Contar visitas
    res = conn.execute(text("SELECT COUNT(*) FROM VISITAS_MERCADERISTA"))
    print(f"Total Visitas: {res.scalar()}")

    # 3. Contar coincidencias ID_VISITA
    res = conn.execute(text("""
        SELECT COUNT(DISTINCT bt.ID_VISITA) 
        FROM BALANCES_TOTALES bt
        JOIN VISITAS_MERCADERISTA vm ON bt.ID_VISITA = vm.id_visita
    """))
    print(f"Visitas con Balances (coincidentes): {res.scalar()}")

    # 4. Ver muestra de Balances con ID_VISITA
    res = conn.execute(text("SELECT TOP 5 ID_BALANCE, ID_VISITA, ID_CLIENTE FROM BALANCES_TOTALES"))
    print(f"Muestra de Balances: {res.fetchall()}")

    # 5. Ver si hay balances para el cliente 43
    res = conn.execute(text("SELECT COUNT(*) FROM BALANCES_TOTALES WHERE ID_CLIENTE = 43"))
    print(f"Balances para Cliente 43: {res.scalar()}")
    
    # 6. Ver analistas-clientes para Dilcia (id_analista 1)
    res = conn.execute(text("SELECT * FROM ANALISTAS_CLIENTE WHERE id_analista = 1"))
    print(f"Analistas-Clientes para Dilcia: {res.fetchall()}")
