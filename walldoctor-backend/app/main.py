from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import Base, engine
from app.routers import auth, categories, services, providers, diagnosis, bookings

settings = get_settings()

# Creates tables if they don't exist yet. For real schema changes later,
# switch to Alembic migrations instead of relying on this.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="WallDoctor API",
    description="Backend for photo-based surface diagnosis, service catalog, providers, and bookings.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Ye line update ki gayi hai taaki frontend connect ho sake
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(categories.router)
app.include_router(services.router)
app.include_router(providers.router)
app.include_router(diagnosis.router)
app.include_router(bookings.router)


@app.get("/api/health")
def health_check():
    return {"status": "ok"}