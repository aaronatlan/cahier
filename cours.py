#!/usr/bin/env python3
"""
cours.py — Enregistre un cours depuis le micro, puis le transcrit en local
avec faster-whisper (gratuit, open source, aucune limite de durée).

Utilisation :
    python3 cours.py

    - Appuyer sur Entrée pour démarrer l'enregistrement
    - Appuyer sur Entrée une seconde fois pour arrêter
    - La transcription se lance automatiquement et un fichier .txt est créé

Délègue à app/recorder.py et app/transcriber.py (la même logique que l'app
graphique Cahier) pour ne jamais diverger de son comportement.
"""

import datetime
import sys
from pathlib import Path

from app.recorder import recorder
from app.transcriber import transcribe

OUTPUT_DIR = Path.home() / "Cours" / "enregistrements"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# --- Enregistrement ------------------------------------------------------

def record_audio(output_path: Path) -> None:
    print("Appuie sur Entrée pour démarrer l'enregistrement...")
    input()
    print("Enregistrement en cours... Appuie sur Entrée pour arrêter.")

    try:
        recorder.start()
    except Exception as exc:  # noqa: BLE001
        print(f"Impossible d'accéder au micro : {exc}", file=sys.stderr)
        sys.exit(1)

    input()

    try:
        recorder.stop(output_path)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

    print(f"Enregistrement sauvegardé : {output_path}")


# --- Transcription ---------------------------------------------------------

def transcribe_audio(audio_path: Path, transcript_path: Path) -> None:
    print("Transcription en cours (ça peut prendre quelques minutes)...")
    text, _langue = transcribe(audio_path, transcript_path)
    print(text)
    print(f"\nTranscription sauvegardée : {transcript_path}")


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
