"""Marketing routes — Geracao de material promocional"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.database import get_db, Production, User
from app.routes.auth import get_current_user
from app.demo import is_demo_mode, call_hf, DEMO_MODELS
from sqlalchemy.orm import Session

router = APIRouter()

class MarketingRequest(BaseModel):
    production_id: int

@router.post("/generate")
async def generate_marketing(req: MarketingRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Gera material de marketing a partir de uma producao."""
    prod = db.query(Production).filter(Production.id == req.production_id, Production.user_id == user.id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Producao nao encontrada")

    prompt = f"""Generate marketing material in PT-PT for this song:
Title: {prod.nome}
Style: {prod.estilo}
BPM: {prod.bpm} | Key: {prod.key}
Lyrics (excerpt): {(prod.lyrics or '')[:800]}

Generate:
1. 3 Instagram posts (2 sentences each, with emojis)
2. Artist bio (2 sentences)
3. Short press release (3 sentences)
Format with headers: === INSTAGRAM POSTS ===, === ARTIST BIO ===, === PRESS RELEASE ==="""

    if is_demo_mode(user.deepseek_key):
        response = call_hf(DEMO_MODELS["compose"], prompt, 600, 0.7)
        return {"mode": "demo", "content": response}

    from openai import OpenAI
    client = OpenAI(api_key=user.deepseek_key, base_url="https://api.deepseek.com/v1")
    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "system", "content": "You are a music marketing specialist. Reply in PT-PT."}, {"role": "user", "content": prompt}],
        max_tokens=800, temperature=0.7
    )
    return {"mode": "pro", "content": resp.choices[0].message.content.strip()}
