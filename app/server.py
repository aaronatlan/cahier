"""Serveur FastAPI local : enregistrement, transcription, bibliothèque de cours, slides."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import slides as slides_module
from . import storage
from . import subjects as subjects_module
from . import transcriber
from .recorder import recorder

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Cahier")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

_current_course_id: Optional[str] = None


@app.on_event("startup")
def _on_startup() -> None:
    storage.migrate_legacy()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


# --- Enregistrement --------------------------------------------------------


@app.get("/api/subjects")
def get_subjects() -> list[dict]:
    return subjects_module.SUBJECTS


@app.get("/api/record/status")
def record_status() -> dict:
    return {"recording": recorder.is_recording, "id": _current_course_id}


class StartRecordingBody(BaseModel):
    matiere: str = ""


@app.post("/api/record/start")
def start_recording(body: StartRecordingBody = StartRecordingBody()) -> dict:
    global _current_course_id
    if recorder.is_recording:
        raise HTTPException(status_code=400, detail="Un enregistrement est déjà en cours.")
    try:
        recorder.start()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    course_id, _course_dir = storage.create_course(matiere=body.matiere)
    _current_course_id = course_id
    return {"id": course_id}


@app.post("/api/record/stop")
def stop_recording(background_tasks: BackgroundTasks) -> dict:
    global _current_course_id
    if not recorder.is_recording or _current_course_id is None:
        raise HTTPException(status_code=400, detail="Aucun enregistrement en cours.")

    course_id = _current_course_id
    _current_course_id = None
    course_dir = storage.get_course_dir(course_id)
    audio_path = course_dir / "audio.wav"

    try:
        duration = recorder.stop(audio_path)
    except Exception as exc:  # noqa: BLE001
        storage.update_course(course_id, statut="error", erreur=str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    storage.update_course(course_id, duree_sec=duration, statut="transcribing")
    background_tasks.add_task(_process_transcription, course_id)
    return {"id": course_id}


def _process_transcription(course_id: str) -> None:
    course_dir = storage.get_course_dir(course_id)
    audio_path = course_dir / "audio.wav"
    transcript_path = course_dir / "transcription.txt"
    try:
        text = transcriber.transcribe(audio_path, transcript_path)
        title = storage.derive_title(text)
        storage.update_course(course_id, statut="done", titre=title, erreur=None)
    except Exception as exc:  # noqa: BLE001
        storage.update_course(course_id, statut="error", erreur=str(exc))


# --- Bibliothèque de cours ---------------------------------------------------


@app.get("/api/courses")
def list_courses() -> list[dict]:
    return storage.list_courses()


def _read_text_or_empty(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ""


@app.get("/api/courses/{course_id}")
def get_course(course_id: str) -> dict:
    meta = storage.get_course(course_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="Cours introuvable.")

    course_dir = storage.get_course_dir(course_id)
    meta["transcription"] = _read_text_or_empty(course_dir / "transcription.txt")
    meta["resume"] = _read_text_or_empty(course_dir / "resume.md")

    slides_dir = course_dir / "slides"
    pages = sorted(slides_dir.glob("page-*.png")) if slides_dir.exists() else []
    meta["slides_pages"] = [p.name for p in pages]

    return meta


class RenameBody(BaseModel):
    titre: str


@app.patch("/api/courses/{course_id}")
def rename_course(course_id: str, body: RenameBody) -> dict:
    meta = storage.update_course(course_id, titre=body.titre)
    if meta is None:
        raise HTTPException(status_code=404, detail="Cours introuvable.")
    return meta


@app.delete("/api/courses/{course_id}")
def delete_course(course_id: str) -> dict:
    if not storage.delete_course(course_id):
        raise HTTPException(status_code=404, detail="Cours introuvable.")
    return {"ok": True}


@app.post("/api/courses/{course_id}/slides")
async def upload_slides(course_id: str, file: UploadFile) -> dict:
    meta = storage.get_course(course_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="Cours introuvable.")
    if file.content_type != "application/pdf" and not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Seuls les fichiers PDF sont acceptés.")

    course_dir = storage.get_course_dir(course_id)
    pdf_bytes = await file.read()
    page_count = slides_module.process_pdf(pdf_bytes, course_dir / "slides")
    return {"pages": page_count}


@app.get("/api/courses/{course_id}/prompt-fiche")
def prompt_fiche(course_id: str) -> dict:
    meta = storage.get_course(course_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="Cours introuvable.")
    return {"prompt": f"/fiche {course_id}"}


@app.get("/api/courses/{course_id}/file/{file_path:path}")
def get_course_file(course_id: str, file_path: str) -> FileResponse:
    try:
        course_dir = storage.get_course_dir(course_id).resolve()
    except ValueError:
        raise HTTPException(status_code=404, detail="Cours introuvable.")
    target = (course_dir / file_path).resolve()
    if target != course_dir and course_dir not in target.parents:
        raise HTTPException(status_code=403, detail="Interdit.")
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Fichier introuvable.")
    return FileResponse(target)
