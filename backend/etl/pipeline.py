"""
pipeline.py
-----------
Orquestador del ETL completo.

Flujo:
  1. extract  → lee bytes → DataFrame crudo
  2. transform → limpia y valida → DataFrame limpio + ValidationReport
  3. spark_ops → deduplica entre archivos (Spark o pandas fallback)
  4. load      → guarda Excel consolidado
  5. transform.apply_formatting → aplica estilos openpyxl
  6. Devuelve dict con resultado, stats y alertas para Flask
"""

import logging
import os

import numpy as np
import pandas as pd

from .extract import extract_excel
from .transform import (
    transform,
    apply_formatting,
    DATE_COLUMNS,
    MONTH_NAMES,
)
from .spark_ops import deduplicate
from .load import save_excel

log = logging.getLogger(__name__)


def run_pipeline(files, mes: str, anio: str, tmp_dir: str) -> dict:
    """
    Parámetros
    ----------
    files    : lista de objetos FileStorage de Flask (con .filename y .read())
    mes      : string "01"–"12"
    anio     : string año, e.g. "2025"
    tmp_dir  : directorio temporal donde se guarda el Excel de salida

    Retorna
    -------
    dict con claves: filename, file_results, alerts, rows, stats
    """
    all_dfs: list[pd.DataFrame] = []
    file_results: list[dict] = []
    all_alerts: list[dict] = []

    log.info("📂 Archivos recibidos: %s", [f.filename for f in files])

    # ------------------------------------------------------------------
    # 1 + 2: Extract & Transform por archivo
    # ------------------------------------------------------------------
    for f in files:
        fname = f.filename
        log.info("Procesando: %s", fname)

        try:
            file_bytes = f.read()

            # Extract
            df_raw = extract_excel(file_bytes)

            # Transform
            df_clean, report = transform(df_raw)

            if df_clean.empty:
                log.warning("DataFrame vacío tras transform: %s", fname)
                continue

            all_dfs.append(df_clean)
            alerts_list = report.to_list()

            file_results.append({
                "filename": fname,
                "rows": len(df_clean),
                "status": "ok",
                "errores": report.count("error"),
                "advertencias": report.count("warn"),
                "alerts": alerts_list,
            })
            all_alerts.extend([dict(a, file=fname) for a in alerts_list])

        except Exception:
            import traceback
            msg = traceback.format_exc()
            log.error("Error procesando %s:\n%s", fname, msg)
            file_results.append({
                "filename": fname,
                "rows": 0,
                "status": "error",
                "errores": 1,
                "advertencias": 0,
                "alerts": [{"type": "error", "doc": "", "campo": "", "msg": str(msg)}],
            })
            all_alerts.append({
                "type": "error", "file": fname,
                "doc": "", "campo": "", "msg": str(msg),
            })

    if not all_dfs:
        raise ValueError("No se pudo procesar ningún archivo.")

    # ------------------------------------------------------------------
    # 3: Consolidar y deduplicar con Spark (o pandas fallback)
    # ------------------------------------------------------------------
    log.info("Consolidando %d DataFrames...", len(all_dfs))
    consolidated = pd.concat(all_dfs, ignore_index=True)

    rows_before = len(consolidated)
    consolidated = deduplicate(consolidated, key_col="DOCUMENTO")
    rows_after = len(consolidated)

    if rows_before != rows_after:
        log.info("Duplicados eliminados: %d", rows_before - rows_after)
        all_alerts.append({
            "type": "warn",
            "file": "(consolidado)",
            "doc": "",
            "campo": "DOCUMENTO",
            "msg": f"Se eliminaron {rows_before - rows_after} filas duplicadas por DOCUMENTO.",
        })

    # ID correlativo al frente
    consolidated.insert(0, "ID_REGISTRO", range(1, len(consolidated) + 1))

    # ------------------------------------------------------------------
    # 4: Preparar fechas para Excel (strings ISO)
    # ------------------------------------------------------------------
    for col in DATE_COLUMNS:
        if col in consolidated.columns:
            consolidated[col] = pd.to_datetime(
                consolidated[col], errors="coerce"
            ).apply(
                lambda x: x.strftime("%Y-%m-%d") if pd.notna(x) else ""
            )

    # ------------------------------------------------------------------
    # 5: Load → guardar Excel
    # ------------------------------------------------------------------
    month_name = MONTH_NAMES.get(int(mes), mes)
    output_filename = f"PaquetesAlimentarios_{month_name}{anio}_PROCESADO.xlsx"
    tmp_path = os.path.join(tmp_dir, output_filename)

    log.info("Guardando en: %s", tmp_path)
    save_excel(consolidated, tmp_path)
    apply_formatting(tmp_path)

    # ------------------------------------------------------------------
    # 6: Calcular estadísticas para el frontend
    # ------------------------------------------------------------------
    stats = {
        "total_beneficiarios": len(consolidated),
        "total_paquetes": (
            int(consolidated["CANTIDAD DE PAQUETES"].apply(
                lambda x: int(float(x)) if str(x).strip() not in ("", "nan") else 0
            ).sum())
            if "CANTIDAD DE PAQUETES" in consolidated.columns else 0
        ),
        "femenino": int(
            (consolidated.get("GENERO", pd.Series()) == "FEMENINO").sum()
        ),
        "masculino": int(
            (consolidated.get("GENERO", pd.Series()) == "MASCULINO").sum()
        ),
        "dias_unicos": int(
            consolidated["FECHA ENTREGA"].replace("", np.nan).nunique()
            if "FECHA ENTREGA" in consolidated.columns else 0
        ),
        "archivos_procesados": len(all_dfs),
        "total_errores": sum(1 for a in all_alerts if a.get("type") == "error"),
        "total_advertencias": sum(1 for a in all_alerts if a.get("type") == "warn"),
    }

    log.info("✅ Pipeline completado — %d registros", len(consolidated))

    return {
        "filename": output_filename,
        "file_results": file_results,
        "alerts": all_alerts,
        "rows": len(consolidated),
        "stats": stats,
    }
