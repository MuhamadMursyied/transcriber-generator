"""Audio decoding and transcription."""

import shutil
import subprocess

import numpy as np

from .models import is_malaysian_model

SAMPLE_RATE = 16000

LANGUAGES = {
    "mixed": "Malay + English (mixed)",
    "ms": "Bahasa Melayu",
    "en": "English",
    "auto": "Auto-detect",
}

# A short example in the target style nudges Whisper to keep English words in
# English and Malay words in Malay instead of translating one into the other.
STYLE_PROMPTS = {
    "mixed": "Okay, jadi hari ni kita nak discuss pasal project tu. "
    "So lepas meeting, kita proceed dengan plan yang baru.",
    "ms": "Selamat pagi semua. Hari ini kita akan membincangkan perkara berikut.",
    "en": "",
    "auto": "",
}


class AudioError(Exception):
    pass


def load_audio(path):
    """Decode any audio or video file to 16 kHz mono float32.

    PyAV (installed with faster-whisper) handles almost every format. The
    ffmpeg command line is a fallback for rare containers PyAV cannot open.
    """
    import av
    from faster_whisper import decode_audio

    try:
        with av.open(path, metadata_errors="ignore") as container:
            has_audio = bool(container.streams.audio)
    except Exception:
        has_audio = True  # PyAV cannot open it; let the ffmpeg fallback try
    if not has_audio:
        raise AudioError("This file has no audio track.")

    try:
        audio = decode_audio(path, sampling_rate=SAMPLE_RATE)
    except Exception as first_error:
        if not shutil.which("ffmpeg"):
            raise AudioError(f"Could not read this file: {first_error}") from first_error
        audio = _decode_with_ffmpeg(path)

    if audio.size == 0:
        raise AudioError("No audio track found in this file.")
    return audio


def _decode_with_ffmpeg(path):
    cmd = [
        "ffmpeg", "-nostdin", "-v", "error", "-i", path,
        "-vn", "-ac", "1", "-ar", str(SAMPLE_RATE), "-f", "f32le", "-",
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        message = result.stderr.decode(errors="ignore").strip().splitlines()
        raise AudioError("Could not read this file: " + (message[-1] if message else "ffmpeg failed"))
    return np.frombuffer(result.stdout, dtype=np.float32)


def build_options(language, model_id, quality, vocabulary=""):
    """Translate the UI choices into faster-whisper arguments."""
    options = {"vad_filter": True}

    if language in ("ms", "en"):
        options["language"] = language
    elif language == "mixed":
        if is_malaysian_model(model_id):
            # This model was trained on code-switched speech under the "ms" token.
            options["language"] = "ms"
        else:
            options["language"] = None
            options["multilingual"] = True  # detect the language per segment
    else:
        options["language"] = None

    prompt = " ".join(p for p in (STYLE_PROMPTS.get(language, ""), vocabulary.strip()) if p)
    if prompt:
        options["initial_prompt"] = prompt

    if quality == "accurate":
        options["beam_size"] = 5
    else:
        options["beam_size"] = 1  # greedy decoding: much faster, small accuracy cost
    return options


def transcribe(model, audio, language="mixed", model_id="", quality="fast",
               vocabulary="", device="cpu"):
    """Return (info, segments) where segments yields (segment, progress) lazily.

    Fast mode uses the batched pipeline, which transcribes several speech
    chunks in parallel (about 3-4x faster on GPU, ~2x on CPU). Accurate mode
    runs sequentially with beam search and uses the previous text as context.
    """
    from faster_whisper import BatchedInferencePipeline

    options = build_options(language, model_id, quality, vocabulary)
    duration = len(audio) / SAMPLE_RATE

    if quality == "accurate":
        segments, info = model.transcribe(audio, **options)
    else:
        batch_size = 16 if device == "cuda" else 8
        pipeline = BatchedInferencePipeline(model=model)
        segments, info = pipeline.transcribe(audio, batch_size=batch_size, **options)

    def results():
        for seg in segments:
            text = seg.text.strip()
            if not text:
                continue
            progress = min(seg.end / duration, 1.0) if duration else 1.0
            yield {"start": round(seg.start, 2), "end": round(seg.end, 2), "text": text}, progress

    return info, results()
