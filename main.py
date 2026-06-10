"""
INFINITY SOUNDWORKS v3.0 — Backend API
FastAPI + SQLite + JWT + HuggingFace Demo Mode
"""
import os
import sys
from pathlib import Path

# Add parent modules to path
BASE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE))

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.database import engine, Base
from app.routes import auth, compose, forense, beatriz, galeria, assinatura, admin, marketing
from app.database import SessionLocal, User
import hashlib

# Auto-seed admin user on startup
def seed_admin():
    db = SessionLocal()
    try:
        admin_email = "oficialdjjosesilva@gmail.com"
        existing = db.query(User).filter(User.email == admin_email).first()
        if not existing:
            salt = os.getenv("PASSWORD_SALT", "infinity-soundworks-salt")
            user = User(
                email=admin_email,
                password_hash=hashlib.sha256(f"{salt}admin123".encode()).hexdigest(),
                nome="DJ Jose Silva",
                role="admin",
            )
            db.add(user)
            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_admin()
    yield


app = FastAPI(
    title="INFINITY SOUNDWORKS API v3.0",
    description="Estudio de Producao Musical — DJ Jose Silva",
    version="3.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(compose.router, prefix="/api/compose", tags=["Compose"])
app.include_router(forense.router, prefix="/api/forense", tags=["Forense"])
app.include_router(beatriz.router, prefix="/api/beatriz", tags=["Beatriz"])
app.include_router(galeria.router, prefix="/api/galeria", tags=["Galeria"])
app.include_router(assinatura.router, prefix="/api/assinatura", tags=["Assinatura"])
app.include_router(marketing.router, prefix="/api/marketing", tags=["Marketing"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])

# No static files needed
# app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "3.0.0", "name": "INFINITY SOUNDWORKS"}


@app.get("/api/system/info")
async def system_info():
    return {
        "python": sys.version,
        "deepseek_available": os.getenv("DEEPSEEK_API_KEY") is not None,
        "ffmpeg_available": os.system("ffmpeg -version >nul 2>&1") == 0,
        "demo_mode": os.getenv("DEMO_MODE", "true").lower() == "true",
    }
