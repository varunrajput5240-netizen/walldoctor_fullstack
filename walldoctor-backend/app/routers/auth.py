from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas, security
from app.database import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup", response_model=schemas.TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: schemas.SignupRequest, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    user = models.User(
        name=payload.name.strip(),
        email=payload.email.lower(),
        password_hash=security.hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = security.create_access_token(subject=user.id)
    return schemas.TokenResponse(access_token=token, user_name=user.name, user_email=user.email)


@router.post("/login", response_model=schemas.TokenResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email.lower()).first()
    # Deliberately identical error for "no such user" and "wrong password" — don't leak which one it was.
    if not user or not security.verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    token = security.create_access_token(subject=user.id)
    return schemas.TokenResponse(access_token=token, user_name=user.name, user_email=user.email)


@router.get("/me", response_model=schemas.UserOut)
def me(current_user: models.User = Depends(security.get_current_user)):
    return current_user
