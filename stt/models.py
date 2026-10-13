"""Model catalogue, device detection and a small model cache.

Every model here is free and runs locally through faster-whisper (CTranslate2).
Weights are downloaded once from Hugging Face on first use and cached in
~/.cache/huggingface, so later runs work offline.
"""

import os
import threading

# Listed from fastest to most accurate. Sizes are the download size.
MODELS = [
    {
        "id": "tiny",
        "repo": "tiny",
        "label": "Tiny",
        "size": "75 MB",
        "note": "Fastest. Rough accuracy, good for a quick look.",
    },
    {
        "id": "base",
        "repo": "base",
        "label": "Base",
        "size": "145 MB",
        "note": "Very fast. OK for clear English.",
    },
    {
        "id": "small",
        "repo": "small",
        "label": "Small",
        "size": "480 MB",
        "note": "Best choice for a laptop CPU.",
    },
    {
        "id": "medium",
        "repo": "medium",
        "label": "Medium",
        "size": "1.5 GB",
        "note": "Better Malay. Slow on CPU.",
    },
    {
        "id": "large-v3-turbo",
        "repo": "large-v3-turbo",
        "label": "Large v3 Turbo",
        "size": "1.6 GB",
        "note": "Near large-v3 accuracy at ~6x the speed. Best on a GPU.",
    },
    {
        "id": "large-v3",
        "repo": "large-v3",
        "label": "Large v3",
        "size": "3.1 GB",
        "note": "Most accurate general model. Slowest.",
    },
    {
        "id": "malaysian-turbo",
        "repo": "SeamlessX/malaysian-faster-whisper-large-v3-turbo-v3-ct2",
        "label": "Malaysian Turbo",
        "size": "1.6 GB",
        "note": "Turbo fine-tuned on Malaysian speech (Malay, Manglish). "
        "Best for local accents.",
    },
]

MODELS_BY_ID = {m["id"]: m for m in MODELS}

# Folder for models you convert yourself (see scripts/convert_malaysian.sh).
LOCAL_MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")


def detect_device():
    """Return ("cuda", "float16") when a CUDA GPU is usable, else ("cpu", "int8")."""
    try:
        import ctranslate2

        if ctranslate2.get_cuda_device_count() > 0:
            return "cuda", "float16"
    except Exception:
        pass
    return "cpu", "int8"


def list_models():
    """Catalogue plus any converted models found in ./models/<name>/model.bin."""
    models = [dict(m) for m in MODELS]
    if os.path.isdir(LOCAL_MODEL_DIR):
        for name in sorted(os.listdir(LOCAL_MODEL_DIR)):
            path = os.path.join(LOCAL_MODEL_DIR, name)
            if os.path.isfile(os.path.join(path, "model.bin")):
                models.append(
                    {
                        "id": "local:" + name,
                        "repo": path,
                        "label": name + " (local)",
                        "size": "on disk",
                        "note": "Converted model from the models/ folder.",
                    }
                )
    return models


def resolve_repo(model_id):
    if model_id.startswith("local:"):
        return os.path.join(LOCAL_MODEL_DIR, model_id.split(":", 1)[1])
    if model_id in MODELS_BY_ID:
        return MODELS_BY_ID[model_id]["repo"]
    raise ValueError("Unknown model: " + model_id)


def is_malaysian_model(model_id):
    return "malaysian" in model_id.lower()


class ModelCache:
    """Keeps the last used model in memory so the next file starts instantly.

    Only one model is kept: large models use several GB of RAM/VRAM and a
    NUC or Jetson cannot hold two at once.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._key = None
        self._model = None
        self.device, self.compute_type = detect_device()

    def get(self, model_id):
        from faster_whisper import WhisperModel

        with self._lock:
            if self._key == model_id:
                return self._model
            self._model = None  # free the old model before loading the new one
            self._model = WhisperModel(
                resolve_repo(model_id),
                device=self.device,
                compute_type=self.compute_type,
                cpu_threads=os.cpu_count() or 4,
            )
            self._key = model_id
            return self._model
