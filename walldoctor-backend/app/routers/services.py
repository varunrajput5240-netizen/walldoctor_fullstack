from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/api/services", tags=["services"])

SortOption = Literal["recommended", "price_low", "price_high", "rating", "fastest"]
_DURATION_ORDER = {"same": 0, "short": 1, "long": 2}


@router.get("", response_model=list[schemas.ServiceOut])
def list_services(
    db: Session = Depends(get_db),
    category: str | None = Query(default=None, description="Category key, or omit for all"),
    budget: str | None = Query(default=None, pattern="^(budget|mid|premium)$"),
    min_rating: float = Query(default=0, ge=0, le=5),
    duration: str | None = Query(default=None, pattern="^(same|short|long)$"),
    sort: SortOption = "recommended",
):
    q = db.query(models.Service).filter(models.Service.active.is_(True))
    if category:
        q = q.filter(models.Service.category_key == category)
    if budget:
        q = q.filter(models.Service.tier == budget)
    if min_rating:
        q = q.filter(models.Service.rating >= min_rating)
    if duration:
        q = q.filter(models.Service.duration == duration)

    results = q.all()

    if sort == "price_low":
        results.sort(key=lambda s: s.price)
    elif sort == "price_high":
        results.sort(key=lambda s: -s.price)
    elif sort == "rating":
        results.sort(key=lambda s: -s.rating)
    elif sort == "fastest":
        results.sort(key=lambda s: _DURATION_ORDER.get(s.duration, 99))
    # "recommended" keeps natural DB order

    return results
