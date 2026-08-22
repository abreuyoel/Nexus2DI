"""CRUD de FRECUENCIAS_PDVS_CLIENTE: cuantas veces por semana debe visitarse
un PDV para un cliente dado."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile, Form
import io
from openpyxl import load_workbook
from sqlalchemy import text, select, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.db.session import get_async_db
from app.core.dependencies import require_permission
from app.models.user import Usuario
from app.models.cliente import Cliente
from app.models.punto import PuntoInteres
from app.models.frecuencia_pdv_cliente import FrecuenciaPdvCliente
from app.schemas.frecuencia_pdv_cliente import (
    FrecuenciaPdvClienteCreate, FrecuenciaPdvClienteUpdate, FrecuenciaPdvClienteResponse,
    FrecuenciaBulkCreate,
)

router = APIRouter(prefix="/api/frecuencias-pdvs-cliente", tags=["Frecuencias PDVs Cliente"])


def _build_stmt():
    return (
        select(
            FrecuenciaPdvCliente,
            Cliente.nombre.label("cliente_nombre"),
            PuntoInteres.nombre.label("pdv_nombre"),
            Usuario.username.label("usuario_username")
        )
        .outerjoin(Cliente, Cliente.id == FrecuenciaPdvCliente.id_cliente)
        .outerjoin(PuntoInteres, PuntoInteres.id == FrecuenciaPdvCliente.id_punto_interes)
        .outerjoin(Usuario, Usuario.id == FrecuenciaPdvCliente.id_usuario)
    )


def _scope_analista_stmt(stmt, current_user: Usuario):
    if not (current_user.is_analyst and current_user.id_perfil):
        return stmt
    return stmt.filter(text("""
        EXISTS (
            SELECT 1 FROM RUTA_PROGRAMACION rp_a
            JOIN analistas_rutas ar_a ON rp_a.id_ruta = ar_a.id_ruta
            WHERE rp_a.id_punto_interes = FRECUENCIAS_PDVS_CLIENTE.id_punto_interes
              AND rp_a.id_cliente = FRECUENCIAS_PDVS_CLIENTE.id_cliente
              AND rp_a.activa = 1 AND ar_a.id_analista = :analista_id
        )
    """)).params(analista_id=int(current_user.id_perfil))


def _to_resp(row) -> FrecuenciaPdvClienteResponse:
    f = row.FrecuenciaPdvCliente
    return FrecuenciaPdvClienteResponse(
        id=f.id, id_cliente=f.id_cliente, id_punto_interes=f.id_punto_interes,
        frecuencia_semanal=float(f.frecuencia_semanal), observaciones=f.observaciones, activo=f.activo,
        fecha_creacion=f.fecha_creacion, fecha_modificacion=f.fecha_modificacion, id_usuario=f.id_usuario,
        cliente_nombre=row.cliente_nombre, pdv_nombre=row.pdv_nombre, usuario_username=row.usuario_username,
    )


@router.get("", response_model=List[FrecuenciaPdvClienteResponse])
async def list_frecuencias(
    id_cliente: Optional[int] = Query(None),
    id_punto_interes: Optional[str] = Query(None),
    activo: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(require_permission('frecuencias-pdvs-cliente', 'read')),
):
    stmt = _build_stmt()
    if id_cliente is not None:
        stmt = stmt.filter(FrecuenciaPdvCliente.id_cliente == id_cliente)
    if id_punto_interes is not None:
        stmt = stmt.filter(FrecuenciaPdvCliente.id_punto_interes == id_punto_interes)
    if activo is not None:
        stmt = stmt.filter(FrecuenciaPdvCliente.activo == activo)
    stmt = _scope_analista_stmt(stmt, current_user)
    stmt = stmt.order_by(FrecuenciaPdvCliente.id.desc())
    rows = (await db.execute(stmt)).all()
    return [_to_resp(row) for row in rows]


@router.get("/pdvs-disponibles/{id_cliente}")
async def pdvs_disponibles_cliente(
    id_cliente: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(require_permission('frecuencias-pdvs-cliente', 'read')),
):
    """PDVs unicos donde aparece el cliente en RUTA_PROGRAMACION, marcando la
    frecuencia ya asignada (si existe) para poder editarla en la carga masiva.
    Si el que pregunta es analista, solo ve los PDVs de ESE cliente que caen
    dentro de sus propias rutas asignadas (analistas_rutas).
    Optimizado: una sola query con LEFT JOIN en vez de 2 queries separadas."""
    if not (await db.execute(select(Cliente).filter(Cliente.id == id_cliente))).scalars().first():
        raise HTTPException(404, "Cliente no existe")
    scope_sql = ""
    params = {"cid": id_cliente}
    if current_user.is_analyst and current_user.id_perfil:
        scope_sql = """
            AND EXISTS (SELECT 1 FROM analistas_rutas ar_a
                WHERE ar_a.id_ruta = rp.id_ruta AND ar_a.id_analista = :analista_id)
        """
        params["analista_id"] = int(current_user.id_perfil)
    rows = (await db.execute(text(f"""
        SELECT DISTINCT
            rp.id_punto_interes,
            rp.punto_interes,
            f.id_frecuencia_pdv_cliente,
            f.frecuencia_semanal,
            f.observaciones
        FROM RUTA_PROGRAMACION rp
        LEFT JOIN FRECUENCIAS_PDVS_CLIENTE f
            ON f.id_punto_interes = rp.id_punto_interes
            AND f.id_cliente = rp.id_cliente
        WHERE rp.id_cliente = :cid AND rp.activa = 1 AND rp.id_punto_interes IS NOT NULL
        {scope_sql}
        ORDER BY rp.punto_interes
    """), params)).fetchall()
    return [
        {
            "id_punto_interes": r.id_punto_interes,
            "pdv_nombre": r.punto_interes,
            "id_frecuencia": r.id_frecuencia_pdv_cliente,
            "frecuencia_semanal": float(r.frecuencia_semanal) if r.frecuencia_semanal is not None else None,
            "observaciones": r.observaciones,
        }
        for r in rows
    ]


@router.post("/bulk")
async def bulk_upsert_frecuencias(
    data: FrecuenciaBulkCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(require_permission('frecuencias-pdvs-cliente.carga_masiva', 'read')),
):
    """Crea o actualiza (upsert) varias frecuencias de una vez para un mismo
    cliente — pensado para la carga masiva desde los PDVs de su programación."""
    if not (await db.execute(select(Cliente).filter(Cliente.id == data.id_cliente))).scalars().first():
        raise HTTPException(404, "Cliente no existe")
    creados = 0
    actualizados = 0
    for item in data.items:
        existente = (await db.execute(
            select(FrecuenciaPdvCliente).filter_by(
                id_cliente=data.id_cliente, id_punto_interes=item.id_punto_interes
            )
        )).scalars().first()
        if existente:
            existente.frecuencia_semanal = item.frecuencia_semanal
            existente.observaciones = item.observaciones
            existente.activo = True
            existente.id_usuario = current_user.id
            existente.fecha_modificacion = datetime.utcnow()
            actualizados += 1
        else:
            db.add(FrecuenciaPdvCliente(
                id_cliente=data.id_cliente, id_punto_interes=item.id_punto_interes,
                frecuencia_semanal=item.frecuencia_semanal, observaciones=item.observaciones,
                activo=True, id_usuario=current_user.id,
            ))
            creados += 1
    await db.commit()
    return {"creados": creados, "actualizados": actualizados}


@router.get("/{id_frecuencia}", response_model=FrecuenciaPdvClienteResponse)
async def get_frecuencia(id_frecuencia: int, db: AsyncSession = Depends(get_async_db), _: Usuario = Depends(require_permission('frecuencias-pdvs-cliente', 'read'))):
    row = (await db.execute(_build_stmt().filter(FrecuenciaPdvCliente.id == id_frecuencia))).first()
    if not row:
        raise HTTPException(404, "Registro no encontrado")
    return _to_resp(row)


@router.post("", response_model=FrecuenciaPdvClienteResponse, status_code=201)
async def create_frecuencia(
    data: FrecuenciaPdvClienteCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(require_permission('frecuencias-pdvs-cliente.crear', 'read')),
):
    if not (await db.execute(select(Cliente).filter(Cliente.id == data.id_cliente))).scalars().first():
        raise HTTPException(404, "Cliente no existe")
    if not (await db.execute(select(PuntoInteres).filter(PuntoInteres.id == data.id_punto_interes))).scalars().first():
        raise HTTPException(404, "PDV no existe")
    f = FrecuenciaPdvCliente(
        id_cliente=data.id_cliente, id_punto_interes=data.id_punto_interes,
        frecuencia_semanal=data.frecuencia_semanal, observaciones=data.observaciones,
        activo=data.activo, id_usuario=current_user.id,
    )
    db.add(f)
    await db.commit()
    await db.refresh(f)
    return await get_frecuencia(f.id, db, current_user)


@router.put("/{id_frecuencia}", response_model=FrecuenciaPdvClienteResponse)
async def update_frecuencia(
    id_frecuencia: int,
    data: FrecuenciaPdvClienteUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(require_permission('frecuencias-pdvs-cliente.editar', 'read')),
):
    f = (await db.execute(select(FrecuenciaPdvCliente).filter(FrecuenciaPdvCliente.id == id_frecuencia))).scalars().first()
    if not f:
        raise HTTPException(404, "Registro no encontrado")
    if data.id_cliente is not None and not (await db.execute(select(Cliente).filter(Cliente.id == data.id_cliente))).scalars().first():
        raise HTTPException(404, "Cliente no existe")
    if data.id_punto_interes is not None and not (await db.execute(select(PuntoInteres).filter(PuntoInteres.id == data.id_punto_interes))).scalars().first():
        raise HTTPException(404, "PDV no existe")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(f, k, v)
    f.id_usuario = current_user.id
    f.fecha_modificacion = datetime.utcnow()
    await db.commit()
    return await get_frecuencia(id_frecuencia, db, current_user)


@router.delete("/{id_frecuencia}")
async def delete_frecuencia(
    id_frecuencia: int,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_permission('frecuencias-pdvs-cliente.eliminar', 'read')),
):
    f = (await db.execute(select(FrecuenciaPdvCliente).filter(FrecuenciaPdvCliente.id == id_frecuencia))).scalars().first()
    if not f:
        raise HTTPException(404, "Registro no encontrado")
    await db.delete(f)
    await db.commit()
    return {"detail": "Registro eliminado"}


@router.post("/importar-excel")
async def importar_excel_frecuencias(
    id_cliente: int = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(require_permission('frecuencias-pdvs-cliente.carga_masiva', 'read')),
):
    """
    Recibe el archivo Excel cargado por el usuario, valida que corresponda al cliente,
    y realiza el upsert de frecuencias de forma masiva y optimizada en la base de datos.

    Optimizado: usa openpyxl read_only (no pandas) + bulk SQL (no N+1 queries).
    """
    if not (await db.execute(select(Cliente).filter(Cliente.id == id_cliente))).scalars().first():
        raise HTTPException(404, "Cliente no existe")

    try:
        # ── 1. Leer archivo de forma async ──────────────────────────────
        contents = await file.read()

        # ── 2. Parsear con openpyxl read_only (ligero, sin pandas) ──────
        wb = load_workbook(io.BytesIO(contents), read_only=True, data_only=True)

        if "Frecuencias" not in wb.sheetnames:
            wb.close()
            raise HTTPException(400, "No se encontró la hoja 'Frecuencias' en el archivo.")

        ws = wb["Frecuencias"]

        # ── 3. Validar metadatos (filas 1-8) ────────────────────────────
        # En openpyxl read_only, iterar las primeras filas para obtener B5
        meta_rows = []
        for i, row in enumerate(ws.iter_rows(min_row=1, max_row=8, max_col=2, values_only=True), 1):
            meta_rows.append(row)
            if i >= 8:
                break

        if len(meta_rows) < 5 or len(meta_rows[4]) < 2:
            wb.close()
            raise HTTPException(400, "Formato de cabecera inválido en la hoja Frecuencias.")

        id_cliente_excel_raw = meta_rows[4][1]  # Fila 5 (índice 4), Columna B (índice 1)
        try:
            id_cliente_excel = int(id_cliente_excel_raw)
        except (ValueError, TypeError):
            wb.close()
            raise HTTPException(
                400,
                f"No se pudo leer el ID del cliente en la celda B5 del archivo. Encontrado: {id_cliente_excel_raw}"
            )

        if id_cliente_excel != id_cliente:
            wb.close()
            raise HTTPException(
                400,
                f"El cliente del archivo ({id_cliente_excel}) no coincide con el seleccionado ({id_cliente})."
            )

        # ── 4. Extraer datos (desde fila 10, saltando cabecera fila 9) ──
        items = []
        for row in ws.iter_rows(min_row=10, values_only=True):
            if not row or len(row) < 5:
                continue

            id_pdv_raw = row[0]
            if id_pdv_raw is None:
                continue
            id_pdv = str(id_pdv_raw).strip()
            if not id_pdv or id_pdv.lower() == "none":
                continue

            freq_raw = row[3]  # Columna D: Frecuencia Semanal
            if freq_raw is None or str(freq_raw).strip() == "":
                continue

            try:
                freq_str = str(freq_raw).replace(",", ".")
                freq_val = float(freq_str)
            except (ValueError, TypeError):
                continue

            obs_raw = row[4]  # Columna E: Observaciones
            obs_val = str(obs_raw).strip() if obs_raw is not None and str(obs_raw).strip() else None

            items.append({
                "id_pdv": id_pdv,
                "freq": freq_val,
                "obs": obs_val,
            })

        wb.close()

        if not items:
            raise HTTPException(400, "El archivo no contiene registros válidos para procesar.")

        # ── 5. Bulk upsert: 1 SELECT + 1 INSERT batch + 1 UPDATE batch ─
        # Un solo SELECT para traer todos los existentes del cliente
        existing_rows = (await db.execute(
            select(
                FrecuenciaPdvCliente.id,
                FrecuenciaPdvCliente.id_punto_interes,
            ).filter_by(id_cliente=id_cliente)
        )).fetchall()
        existing_map = {r.id_punto_interes: r.id for r in existing_rows}

        to_insert = []
        to_update = []
        now = datetime.utcnow()

        for item in items:
            existing_id = existing_map.get(item["id_pdv"])
            if existing_id is not None:
                to_update.append({
                    "fid": existing_id,
                    "freq": item["freq"],
                    "obs": item["obs"],
                    "uid": current_user.id,
                    "now": now,
                })
            else:
                to_insert.append({
                    "id_cliente": id_cliente,
                    "id_pdv": item["id_pdv"],
                    "freq": item["freq"],
                    "obs": item["obs"],
                    "uid": current_user.id,
                })

        # Batch INSERT (nuevos registros)
        if to_insert:
            await db.execute(
                text("""
                    INSERT INTO FRECUENCIAS_PDVS_CLIENTE
                        (id_cliente, id_punto_interes, frecuencia_semanal, observaciones, activo, id_usuario)
                    VALUES
                        (:id_cliente, :id_pdv, :freq, :obs, 1, :uid)
                """),
                to_insert,
            )

        # Batch UPDATE (registros existentes)
        if to_update:
            await db.execute(
                text("""
                    UPDATE FRECUENCIAS_PDVS_CLIENTE
                    SET frecuencia_semanal = :freq,
                        observaciones = :obs,
                        activo = 1,
                        id_usuario = :uid,
                        fecha_modificacion = :now
                    WHERE id_frecuencia_pdv_cliente = :fid
                """),
                to_update,
            )

        await db.commit()
        return {"creados": len(to_insert), "actualizados": len(to_update)}

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(500, f"Error al procesar el archivo Excel en el servidor: {str(e)}")

