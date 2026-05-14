import asyncio
from fastapi import APIRouter, HTTPException
from app.models.schemas import AnalyzeRequest
from app.services.llm_service import analyze_transcript

router = APIRouter(prefix="/api", tags=["analysis"])


@router.post("/analyze")
async def analyze_transcripts(request: AnalyzeRequest):
    if not request.api_key:
        raise HTTPException(status_code=400, detail="API key is required for LLM analysis")

    async def process_one(item):
        try:
            analysis = await analyze_transcript(
                transcript=item.transcript,
                api_key=request.api_key,
                prompt=request.prompt,
                model=request.model,
            )
            return {
                "filename": item.filename,
                "transcript": item.transcript,
                "analysis": analysis,
            }
        except Exception as e:
            return {
                "filename": item.filename,
                "transcript": item.transcript,
                "analysis": f"Error: {str(e)}",
            }

    results = await asyncio.gather(*[process_one(t) for t in request.transcripts])
    return {"results": list(results)}
