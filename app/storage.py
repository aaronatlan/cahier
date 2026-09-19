"""Gestion des dossiers de cours : création, méta-données, liste, migration."""

from __future__ import annotations

import datetime
import json
import re
import shutil
from pathlib import Path
from typing import Optional

from . import subjects as subjects_module

BASE_DIR = Path.home() / "Cours"
LEGACY_DIR = BASE_DIR / "enregistrements"

BASE_DIR.mkdir(parents=True, exist_ok=True)


def _course_dir(course_id: str) -> Path:
    course_dir = (BASE_DIR / course_id).resolve()
    if course_dir.parent != BASE_DIR.resolve():
        raise ValueError(f"course_id invalide : {course_id!r}")
    return course_dir


def _meta_path(course_dir: Path) -> Path:
    return course_dir / "meta.json"


def new_course_id() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def create_course(matiere: str = "", langue: str = "en") -> tuple[str, Path]:
    base_id = new_course_id()
    course_id = base_id
    course_dir = _course_dir(course_id)
    n = 1
    while course_dir.exists():
        n += 1
        course_id = f"{base_id}-{n}"
        course_dir = _course_dir(course_id)
    course_dir.mkdir(parents=True)
    meta = {
        "id": course_id,
        "titre": "Nouveau cours",
        "matiere": matiere,
        "langue": langue,
        "date": datetime.datetime.now().isoformat(timespec="seconds"),
        "duree_sec": 0,
        "statut": "recording",
        "erreur": None,
    }
    save_meta(course_dir, meta)
    return course_id, course_dir


def save_meta(course_dir: Path, meta: dict) -> None:
    _meta_path(course_dir).write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_meta(course_dir: Path) -> Optional[dict]:
    path = _meta_path(course_dir)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _enrich(meta: dict, course_dir: Path) -> dict:
    """Ajoute les champs calculés à partir de l'état du système de fichiers."""
    meta = dict(meta)
    meta.setdefault("matiere", "")
    meta.setdefault("langue", "en")
    meta["matiere_titre"] = subjects_module.subject_title(meta["matiere"])
    meta["a_des_slides"] = (course_dir / "slides" / "source.pdf").exists()
    meta["resume_ok"] = (course_dir / "resume.md").exists()
    meta["fiche_pdf"] = (course_dir / "fiche.pdf").exists()
    meta["exercices_pdf"] = (course_dir / "exercices.pdf").exists()
    return meta


def get_course(course_id: str) -> Optional[dict]:
    try:
        course_dir = _course_dir(course_id)
    except ValueError:
        return None
    meta = load_meta(course_dir)
    if meta is None:
        return None
    return _enrich(meta, course_dir)


def get_course_dir(course_id: str) -> Path:
    return _course_dir(course_id)


def update_course(course_id: str, **fields) -> Optional[dict]:
    try:
        course_dir = _course_dir(course_id)
    except ValueError:
        return None
    meta = load_meta(course_dir)
    if meta is None:
        return None
    meta.update(fields)
    save_meta(course_dir, meta)
    return _enrich(meta, course_dir)


def delete_course(course_id: str) -> bool:
    try:
        course_dir = _course_dir(course_id)
    except ValueError:
        return False
    if not course_dir.exists():
        return False
    shutil.rmtree(course_dir)
    if course_id.startswith("legacy_"):
        timestamp = course_id.removeprefix("legacy_")
        (LEGACY_DIR / f"cours_{timestamp}.txt").unlink(missing_ok=True)
        (LEGACY_DIR / f"cours_{timestamp}.wav").unlink(missing_ok=True)
    return True


def list_courses() -> list[dict]:
    if not BASE_DIR.exists():
        return []
    courses = []
    for entry in BASE_DIR.iterdir():
        if not entry.is_dir() or entry == LEGACY_DIR:
            continue
        meta = load_meta(entry)
        if meta is None:
            continue
        courses.append(_enrich(meta, entry))
    courses.sort(key=lambda m: m.get("date", ""), reverse=True)
    return courses


_TIMESTAMP_PREFIX = re.compile(r"^\[\d{1,2}:\d{2}(:\d{2})?\]\s*")


def derive_title(transcript_text: str) -> str:
    clean_lines = [_TIMESTAMP_PREFIX.sub("", line) for line in transcript_text.splitlines()]
    words = " ".join(clean_lines).strip().split()
    if not words:
        return "Cours du " + datetime.datetime.now().strftime("%d/%m/%Y")
    snippet = " ".join(words[:8])
    if len(words) > 8:
        snippet += "…"
    return snippet[0].upper() + snippet[1:] if snippet else snippet


def migrate_legacy() -> int:
    """Importe les anciens fichiers cours_AAAA-MM-JJ_HH-MM.wav/.txt (non vides) une seule
    fois, sans rien supprimer de l'ancien dossier."""
    if not LEGACY_DIR.exists():
        return 0

    imported = 0
    for txt_path in sorted(LEGACY_DIR.glob("cours_*.txt")):
        if txt_path.stat().st_size == 0:
            continue
        stem = txt_path.stem  # cours_2026-09-15_18-12
        timestamp = stem.removeprefix("cours_")
        wav_path = LEGACY_DIR / f"{stem}.wav"
        if not wav_path.exists():
            continue

        course_id = f"legacy_{timestamp}"
        course_dir = _course_dir(course_id)
        if course_dir.exists():
            continue  # déjà importé

        course_dir.mkdir(parents=True)
        shutil.copy2(wav_path, course_dir / "audio.wav")
        transcript_text = txt_path.read_text(encoding="utf-8")
        (course_dir / "transcription.txt").write_text(transcript_text, encoding="utf-8")

        duration_sec = 0
        try:
            import soundfile as sf

            duration_sec = sf.info(str(wav_path)).duration
        except Exception:
            pass

        try:
            date_iso = datetime.datetime.strptime(timestamp, "%Y-%m-%d_%H-%M").isoformat(
                timespec="seconds"
            )
        except ValueError:
            date_iso = datetime.datetime.now().isoformat(timespec="seconds")

        meta = {
            "id": course_id,
            "titre": derive_title(transcript_text),
            "date": date_iso,
            "duree_sec": duration_sec,
            "statut": "done",
            "erreur": None,
        }
        save_meta(course_dir, meta)
        imported += 1

    return imported
