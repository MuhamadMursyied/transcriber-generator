"""Built-in summary model: a small instruction-tuned LLM run with CTranslate2.

CTranslate2 and the tokenizers library are already installed with
faster-whisper, so summaries work out of the box with no extra packages and
no Ollama. Qwen2.5 is used because it handles Malay and English well for its
size. Weights are downloaded once from Hugging Face on first use.
"""

import os
import threading

LLMS = {
    "qwen2.5-3b": {
        "repo": "jncraton/Qwen2.5-3B-Instruct-ct2-int8",
        "label": "Qwen2.5 3B",
        "size": "3.1 GB",
        "note": "Better summaries. Needs about 4 GB of free RAM.",
    },
    "qwen2.5-1.5b": {
        "repo": "jncraton/Qwen2.5-1.5B-Instruct-ct2-int8",
        "label": "Qwen2.5 1.5B",
        "size": "1.5 GB",
        "note": "About twice as fast. A rough draft: may miss tasks or slip into English.",
    },
}
DEFAULT_LLM = "qwen2.5-3b"

SYSTEM_PROMPT = (
    "You are a careful assistant that summarises recordings. You only use facts "
    "from the given text and never invent names, numbers or dates."
)
END_TOKENS = ["<|im_end|>", "<|endoftext|>"]


def is_downloaded(llm_id):
    try:
        from huggingface_hub import try_to_load_from_cache

        path = try_to_load_from_cache(LLMS[llm_id]["repo"], "model.bin")
        return isinstance(path, str)
    except Exception:
        return False


class LocalLLM:
    """Loads one summary model at a time and keeps it for the next summary."""

    def __init__(self):
        self._lock = threading.Lock()
        self._key = None
        self._generator = None
        self._tokenizer = None

    def _load(self, llm_id, on_progress):
        import ctranslate2
        from huggingface_hub import snapshot_download
        from tokenizers import Tokenizer

        if self._key == llm_id:
            return
        info = LLMS[llm_id]
        if on_progress and not is_downloaded(llm_id):
            on_progress(f"Downloading summary model ({info['size']}, first time only)")
        path = snapshot_download(info["repo"])

        if on_progress:
            on_progress("Loading summary model")
        if ctranslate2.get_cuda_device_count() > 0:
            device, compute_type = "cuda", "int8_float16"
        else:
            device, compute_type = "cpu", "int8"
        self._generator = None  # free the old model first
        self._generator = ctranslate2.Generator(
            path, device=device, compute_type=compute_type, intra_threads=os.cpu_count() or 4
        )
        self._tokenizer = Tokenizer.from_file(os.path.join(path, "tokenizer.json"))
        self._key = llm_id

    def generate(self, llm_id, prompt, on_progress=None, on_text=None, max_tokens=800):
        """Answer one prompt. on_text(partial_answer) is called while it writes."""
        with self._lock:
            self._load(llm_id, on_progress)
            chat = (
                f"<|im_start|>system\n{SYSTEM_PROMPT}<|im_end|>\n"
                f"<|im_start|>user\n{prompt}<|im_end|>\n"
                "<|im_start|>assistant\n"
            )
            tokens = self._tokenizer.encode(chat, add_special_tokens=False).tokens
            ids = []
            for step in self._generator.generate_tokens(
                tokens,
                max_length=max_tokens,
                sampling_topk=1,  # greedy: stable, factual output
                repetition_penalty=1.1,  # small models tend to repeat bullet points
                end_token=END_TOKENS,
            ):
                ids.append(step.token_id)
                if on_text and len(ids) % 8 == 0:
                    on_text(self._tokenizer.decode(ids))
            return self._tokenizer.decode(ids).strip()
