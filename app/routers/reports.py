from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Item, Site
from app.schemas import ItemsBySiteReport, SiteTypeCount

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/items-by-site", response_model=ItemsBySiteReport)
def items_by_site(db: Session = Depends(get_db)) -> ItemsBySiteReport:
    """Counts of items per site per type.

    One GROUP BY in the database rather than N queries from the caller — the
    aggregation belongs on the side of the wire that already has the data.
    """
    stmt = (
        select(Site.code, Site.name, Item.type, func.count(Item.id))
        .join(Item, Item.site_id == Site.id)
        .group_by(Site.code, Site.name, Item.type)
        .order_by(Site.code, Item.type)
    )
    rows = [
        SiteTypeCount(site_code=code, site_name=name, type=type_, count=count)
        for code, name, type_, count in db.execute(stmt)
    ]
    # as_of so consumers know how fresh this is — machine clients can't ask.
    return ItemsBySiteReport(generated_at=datetime.now(UTC), rows=rows)
