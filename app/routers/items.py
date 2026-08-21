from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Item, Site
from app.schemas import ItemCreate, ItemOut, ItemPage
from app.security import require_api_key

router = APIRouter(prefix="/items", tags=["items"])


@router.get("", response_model=ItemPage)
def list_items(
    db: Session = Depends(get_db),
    site_id: int | None = None,
    type: str | None = None,
    q: str | None = Query(None, min_length=2, description="Substring match on name"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> ItemPage:
    stmt = select(Item)
    if site_id is not None:
        stmt = stmt.where(Item.site_id == site_id)
    if type is not None:
        stmt = stmt.where(Item.type == type)
    if q is not None:
        stmt = stmt.where(Item.name.ilike(f"%{q}%"))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(Item.id).limit(limit).offset(offset)).all()
    return ItemPage(total=total, limit=limit, offset=offset, results=list(rows))


@router.post(
    "",
    response_model=ItemOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_api_key)],
)
def create_item(payload: ItemCreate, db: Session = Depends(get_db)) -> Item:
    if db.get(Site, payload.site_id) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Unknown site_id")

    item = Item(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/{item_id}", response_model=ItemOut)
def get_item(item_id: int, db: Session = Depends(get_db)) -> Item:
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    return item
