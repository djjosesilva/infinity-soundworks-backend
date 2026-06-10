"""
Compose routes — ZACOR AI Pipeline + Alcateia
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.database import get_db, Production, User
from app.auth import get_current_user
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

    # Modo Pro — DeepSeek
    try:
        from modules.idiomas import get_prompts
        from openai import OpenAI
        client = OpenAI(api_key=user.deepseek_key, base_url="https://api.deepseek.com/v1")
        prompts = get_prompts(req.idioma)

        # Maestro
        sp = "You are the MAESTRO of MASTER STUDIO PT. Plan composition using GMIV framework."
        leader_resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": sp}, {"role": "user", "content": f"Tema: {req.tema}\nEstilo: {req.estilo}\nBPM: {req.bpm}\nKey: {req.key}"}],
            max_tokens=1000, temperature=0.5
        )
        leader = leader_resp.choices[0].message.content.strip()

        # Letrista
        lyricist_resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": prompts["letrista_base"]}, {"role": "user", "content": f"PLANO DO MAESTRO:\n{leader}\n\nEscreve a letra completa em {req.idioma}."}],
            max_tokens=3000, temperature=0.92
        )
        lyricist = lyricist_resp.choices[0].message.content.strip()

        # Packager (simplificado para API)
        pack_resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "system", "content": "You are the FINAL SUNO PACKAGER v5.5. Compile Style Description + Lyrics + Exclude Style."},
                       {"role": "user", "content": f"PLANO:\n{leader}\n\nLETRA:\n{lyricist}\n\nCompila pacote Suno v5.5."}],
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
        return {"mode": "pro", "production_id": production.id, "lyrics": lyricist, "suno_package": final_pack, "leader": leader}

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
        from modules.alcateia import gerar_com_alcateia, extrair_output
        from openai import OpenAI
        client = OpenAI(api_key=user.deepseek_key, base_url="https://api.deepseek.com/v1")
        resultado = gerar_com_alcateia(req.tema, req.estilo, client, "deepseek-chat", req.idioma)
        return {"mode": "pro", **resultado}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])
