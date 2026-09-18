"""Récupération au démarrage des enregistrements interrompus (app fermée ou tuée
avant la fin de l'arrêt) : reconstruit audio.wav depuis la sauvegarde continue
audio.partial.pcm, transcrit ce que la transcription en flux n'avait pas encore
couvert, puis clôt le cours. Au démarrage rien n'enregistre ni ne transcrit, donc
tout cours resté "recording"/"transcribing" est forcément orphelin."""

from __future__ import annotations

import re
from pathlib import Path

import soundfile as sf

from . import storage, transcriber
from .live_transcription import OFFSET_FILENAME
from .recorder import PARTIAL_FILENAME, SAMPLE_RATE, recorder

_TIMESTAMP = re.compile(r"^\[(?:(\d+):)?(\d{1,2}):(\d{2})\]", re.MULTILINE)
# Sans marqueur précis de couverture, on ne retranscrit la fin que si elle est
# nettement plus longue qu'un segment (évite de dupliquer la dernière phrase).
MIN_TAIL_WITH_MARKER_SEC = 2.0
MIN_TAIL_WITHOUT_MARKER_SEC = 30.0


def _last_timestamp_sec(text: str) -> float:
    last = 0.0
    for m in _TIMESTAMP.finditer(text):
        last = int(m.group(1) or 0) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
    return last


def _read_transcript(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8") if path.exists() else ""
    except UnicodeDecodeError:
        return ""


def _rebuild_wav(partial: Path, audio_path: Path) -> float:
    with sf.SoundFile(
        str(partial), "r", samplerate=SAMPLE_RATE, channels=1,
        format="RAW", subtype="PCM_16", endian="LITTLE",
    ) as src:
        total_frames = src.frames
        with sf.SoundFile(
            str(audio_path), "w", samplerate=SAMPLE_RATE, channels=1, subtype="PCM_16"
        ) as dst:
            for block in src.blocks(blocksize=SAMPLE_RATE * 30, dtype="int16"):
                dst.write(block)
    return total_frames / SAMPLE_RATE


def _recover(course_id: str) -> None:
    course_dir = storage.get_course_dir(course_id)
    partial = course_dir / PARTIAL_FILENAME
    audio_path = course_dir / "audio.wav"
    transcript_path = course_dir / "transcription.txt"
    offset_path = course_dir / OFFSET_FILENAME

    text = _read_transcript(transcript_path)
    has_audio = True
    if partial.exists() and partial.stat().st_size > 0:
        storage.update_course(course_id, statut="transcribing")
        duration = _rebuild_wav(partial, audio_path)
        partial.unlink()
    elif audio_path.exists():
        duration = sf.info(str(audio_path)).duration
    else:
        # Audio perdu (arrêt avant la sauvegarde continue) : il reste la
        # transcription partielle, on garde au moins ça.
        has_audio = False
        duration = _last_timestamp_sec(text)

    if has_audio:
        if offset_path.exists():
            covered, min_tail = float(offset_path.read_text(encoding="utf-8")), MIN_TAIL_WITH_MARKER_SEC
        else:
            covered, min_tail = _last_timestamp_sec(text), MIN_TAIL_WITHOUT_MARKER_SEC
        if duration - covered > min_tail:
            audio, _ = sf.read(str(audio_path), start=int(covered * SAMPLE_RATE), dtype="float32")
            tail_text = transcriber.transcribe_array(audio, offset_sec=covered)
            if tail_text:
                separator = "\n" if text and not text.endswith("\n") else ""
                with transcript_path.open("a", encoding="utf-8") as f:
                    f.write(separator + tail_text + "\n")
                text += separator + tail_text

    offset_path.unlink(missing_ok=True)
    fields: dict = {"statut": "done", "duree_sec": duration, "erreur": None}
    meta = storage.get_course(course_id)
    if meta and meta.get("titre") == "Nouveau cours" and text.strip():
        fields["titre"] = storage.derive_title(text)
    storage.update_course(course_id, **fields)


def recover_orphans() -> None:
    if recorder.is_recording:
        return
    for course in storage.list_courses():
        if course.get("statut") not in ("recording", "transcribing"):
            continue
        try:
            _recover(course["id"])
        except Exception as exc:  # noqa: BLE001
            storage.update_course(
                course["id"], statut="error", erreur=f"Récupération impossible : {exc}"
            )
