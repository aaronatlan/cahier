"""Serveur FastAPI local : enregistrement, transcription, bibliothèque de cours, slides."""

from __future__ import annotations

import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import slides as slides_module
from . import storage
from . import subjects as subjects_module
from .live_transcription import live_transcriber
from .recorder import recorder

STATIC_DIR = Path(__file__).parent / "static"

class NoCacheStaticFiles(StaticFiles):
    """Empêche la mise en cache agressive des fichiers statiques par la webview :
    sans ça, un changement d'app.js/style.css peut rester invisible après un
    simple relancement de l'app tant que le cache HTTP local n'a pas expiré."""

    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-store"
        return response


app = FastAPI(title="Cahier")
app.mount("/static", NoCacheStaticFiles(directory=STATIC_DIR), name="static")

_current_course_id: Optional[str] = None

# --- Génération résumé/fiche/exercices via /fiche (Claude Code CLI) --------

CAHIER_ROOT = Path(__file__).resolve().parent.parent
# Chemin absolu : les apps GUI lancées depuis le Finder n'héritent pas du PATH
# du shell (~/.zshrc etc.), un simple "claude" ne serait pas trouvé — même
# raison que le chemin absolu déjà utilisé pour pdflatex (voir CLAUDE.md).
CLAUDE_BIN = str(Path.home() / ".local" / "bin" / "claude")
GENERATION_STALE_SEC = 30 * 60  # au-delà, on considère le verrou abandonné

_generation_procs: dict[str, subprocess.Popen] = {}


def _generation_lock_path(course_dir: Path) -> Path:
    return course_dir / ".generating"


def _generation_running(course_dir: Path) -> bool:
    lock_path = _generation_lock_path(course_dir)
    if not lock_path.exists():
        return False
    age = time.time() - lock_path.stat().st_mtime
    return age < GENERATION_STALE_SEC


@app.on_event("startup")
def _on_startup() -> None:
    storage.migrate_legacy()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html", headers={"Cache-Control": "no-store"})


# --- Enregistrement --------------------------------------------------------


@app.get("/api/subjects")
def get_subjects() -> list[dict]:
    return subjects_module.SUBJECTS


@app.get("/api/record/status")
def record_status() -> dict:
    return {
        "recording": recorder.is_recording,
        "id": _current_course_id,
        "elapsed_sec": recorder.elapsed_sec,
    }


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
    course_id, course_dir = storage.create_course(matiere=body.matiere)
    _current_course_id = course_id
    live_transcriber.start(course_dir / "transcription.txt")
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

    # pause() capture ce qui n'a pas encore été transcrit AVANT recorder.stop(),
    # qui vide le buffer du recorder — le gros du cours a déjà été transcrit au
    # fil de l'enregistrement, il ne reste que cette dernière tranche à traiter.
    tail_audio = live_transcriber.pause()

    try:
        duration = recorder.stop(audio_path)
    except Exception as exc:  # noqa: BLE001
        storage.update_course(course_id, statut="error", erreur=str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    storage.update_course(course_id, duree_sec=duration, statut="transcribing")
    background_tasks.add_task(_finalize_transcription, course_id, tail_audio)
    return {"id": course_id}


def _finalize_transcription(course_id: str, tail_audio) -> None:
    try:
        text = live_transcriber.finalize(tail_audio)
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
    if course_id == _current_course_id:
        # Supprimer le dossier pendant que le micro enregistre encore dessus
        # laisse le recorder tourner indéfiniment vers un dossier qui n'existe
        # plus plus moyen de l'arrêter proprement, micro resté allumé.
        raise HTTPException(
            status_code=409, detail="Arrête l'enregistrement avant de supprimer ce cours."
        )
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


@app.delete("/api/courses/{course_id}/slides")
def delete_slides(course_id: str) -> dict:
    meta = storage.get_course(course_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="Cours introuvable.")
    slides_dir = storage.get_course_dir(course_id) / "slides"
    if slides_dir.exists():
        shutil.rmtree(slides_dir)
    return {"ok": True}


@app.delete("/api/courses/{course_id}/slides/{page_number}")
def delete_slide_page(course_id: str, page_number: int) -> dict:
    meta = storage.get_course(course_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="Cours introuvable.")
    slides_dir = storage.get_course_dir(course_id) / "slides"
    if not (slides_dir / "source.pdf").exists():
        raise HTTPException(status_code=404, detail="Pas de slides pour ce cours.")
    try:
        remaining = slides_module.delete_page(slides_dir, page_number)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"pages": remaining}


@app.post("/api/courses/{course_id}/generate")
def start_generation(course_id: str) -> dict:
    meta = storage.get_course(course_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="Cours introuvable.")
    course_dir = storage.get_course_dir(course_id)
    if _generation_running(course_dir):
        raise HTTPException(status_code=409, detail="Génération déjà en cours pour ce cours.")

    lock_path = _generation_lock_path(course_dir)
    lock_path.write_text("", encoding="utf-8")
    log_file = (course_dir / "generation.log").open("w", encoding="utf-8")
    proc = subprocess.Popen(
        [
            CLAUDE_BIN,
            "-p",
            f"/fiche {course_id}",
            "--permission-mode",
            "acceptEdits",
            "--allowedTools",
            "Read Write Edit Bash Grep Glob WebSearch WebFetch Agent",
        ],
        cwd=str(CAHIER_ROOT),
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )
    _generation_procs[course_id] = proc

    def _watch() -> None:
        proc.wait()
        log_file.close()
        lock_path.unlink(missing_ok=True)

    threading.Thread(target=_watch, daemon=True).start()
    return {"ok": True}


@app.get("/api/courses/{course_id}/generate/status")
def generation_status(course_id: str) -> dict:
    course_dir = storage.get_course_dir(course_id)
    if _generation_running(course_dir):
        return {"state": "running"}
    proc = _generation_procs.get(course_id)
    if proc is None:
        return {"state": "idle"}
    return {"state": "done" if proc.returncode == 0 else "error", "exit_code": proc.returncode}


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
