"""Command-line transcription, for scripts and headless machines (NUC, Jetson).

Examples:
  python cli.py meeting.mp4
  python cli.py lecture.m4a --model large-v3-turbo --language ms --format txt,srt,docx
  python cli.py *.mp3 --out transcripts/ --ollama qwen2.5:3b
"""

import argparse
import os
import sys
import time

from stt import engine, export, summary
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
    parser.add_argument("--ollama", default=None, metavar="MODEL",
                        help="also write an AI summary with this Ollama model")
    args = parser.parse_args()

    formats = [f.strip() for f in args.format.split(",") if f.strip()]
    for fmt in formats:
        if fmt not in export.FORMATS:
            parser.error(f"unknown format '{fmt}'")

    models = ModelCache()
    print(f"Loading model '{args.model}' on {models.device} ({models.compute_type})...")
    model = models.get(args.model)

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
        if args.ollama:
            print(f"Summarising with {args.ollama}...")
            text = " ".join(s["text"] for s in segments)
            summary_data["ai"] = summary.ollama_summary(text, args.ollama)
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
