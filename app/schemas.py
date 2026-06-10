from pydantic import BaseModel
from typing import List, Optional, Any, Dict

class ModelSpec(BaseModel):
    model_id: str
    asset_reference: Optional[str] = None
    version: Optional[str] = None
    notes: Optional[str] = None

class UnderstandRequest(BaseModel):
    text: str
    model: Optional[str] = "gpt-4o-mini"

class Character(BaseModel):
    name: str
    role: Optional[str]
    personality_tags: List[str] = []
    visual_cues: List[str] = []
    # Optional fixed model assignment for this character
    model_id: Optional[str] = None

class KeyScene(BaseModel):
    id: int
    short_desc: str
    importance_rank: Optional[int]

class UnderstandResponse(BaseModel):
    summary: str
    genre: Optional[str]
    main_characters: List[Character]
    key_scenes: List[KeyScene]
    themes_and_moods: List[str]
    pacing: Optional[str]
    visual_keywords: List[str]
    recommended_duration_seconds: Optional[int]
    # A mapping from character name -> ModelSpec to enforce consistent modelling
    character_models: Optional[Dict[str, ModelSpec]] = None
    raw: Optional[Any]

# Preference questionnaire models
class PreferenceQuestion(BaseModel):
    id: str
    text: str
    type: str  # 'choice' | 'text' | 'upload' | 'number' | 'multi'
    options: Optional[List[str]] = None
    default: Optional[Any] = None

class PreferenceRequest(BaseModel):
    understanding: UnderstandResponse

class PreferenceResponse(BaseModel):
    questions: List[PreferenceQuestion]
    suggested_defaults: Optional[Dict[str, Any]] = None
    micro_frame_examples: Optional[List[str]] = None
    raw: Optional[Any] = None

# Customer answers
class PreferenceAnswers(BaseModel):
    # mapping question id -> answer
    answers: Dict[str, Any]

# Shot detail produced after finalization
class ShotDetail(BaseModel):
    id: int
    duration_seconds: float
    visual_description: str
    camera_move: Optional[str]
    expressions: Optional[List[str]]
    hand_actions: Optional[List[str]]
    modeling_instructions: Optional[str]
    music_cue: Optional[str]
    dialogue_or_voiceover: Optional[str]
    # explicitly include the model_id used for each character mentioned in this shot
    character_model_ids: Optional[Dict[str, str]] = None

class GenerateShotsRequest(BaseModel):
    understanding: UnderstandResponse
    answers: PreferenceAnswers
    # optional: allow the caller to provide or override character_models mapping
    character_models: Optional[Dict[str, ModelSpec]] = None

class GenerateShotsResponse(BaseModel):
    shots: List[ShotDetail]
    notes: Optional[str]
    raw: Optional[Any]
