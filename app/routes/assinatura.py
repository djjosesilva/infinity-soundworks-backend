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
        # Assinatura local (ID3 + hash, sem dependencia de modules/)
        import hashlib, mutagen
        from mutagen.id3 import ID3, TIT2, TPE1, TXXX
        sha256 = hashlib.sha256(open(audio_path, 'rb').read()).hexdigest()
        track_id = f"EDJJS-{sha256[:12].upper()}"

        try:
            tags = ID3(audio_path)
        except Exception:
            tags = ID3()
        tags.add(TIT2(encoding=3, text=titulo))
        tags.add(TPE1(encoding=3, text=artista))
        tags.add(TXXX(encoding=3, desc='ESTUDIO', text='Estudio DJ Jose Silva'))
        tags.add(TXXX(encoding=3, desc='TRACK_ID', text=track_id))
        tags.add(TXXX(encoding=3, desc='HASH_SHA256', text=sha256))
        tags.save(audio_path, v2_version=4)

        cert = Certificate(user_id=user.id, production_id=0, track_id=track_id,
                          hash_sha256=sha256, titulo=titulo)
        db.add(cert)
        db.commit()

        return {"track_id": track_id, "hash_sha256": sha256,
                "camadas": {"id3": True, "watermark": False, "certificado": False}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])
    finally:
        try: os.unlink(audio_path)
        except: pass

@router.get("/certificates")
async def list_certificates(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    certs = db.query(Certificate).filter(Certificate.user_id == user.id).order_by(Certificate.created_at.desc()).all()
    return [{"id": c.id, "track_id": c.track_id, "hash_sha256": c.hash_sha256, "titulo": c.titulo, "created_at": str(c.created_at)[:19]} for c in certs]
