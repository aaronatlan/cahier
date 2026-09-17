"""Transcription audio en local avec faster-whisper (anglais, sans traduction)."""

from __future__ import annotations

import threading
from pathlib import Path

MODEL_SIZE = "medium"
LANGUAGE = "en"  # cours toujours en anglais, pas de détection auto ni de traduction

_model = None
_lock = threading.Lock()


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        _model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8", cpu_threads=8)
    return _model


def format_timestamp(seconds: float) -> str:
    minutes, sec = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{sec:02d}"
    return f"{minutes:02d}:{sec:02d}"


def _run(audio, offset_sec: float = 0.0) -> str:
    # Un seul modèle Whisper partagé : on sérialise les transcriptions pour éviter
    # deux inférences concurrentes sur la même instance (non garanti thread-safe côté
    # faster-whisper/CTranslate2) si un nouvel enregistrement est lancé pendant qu'une
    # transcription précédente tourne encore en tâche de fond, ou si des tranches
    # d'un même enregistrement s'enchaînent.
    with _lock:
        model = _get_model()
        # beam_size=1 (glouton) + vad_filter (saute les silences) : ~25% plus rapide
        # que les réglages par défaut sur les tests, sans perte notable de qualité
        # vu que ce texte sert de matière première à un résumé généré par la suite.
        segments, _info = model.transcribe(
            audio, language=LANGUAGE, task="transcribe", beam_size=1, vad_filter=True
        )

        lines = []
        for segment in segments:
            start = format_timestamp(segment.start + offset_sec)
            lines.append(f"[{start}] {segment.text.strip()}")
        return "\n".join(lines)


def transcribe(audio_path: Path, transcript_path: Path) -> str:
    text = _run(str(audio_path))
    transcript_path.write_text(text, encoding="utf-8")
    return text


def transcribe_array(audio, offset_sec: float = 0.0) -> str:
    """Transcrit une tranche d'audio déjà en mémoire (float32 mono, 1D), avec un
    décalage de timestamp pour rester cohérent avec le reste de l'enregistrement."""
    return _run(audio, offset_sec=offset_sec)
