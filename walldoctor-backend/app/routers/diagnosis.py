from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app import models, schemas, security
from app.database import get_db
from app.diagnosis_engine import diagnose

router = APIRouter(prefix="/api/diagnosis", tags=["diagnosis"])

MAX_IMAGE_BYTES = 8 * 1024 * 1024  # 8 MB


@router.post("", response_model=schemas.DiagnosisOut)
async def create_diagnosis(
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User | None = Depends(security.get_optional_user),
):
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file must be an image.")

    image_bytes = await image.read()
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image is too large (max 8MB).")

    result, source = await diagnose(image_bytes)

    record = models.Diagnosis(
        user_id=current_user.id if current_user else None,
        source=source,
        **result,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/mine", response_model=list[schemas.DiagnosisOut])
def my_diagnoses(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    return (
        db.query(models.Diagnosis)
        .filter(models.Diagnosis.user_id == current_user.id)
        .order_by(models.Diagnosis.created_at.desc())
        .all()
    )
