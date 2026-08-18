import hashlib

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/api/providers", tags=["providers"])


def _quote_for(provider: models.Provider, avg_price: float) -> int:
    """Deterministic, stable per-provider quote around the category average price."""
    digest = hashlib.sha256(provider.id.encode()).hexdigest()
    variance = ((int(digest[:2], 16) % 5) - 2) * 0.04  # -8% .. +8%, steps of 4%
    return round((avg_price * (1 + variance)) / 5) * 5


@router.get("", response_model=list[schemas.ProviderOut])
def list_providers(category: str, db: Session = Depends(get_db)):
    providers = (
        db.query(models.Provider)
        .filter(models.Provider.category_key == category, models.Provider.active.is_(True))
        .order_by(models.Provider.rating.desc())
        .all()
    )
    services_in_cat = db.query(models.Service).filter(models.Service.category_key == category).all()
    avg_price = (sum(s.price for s in services_in_cat) / len(services_in_cat)) if services_in_cat else 100

    out = []
    for p in providers:
        item = schemas.ProviderOut.model_validate(p)
        item.quoted_price = _quote_for(p, avg_price)
        out.append(item)
    return out


@router.get("/{provider_id}", response_model=schemas.ProviderOut)
def get_provider(provider_id: str, db: Session = Depends(get_db)):
    provider = db.get(models.Provider, provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found.")
    return provider
