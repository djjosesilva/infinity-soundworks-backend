"""Forense routes — Analise de audio 3 niveis"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from app.database import get_db, User
from app.routes.auth import get_current_user
from app.demo import is_demo_mode, call_hf, DEMO_MODELS
from sqlalchemy.orm import Session
import tempfile, os, json

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
        from modules.forense import build_forensic_json, call_forense, render_forensic_report

        meta_json = build_forensic_json(mp3_path, nivel=nivel)

        if is_demo_mode(user.deepseek_key):
            analysis = {"mode": "demo", "message": "DeepSeek nao configurado. Analise local apenas.", "metadata": meta_json}
        else:
            from openai import OpenAI
            client = OpenAI(api_key=user.deepseek_key, base_url="https://api.deepseek.com/v1")
            analysis = call_forense(meta_json, client, "deepseek-chat")
            analysis["mode"] = "pro"

        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])
    finally:
        try: os.unlink(mp3_path)
        except: pass
