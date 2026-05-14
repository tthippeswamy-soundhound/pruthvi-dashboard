from fastapi import APIRouter
from fastapi.responses import Response
from app.models.schemas import ExportRequest
from app.services.excel_service import create_excel

router = APIRouter(prefix="/api", tags=["export"])


@router.post("/export")
async def export_excel(request: ExportRequest):
    data = [item.model_dump() for item in request.results]
    excel_bytes = create_excel(data)
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=transcription_results.xlsx"},
    )
