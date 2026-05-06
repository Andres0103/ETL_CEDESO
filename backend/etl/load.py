"""
load.py
-------
Responsabilidad única: persistir el DataFrame consolidado en PostgreSQL.
Usa INSERT ... ON CONFLICT DO NOTHING para acumular historial
sin duplicar registros ya existentes (único por documento + fecha_entrega).
"""

import json
import logging
from datetime import datetime, date

import numpy as np
import pandas as pd
from sqlalchemy.dialects.postgresql import insert

from backend.db.session import get_session, engine
from backend.db.models import Base, PaqueteAlimentario, CargaETL

log = logging.getLogger(__name__)

COLUMN_MAP = {
    "DOCUMENTO":                        "documento",
    "AUTORIZ.":                         "autorizacion",
    "NOMBRE_REPRESENTANTE":             "nombre_representante",
    "GENERO":                           "genero",
    "CANTIDAD DE PAQUETES":             "cantidad_paquetes",
    "PROGRAMA POR EL QUE INGRESA":      "programa",
    "COMUNA":                           "comuna",
    "ESTADO":                           "estado",
    "NOMBRE PUNTO":                     "nombre_punto",
    "DIRECCION":                        "direccion",
    "REFERENTE":                        "referente",
    "FECHA PROGRAMADA EN CONVOCATORIA": "fecha_programada",
    "GRUPO":                            "grupo",
    "HORARIO":                          "horario",
    "RESULTADO CONVOCATORIA":           "resultado_convocatoria",
    "QUIEN SDM":                        "quien_sdm",
    "RESPONSABLE":                      "responsable",
    "OTRO TELEFONO":                    "otro_telefono",
    "FECHA ENTREGA":                    "fecha_entrega",
    "RESPONSABLE6":                     "responsable6",
    "ANIO ENTREGA":                     "anio_entrega",
    "MES ENTREGA":                      "mes_entrega",
    "MES NOMBRE":                       "mes_nombre",
    "DIA ENTREGA":                      "dia_entrega",
    "ENTREGADO":                        "entregado",
}

DATE_COLS = {"fecha_programada", "fecha_entrega"}
INT_COLS  = {"cantidad_paquetes", "anio_entrega", "mes_entrega", "dia_entrega"}
BOOL_COLS = {"entregado"}


def _ensure_tables():
    """Crea las tablas si no existen (idempotente)."""
    Base.metadata.create_all(bind=engine)


def _clean_value(col: str, val):
    """Convierte un valor del DataFrame al tipo Python correcto para PostgreSQL."""
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(val, float) and np.isnan(val):
        return None
    if isinstance(val, str) and val.strip() in ("", "nan", "NaT", "None"):
        return None

    if col in DATE_COLS:
        if pd.isna(val) if hasattr(pd, 'isna') else False:
            return None
        if val is pd.NaT:
            return None
        if isinstance(val, date):
            return val
        if isinstance(val, datetime):
            return val.date()
        try:
            ts = pd.to_datetime(val, errors="coerce")
            return None if pd.isna(ts) else ts.date()
        except Exception:
            return None

    if col in INT_COLS:
        try:
            return int(float(val))
        except Exception:
            return None

    if col in BOOL_COLS:
        if isinstance(val, bool):
            return val
        return str(val).strip().upper() == "SI"

    return val


def save_to_db(
    df: pd.DataFrame,
    mes: str,
    anio: str,
    file_results: list,
    archivo_origen: str = "",
) -> dict:
    """
    Inserta el DataFrame consolidado en PostgreSQL acumulando historial.
    Registros duplicados (doc + fecha_entrega) se omiten silenciosamente.
    """
    _ensure_tables()

    df = df.copy()
    if "ID_REGISTRO" in df.columns:
        df = df.drop(columns=["ID_REGISTRO"])

    df = df.rename(columns={k: v for k, v in COLUMN_MAP.items() if k in df.columns})

    records = []
    for _, row in df.iterrows():
        record = {"archivo_origen": archivo_origen}
        for orm_col in COLUMN_MAP.values():
            if orm_col in row.index:
                record[orm_col] = _clean_value(orm_col, row[orm_col])
        records.append(record)

    if not records:
        log.warning("No hay registros para insertar.")
        return {"insertados": 0, "duplicados": 0, "total": 0}

    with get_session() as session:
        stmt = (
            insert(PaqueteAlimentario)
            .values(records)
            .on_conflict_do_nothing(
                index_elements=["documento", "fecha_entrega"]
            )
        )
        result = session.execute(stmt)
        insertados = result.rowcount if result.rowcount >= 0 else len(records)
        duplicados = len(records) - insertados

        carga = CargaETL(
            mes=mes,
            anio=anio,
            archivos=json.dumps([fr["filename"] for fr in file_results]),
            total_registros=len(records),
            registros_nuevos=insertados,
            registros_dup=duplicados,
            errores=sum(fr.get("errores", 0) for fr in file_results),
            advertencias=sum(fr.get("advertencias", 0) for fr in file_results),
            estado="ok",
        )
        session.add(carga)

    log.info("BD: %d insertados, %d duplicados omitidos", insertados, duplicados)
    return {"insertados": insertados, "duplicados": duplicados, "total": len(records)}
