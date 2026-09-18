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
MAX_CHUNK_SEC = 120.0  # borne une tranche même si la transcription prend du retard
OFFSET_FILENAME = ".transcribed_until"  # jusqu'où (en s) l'audio est déjà transcrit


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
            self._drain()

    def _drain(self) -> None:
        # Si Whisper est plus lent que le temps réel, on traite le retard tranche
        # par tranche (au lieu d'un seul bloc géant) en vérifiant l'arrêt entre deux.
        max_samples = int(MAX_CHUNK_SEC * SAMPLE_RATE)
        while not self._stop_event.is_set():
            audio = recorder.peek_new_frames(max_samples=max_samples)
            if audio is None:
                return
            self._process(audio)
            if len(audio) < max_samples:
                return

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
            if self._transcript_path is not None:
                offset_path = self._transcript_path.parent / OFFSET_FILENAME
                offset_path.write_text(str(self._offset_sec), encoding="utf-8")

    def signal_stop(self) -> None:
        """Demande l'arrêt de la boucle périodique, sans attendre : à appeler avant
        recorder.stop() pour que le micro se coupe immédiatement."""
        self._stop_event.set()

    def finalize(self, tail_audio: np.ndarray | None) -> str:
        """Attend la fin de la tranche en cours, transcrit la dernière tranche
        (renvoyée par recorder.stop()) et renvoie le texte complet du cours. Peut
        prendre du temps : à lancer en tâche de fond."""
        if self._thread is not None:
            self._thread.join()
            self._thread = None
        self._process(tail_audio)
        if self._transcript_path is not None:
            (self._transcript_path.parent / OFFSET_FILENAME).unlink(missing_ok=True)
        return "\n".join(self._chunks)


live_transcriber = LiveTranscriber()
