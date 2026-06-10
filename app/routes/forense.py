"""Forense routes — Analise de audio 3 niveis"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from app.database import get_db, User
from app.routes.auth import get_current_user
from app.demo import is_demo_mode, call_hf, DEMO_MODELS
from sqlalchemy.orm import Session
import tempfile, os, json as _json

router = APIRouter()

@router.post("/analyze")
async def forensic_analyze(
    file: UploadFile = File(...),
    nivel: int = Form(1),
    user: User = Depends(get_current_user),
):
    """Analise forense de audio."""
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp.write(await file.read())
        mp3_path = tmp.name

    try:
        # Analise local apenas (sem dependencia de modules/)
        import mutagen, librosa, numpy as np, json as _json
        from mutagen.mp3 import MP3
        info = MP3(mp3_path).info
        meta = {
            "filename": os.path.basename(mp3_path),
            "duration_seconds": round(info.length, 2),
            "bitrate": getattr(info, 'bitrate', 0),
            "sample_rate": info.sample_rate,
            "channels": info.channels,
        }

        if is_demo_mode(user.deepseek_key):
            return {"mode": "demo", "metadata": meta, "note": "DeepSeek nao configurado. Analise local apenas."}

        from openai import OpenAI
        client = OpenAI(api_key=user.deepseek_key, base_url="https://api.deepseek.com/v1")
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": "You are an audio forensic analyst. Analyze this audio metadata and return a detailed report in PT-PT as JSON."},
                       {"role": "user", "content": _json.dumps(meta, indent=2)}],
            max_tokens=2000, temperature=0.3,
            extra_body={"response_format": {"type": "json_object"}}
        )
        return {"mode": "pro", "metadata": meta, "analysis": resp.choices[0].message.content.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])
    finally:
        try: os.unlink(mp3_path)
        except: pass
