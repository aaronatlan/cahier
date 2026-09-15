#!/usr/bin/env python3
"""
cours.py — Enregistre un cours depuis le micro, puis le transcrit en local
avec faster-whisper (gratuit, open source, aucune limite de durée).

Utilisation :
    python3 cours.py

    - Appuyer sur Entrée pour démarrer l'enregistrement
    - Appuyer sur Entrée une seconde fois pour arrêter
    - La transcription se lance automatiquement et un fichier .txt est créé
"""

import datetime
import sys
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf

# --- Configuration -----------------------------------------------------

SAMPLE_RATE = 16000          # fréquence attendue par Whisper
CHANNELS = 1
OUTPUT_DIR = Path.home() / "Cours" / "enregistrements"
MODEL_SIZE = "medium"        # "tiny", "base", "small", "medium", "large-v3"
LANGUAGE = None              # None = détection automatique, pas de traduction forcée

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# --- Enregistrement ------------------------------------------------------

def record_audio(output_path: Path) -> None:
    frames = []

    def callback(indata, frame_count, time_info, status):
        if status:
            print(status, file=sys.stderr)
        frames.append(indata.copy())

    print("Appuie sur Entrée pour démarrer l'enregistrement...")
    input()
    print("Enregistrement en cours... Appuie sur Entrée pour arrêter.")

    try:
        with sd.InputStream(
            samplerate=SAMPLE_RATE, channels=CHANNELS, callback=callback
        ):
            input()
    except sd.PortAudioError as exc:
        print(f"Impossible d'accéder au micro : {exc}", file=sys.stderr)
        sys.exit(1)

    if not frames:
        print("Aucun audio capturé, abandon.")
        sys.exit(1)

    audio_data = np.concatenate(frames, axis=0)
    sf.write(str(output_path), audio_data, SAMPLE_RATE)
    print(f"Enregistrement sauvegardé : {output_path}")


# --- Transcription ---------------------------------------------------------

def transcribe_audio(audio_path: Path, transcript_path: Path) -> None:
    from faster_whisper import WhisperModel

    print(f"Chargement du modèle Whisper ({MODEL_SIZE})...")
    model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")

    print("Transcription en cours (ça peut prendre quelques minutes)...")
    segments, info = model.transcribe(str(audio_path), language=LANGUAGE)
    print(f"Langue détectée : {info.language} (confiance {info.language_probability:.0%})")

    lines = []
    for segment in segments:
        start = format_timestamp(segment.start)
        lines.append(f"[{start}] {segment.text.strip()}")
        print(f"[{start}] {segment.text.strip()}")

    transcript_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nTranscription sauvegardée : {transcript_path}")


def format_timestamp(seconds: float) -> str:
    minutes, sec = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{sec:02d}"
    return f"{minutes:02d}:{sec:02d}"


# --- Main ------------------------------------------------------------------

def main() -> None:
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    audio_path = OUTPUT_DIR / f"cours_{timestamp}.wav"
    transcript_path = OUTPUT_DIR / f"cours_{timestamp}.txt"

    record_audio(audio_path)
    transcribe_audio(audio_path, transcript_path)

    print("\nTerminé. Colle le contenu du .txt dans Claude si tu veux un résumé structuré.")


if __name__ == "__main__":
    main()
