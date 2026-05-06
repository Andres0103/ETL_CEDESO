"""
spark_ops.py
------------
Responsabilidad única: operaciones que se benefician de Spark.
Actualmente: deduplicación entre múltiples DataFrames consolidados.

Spark se inicializa SOLO cuando este módulo se llama,
no al arrancar la app. Si Spark no está disponible,
el pipeline cae back a pandas de forma transparente.
"""

import logging

import pandas as pd

log = logging.getLogger(__name__)

import os
_spark = None  # instancia singleton, lazy

# Forzar Python 3.11 para workers de Spark
_py311 = r"C:\Users\Administrador\AppData\Local\Programs\Python\Python311\python.exe"
if os.path.exists(_py311):
    os.environ["PYSPARK_PYTHON"] = _py311
    os.environ["PYSPARK_DRIVER_PYTHON"] = _py311


def _get_spark():
    """
    Inicializa SparkSession solo la primera vez que se necesita.
    Lanza ImportError si pyspark no está instalado.
    """
    global _spark
    if _spark is None:
        from pyspark.sql import SparkSession
        _spark = (
            SparkSession.builder
            .appName("raizal_etl")
            .config("spark.sql.shuffle.partitions", "4")   # adecuado para volúmenes pequeños
            .config("spark.driver.memory", "2g")
            .getOrCreate()
        )
        _spark.sparkContext.setLogLevel("WARN")
        log.info("SparkSession iniciada correctamente.")
    return _spark


def deduplicate(df: pd.DataFrame, key_col: str = "DOCUMENTO") -> pd.DataFrame:
    """
    Elimina duplicados en el DataFrame consolidado usando Spark.
    Conserva la primera ocurrencia por key_col.

    Si pyspark no está disponible cae back a pandas.
    """
    try:
        spark = _get_spark()

        # Spark no maneja bien tipos mixtos: convertir todo a str primero
        df_str = df.copy()
        for col in df_str.columns:
            df_str[col] = df_str[col].astype(str).replace("NaT", "").replace("nan", "")

        spark_df = spark.createDataFrame(df_str)

        # dropDuplicates mantiene la primera aparición por orden del DataFrame
        spark_df = spark_df.dropDuplicates([key_col])

        result = spark_df.toPandas()
        log.info("Deduplicación con Spark: %d → %d filas", len(df), len(result))
        return result

    except ImportError:
        log.warning("pyspark no disponible, usando pandas para deduplicación.")
        return _deduplicate_pandas(df, key_col)

    except Exception as exc:
        log.error("Error en Spark (%s), fallback a pandas.", exc)
        return _deduplicate_pandas(df, key_col)


def _deduplicate_pandas(df: pd.DataFrame, key_col: str) -> pd.DataFrame:
    """Fallback: deduplicación pandas cuando Spark no está disponible."""
    before = len(df)
    result = df.drop_duplicates(subset=[key_col], keep="first").reset_index(drop=True)
    log.info("Deduplicación con pandas: %d → %d filas", before, len(result))
    return result
