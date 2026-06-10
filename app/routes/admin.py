"""Admin routes — Dashboard, users, diagnosticos"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.database import get_db, User, Production, Certificate
from app.routes.auth import get_current_user
from sqlalchemy.orm import Session
from datetime import datetime

router = APIRouter()

def require_admin(user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")
    return user

class MessageRequest(BaseModel):
    user_id: int
    message: str

@router.get("/dashboard")
async def dashboard(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    users = db.query(User).all()
    users_data = [{"id": u.id, "email": u.email, "nome": u.nome, "role": u.role,
                   "login_count": u.login_count or 0,
                   "last_login": str(u.last_login)[:19] if u.last_login else "Nunca",
                   "is_active": u.is_active,
                   "has_deepseek": bool(u.deepseek_key),
                   "productions": db.query(Production).filter(Production.user_id == u.id).count()} for u in users]
    prods_count = db.query(Production).count()
    certs_count = db.query(Certificate).count()
    return {
        "users": len(users), "productions": prods_count, "certificates": certs_count,
        "users_list": users_data,
    }

@router.delete("/users/{user_id}")
async def delete_user(user_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Nao podes apagar a tua propria conta")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilizador nao encontrado")
    db.delete(user)
    db.commit()
    return {"status": "ok", "message": f"Utilizador {user.email} removido"}

@router.post("/message")
async def send_message(req: MessageRequest, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilizador nao encontrado")
    user.system_message = req.message
    db.commit()
    return {"status": "ok", "message": f"Mensagem enviada para {user.email}"}

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
