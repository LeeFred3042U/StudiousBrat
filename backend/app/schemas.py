"""Pydantic schemas used to validate every tool's JSON response before it is
returned. A validation failure is a tool failure (one retry, then abort)."""
from pydantic import BaseModel, Field


class SubConcept(BaseModel):
    id: str
    label: str
    description: str


class SubConceptsResult(BaseModel):
    sub_concepts: list[SubConcept] = Field(..., min_length=3, max_length=5)
    has_sequence: bool


class MappingItem(BaseModel):
    sub_concept_id: str
    maps_to: str


class AnalogyResult(BaseModel):
    analogy_text: str
    mapping: list[MappingItem]


class Flashcard(BaseModel):
    question: str
    answer: str
    hint: str | None = None


class FlashcardsResult(BaseModel):
    cards: list[Flashcard] = Field(..., min_length=3, max_length=3)


class MermaidResult(BaseModel):
    mermaid_source: str


class Meme(BaseModel):
    caption: str
    punchline: str


class MemesResult(BaseModel):
    memes: list[Meme] = Field(..., min_length=2, max_length=4)


class EvaluateResult(BaseModel):
    covered: list[str]
    missing: list[str]
    relationship_correct: bool
    feedback: str
