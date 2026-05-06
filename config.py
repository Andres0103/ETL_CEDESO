"""
config.py
---------
Carga centralizada de configuración desde variables de entorno / .env
Todos los módulos importan desde aquí — nunca hardcodean credenciales.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Carga el .env desde la raíz del proyecto
_ROOT = Path(__file__).parent
load_dotenv(_ROOT / ".env")


class Settings:
    # PostgreSQL
    POSTGRES_DB: str       = os.getenv("POSTGRES_DB", "raizal")
    POSTGRES_USER: str     = os.getenv("POSTGRES_USER", "raizal_user")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "")
    POSTGRES_HOST: str     = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: str     = os.getenv("POSTGRES_PORT", "5433")

    # SQLAlchemy URL completa
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
        f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}",
    )

    # Flask
    FLASK_HOST: str  = os.getenv("FLASK_HOST", "127.0.0.1")
    FLASK_PORT: int  = int(os.getenv("FLASK_PORT", "5000"))
    FLASK_DEBUG: bool = os.getenv("FLASK_DEBUG", "false").lower() == "true"

    # Directorio temporal para archivos en tránsito
    TMP_DIR: str = os.path.join(os.path.expanduser("~"), ".raizal_tmp")


settings = Settings()
