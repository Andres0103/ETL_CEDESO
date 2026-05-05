"""
transform.py
------------
Responsabilidad única: limpiar, normalizar y validar
un DataFrame crudo. Devuelve (df_limpio, ValidationReport).

NO contiene lógica de Spark ni de Flask.
NO lee archivos, NO guarda archivos.
"""

import re
import unicodedata
from datetime import datetime, date

import numpy as np
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


# ---------------------------------------------------------------------------
# Mapas de columnas y constantes
# ---------------------------------------------------------------------------

COLUMN_MAP = {
    "DOCUMENTO":                        "DOCUMENTO",
    "AUTORIZ.":                         "AUTORIZ.",
    "NOMBRE_REPRESENTANTE":             "NOMBRE_REPRESENTANTE",
    "GENERO":                           "GENERO",
    "CANTIDAD DE PAQUETES":             "CANTIDAD DE PAQUETES",
    "PROGRAMA POR EL QUE INGRESA":      "PROGRAMA POR EL QUE INGRESA",
    "COMUNA":                           "COMUNA",
    "ESTADO":                           "ESTADO",
    "NOMBRE PUNTO":                     "NOMBRE PUNTO",
    "DIRECCION":                        "DIRECCION",
    "REFERENTE":                        "REFERENTE",
    "FECHA PROGRAMADA EN CONVOCATORIA": "FECHA PROGRAMADA EN CONVOCATORIA",
    "GRUPO":                            "GRUPO",
    "HORARIO":                          "HORARIO",
    "RESULTADO CONVOCATORIA":           "RESULTADO CONVOCATORIA",
    "QUIEN SDM":                        "QUIEN SDM",
    "RESPONSABLE":                      "RESPONSABLE",
    "OTRO TELEFONO":                    "OTRO TELEFONO",
    "FECHA ENTREGA":                    "FECHA ENTREGA",
    "RESPONSABLE6":                     "RESPONSABLE6",
}

TEXT_COLUMNS = [
    "NOMBRE_REPRESENTANTE", "PROGRAMA POR EL QUE INGRESA",
    "COMUNA", "ESTADO", "NOMBRE PUNTO", "DIRECCION",
    "REFERENTE", "RESULTADO CONVOCATORIA", "RESPONSABLE", "RESPONSABLE6",
]

DATE_COLUMNS = ["FECHA PROGRAMADA EN CONVOCATORIA", "FECHA ENTREGA"]

FILL_WITH_SIN_DATO = [
    "RESULTADO CONVOCATORIA", "QUIEN SDM", "RESPONSABLE",
    "GRUPO", "HORARIO", "RESPONSABLE6", "AUTORIZ.",
]

GENDER_MAP = {
    "F": "FEMENINO", "FEM": "FEMENINO", "FEMENINO": "FEMENINO",
    "FEMENINA": "FEMENINO", "MUJ": "FEMENINO", "MUJER": "FEMENINO",
    "M": "MASCULINO", "MAS": "MASCULINO", "MASCULINO": "MASCULINO",
    "MASC": "MASCULINO", "HOMBRE": "MASCULINO", "H": "MASCULINO",
}

MONTH_NAMES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}

COL_WIDTHS = {
    "DOCUMENTO": 14, "AUTORIZ.": 10, "NOMBRE_REPRESENTANTE": 35,
    "GENERO": 12, "CANTIDAD DE PAQUETES": 16,
    "PROGRAMA POR EL QUE INGRESA": 30, "COMUNA": 14, "ESTADO": 10,
    "NOMBRE PUNTO": 40, "DIRECCION": 35, "REFERENTE": 30,
    "FECHA PROGRAMADA EN CONVOCATORIA": 22, "GRUPO": 8, "HORARIO": 10,
    "RESULTADO CONVOCATORIA": 22, "QUIEN SDM": 12, "RESPONSABLE": 25,
    "OTRO TELEFONO": 16, "FECHA ENTREGA": 14, "RESPONSABLE6": 25,
    "ANIO ENTREGA": 12, "MES ENTREGA": 12, "MES NOMBRE": 14,
    "DIA ENTREGA": 10, "ENTREGADO": 12,
}

EXCEL_DATE_BASE = pd.Timestamp("1899-12-30")


# ---------------------------------------------------------------------------
# Helpers de limpieza
# ---------------------------------------------------------------------------

def _norm_col(name: str) -> str:
    return str(name).strip().upper()


