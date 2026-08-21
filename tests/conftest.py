import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import Item, Site


@pytest.fixture()
def db_session():
    """In-memory SQLite, fresh per test. StaticPool keeps every connection on
    the same in-memory database."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    with Session() as session:
        site = Site(code="TST-01", name="Test Solar", city="Testville", state="FL")
        session.add(site)
        session.flush()
        session.add_all(
            [
                Item(name="Inverter 1", model_number="INV-1", type="inverter", site_id=site.id),
                Item(name="Inverter 2", model_number="INV-2", type="inverter", site_id=site.id),
                Item(name="Meter 1", model_number="MTR-1", type="meter", site_id=site.id),
            ]
        )
        session.commit()
        yield session

    engine.dispose()


@pytest.fixture()
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
