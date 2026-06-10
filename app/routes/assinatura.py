"""Assinatura routes — Assinatura Digital 3 camadas"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from app.database import get_db, User, Certificate
from app.routes.auth import get_current_user
from sqlalchemy.orm import Session
import tempfile, os

router = APIRouter()

@router.post("/sign")
async def sign_audio(
    file: UploadFile = File(...),
    titulo: str = Form(...),
    artista: str = Form("DJ Jose Silva"),
    genero: str = Form(""),
    ano: int = Form(2026),
    autor_letra: str = Form("DJ Jose Silva"),
    autor_instrumental: str = Form("DJ Jose Silva"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Assina audio com 3 camadas."""
    ext = os.path.splitext(file.filename)[1] or ".mp3"
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(await file.read())
        audio_path = tmp.name

    try:
        from modules.assinar_pipeline import assinar_musica_completa
        meta = {"titulo": titulo, "artista": artista, "genero": genero, "ano": ano,
                "autor_letra": autor_letra, "autor_instrumental": autor_instrumental,
                "produtor": "Estudio DJ Jose Silva", "licenca": "Todos os direitos reservados"}
        result = assinar_musica_completa(audio_path, meta)

        cert = Certificate(user_id=user.id, production_id=0, track_id=result["track_id"],
                          hash_sha256=result["hash_sha256"], titulo=titulo,
                          file_path=result["ficheiro_assinado"])
        db.add(cert)
        db.commit()

        # Read signed file for download
        with open(result["ficheiro_assinado"], "rb") as f:
            signed_bytes = f.read()

        return {"track_id": result["track_id"], "hash_sha256": result["hash_sha256"],
                "camadas": result["camadas"], "file_size": len(signed_bytes)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])
    finally:
        try: os.unlink(audio_path)
        except: pass

@router.get("/certificates")
async def list_certificates(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    certs = db.query(Certificate).filter(Certificate.user_id == user.id).order_by(Certificate.created_at.desc()).all()
    return [{"id": c.id, "track_id": c.track_id, "hash_sha256": c.hash_sha256, "titulo": c.titulo, "created_at": str(c.created_at)[:19]} for c in certs]
