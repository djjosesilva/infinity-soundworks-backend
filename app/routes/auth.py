"""
Auth routes — Login, Register, JWT
"""
import os
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
import jwt

from app.database import get_db, User

router = APIRouter()
security = HTTPBearer()
JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_hex(32))
JWT_ALGORITHM = "HS256"
JWT_EXPIRY = timedelta(days=30)


class RegisterRequest(BaseModel):
    email: str
    password: str
    nome: str = "DJ Jose Silva"


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class APIKeySetRequest(BaseModel):
    deepseek_key: str


def hash_password(password: str) -> str:
    salt = os.getenv("PASSWORD_SALT", "infinity-soundworks-salt")
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()


def create_jwt(user_id: int, email: str, role: str) -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + JWT_EXPIRY,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = int(payload["sub"])
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="Utilizador invalido")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except Exception:
        raise HTTPException(status_code=401, detail="Token invalido")


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email ja registado")
    user = User(
        email=req.email,
        password_hash=hash_password(req.password),
        nome=req.nome,
        role="admin" if req.email == "oficialdjjosesilva@gmail.com" else "user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_jwt(user.id, user.email, user.role)
    return TokenResponse(access_token=token, user={"id": user.id, "email": user.email, "nome": user.nome, "role": user.role})


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or user.password_hash != hash_password(req.password):
        raise HTTPException(status_code=401, detail="Credenciais invalidas")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Conta desactivada")
    token = create_jwt(user.id, user.email, user.role)
    return TokenResponse(access_token=token, user={"id": user.id, "email": user.email, "nome": user.nome, "role": user.role})


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email, "nome": user.nome, "role": user.role, "has_deepseek": bool(user.deepseek_key)}


@router.post("/me/api-key")
async def set_api_key(req: APIKeySetRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user.deepseek_key = req.deepseek_key
    db.commit()
    return {"status": "ok", "message": "DeepSeek API Key guardada"}


@router.get("/demo/status")
async def demo_status(user: User = Depends(get_current_user)):
    if user.deepseek_key:
        return {"mode": "pro", "deepseek_active": True, "message": "Todos os modulos activos"}
    return {"mode": "demo", "deepseek_active": False, "message": "Modo Demo — HuggingFace gratuito. Qualidade limitada. Adiciona DeepSeek API Key para acesso completo."}
