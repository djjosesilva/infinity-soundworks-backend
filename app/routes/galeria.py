"""Galeria routes — CRUD de producoes"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.database import get_db, Production, User
from app.routes.auth import get_current_user
from sqlalchemy.orm import Session
from typing import Optional

router = APIRouter()

class ProductionUpdate(BaseModel):
    nome: Optional[str] = None
    lyrics: Optional[str] = None
    metadata_json: Optional[dict] = None

@router.get("/")
async def list_productions(user: User = Depends(get_current_user), db: Session = Depends(get_db), search: str = "", page: int = 1):
    query = db.query(Production).filter(Production.user_id == user.id)
    if search:
        query = query.filter(
            (Production.nome.ilike(f"%{search}%")) |
            (Production.conceito.ilike(f"%{search}%")) |
            (Production.estilo.ilike(f"%{search}%"))
        )
    total = query.count()
    productions = query.order_by(Production.created_at.desc()).offset((page - 1) * 20).limit(20).all()
    return {
        "total": total, "page": page, "pages": max(1, (total - 1) // 20 + 1),
        "productions": [
            {"id": p.id, "nome": p.nome, "estilo": p.estilo, "bpm": p.bpm, "key": p.key,
             "lyrics_preview": (p.lyrics or "")[:100], "created_at": str(p.created_at)[:19],
             "has_suno": bool(p.suno_package), "has_abc": bool(p.abc)} for p in productions
        ]
    }

@router.get("/{prod_id}")
async def get_production(prod_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    prod = db.query(Production).filter(Production.id == prod_id, Production.user_id == user.id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Producao nao encontrada")
    return {
        "id": prod.id, "nome": prod.nome, "conceito": prod.conceito,
        "estilo": prod.estilo, "bpm": prod.bpm, "key": prod.key,
        "lyrics": prod.lyrics, "suno_package": prod.suno_package,
        "abc": prod.abc, "critic": prod.critic, "negative": prod.negative,
        "metadata_json": prod.metadata_json, "agent_outputs": prod.agent_outputs,
        "created_at": str(prod.created_at)[:19]
    }

@router.put("/{prod_id}")
async def update_production(prod_id: int, update: ProductionUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    prod = db.query(Production).filter(Production.id == prod_id, Production.user_id == user.id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Producao nao encontrada")
    if update.nome is not None: prod.nome = update.nome
    if update.lyrics is not None: prod.lyrics = update.lyrics
    if update.metadata_json is not None: prod.metadata_json = update.metadata_json
    db.commit()
    return {"status": "ok"}

@router.delete("/{prod_id}")
async def delete_production(prod_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    prod = db.query(Production).filter(Production.id == prod_id, Production.user_id == user.id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Producao nao encontrada")
    db.delete(prod)
    db.commit()
    return {"status": "ok"}
