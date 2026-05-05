"""
extract.py
----------
Responsabilidad única: leer bytes de un archivo Excel
y devolver un DataFrame pandas crudo, sin transformar.
"""

import io
import pandas as pd


def find_header_row(file_bytes: bytes) -> int:
    """
    Busca la fila que contiene los encabezados esperados
    dentro de las primeras 15 filas del archivo.
    """
    df = pd.read_excel(io.BytesIO(file_bytes), header=None, nrows=15)
    for i, row in df.iterrows():
        vals = [str(v).strip().upper() for v in row.dropna().values]
        if "DOCUMENTO" in vals and "NOMBRE_REPRESENTANTE" in vals:
            return i
    raise ValueError(
        "No se encontraron encabezados DOCUMENTO / NOMBRE_REPRESENTANTE "
        "en las primeras 15 filas del archivo."
    )


def extract_excel(file_bytes: bytes) -> pd.DataFrame:
    """
    Lee el archivo Excel desde bytes y devuelve un DataFrame crudo.
    Detecta automáticamente la fila de encabezado.
    """
    header_row = find_header_row(file_bytes)
    df = pd.read_excel(io.BytesIO(file_bytes), header=header_row, dtype=str)
    df.columns = [str(c).strip() for c in df.columns]
    return df