def clean_text_value(val):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return np.nan
    txt = unicodedata.normalize("NFC", str(val))
    txt = "".join(c for c in txt if unicodedata.category(c) not in ("Cc", "Cf"))
    txt = txt.upper()
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt if txt else np.nan


def clean_gender(val):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return np.nan
    key = re.sub(r"\s+", "", str(val).strip().upper())
    return GENDER_MAP.get(key, np.nan)


def clean_document(val):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return np.nan
    s = re.sub(r"\.0+$", "", str(val).strip())
    s = re.sub(r"[^\d]", "", s)
    return s if s else np.nan


def parse_date_value(val):
    if val is None:
        return pd.NaT
    if isinstance(val, float) and np.isnan(val):
        return pd.NaT
    if isinstance(val, (pd.Timestamp, datetime, date)):
        return pd.Timestamp(val)
    if isinstance(val, (int, float)):
        try:
            return EXCEL_DATE_BASE + pd.Timedelta(days=int(val))
        except Exception:
            return pd.NaT
    s = str(val).strip()
    if not s:
        return pd.NaT
    if re.match(r"^\d{5,6}$", s):
        n = int(s)
        if 36526 <= n <= 73050:
            return EXCEL_DATE_BASE + pd.Timedelta(days=n)
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y",
                "%Y/%m/%d", "%d.%m.%Y", "%Y-%m-%d %H:%M:%S"):
        try:
            return pd.Timestamp(datetime.strptime(s, fmt))
        except ValueError:
            pass
    try:
        return pd.Timestamp(pd.to_datetime(s, dayfirst=True, errors="raise"))
    except Exception:
        return pd.NaT


def clean_phone(val):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return np.nan
    s = re.sub(r"[^\d+]", "", str(val).strip())
    s = re.sub(r"^0+$", "", s)
    return s if s else np.nan


def clean_quantity(val):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return 0
    try:
        return max(int(float(str(val).strip())), 0)
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# Validación
# ---------------------------------------------------------------------------

class ValidationReport:
    """Acumula errores y advertencias durante el procesamiento."""

    def __init__(self):
        self.items: list[dict] = []

    def add(self, tipo: str, doc, campo: str, msg: str):
        self.items.append({"type": tipo, "doc": str(doc), "campo": campo, "msg": msg})

    def error(self, doc, campo: str, msg: str):
        self.add("error", doc, campo, msg)

    def warn(self, doc, campo: str, msg: str):
        self.add("warn", doc, campo, msg)

    def to_list(self) -> list[dict]:
        return self.items

    def count(self, tipo: str) -> int:
        return sum(1 for i in self.items if i["type"] == tipo)


def _validate_row(row: dict, report: ValidationReport):
    doc = row.get("DOCUMENTO", "?")

    if not doc or str(doc).strip() in ("", "nan", "NaN"):
        report.error(doc, "DOCUMENTO", "Documento vacío o inválido")

    nombre = row.get("NOMBRE_REPRESENTANTE")
    if not nombre or str(nombre).strip() in ("", "nan", "NaN"):
        report.error(doc, "NOMBRE_REPRESENTANTE", "Nombre vacío")

    genero = row.get("GENERO")
    if not genero or str(genero).strip() in ("", "nan", "NaN"):
        report.warn(doc, "GENERO", "Género vacío o no reconocido")

    fecha = row.get("FECHA ENTREGA")
    if fecha is None or (isinstance(fecha, float) and np.isnan(fecha)) or fecha == "":
        report.warn(doc, "FECHA ENTREGA", "Fecha de entrega vacía")

    cantidad = row.get("CANTIDAD DE PAQUETES", 0)
    try:
        if int(float(str(cantidad))) <= 0:
            report.warn(doc, "CANTIDAD DE PAQUETES", "Cantidad es 0")
    except Exception:
        report.warn(doc, "CANTIDAD DE PAQUETES", f"Cantidad no numérica: {cantidad}")


# ---------------------------------------------------------------------------
# Procesamiento principal (pandas puro)
# ---------------------------------------------------------------------------

