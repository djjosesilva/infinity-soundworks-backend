"""
Compose routes — ZACOR AI Pipeline + Alcateia
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.database import get_db, Production, User
from app.routes.auth import get_current_user
from app.demo import is_demo_mode, call_hf, DEMO_MODELS
from sqlalchemy.orm import Session
import json

router = APIRouter()


class ComposeRequest(BaseModel):
    tema: str
    estilo: str = "Fado + Deep House"
    bpm: int = 120
    key: str = "Cm"
    idioma: str = "PT-PT"
    referencias: list = []
    instrucoes_extra: dict = {}


class AlcateiaRequest(BaseModel):
    tema: str
    estilo: str = "Fado + Deep House"
    idioma: str = "PT-PT"


@router.post("/zacor")
async def compose_zacor(req: ComposeRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Executa o pipeline ZACOR AI (8 agentes)."""
    if is_demo_mode(user.deepseek_key):
        prompt = f"Compose a song in {req.idioma} about: {req.tema}. Style: {req.estilo}. BPM: {req.bpm}. Key: {req.key}. Write complete lyrics with [Intro][Verse][Chorus][Bridge][Outro] tags."
        response = call_hf(DEMO_MODELS["compose"], prompt, 2000, 0.8)

        production = Production(
            user_id=user.id, nome=req.tema[:40], conceito=req.tema,
            estilo=req.estilo, bpm=req.bpm, key=req.key,
            lyrics=response, suno_package=response,
        )
        db.add(production)
        db.commit()
        db.refresh(production)
        return {"mode": "demo", "production_id": production.id, "lyrics": response, "note": "Modo Demo — DeepSeek nao configurado. Qualidade limitada."}

    # Modo Pro — DeepSeek (API directa, sem dependencias externas)
    try:
        from openai import OpenAI
        client = OpenAI(api_key=user.deepseek_key, base_url="https://api.deepseek.com/v1")

        # Maestro
        sp_maestro = f"You are the MAESTRO. Plan a song in {req.idioma}. Style: {req.estilo}. BPM: {req.bpm}. Key: {req.key}. Use GMIV framework."
        leader_resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": sp_maestro}, {"role": "user", "content": f"Theme: {req.tema}"}],
            max_tokens=1000, temperature=0.5
        )
        leader = leader_resp.choices[0].message.content.strip()

        # Letrista
        sp_lyrics = f"You are a professional lyricist. Write complete lyrics in {req.idioma} with sections: [Intro][Verse 1][Pre-Chorus][Chorus][Verse 2][Chorus][Bridge][Outro][Fade Out]. 200-300 words. Include instrument tags [instrument: ...] [dynamics: ...]."
        lyricist_resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": sp_lyrics}, {"role": "user", "content": f"MAESTRO PLAN:\n{leader}\n\nWrite the complete lyrics in {req.idioma}."}],
            max_tokens=3000, temperature=0.92
        )
        lyricist = lyricist_resp.choices[0].message.content.strip()

        # Packager
        sp_pack = f"You are the FINAL SUNO PACKAGER v5.5. Create a complete Suno AI package. Include: === STYLE DESCRIPTION EN === (max 1000 chars), === LYRICS {req.idioma} ===, === EXCLUDE STYLE === (15+ terms)."
        pack_resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": sp_pack}, {"role": "user", "content": f"PLAN:\n{leader}\n\nLYRICS:\n{lyricist}\n\nCompile the Suno v5.5 package."}],
            max_tokens=3500, temperature=0.5
        )
        final_pack = pack_resp.choices[0].message.content.strip()

        production = Production(
            user_id=user.id, nome=req.tema[:40], conceito=req.tema,
            estilo=req.estilo, bpm=req.bpm, key=req.key,
            lyrics=lyricist, suno_package=final_pack,
            agent_outputs={"lider": leader, "letrista": lyricist, "packager": final_pack},
        )
        db.add(production)
        db.commit()
        db.refresh(production)
        return {"mode": "pro", "production_id": production.id, "lyrics": lyricist, "suno_package": final_pack}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro pipeline: {str(e)[:200]}")


@router.post("/alcateia")
async def alcateia(req: AlcateiaRequest, user: User = Depends(get_current_user)):
    """Gera com Alcateia 8 Mestres."""
    if is_demo_mode(user.deepseek_key):
        prompt = f"Generate a complete music composition for: {req.tema}. Style: {req.estilo}. Language: {req.idioma}. Include BPM, key, lyrics, hooks, arrangement."
        response = call_hf(DEMO_MODELS["compose"], prompt, 2000, 0.8)
        return {"mode": "demo", "output": response}

    try:
        from openai import OpenAI
        client = OpenAI(api_key=user.deepseek_key, base_url="https://api.deepseek.com/v1")
        prompt = f"Generate a complete music composition as JSON for theme '{req.tema}' in style '{req.estilo}' language '{req.idioma}'. Return JSON with: compositor(bpm,key,arco_emocional), letrista(tema,metrica,rima,letra_crua), hooks(primario,secundario), arranjador(letra_final with [Intro][Verse][Chorus] tags), revisor(style_of_music,exclude_style,aprovado)."
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": "You are a music composition AI. Return ONLY valid JSON."}, {"role": "user", "content": prompt}],
            max_tokens=3000, temperature=0.8,
            extra_body={"response_format": {"type": "json_object"}}
        )
        return {"mode": "pro", "output": resp.choices[0].message.content.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])
