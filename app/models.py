from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Site(Base):
    __tablename__ = "sites"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    city: Mapped[str] = mapped_column(String(80))
    state: Mapped[str] = mapped_column(String(2))

    items: Mapped[list["Item"]] = relationship(back_populates="site")


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    model_number: Mapped[str] = mapped_column(String(64), index=True)
    type: Mapped[str] = mapped_column(String(48), index=True)
    # FKs are not auto-indexed in Postgres — index it explicitly.
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    site: Mapped[Site] = relationship(back_populates="items")