def transform(df_raw: pd.DataFrame) -> tuple[pd.DataFrame, ValidationReport]:
    """
    Recibe el DataFrame crudo de extract.py,
    aplica todas las limpiezas y devuelve (df_limpio, report).
    """
    report = ValidationReport()
    df = df_raw.copy()

    # -- Eliminar columnas y filas completamente vacías
    df = df.dropna(axis=1, how="all")
    df = df.replace(r"^\s*$", np.nan, regex=True)

    # -- Mapear columnas al esquema esperado
    map_upper = {_norm_col(k): v for k, v in COLUMN_MAP.items()}
    col_mapping = {c: map_upper[_norm_col(c)] for c in df.columns if _norm_col(c) in map_upper}

    missing = [v for k, v in COLUMN_MAP.items()
               if _norm_col(k) not in {_norm_col(c) for c in df.columns}]
    if missing:
        report.warn("(archivo)", "COLUMNAS", "Columnas omitidas: " + ", ".join(missing))

    df = df[[c for c in df.columns if c in col_mapping]].rename(columns=col_mapping)
    df = df.dropna(how="all").reset_index(drop=True)

    # -- Filtrar filas sin documento
    df = df[df["DOCUMENTO"].notna()].reset_index(drop=True)
    df["DOCUMENTO"] = df["DOCUMENTO"].apply(clean_document)
    df = df[df["DOCUMENTO"].notna()].reset_index(drop=True)

    # -- Limpiar columnas de texto
    for col in TEXT_COLUMNS:
        if col in df.columns:
            df[col] = df[col].apply(clean_text_value)

    # -- Género
    if "GENERO" in df.columns:
        df["GENERO"] = df["GENERO"].apply(clean_gender)

    # -- Fechas
    for col in DATE_COLUMNS:
        if col in df.columns:
            df[col] = df[col].apply(parse_date_value)

    # -- Cantidad
    if "CANTIDAD DE PAQUETES" in df.columns:
        df["CANTIDAD DE PAQUETES"] = df["CANTIDAD DE PAQUETES"].apply(clean_quantity)

    # -- Teléfono
    if "OTRO TELEFONO" in df.columns:
        df["OTRO TELEFONO"] = df["OTRO TELEFONO"].apply(clean_phone)

    # -- Rellenar campos opcionales vacíos
    for col in FILL_WITH_SIN_DATO:
        if col in df.columns:
            df[col] = df[col].fillna("SIN DATO").replace("", "SIN DATO")

    # -- Columnas derivadas de fecha de entrega
    if "FECHA ENTREGA" in df.columns:
        df["ANIO ENTREGA"] = df["FECHA ENTREGA"].apply(
            lambda x: int(x.year) if pd.notna(x) else "")
        df["MES ENTREGA"] = df["FECHA ENTREGA"].apply(
            lambda x: int(x.month) if pd.notna(x) else "")
        df["MES NOMBRE"] = df["FECHA ENTREGA"].apply(
            lambda x: MONTH_NAMES.get(x.month, "") if pd.notna(x) else "")
        df["DIA ENTREGA"] = df["FECHA ENTREGA"].apply(
            lambda x: int(x.day) if pd.notna(x) else "")
        df["ENTREGADO"] = df["FECHA ENTREGA"].apply(
            lambda x: "SI" if pd.notna(x) else "NO")

    # -- Validar cada fila
    for _, row in df.iterrows():
        _validate_row(row.to_dict(), report)

    return df, report


# ---------------------------------------------------------------------------
# Formato Excel (openpyxl)
# ---------------------------------------------------------------------------

def apply_formatting(filepath: str):
    """Aplica estilos visuales al Excel consolidado ya guardado."""
    wb = load_workbook(filepath)
    ws = wb.active
    thin = Side(style="thin", color="BFBFBF")
    brd = Border(left=thin, right=thin, top=thin, bottom=thin)

    # Encabezado
    for cell in ws[1]:
        cell.font = Font(name="Arial", bold=True, color="FFFFFF", size=10)
        cell.fill = PatternFill("solid", fgColor="1F4E79")
        cell.border = brd
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[1].height = 35

    # Filas de datos con rayas alternas
    for idx, row in enumerate(ws.iter_rows(min_row=2), start=2):
        fill = PatternFill("solid", fgColor="D6E4F0" if idx % 2 == 0 else "FFFFFF")
        for cell in row:
            cell.font = Font(name="Arial", size=9)
            cell.fill = fill
            cell.border = brd
            cell.alignment = Alignment(vertical="center")

    # Anchos de columna
    for idx, cell in enumerate(ws[1], start=1):
        h = str(cell.value or "").strip()
        ws.column_dimensions[get_column_letter(idx)].width = COL_WIDTHS.get(h, 15)

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    wb.save(filepath)
