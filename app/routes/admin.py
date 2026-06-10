"""Admin routes — Dashboard e diagnosticos"""
from fastapi import APIRouter, Depends, HTTPException
from app.database import get_db, User, Production, Certificate
from app.routes.auth import get_current_user
from sqlalchemy.orm import Session

router = APIRouter()

def require_admin(user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")
    return user

@router.get("/dashboard")
async def dashboard(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    users_count = db.query(User).count()
    prods_count = db.query(Production).count()
    certs_count = db.query(Certificate).count()
    recent = db.query(Production).order_by(Production.created_at.desc()).limit(5).all()
    return {
        "users": users_count, "productions": prods_count, "certificates": certs_count,
        "recent": [{"id": p.id, "nome": p.nome, "estilo": p.estilo, "created_at": str(p.created_at)[:19]} for p in recent]
    }

@router.get("/diagnostic")
async def diagnostic(admin: User = Depends(require_admin)):
    import sys, subprocess, importlib
    deps = {}
    for mod in ["openai", "streamlit", "librosa", "mutagen", "pyloudnorm", "numpy", "soundfile", "demucs"]:
        try:
            importlib.import_module(mod)
            deps[mod] = "OK"
        except: deps[mod] = "MISSING"
    ffmpeg = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5).returncode == 0
    return {"python": sys.version, "dependencies": deps, "ffmpeg": ffmpeg, "deepseek_available": bool(admin.deepseek_key)}
