"""
pipeline.py - Orquestador ETL completo con carga a PostgreSQL
"""
import logging, os
import numpy as np
import pandas as pd

from .extract import extract_excel
from .transform import transform, DATE_COLUMNS, MONTH_NAMES
from .spark_ops import deduplicate
from .load import save_to_db

log = logging.getLogger(__name__)

def run_pipeline(files, mes: str, anio: str, tmp_dir: str) -> dict:
    all_dfs, file_results, all_alerts = [], [], []
    log.info("📂 Archivos: %s", [f.filename for f in files])

    for f in files:
        fname = f.filename
        try:
            df_raw = extract_excel(f.read())
            df_clean, report = transform(df_raw)
            if df_clean.empty:
                continue
            all_dfs.append(df_clean)
            alerts_list = report.to_list()
            file_results.append({
                "filename": fname, "rows": len(df_clean), "status": "ok",
                "errores": report.count("error"), "advertencias": report.count("warn"),
                "alerts": alerts_list,
            })
            all_alerts.extend([dict(a, file=fname) for a in alerts_list])
        except Exception:
            import traceback
            msg = traceback.format_exc()
            log.error("Error en %s:\n%s", fname, msg)
            file_results.append({"filename": fname, "rows": 0, "status": "error",
                "errores": 1, "advertencias": 0,
                "alerts": [{"type": "error", "doc": "", "campo": "", "msg": msg}]})
            all_alerts.append({"type": "error", "file": fname, "doc": "", "campo": "", "msg": msg})

    if not all_dfs:
        raise ValueError("No se pudo procesar ningún archivo.")

    consolidated = pd.concat(all_dfs, ignore_index=True)
    rows_before = len(consolidated)
    consolidated = deduplicate(consolidated, key_col="DOCUMENTO")
    if rows_before != len(consolidated):
        dupes = rows_before - len(consolidated)
        all_alerts.append({"type": "warn", "file": "(consolidado)", "doc": "",
            "campo": "DOCUMENTO", "msg": f"Se eliminaron {dupes} duplicados."})

    consolidated.insert(0, "ID_REGISTRO", range(1, len(consolidated) + 1))

    month_name = MONTH_NAMES.get(int(mes), mes)
    db_result = save_to_db(
        df=consolidated, mes=mes, anio=anio,
        file_results=file_results,
        archivo_origen=f"PaquetesAlimentarios_{month_name}{anio}",
    )

    stats = {
        "total_beneficiarios": len(consolidated),
        "total_paquetes": (
            int(consolidated["CANTIDAD DE PAQUETES"].apply(
                lambda x: int(float(x)) if str(x).strip() not in ("", "nan") else 0
            ).sum()) if "CANTIDAD DE PAQUETES" in consolidated.columns else 0
        ),
        "femenino": int((consolidated.get("GENERO", pd.Series()) == "FEMENINO").sum()),
        "masculino": int((consolidated.get("GENERO", pd.Series()) == "MASCULINO").sum()),
        "dias_unicos": int(
            consolidated["FECHA ENTREGA"].replace("", np.nan).nunique()
            if "FECHA ENTREGA" in consolidated.columns else 0
        ),
        "archivos_procesados": len(all_dfs),
        "total_errores": sum(1 for a in all_alerts if a.get("type") == "error"),
        "total_advertencias": sum(1 for a in all_alerts if a.get("type") == "warn"),
        "db_insertados": db_result["insertados"],
        "db_duplicados": db_result["duplicados"],
    }

    log.info("✅ Pipeline completado — %d registros, %d en BD", len(consolidated), db_result["insertados"])
    return {"file_results": file_results, "alerts": all_alerts,
            "rows": len(consolidated), "stats": stats, "db_result": db_result}
