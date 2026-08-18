import datetime
from pydantic import BaseModel, EmailStr, Field


# ---------- Auth ----------

class SignupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_name: str
    user_email: str


class UserOut(BaseModel):
    name: str
    email: str

    class Config:
        from_attributes = True


# ---------- Categories / Services ----------

class CategoryOut(BaseModel):
    key: str
    label_en: str
    label_hi: str

    class Config:
        from_attributes = True


class ServiceOut(BaseModel):
    id: str
    category_key: str
    name: str
    description: str
    price: int
    price_label: str
    tier: str
    rating: float
    reviews: int
    duration: str
    duration_label: str
    icon_svg: str

    class Config:
        from_attributes = True


# ---------- Providers ----------

class ProviderOut(BaseModel):
    id: str
    category_key: str
    name: str
    company: str
    area: str
    rating: float
    reviews: int
    experience_years: int
    phone_display: str
    phone_link: str
    whatsapp: str
    quoted_price: int | None = None  # filled in per-request based on category avg

    class Config:
        from_attributes = True


# ---------- Diagnosis ----------

class DiagnosisOut(BaseModel):
    id: str
    problem_detected: bool
    problem_type_en: str
    problem_type_hi: str
    surface_en: str
    surface_hi: str
    severity: int
    description_en: str
    description_hi: str
    likely_cause_en: str
    likely_cause_hi: str
    recommended_solution_en: str
    recommended_solution_hi: str
    service_category: str
    urgency_en: str
    urgency_hi: str
    source: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True


# ---------- Bookings ----------

class BookingCreate(BaseModel):
    provider_id: str
    service_category: str
    quoted_amount: int = Field(gt=0)
    payment_method: str = Field(pattern="^(card|upi|netbanking|cash)$")
    customer_name: str = Field(min_length=1, max_length=120)
    customer_phone: str = Field(min_length=6, max_length=40)


class BookingOut(BaseModel):
    id: str
    booking_ref: str
    provider_id: str
    service_category: str
    quoted_amount: int
    payment_method: str
    payment_status: str
    status: str
    customer_name: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True
