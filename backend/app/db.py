from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True, pool_size=5, max_overflow=5)
analytics_engine = create_engine(
    settings.analytics_database_url, pool_pre_ping=True, pool_size=3, max_overflow=2
)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def get_session():
    with Session(engine) as session:
        yield session
