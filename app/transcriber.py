"""Transcription audio en local avec faster-whisper (anglais, sans traduction)."""

from __future__ import annotations

from pathlib import Path

MODEL_SIZE = "medium"
LANGUAGE = "en"  # cours toujours en anglais, pas de détection auto ni de traduction

_model = None


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        _model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    return _model


def format_timestamp(seconds: float) -> str:
    minutes, sec = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{sec:02d}"
    return f"{minutes:02d}:{sec:02d}"


def transcribe(audio_path: Path, transcript_path: Path) -> str:
    model = _get_model()
    segments, _info = model.transcribe(str(audio_path), language=LANGUAGE, task="transcribe")

    lines = []
    for segment in segments:
        start = format_timestamp(segment.start)
        lines.append(f"[{start}] {segment.text.strip()}")

    text = "\n".join(lines)
    transcript_path.write_text(text, encoding="utf-8")
    return text
