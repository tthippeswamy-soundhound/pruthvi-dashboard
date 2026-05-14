import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, Form, HTTPException
from app.config import UPLOAD_DIR, ALLOWED_EXTENSIONS, MAX_FILE_SIZE_MB
from app.services.whisper_service import transcribe_file

router = APIRouter(prefix="/api", tags=["transcription"])


@router.post("/transcribe")
async def transcribe_files(files: list[UploadFile], diarize: bool = Form(False)):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    results = []
    for file in files:
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            results.append({
                "filename": file.filename,
                "transcript": "",
                "error": f"Unsupported file type: {ext}",
            })
            continue

        # Save temporarily
        unique_name = f"{uuid.uuid4().hex}{ext}"
        file_path = UPLOAD_DIR / unique_name
        try:
            content = await file.read()
            if len(content) > MAX_FILE_SIZE_MB * 1024 * 1024:
                results.append({
                    "filename": file.filename,
                    "transcript": "",
                    "error": f"File exceeds {MAX_FILE_SIZE_MB}MB limit",
                })
                continue

            file_path.write_bytes(content)

            result = await transcribe_file(str(file_path), diarize=diarize)
            results.append({
                "filename": file.filename,
                "transcript": result["text"],
                "language": result["language"],
            })
        except Exception as e:
            results.append({
                "filename": file.filename,
                "transcript": "",
                "error": str(e),
            })
        finally:
            if file_path.exists():
                file_path.unlink()

    return {"results": results}
