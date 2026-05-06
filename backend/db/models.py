"""
db/models.py
------------
Modelos ORM — definen el esquema de la base de datos.
Alembic lee estos modelos para generar migraciones automáticamente.
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger, Boolean, Column, Date, DateTime,
    Integer, Numeric, String, Text, UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class PaqueteAlimentario(Base):
    """
    Tabla principal. Acumula historial mes a mes.
    La combinación (documento, fecha_entrega) es única
    para evitar duplicados entre cargas.
    """
    __tablename__ = "paquetes_alimentarios"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Identificación
    documento            = Column(String(20),  nullable=False, index=True)
    autorizacion         = Column(String(50),  nullable=True)
    nombre_representante = Column(String(200), nullable=False)
    genero               = Column(String(20),  nullable=True)

    # Paquete
    cantidad_paquetes    = Column(Integer, nullable=True, default=0)
    programa             = Column(String(200), nullable=True)

    # Ubicación
    comuna               = Column(String(100), nullable=True)
    estado               = Column(String(50),  nullable=True)
    nombre_punto         = Column(String(200), nullable=True)
    direccion            = Column(Text,        nullable=True)
    referente            = Column(String(200), nullable=True)

    # Fechas
    fecha_programada     = Column(Date, nullable=True)
    fecha_entrega        = Column(Date, nullable=True, index=True)

    # Logística
    grupo                = Column(String(50),  nullable=True)
    horario              = Column(String(100), nullable=True)
    resultado_convocatoria = Column(String(100), nullable=True)
    quien_sdm            = Column(String(100), nullable=True)
    responsable          = Column(String(200), nullable=True)
    otro_telefono        = Column(String(30),  nullable=True)
    responsable6         = Column(String(200), nullable=True)

    # Columnas derivadas (calculadas en ETL)
    anio_entrega         = Column(Integer, nullable=True)
    mes_entrega          = Column(Integer, nullable=True)
    mes_nombre           = Column(String(20), nullable=True)
    dia_entrega          = Column(Integer, nullable=True)
    entregado            = Column(Boolean, nullable=True, default=False)

    # Auditoría
    cargado_en           = Column(DateTime, server_default=func.now(), nullable=False)
    archivo_origen       = Column(String(255), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "documento", "fecha_entrega",
            name="uq_documento_fecha_entrega"
        ),
    )

    def __repr__(self):
        return (
            f"<PaqueteAlimentario doc={self.documento} "
            f"fecha={self.fecha_entrega}>"
        )


class CargaETL(Base):
    """
    Registro de auditoría de cada ejecución del pipeline.
    Permite saber cuándo se cargó qué, cuántos registros, etc.
    """
    __tablename__ = "cargas_etl"

    id               = Column(BigInteger, primary_key=True, autoincrement=True)
    fecha_carga      = Column(DateTime, server_default=func.now(), nullable=False)
    mes              = Column(String(2),  nullable=False)
    anio             = Column(String(4),  nullable=False)
    archivos         = Column(Text,       nullable=True)   # JSON con nombres
    total_registros  = Column(Integer,    nullable=True)
    registros_nuevos = Column(Integer,    nullable=True)
    registros_dup    = Column(Integer,    nullable=True)
    errores          = Column(Integer,    nullable=True, default=0)
    advertencias     = Column(Integer,    nullable=True, default=0)
    estado           = Column(String(20), nullable=False, default="ok")
    detalle          = Column(Text,       nullable=True)
