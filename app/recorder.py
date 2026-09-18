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
PERSIST_INTERVAL_SEC = 5.0
STREAM_RELEASE_TIMEOUT_SEC = 5.0
PARTIAL_FILENAME = "audio.partial.pcm"


class Recorder:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._stream: sd.InputStream | None = None
        self._frames: list[np.ndarray] = []
        self._started_at: float | None = None
        self._peeked_until: int = 0
        self._flushed_until: int = 0
        self._persist_path: Path | None = None
        self._persist_stop = threading.Event()
        self._persist_thread: threading.Thread | None = None

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

    def start(self, persist_path: Path | None = None) -> None:
        """Démarre la capture. Si persist_path est donné, l'audio est aussi écrit en
        continu dessus (PCM 16 bits brut, sans en-tête) : si l'app est tuée avant
        stop(), rien n'est perdu et le fichier peut être récupéré au redémarrage."""
        with self._lock:
            if self._stream is not None:
                raise RuntimeError("Un enregistrement est déjà en cours.")
            self._frames = []
            self._started_at = time.monotonic()
            self._peeked_until = 0
            self._flushed_until = 0

            def callback(indata, frame_count, time_info, status):
                with self._lock:
                    self._frames.append(indata.copy())

            stream = sd.InputStream(
                samplerate=SAMPLE_RATE, channels=CHANNELS, callback=callback
            )
            stream.start()
            self._stream = stream

        if persist_path is not None:
            self._persist_path = persist_path
            self._persist_stop.clear()
            self._persist_thread = threading.Thread(target=self._persist_loop, daemon=True)
            self._persist_thread.start()

    def _persist_loop(self) -> None:
        path = self._persist_path
        if path is None:
            return
        try:
            with open(path, "ab") as f:
                while True:
                    stopping = self._persist_stop.wait(PERSIST_INTERVAL_SEC)
                    with self._lock:
                        new_frames = self._frames[self._flushed_until :]
                        self._flushed_until = len(self._frames)
                    if new_frames:
                        mono = np.concatenate(new_frames, axis=0)[:, 0]
                        pcm = (np.clip(mono, -1.0, 1.0) * 32767.0).astype("<i2")
                        f.write(pcm.tobytes())
                        f.flush()
                    if stopping:
                        break
        except Exception as exc:  # noqa: BLE001
            print(f"recorder: sauvegarde continue interrompue : {exc!r}")

    def peek_new_frames(self, max_samples: int | None = None) -> np.ndarray | None:
        """Retourne l'audio capturé depuis le dernier appel (mono, float32, 1D),
        sans perturber l'enregistrement en cours ni ce que stop() écrira au final.
        max_samples borne la taille de la tranche (le reste sera renvoyé aux appels
        suivants). Utilisé pour transcrire par tranches pendant l'enregistrement."""
        with self._lock:
            pending = self._frames[self._peeked_until :]
            if max_samples is None:
                taken = pending
            else:
                taken = []
                total = 0
                for arr in pending:
                    taken.append(arr)
                    total += len(arr)
                    if total >= max_samples:
                        break
            self._peeked_until += len(taken)
        if not taken:
            return None
        return np.concatenate(taken, axis=0)[:, 0]

    @staticmethod
    def _release_stream(stream: sd.InputStream) -> Exception | None:
        """stream.stop()/close() peuvent lever une erreur PortAudio, voire bloquer
        (appareil audio changé d'état pendant une veille prolongée). On les exécute
        dans un thread avec délai maximal : dans tous les cas on récupère ensuite
        l'audio déjà capturé plutôt que de rester coincé avec le micro allumé."""
        result: dict[str, Exception] = {}

        def work() -> None:
            try:
                stream.stop()
            except Exception as exc:  # noqa: BLE001
                result["error"] = exc
            try:
                stream.close()
            except Exception:  # noqa: BLE001
                pass

        thread = threading.Thread(target=work, daemon=True)
        thread.start()
        thread.join(STREAM_RELEASE_TIMEOUT_SEC)
        if thread.is_alive():
            return TimeoutError("stream.stop() ne répond pas")
        return result.get("error")

    def stop(self, output_path: Path) -> tuple[float, np.ndarray | None]:
        """Arrête la capture, écrit output_path. Retourne (durée, audio non encore
        consommé par peek_new_frames) — ce dernier morceau est à transcrire."""
        with self._lock:
            if self._stream is None:
                raise RuntimeError("Aucun enregistrement en cours.")
            stream = self._stream

        stop_error = self._release_stream(stream)

        self._persist_stop.set()
        if self._persist_thread is not None:
            self._persist_thread.join(timeout=10)
            self._persist_thread = None

        with self._lock:
            frames = self._frames
            tail_frames = frames[self._peeked_until :]
            self._stream = None
            self._frames = []
            self._started_at = None
        persist_path, self._persist_path = self._persist_path, None

        if not frames:
            raise RuntimeError("Aucun audio capturé.")

        audio_data = np.concatenate(frames, axis=0)
        sf.write(str(output_path), audio_data, SAMPLE_RATE)
        if persist_path is not None:
            persist_path.unlink(missing_ok=True)

        if stop_error is not None:
            print(f"recorder.stop: arrêt du flux en erreur mais l'audio a été récupéré : {stop_error!r}")

        duration = len(audio_data) / SAMPLE_RATE
        tail = np.concatenate(tail_frames, axis=0)[:, 0] if tail_frames else None
        return duration, tail


recorder = Recorder()
