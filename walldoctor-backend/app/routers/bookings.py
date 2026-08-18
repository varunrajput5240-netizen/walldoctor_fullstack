import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas, security
from app.database import get_db

router = APIRouter(prefix="/api/bookings", tags=["bookings"])


def _generate_ref() -> str:
    return "WD-" + secrets.token_hex(3).upper()


@router.post("", response_model=schemas.BookingOut)
def create_booking(
    payload: schemas.BookingCreate,
    db: Session = Depends(get_db),
    current_user: models.User | None = Depends(security.get_optional_user),
):
    provider = db.get(models.Provider, payload.provider_id)
    if not provider or not provider.active:
        raise HTTPException(status_code=404, detail="Provider not found.")

    # Cash payments settle in person; everything else is "pending" until a real
    # payment processor (see README) confirms it via webhook.
    payment_status = "cash_on_completion" if payload.payment_method == "cash" else "pending"

    booking = models.Booking(
        booking_ref=_generate_ref(),
        user_id=current_user.id if current_user else None,
        provider_id=provider.id,
        service_category=payload.service_category,
        quoted_amount=payload.quoted_amount,
        payment_method=payload.payment_method,
        payment_status=payment_status,
        customer_name=payload.customer_name,
        customer_phone=payload.customer_phone,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


@router.get("/mine", response_model=list[schemas.BookingOut])
def my_bookings(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    return (
        db.query(models.Booking)
        .filter(models.Booking.user_id == current_user.id)
        .order_by(models.Booking.created_at.desc())
        .all()
    )


@router.get("/{booking_ref}", response_model=schemas.BookingOut)
def get_booking(booking_ref: str, db: Session = Depends(get_db)):
    booking = db.query(models.Booking).filter(models.Booking.booking_ref == booking_ref).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")
    return booking
