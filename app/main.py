import os
import json
from fastapi import FastAPI, HTTPException
from pydantic import ValidationError
from app.schemas import (
    UnderstandRequest, UnderstandResponse, PreferenceRequest, PreferenceResponse,
    PreferenceQuestion, PreferenceAnswers, GenerateShotsRequest, GenerateShotsResponse, ShotDetail, ModelSpec
)
from app import prompt_templates

try:
    import openai
except Exception:
    openai = None

app = FastAPI(title="Novel Understand & Preferences MVP")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEFAULT_MODEL = "gpt-4o-mini"


def call_openai_chat(system: str, user: str, model: str = DEFAULT_MODEL, temperature: float = 0.2, max_tokens: int = 1500):
    if openai is None:
        raise RuntimeError("openai package not installed or not importable")
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not set")
    openai.api_key = OPENAI_API_KEY
    resp = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content


@app.post("/understand", response_model=UnderstandResponse)
async def understand(req: UnderstandRequest):
    text = req.text
    model = req.model or DEFAULT_MODEL
    system = prompt_templates.SYSTEM_PROMPT_UNDERSTAND
    user = prompt_templates.USER_PROMPT_UNDERSTAND.format(novel_text=text)
    try:
        raw = call_openai_chat(system=system, user=user, model=model, max_tokens=2000)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    parsed = None
    try:
        parsed = json.loads(raw)
    except Exception:
        import re
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            try:
                parsed = json.loads(m.group(0))
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"LLM output not valid JSON: {e}\nRaw:\n{raw}")
        else:
            raise HTTPException(status_code=500, detail=f"LLM output not valid JSON and no JSON substring found. Raw:\n{raw}")
    try:
        # if main_characters include model_id, build character_models mapping
        char_models = {}
        for c in parsed.get('main_characters', []):
            if isinstance(c, dict) and c.get('model_id'):
                char_models[c.get('name')] = {
                    'model_id': c.get('model_id'),
                    'asset_reference': None,
                    'version': None,
                    'notes': 'inferred from main_characters.model_id'
                }
        if char_models:
            parsed['character_models'] = char_models
        parsed['raw'] = raw
        resp = UnderstandResponse(**parsed)
    except ValidationError as ve:
        raise HTTPException(status_code=500, detail=f"Response validation failed: {ve}\nRaw output:\n{raw}")
    return resp


@app.post("/preferences", response_model=PreferenceResponse)
async def preferences(req: PreferenceRequest):
    understanding = req.understanding
    system = prompt_templates.SYSTEM_PROMPT_PREFERENCES
    user = json.dumps(understanding.dict(), ensure_ascii=False)
    try:
        raw = call_openai_chat(system=system, user=user, max_tokens=800)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    try:
        parsed = json.loads(raw)
    except Exception:
        import re
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            try:
                parsed = json.loads(m.group(0))
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"LLM output not valid JSON: {e}\nRaw:\n{raw}")
        else:
            raise HTTPException(status_code=500, detail=f"LLM output not valid JSON and no JSON substring found. Raw:\n{raw}")
    # basic shaping
    questions = []
    for q in parsed.get('questions', []):
        questions.append(q)
    suggested = parsed.get('suggested_defaults')
    micro = parsed.get('micro_frame_examples')
    return PreferenceResponse(questions=questions, suggested_defaults=suggested, micro_frame_examples=micro, raw=raw)


@app.post("/generate_shots", response_model=GenerateShotsResponse)
async def generate_shots(req: GenerateShotsRequest):
    understanding = req.understanding
    answers = req.answers.answers
    # allow overrides: take character_models from request if provided, otherwise from understanding
    char_models = req.character_models or (understanding.character_models or {})
    # ensure character_models are serialized to simple dicts
    serializable_char_models = {}
    for k, v in (char_models.items() if isinstance(char_models, dict) else []):
        if isinstance(v, dict):
            serializable_char_models[k] = v
        else:
            # pydantic model
            try:
                serializable_char_models[k] = v.dict()
            except Exception:
                serializable_char_models[k] = {'model_id': str(v)}

    system = prompt_templates.SYSTEM_PROMPT_GENERATE_SHOTS
    payload = {
        "understanding": understanding.dict(),
        "answers": answers,
        "character_models": serializable_char_models
    }
    user = json.dumps(payload, ensure_ascii=False)
    try:
        raw = call_openai_chat(system=system, user=user, max_tokens=2000)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    try:
        parsed = json.loads(raw)
    except Exception:
        import re
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            try:
                parsed = json.loads(m.group(0))
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"LLM output not valid JSON: {e}\nRaw:\n{raw}")
        else:
            raise HTTPException(status_code=500, detail=f"LLM output not valid JSON and no JSON substring found. Raw:\n{raw}")
    shots = []
    for s in parsed.get('shots', []):
        shots.append(ShotDetail(**s))
    notes = parsed.get('notes')
    return GenerateShotsResponse(shots=shots, notes=notes, raw=raw)


@app.get("/health")
async def health():
    return {"status": "ok"}
