from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from .config import settings

Base = declarative_base()
engine = None
SessionLocal = None


def init_db():
    global engine, SessionLocal
    settings.ensure_dirs()
    kwargs = {}
    if settings.db_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    engine = create_engine(settings.db_url, **kwargs)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    from . import models  # noqa: 确保表模型已注册

    Base.metadata.create_all(bind=engine)
    return engine


def get_db():
    if SessionLocal is None:
        init_db()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
