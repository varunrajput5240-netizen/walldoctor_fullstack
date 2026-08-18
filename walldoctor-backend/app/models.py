import datetime
import uuid

from sqlalchemy import String, Integer, Float, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return uuid.uuid4().hex[:12]


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

    diagnoses: Mapped[list["Diagnosis"]] = relationship(back_populates="user")
    bookings: Mapped[list["Booking"]] = relationship(back_populates="user")


class Category(Base):
    __tablename__ = "categories"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    label_en: Mapped[str] = mapped_column(String(120))
    label_hi: Mapped[str] = mapped_column(String(120))

    services: Mapped[list["Service"]] = relationship(back_populates="category")
    providers: Mapped[list["Provider"]] = relationship(back_populates="category")


class Service(Base):
    __tablename__ = "services"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    category_key: Mapped[str] = mapped_column(ForeignKey("categories.key"))
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text)
    price: Mapped[int] = mapped_column(Integer)
    price_label: Mapped[str] = mapped_column(String(40))
    tier: Mapped[str] = mapped_column(String(20))          # budget | mid | premium
    rating: Mapped[float] = mapped_column(Float, default=4.5)
    reviews: Mapped[int] = mapped_column(Integer, default=0)
    duration: Mapped[str] = mapped_column(String(20))       # same | short | long
    duration_label: Mapped[str] = mapped_column(String(40))
    icon_svg: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    category: Mapped["Category"] = relationship(back_populates="services")


class Provider(Base):
    __tablename__ = "providers"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    category_key: Mapped[str] = mapped_column(ForeignKey("categories.key"))
    name: Mapped[str] = mapped_column(String(120))
    company: Mapped[str] = mapped_column(String(160))
    area: Mapped[str] = mapped_column(String(120))
    rating: Mapped[float] = mapped_column(Float, default=4.5)
    reviews: Mapped[int] = mapped_column(Integer, default=0)
    experience_years: Mapped[int] = mapped_column(Integer, default=5)
    phone_display: Mapped[str] = mapped_column(String(40))
    phone_link: Mapped[str] = mapped_column(String(40))
    whatsapp: Mapped[str] = mapped_column(String(40))
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    category: Mapped["Category"] = relationship(back_populates="providers")


class Diagnosis(Base):
    __tablename__ = "diagnoses"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    problem_detected: Mapped[bool] = mapped_column(Boolean)
    problem_type_en: Mapped[str] = mapped_column(String(80))
    problem_type_hi: Mapped[str] = mapped_column(String(80))
    surface_en: Mapped[str] = mapped_column(String(40))
    surface_hi: Mapped[str] = mapped_column(String(40))
    severity: Mapped[int] = mapped_column(Integer)
    description_en: Mapped[str] = mapped_column(Text)
    description_hi: Mapped[str] = mapped_column(Text)
    likely_cause_en: Mapped[str] = mapped_column(Text)
    likely_cause_hi: Mapped[str] = mapped_column(Text)
    recommended_solution_en: Mapped[str] = mapped_column(Text)
    recommended_solution_hi: Mapped[str] = mapped_column(Text)
    service_category: Mapped[str] = mapped_column(String(64))
    urgency_en: Mapped[str] = mapped_column(String(20))
    urgency_hi: Mapped[str] = mapped_column(String(20))

    # "ai" = real Claude vision call succeeded. "fallback" = heuristic degraded mode.
    # This is surfaced to the frontend so it can be honest with the user about which one ran.
    source: Mapped[str] = mapped_column(String(20), default="ai")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

    user: Mapped["User | None"] = relationship(back_populates="diagnoses")


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    booking_ref: Mapped[str] = mapped_column(String(20), unique=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    provider_id: Mapped[str] = mapped_column(ForeignKey("providers.id"))
    service_category: Mapped[str] = mapped_column(String(64))
    quoted_amount: Mapped[int] = mapped_column(Integer)
    payment_method: Mapped[str] = mapped_column(String(20))   # card | upi | netbanking | cash
    payment_status: Mapped[str] = mapped_column(String(20), default="pending")
    status: Mapped[str] = mapped_column(String(20), default="confirmed")
    customer_name: Mapped[str] = mapped_column(String(120))
    customer_phone: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

    user: Mapped["User | None"] = relationship(back_populates="bookings")
    provider: Mapped["Provider"] = relationship()
