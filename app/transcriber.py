"""Transcription audio en local avec faster-whisper (langue choisie par cours, sans traduction)."""

from __future__ import annotations

import threading
from pathlib import Path

MODEL_SIZE = "medium"
DEFAULT_LANGUAGE = "en"  # cours du MIT : anglais ; None = détection automatique par Whisper

LANGUAGES = ("en", "fr", "auto")  # valeurs possibles du champ `langue` d'un cours

_model = None
_lock = threading.Lock()


def resolve_language(code: str | None) -> str | None:
    """Code stocké dans meta.json -> argument Whisper ("auto" = détection automatique)."""
    if code is None:
        return DEFAULT_LANGUAGE
    return None if code == "auto" else code


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


def _run(audio, offset_sec: float = 0.0, language: str | None = DEFAULT_LANGUAGE) -> tuple[str, str]:
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
        segments, info = model.transcribe(
            audio, language=language, task="transcribe", beam_size=1, vad_filter=True
        )

        lines = []
        for segment in segments:
            start = format_timestamp(segment.start + offset_sec)
            lines.append(f"[{start}] {segment.text.strip()}")
        return "\n".join(lines), info.language


def transcribe(
    audio_path: Path, transcript_path: Path, language: str | None = DEFAULT_LANGUAGE
) -> tuple[str, str]:
    """Transcrit un fichier audio entier. Retourne (texte, langue utilisée/détectée)."""
    text, detected = _run(str(audio_path), language=language)
    transcript_path.write_text(text, encoding="utf-8")
    return text, detected


def transcribe_array(
    audio, offset_sec: float = 0.0, language: str | None = DEFAULT_LANGUAGE
) -> tuple[str, str]:
    """Transcrit une tranche d'audio déjà en mémoire (float32 mono, 1D), avec un
    décalage de timestamp pour rester cohérent avec le reste de l'enregistrement.
    Retourne (texte, langue utilisée/détectée)."""
    return _run(audio, offset_sec=offset_sec, language=language)
