"""Two free, local ways to summarise a transcript.

1. quick_summary: picks the most important sentences (extractive). No model,
   instant, works for Malay, English and mixed speech.
2. ollama_summary: writes a real summary with a local LLM through Ollama
   (https://ollama.com), if it is installed. Still free and offline.
"""

import json
import os
import re
import urllib.error
import urllib.request
from collections import Counter

# Common words that carry no topic meaning, in both languages plus casual
# Malaysian speech fillers.
STOPWORDS = set(
    """
    a about above after again against all also am an and any are as at be because been
    before being below between both but by can could did do does doing down during each
    few for from further had has have having he her here hers him his how i if in into is
    it its itself just let me more most my no nor not now of off on once only or other our
    out over own same she should so some such than that the their them then there these
    they this those through to too under until up very was we were what when where which
    while who whom why will with would you your yours yeah okay ok oh uh um like really
    actually basically right so gonna wanna got get going thing things know think mean
    one two well yes
    ada adalah agar akan aku anda apa apabila atau bagi bahawa bahkan banyak beberapa
    belum benar berada boleh bukan dalam dan dapat dari daripada dengan dia dorang
    hanya hendak ia ialah ini itu jadi jika juga kalau kami kamu kan kat ke kepada
    kerana ketika kita lagi lah lain macam mahu mana masih maka mereka nak nanti oleh
    pada para pernah pula saja sahaja saya sangat sebab sebagai sebelum sedang sejak
    selepas semua seperti serta setiap sini situ sudah supaya tak tapi telah tentang
    tetapi tidak untuk yang ya lepas tu ni pun dah tadi la je jer ke kot kut camne
    macamana betul memang mungkin cuma tahu nampak buat bila nak kena orang
    selamat pagi petang malam terima kasih hari minggu semalam esok okey alright
    thank thanks hello hi everyone today yesterday tomorrow next first second
    """.split()
)

WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z'\-]+")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def _words(text):
    return [w.lower() for w in WORD_RE.findall(text)]


def _sentences(segments):
    """Split segments into sentences, each keeping the time it starts at.

    Very short fragments are joined to the next one so a key point is never
    just "Okay." or "So,".
    """
    sentences = []
    pending = None
    for seg in segments:
        for part in SENTENCE_SPLIT_RE.split(seg["text"].strip()):
            part = part.strip()
            if not part:
                continue
            if pending:
                pending["text"] += " " + part
            else:
                pending = {"start": seg["start"], "text": part}
            if len(_words(pending["text"])) >= 5:
                sentences.append(pending)
                pending = None
    if pending:
        sentences.append(pending)
    return sentences


def quick_summary(segments, max_points=None):
    """Return {"key_points": [{"start", "text"}], "keywords": [str]}."""
    sentences = _sentences(segments)
    if not sentences:
        return {"key_points": [], "keywords": []}

    counts = Counter(
        w for s in sentences for w in _words(s["text"]) if w not in STOPWORDS and len(w) > 2
    )
    if not counts:
        return {"key_points": [], "keywords": []}
    top = counts.most_common(1)[0][1]

    def score(sentence):
        words = [w for w in _words(sentence["text"]) if w in counts]
        if len(words) < 3:
            return 0.0
        # Average word importance, square-rooted length so long sentences are
        # not favoured just for being long.
        return sum(counts[w] / top for w in words) / len(words) ** 0.5

    if max_points is None:
        # About one point per 5 sentences, between 3 and 12.
        max_points = max(3, min(12, round(len(sentences) / 5)))

    ranked = sorted(range(len(sentences)), key=lambda i: score(sentences[i]), reverse=True)
    chosen = sorted(i for i in ranked[:max_points] if score(sentences[i]) > 0)
    keywords = [w for w, n in counts.most_common(12) if n > 1]

    return {"key_points": [sentences[i] for i in chosen], "keywords": keywords}


# ---------------------------------------------------------------- Ollama ----

OLLAMA_URL = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
if not OLLAMA_URL.startswith("http"):
    OLLAMA_URL = "http://" + OLLAMA_URL

# Characters per request. Roughly 3k tokens, which fits the context window of
# small 3B-8B models while leaving room for the answer.
CHUNK_CHARS = 10000

LANGUAGE_NAMES = {
    "ms": "Bahasa Melayu",
    "en": "English",
    "same": "the same language as the transcript (Malay, English, or a natural mix)",
}

HEADINGS = {
    "en": ("Summary", "Key points", "Action items", "None"),
    "ms": ("Ringkasan", "Perkara utama", "Tindakan susulan", "Tiada"),
}


def ollama_models():
    """Names of models installed in Ollama, or [] when Ollama is not running."""
    try:
        with urllib.request.urlopen(OLLAMA_URL + "/api/tags", timeout=1.5) as resp:
            data = json.load(resp)
        return sorted(m["name"] for m in data.get("models", []))
    except (urllib.error.URLError, OSError, ValueError):
        return []


def _ollama_generate(model, prompt):
    body = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2, "num_ctx": 8192},
        }
    ).encode()
    req = urllib.request.Request(
        OLLAMA_URL + "/api/generate", data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=900) as resp:
        return json.load(resp)["response"].strip()


def _chunks(text, size=CHUNK_CHARS):
    words = text.split()
    chunk, length = [], 0
    for word in words:
        if length + len(word) > size and chunk:
            yield " ".join(chunk)
            chunk, length = [], 0
        chunk.append(word)
        length += len(word) + 1
    if chunk:
        yield " ".join(chunk)


def ollama_summary(text, model, language="same", on_progress=None):
    """Summarise with a local LLM. Long transcripts are summarised in parts
    first, then the part summaries are combined (map-reduce)."""
    lang = LANGUAGE_NAMES.get(language, LANGUAGE_NAMES["same"])
    parts = list(_chunks(text))

    if len(parts) > 1:
        notes = []
        for i, part in enumerate(parts, 1):
            if on_progress:
                on_progress(f"Summarising part {i} of {len(parts)}")
            notes.append(
                _ollama_generate(
                    model,
                    "Below is part of a recording transcript. It may mix Malay and English. "
                    "Write concise bullet-point notes of the important facts, decisions, "
                    f"numbers, names and action items. Write in {lang}.\n\n"
                    f"TRANSCRIPT PART {i}:\n{part}",
                )
            )
        source = "\n\n".join(notes)
        source_label = "NOTES FROM EACH PART OF THE RECORDING"
    else:
        source = text
        source_label = "TRANSCRIPT"

    if on_progress:
        on_progress("Writing final summary")
    summary, key_points, actions, none = HEADINGS["ms" if language == "ms" else "en"]
    return _ollama_generate(
        model,
        "You summarise recordings such as meetings, lectures and interviews. The text may "
        f"mix Malay and English. Write the answer in {lang}, in Markdown, using exactly "
        "these sections:\n"
        f"## {summary}\nA short paragraph (3-5 sentences).\n"
        f"## {key_points}\nBullet points of the main points.\n"
        f"## {actions}\nBullet points of tasks, owners and deadlines, or '{none}'.\n\n"
        "Only use information from the text. Do not invent details.\n\n"
        f"{source_label}:\n{source}",
    )
