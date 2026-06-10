"""Beatriz routes — Psicologia Musical v2.0"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.database import get_db, User
from app.routes.auth import get_current_user
from app.demo import is_demo_mode, call_hf, DEMO_MODELS
from sqlalchemy.orm import Session

router = APIRouter()

class BeatrizChatRequest(BaseModel):
    message: str
    letra: str = ""
    idioma: str = "PT-PT"

class BeatrizTrendsRequest(BaseModel):
    genero: str
    regiao: str = "PT"

@router.post("/chat")
async def beatriz_chat(req: BeatrizChatRequest, user: User = Depends(get_current_user)):
    """Chat com a Beatriz (psicologia musical)."""
    if is_demo_mode(user.deepseek_key):
        prompt = f"You are Beatriz, a musical psychology assistant. Reply in {req.idioma}. User message: {req.message}"
        if req.letra:
            prompt += f"\nLyrics to analyze:\n{req.letra[:2000]}"
        response = call_hf(DEMO_MODELS["chat"], prompt, 800, 0.7)
        return {"mode": "demo", "response": response}

    try:
        from openai import OpenAI
        from modules.beatriz import analisar_emocao, fsm_start, fsm_process
        client = OpenAI(api_key=user.deepseek_key, base_url="https://api.deepseek.com/v1")

        if req.letra and not req.message:
            ana = analisar_emocao(req.letra, client, "deepseek-chat")
            return {"mode": "pro", "type": "analysis", "data": ana}

        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are Beatriz, musical psychology assistant. Reply in PT-PT."},
                {"role": "user", "content": req.message}
            ],
            max_tokens=800, temperature=0.7
        )
        return {"mode": "pro", "response": resp.choices[0].message.content.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])

@router.post("/trends")
async def beatriz_trends(req: BeatrizTrendsRequest, user: User = Depends(get_current_user)):
    """Tendencias de mercado."""
    try:
        from modules.beatriz import get_tendencias_genero, gerar_sugestoes_tendencias
        tendencias = get_tendencias_genero(req.genero, req.regiao)

        if is_demo_mode(user.deepseek_key):
            return {"mode": "demo", "tendencias": tendencias, "sugestoes": "Modo Demo — DeepSeek nao configurado."}

        from openai import OpenAI
        client = OpenAI(api_key=user.deepseek_key, base_url="https://api.deepseek.com/v1")
        sugestoes = gerar_sugestoes_tendencias(req.genero, tendencias, client, "deepseek-chat")
        return {"mode": "pro", "tendencias": tendencias, "sugestoes": sugestoes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])
