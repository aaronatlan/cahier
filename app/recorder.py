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

    @property
    def is_recording(self) -> bool:
        with self._lock:
            return self._stream is not None

    def start(self) -> None:
        with self._lock:
            if self._stream is not None:
                raise RuntimeError("Un enregistrement est déjà en cours.")
            self._frames = []
            self._started_at = time.monotonic()

            def callback(indata, frame_count, time_info, status):
                with self._lock:
                    self._frames.append(indata.copy())

            stream = sd.InputStream(
                samplerate=SAMPLE_RATE, channels=CHANNELS, callback=callback
            )
            stream.start()
            self._stream = stream

    def stop(self, output_path: Path) -> float:
        with self._lock:
            if self._stream is None:
                raise RuntimeError("Aucun enregistrement en cours.")
            stream = self._stream

        # stream.stop() bloque jusqu'à ce qu'aucun callback ne puisse plus se
        # déclencher ; appelé hors du verrou pour ne pas bloquer un callback en
        # cours qui attendrait ce même verrou (deadlock). Une fois stop() revenu,
        # self._frames peut être vidé sans risque qu'un callback tardif y écrive
        # encore et perde silencieusement la fin de l'enregistrement.
        stream.stop()

        with self._lock:
            frames = self._frames
            started_at = self._started_at
            self._stream = None
            self._frames = []
            self._started_at = None

        stream.close()

        duration = time.monotonic() - started_at if started_at else 0.0

        if not frames:
            raise RuntimeError("Aucun audio capturé.")

        audio_data = np.concatenate(frames, axis=0)
        sf.write(str(output_path), audio_data, SAMPLE_RATE)
        return duration


recorder = Recorder()
