"""Load the CSVs into the database.

The CSVs are seed data, not the datastore. They live in the repo because they
describe the world as of checkout; the moment POST /items runs, the database is
the truth and these files are only a starting point.

Usage: uv run python -m scripts.seed
"""

import csv
from pathlib import Path

from sqlalchemy import select

from app.db import Base, SessionLocal, engine
from app.models import Item, Site

DATA = Path(__file__).resolve().parent.parent / "data"


def seed() -> None:
    Base.metadata.create_all(engine)

    with SessionLocal() as db:
        by_code: dict[str, Site] = {}

        with (DATA / "sites.csv").open() as fh:
            for row in csv.DictReader(fh):
                site = db.scalar(select(Site).where(Site.code == row["code"]))
                if site is None:
                    site = Site(**row)
                    db.add(site)
                by_code[row["code"]] = site
        db.flush()

        existing = db.scalar(select(Site).join(Item).limit(1))
        if existing is None:
            with (DATA / "items.csv").open() as fh:
                for row in csv.DictReader(fh):
                    site = by_code[row.pop("site_code")]
                    db.add(Item(**row, site=site))

        db.commit()

        sites = db.scalar(select(Site.id).order_by(Site.id.desc()).limit(1)) or 0
        items = len(list(db.scalars(select(Item.id))))
        print(f"seeded: {len(by_code)} sites (max id {sites}), {items} items")


if __name__ == "__main__":
    seed()
