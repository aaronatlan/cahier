"""Enregistrement micro non-bloquant, piloté par start()/stop() (au lieu de input())."""

from __future__ import annotations

import threading
import time
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf

SAMPLE_RATE = 16000
CHANNELS = 1


class Recorder:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._stream: sd.InputStream | None = None
        self._frames: list[np.ndarray] = []
        self._started_at: float | None = None
        self._peeked_until: int = 0

    @property
    def is_recording(self) -> bool:
        with self._lock:
            return self._stream is not None

    @property
    def elapsed_sec(self) -> float:
        """Durée écoulée depuis start(), pour permettre au frontend de rafficher
        un chronomètre cohérent s'il a perdu le fil (ex. navigation ailleurs)."""
        with self._lock:
            if self._started_at is None:
                return 0.0
            return time.monotonic() - self._started_at

    def start(self) -> None:
        with self._lock:
            if self._stream is not None:
                raise RuntimeError("Un enregistrement est déjà en cours.")
            self._frames = []
            self._started_at = time.monotonic()
            self._peeked_until = 0

            def callback(indata, frame_count, time_info, status):
                with self._lock:
                    self._frames.append(indata.copy())

            stream = sd.InputStream(
                samplerate=SAMPLE_RATE, channels=CHANNELS, callback=callback
            )
            stream.start()
            self._stream = stream

    def peek_new_frames(self) -> np.ndarray | None:
        """Retourne l'audio capturé depuis le dernier appel (mono, float32, 1D),
        sans perturber l'enregistrement en cours ni ce que stop() écrira au final.
        Utilisé pour transcrire par tranches pendant l'enregistrement."""
        with self._lock:
            new_frames = self._frames[self._peeked_until :]
            self._peeked_until = len(self._frames)
        if not new_frames:
            return None
        return np.concatenate(new_frames, axis=0)[:, 0]

    def stop(self, output_path: Path) -> float:
        with self._lock:
            if self._stream is None:
                raise RuntimeError("Aucun enregistrement en cours.")
            stream = self._stream

        # stream.stop() bloque jusqu'à ce qu'aucun callback ne puisse plus se
        # déclencher ; appelé hors du verrou pour ne pas bloquer un callback en
        # cours qui attendrait ce même verrou (deadlock). Si l'appareil audio a
        # changé d'état entre-temps (veille prolongée, périphérique déconnecté),
        # stream.stop()/close() peuvent lever une erreur PortAudio — on ne doit
        # surtout pas laisser self._stream orphelin dans ce cas, sous peine de
        # bloquer tout enregistrement futur : on récupère quand même les frames
        # déjà captées plutôt que de propager l'erreur avant d'avoir nettoyé l'état.
        stop_error: Exception | None = None
        try:
            stream.stop()
        except Exception as exc:  # noqa: BLE001
            stop_error = exc
        try:
            stream.close()
        except Exception:  # noqa: BLE001
            pass

        with self._lock:
            frames = self._frames
            started_at = self._started_at
            self._stream = None
            self._frames = []
            self._started_at = None

        duration = time.monotonic() - started_at if started_at else 0.0

        if not frames:
            raise RuntimeError("Aucun audio capturé.")

        audio_data = np.concatenate(frames, axis=0)
        sf.write(str(output_path), audio_data, SAMPLE_RATE)

        if stop_error is not None:
            print(f"recorder.stop: stream.stop() a échoué mais l'audio a été récupéré : {stop_error!r}")

        return duration


recorder = Recorder()
