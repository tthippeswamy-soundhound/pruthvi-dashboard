from __future__ import annotations

from pydantic import BaseModel


class TranscriptItem(BaseModel):
    filename: str
    transcript: str


class AnalyzeRequest(BaseModel):
    transcripts: list[TranscriptItem]
    api_key: str
    prompt: str | None = None
    model: str = "gpt-4o-mini"


class AnalysisResult(BaseModel):
    filename: str
    transcript: str
    analysis: str


class ExportItem(BaseModel):
    filename: str
    transcript: str
    analysis: str = ""


class ExportRequest(BaseModel):
    results: list[ExportItem]
