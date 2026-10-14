"""Command-line transcription, for scripts and headless machines (NUC, Jetson).

Examples:
  python cli.py meeting.mp4
  python cli.py lecture.m4a --model large-v3-turbo --language ms --format txt,srt,docx
  python cli.py meeting.mp4 --summary                  # + AI summary (built-in model)
  python cli.py *.mp3 --out transcripts/ --ollama qwen2.5:7b
"""

import argparse
import os
import sys
import time

from stt import engine, export, llm, summary
from stt.models import ModelCache, list_models


def main():
    model_ids = [m["id"] for m in list_models()]
    parser = argparse.ArgumentParser(description="Transcribe audio/video to text.")
    parser.add_argument("files", nargs="+", help="audio or video files")
    parser.add_argument("--model", default="small", choices=model_ids)
    parser.add_argument("--language", default="mixed", choices=list(engine.LANGUAGES))
    parser.add_argument("--quality", default="fast", choices=["fast", "accurate"])
    parser.add_argument("--vocabulary", default="", help="names or terms to spell correctly")
    parser.add_argument("--format", default="txt,srt,docx",
                        help="comma list of: " + ", ".join(export.FORMATS))
    parser.add_argument("--out", default=None, help="output folder (default: next to input)")
    parser.add_argument("--summary", nargs="?", const=llm.DEFAULT_LLM, default=None,
                        choices=list(llm.LLMS),
                        help=f"also write an AI summary with a built-in model "
                             f"(default {llm.DEFAULT_LLM})")
    parser.add_argument("--summary-language", default="auto", choices=["auto", "ms", "en"])
    parser.add_argument("--ollama", default=None, metavar="MODEL",
                        help="write the AI summary with this Ollama model instead")
    args = parser.parse_args()

    formats = [f.strip() for f in args.format.split(",") if f.strip()]
    for fmt in formats:
        if fmt not in export.FORMATS:
            parser.error(f"unknown format '{fmt}'")

    models = ModelCache()
    print(f"Loading model '{args.model}' on {models.device} ({models.compute_type})...")
    model = models.get(args.model)
    local_llm = llm.LocalLLM()  # loads the summary model only if --summary is used

    for path in args.files:
        print(f"\n== {path}")
        started = time.time()
        try:
            audio = engine.load_audio(path)
        except engine.AudioError as error:
            print(f"   skipped: {error}", file=sys.stderr)
            continue
        duration = len(audio) / engine.SAMPLE_RATE

        info, results = engine.transcribe(
            model, audio, args.language, args.model, args.quality, args.vocabulary, models.device
        )
        segments = []
        for seg, _ in results:
            segments.append(seg)
            print(f"[{export.short_clock(seg['start'])}] {seg['text']}")

        elapsed = time.time() - started
        print(f"-- {duration / 60:.1f} min of audio in {elapsed:.0f} s "
              f"({duration / max(elapsed, 0.01):.1f}x real time), language: {info.language}")

        summary_data = summary.quick_summary(segments)
        if args.summary or args.ollama:
            text = " ".join(s["text"] for s in segments)
            language = args.summary_language
            if language == "auto":
                language = "en" if info.language == "en" else "ms"
            if args.ollama:
                def generate(prompt, _on_text):
                    return summary.ollama_generate(args.ollama, prompt)
            else:
                def generate(prompt, _on_text):
                    return local_llm.generate(args.summary, prompt, on_progress=print)
            print("Writing AI summary...")
            summary_data["ai"] = summary.ai_summary(text, generate, language, on_progress=print)
            print(summary_data["ai"])

        base_name = os.path.splitext(os.path.basename(path))[0]
        out_dir = args.out or os.path.dirname(os.path.abspath(path))
        os.makedirs(out_dir, exist_ok=True)
        result = {
            "title": base_name,
            "meta": f"File: {os.path.basename(path)}  |  Model: {args.model}",
            "filename": os.path.basename(path),
            "duration": duration,
            "language": info.language,
            "segments": segments,
            "summary": summary_data,
        }
        for fmt in formats:
            out_path = os.path.join(out_dir, f"{base_name}.{fmt}")
            with open(out_path, "wb") as f:
                f.write(export.export(result, fmt))
            print(f"   wrote {out_path}")


if __name__ == "__main__":
    main()
