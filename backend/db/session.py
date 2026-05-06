"""
db/session.py
-------------
Engine y SessionFactory de SQLAlchemy.
Importa get_session() para operaciones de BD.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import logging

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import settings

log = logging.getLogger(__name__)

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,       # verifica conexión antes de usarla
    pool_size=5,
    max_overflow=10,
    echo=False,               # True para ver SQL en consola (debug)
)

SessionFactory = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@contextmanager
def get_session() -> Session:
    """
    Context manager para sesiones de BD.

    Uso:
        with get_session() as session:
            session.add(obj)
    """
    session = SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
