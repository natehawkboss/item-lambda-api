from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SiteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    city: str
    state: str


class ItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    model_number: str = Field(min_length=1, max_length=64)
    type: str = Field(min_length=1, max_length=48)
    site_id: int


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    model_number: str
    type: str
    site_id: int
    created_at: datetime


class Page(BaseModel):
    """Envelope so clients can page without guessing whether there's more."""

    total: int
    limit: int
    offset: int


class ItemPage(Page):
    results: list[ItemOut]


class SiteTypeCount(BaseModel):
    site_code: str
    site_name: str
    type: str
    count: int


class ItemsBySiteReport(BaseModel):
    generated_at: datetime
    rows: list[SiteTypeCount]
