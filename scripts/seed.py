"""Load the CSVs into the database.

The CSVs are seed data, not the datastore. They describe the world as of
checkout; the moment POST /items runs, the database is the truth and these
files are only a starting point.

Usage: uv run python -m scripts.seed [--reset]
"""

import csv
import sys
from pathlib import Path

from sqlalchemy import delete, func, select

from app.db import Base, SessionLocal, engine
from app.models import Item, Site

DATA = Path(__file__).resolve().parent.parent / "data"


def seed(reset: bool = False) -> dict[str, int]:
    """Create tables, upsert sites, and load items.

    Idempotent: sites are matched on their code, and items are only loaded when
    the table is empty. `reset=True` clears items first, restoring the demo to
    its documented state.
    """
    Base.metadata.create_all(engine)

    with SessionLocal() as db:
        if reset:
            db.execute(delete(Item))
            db.flush()

        by_code: dict[str, Site] = {}
        with (DATA / "sites.csv").open() as fh:
            for row in csv.DictReader(fh):
                site = db.scalar(select(Site).where(Site.code == row["code"]))
                if site is None:
                    site = Site(**row)
                    db.add(site)
                by_code[row["code"]] = site
        db.flush()

        if not db.scalar(select(func.count()).select_from(Item)):
            with (DATA / "items.csv").open() as fh:
                for row in csv.DictReader(fh):
                    site = by_code[row.pop("site_code")]
                    db.add(Item(**row, site=site))

        db.commit()

        counts = {
            "sites": db.scalar(select(func.count()).select_from(Site)) or 0,
            "items": db.scalar(select(func.count()).select_from(Item)) or 0,
        }

    print(f"seeded: {counts['sites']} sites, {counts['items']} items")
    return counts


if __name__ == "__main__":
    seed(reset="--reset" in sys.argv)
