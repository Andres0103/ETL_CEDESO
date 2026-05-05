"""
load.py
-------
Responsabilidad única: persistir el DataFrame consolidado
como archivo Excel en disco.

NO contiene lógica de negocio ni de formato visual
(eso está en transform.apply_formatting).
"""

import os
import pandas as pd


def save_excel(df: pd.DataFrame, file_path: str, sheet_name: str = "DATOS"):
    """
    Guarda el DataFrame en un archivo Excel.
    Crea el directorio de destino si no existe.
    """
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    df.to_excel(file_path, index=False, sheet_name=sheet_name)
