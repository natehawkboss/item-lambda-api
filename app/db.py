from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

_is_sqlite = settings.database_url.startswith("sqlite")

# SQLite is a local-development convenience, never a deployment target. It
# writes to the disk of whatever machine is running the app, so replacing that
# machine — or running a second copy — loses data. Refuse to start rather than
# discover that in production.
if _is_sqlite and settings.environment != "local":
    raise RuntimeError(
        f"DATABASE_URL is SQLite but ENVIRONMENT={settings.environment!r}. "
        "SQLite writes to this container's own disk, so the data disappears "
        "when the container does. Point DATABASE_URL at a managed Postgres."
    )

# check_same_thread is a SQLite-only quirk.
connect_args = {"check_same_thread": False} if _is_sqlite else {}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    # echo prints SQL *including parameter values* — never on in production.
    echo=settings.debug,
    # Ignored by SQLite; these are the knobs that matter against Postgres.
    # pool_size * workers * tasks must stay under the server's max_connections.
    **({} if _is_sqlite else {"pool_size": 5, "max_overflow": 5, "pool_pre_ping": True}),
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
