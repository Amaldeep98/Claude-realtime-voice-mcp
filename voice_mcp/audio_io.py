"""Microphone capture (VAD-gated), playback, and audio cue tones.

Mirrors the proven approach of webrtcvad (aggressive mode) with an
energy-based fallback for environments/mics where webrtcvad misfires.
"""
from __future__ import annotations

import subprocess
import sys
import threading
import time

import numpy as np
import sounddevice as sd

try:
    import webrtcvad
except ImportError:  # pragma: no cover - optional at import time
    webrtcvad = None

SAMPLE_RATE = 16000
FRAME_MS = 30
FRAME_SAMPLES = SAMPLE_RATE * FRAME_MS // 1000
ENERGY_THRESHOLD = 500  # RMS threshold for the energy-based fallback

_playback_lock = threading.Lock()
_stop_playback = threading.Event()


def _is_speech(frame: np.ndarray, vad: "webrtcvad.Vad | None") -> bool:
    if vad is not None:
        try:
            return vad.is_speech(frame.tobytes(), SAMPLE_RATE)
        except Exception:
            pass
    rms = np.sqrt(np.mean(frame.astype(np.float64) ** 2))
    return rms > ENERGY_THRESHOLD


def record_until_silence(
    *, max_seconds: float = 30.0, silence_ms: int = 1500, on_start=None
) -> np.ndarray:
    """Record from the mic until `silence_ms` of trailing silence is seen."""
    vad = webrtcvad.Vad(3) if webrtcvad is not None else None
    silence_frames_needed = max(1, silence_ms // FRAME_MS)
    frames: list[np.ndarray] = []
    silence_run = 0
    speech_seen = False

    if on_start:
        on_start()

    with sd.InputStream(
        samplerate=SAMPLE_RATE, channels=1, dtype="int16", blocksize=FRAME_SAMPLES
    ) as stream:
        start = time.monotonic()
        while time.monotonic() - start < max_seconds:
            frame, _ = stream.read(FRAME_SAMPLES)
            frame = frame.reshape(-1)
            frames.append(frame)
            if _is_speech(frame, vad):
                speech_seen = True
                silence_run = 0
            elif speech_seen:
                silence_run += 1
                if silence_run >= silence_frames_needed:
                    break

    return np.concatenate(frames) if frames else np.zeros(0, dtype=np.int16)


def record_fixed(duration_seconds: float, *, on_start=None) -> np.ndarray:
    if on_start:
        on_start()
    audio = sd.rec(
        int(duration_seconds * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
    )
    sd.wait()
    return audio.reshape(-1)


def play(audio: np.ndarray, samplerate: int) -> None:
    """Blocking playback; interruptible via stop_playback()."""
    _stop_playback.clear()
    with _playback_lock:
        sd.play(audio, samplerate)
        while sd.get_stream().active:
            if _stop_playback.is_set():
                sd.stop()
                break
            time.sleep(0.05)
        sd.wait()


def stop_playback() -> None:
    _stop_playback.set()
    sd.stop()


def _tone(freq_start: float, freq_end: float, duration: float = 0.18) -> np.ndarray:
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    freq = np.linspace(freq_start, freq_end, t.size)
    tone = 0.15 * np.sin(2 * np.pi * freq * t)
    return tone.astype(np.float32)


def cue_listening_start() -> None:
    sd.play(_tone(440, 880), SAMPLE_RATE)
    sd.wait()


def cue_listening_stop() -> None:
    sd.play(_tone(880, 440), SAMPLE_RATE)
    sd.wait()


def notify(title: str, message: str) -> None:
    if sys.platform != "darwin":
        return
    safe_title = title.replace('"', "'")
    safe_message = message.replace('"', "'")
    script = f'display notification "{safe_message}" with title "{safe_title}"'
    subprocess.run(["osascript", "-e", script], check=False, capture_output=True)
