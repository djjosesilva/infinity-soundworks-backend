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
        client = OpenAI(api_key=user.deepseek_key, base_url="https://api.deepseek.com/v1")
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": "You are Beatriz, a musical psychology assistant. Analyze lyrics emotionally. Return JSON with: emocao_primaria, valencia (-1 to +1), ativacao (-1 to +1), palavras_chave, sugestoes, gems_cluster."},
                       {"role": "user", "content": req.letra[:3000] if req.letra else req.message}],
            max_tokens=800, temperature=0.7,
            extra_body={"response_format": {"type": "json_object"}}
        )
        return {"mode": "pro", "response": resp.choices[0].message.content.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])

@router.post("/trends")
async def beatriz_trends(req: BeatrizTrendsRequest, user: User = Depends(get_current_user)):
    """Tendencias de mercado."""
    try:
        from app.demo import call_hf, DEMO_MODELS
        tendencias = {"termos_relacionados": [], "temas_populares": [], "emocoes_trending": []}

        if is_demo_mode(user.deepseek_key):
            return {"mode": "demo", "tendencias": tendencias, "sugestoes": "Modo Demo — DeepSeek nao configurado."}

        from openai import OpenAI
        client = OpenAI(api_key=user.deepseek_key, base_url="https://api.deepseek.com/v1")
        sugestoes = call_hf(DEMO_MODELS["chat"], f"Market trends for genre: {req.genero} in region {req.regiao}", 500)
        return {"mode": "pro", "tendencias": tendencias, "sugestoes": sugestoes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])
