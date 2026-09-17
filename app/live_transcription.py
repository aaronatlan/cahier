"""Transcription incrémentale pendant l'enregistrement : on transcrit l'audio déjà
capturé par tranches régulières plutôt que d'attendre la fin pour tout traiter d'un
coup. Il ne reste alors que la dernière tranche (quelques dizaines de secondes) à
transcrire une fois l'enregistrement arrêté, au lieu de l'heure de cours entière."""

from __future__ import annotations

import threading
from pathlib import Path

import numpy as np

from . import transcriber
from .recorder import SAMPLE_RATE, recorder

CHUNK_INTERVAL_SEC = 60.0


class LiveTranscriber:
    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._transcript_path: Path | None = None
        self._offset_sec = 0.0
        self._chunks: list[str] = []
        self._process_lock = threading.Lock()

    def start(self, transcript_path: Path) -> None:
        self._transcript_path = transcript_path
        self._offset_sec = 0.0
        self._chunks = []
        transcript_path.write_text("", encoding="utf-8")
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while not self._stop_event.wait(CHUNK_INTERVAL_SEC):
            self._process_available()

    def _process_available(self) -> None:
        self._process(recorder.peek_new_frames())

    def _process(self, audio: np.ndarray | None) -> None:
        if audio is None or len(audio) == 0:
            return
        duration = len(audio) / SAMPLE_RATE
        with self._process_lock:
            try:
                text = transcriber.transcribe_array(audio, offset_sec=self._offset_sec)
            except Exception as exc:  # noqa: BLE001
                # Une tranche ratée ne doit pas faire perdre le reste du cours : on
                # avance quand même l'offset et on continue sur la suivante.
                print(f"live_transcription: échec d'une tranche : {exc!r}")
                text = ""
            self._offset_sec += duration
            if text:
                self._chunks.append(text)
                if self._transcript_path is not None:
                    with self._transcript_path.open("a", encoding="utf-8") as f:
                        f.write(text + "\n")

    def pause(self) -> np.ndarray | None:
        """Arrête la boucle périodique et renvoie la dernière tranche non encore
        traitée, sans la transcrire. À appeler avant recorder.stop(), tant que le
        buffer du recorder existe encore, pour ne rien manquer de la fin du cours."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=CHUNK_INTERVAL_SEC + 60)
            self._thread = None
        return recorder.peek_new_frames()

    def finalize(self, tail_audio: np.ndarray | None) -> str:
        """Transcrit la dernière tranche (capturée par pause()) et renvoie le texte
        complet du cours. Peut prendre quelques secondes : à lancer en tâche de fond."""
        self._process(tail_audio)
        return "\n".join(self._chunks)


live_transcriber = LiveTranscriber()
