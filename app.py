"""Transcriber web app: speech-to-text and summary for Malay, English and mixed.

Run:  python app.py            then open http://127.0.0.1:7860
      python app.py --host 0.0.0.0   to use it from another device on your LAN
"""

import argparse
import os
import tempfile
import threading
import webbrowser

from flask import Flask, Response, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

from stt import engine, export, summary
from stt.jobs import JobManager
from stt.models import list_models

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "transcriber-uploads")


def downloaded_models():
    """Model ids whose weights are already in the Hugging Face cache."""
    try:
        from faster_whisper.utils import _MODELS
        from huggingface_hub.constants import HF_HUB_CACHE
    except ImportError:
        return []
    found = []
    for model in list_models():
        repo = _MODELS.get(model["repo"], model["repo"])
        if os.path.isdir(repo):  # local converted model
            found.append(model["id"])
        elif os.path.isdir(os.path.join(HF_HUB_CACHE, "models--" + repo.replace("/", "--"))):
            found.append(model["id"])
    return found


def create_app(manager=None):
    app = Flask(__name__, static_folder=None)
    app.config["MAX_CONTENT_LENGTH"] = 8 * 1024**3  # 8 GB, long videos are big
    app.json.sort_keys = False  # keep the language order as written
    jobs = manager or JobManager()
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    def find_job(job_id):
        job = jobs.get(job_id)
        if job is None:
            return None, (jsonify(error="Job not found. The server may have restarted."), 404)
        return job, None

    @app.get("/")
    def index():
        return send_from_directory(STATIC_DIR, "index.html")

    @app.get("/static/<path:name>")
    def static_files(name):
        return send_from_directory(STATIC_DIR, name)

    @app.get("/api/config")
    def config():
        return jsonify(
            models=list_models(),
            downloaded=downloaded_models(),
            languages=engine.LANGUAGES,
            device=jobs.models.device,
            ollama_models=summary.ollama_models(),
        )

    @app.post("/api/jobs")
    def create_job():
        upload = request.files.get("file")
        if upload is None or not upload.filename:
            return jsonify(error="Please choose an audio or video file."), 400

        options = {
            "model": request.form.get("model", "small"),
            "language": request.form.get("language", "mixed"),
            "quality": request.form.get("quality", "fast"),
            "vocabulary": request.form.get("vocabulary", "")[:500],
        }
        if options["model"] not in {m["id"] for m in list_models()}:
            return jsonify(error="Unknown model."), 400
        if options["language"] not in engine.LANGUAGES:
            return jsonify(error="Unknown language."), 400

        name = secure_filename(upload.filename) or "upload"
        fd, path = tempfile.mkstemp(dir=UPLOAD_DIR, suffix="-" + name)
        with os.fdopen(fd, "wb") as f:
            upload.save(f)
        job = jobs.submit(upload.filename, path, options)
        return jsonify(id=job.id), 201

    @app.get("/api/jobs/<job_id>")
    def job_status(job_id):
        job, error = find_job(job_id)
        if error:
            return error
        return jsonify(job.to_dict(since=request.args.get("since", 0, type=int)))

    @app.post("/api/jobs/<job_id>/cancel")
    def cancel_job(job_id):
        jobs.cancel(job_id)
        return jsonify(ok=True)

    @app.put("/api/jobs/<job_id>/segments")
    def save_edits(job_id):
        """The transcript is editable in the browser; exports use the edited text."""
        job, error = find_job(job_id)
        if error:
            return error
        if job.status != "done":
            return jsonify(error="Wait until transcription finishes."), 409
        edits = request.get_json(silent=True) or {}
        for index, text in edits.get("texts", {}).items():
            i = int(index)
            if 0 <= i < len(job.segments):
                job.segments[i]["text"] = str(text).strip()
        job.quick_summary = summary.quick_summary(job.segments)
        return jsonify(quick_summary=job.quick_summary)

    @app.post("/api/jobs/<job_id>/summary")
    def ai_summary(job_id):
        job, error = find_job(job_id)
        if error:
            return error
        body = request.get_json(silent=True) or {}
        if not body.get("model"):
            return jsonify(error="Choose an Ollama model."), 400
        jobs.start_ai_summary(job, body["model"], body.get("language", "same"))
        return jsonify(ok=True)

    @app.get("/api/jobs/<job_id>/export/<fmt>")
    def download(job_id, fmt):
        job, error = find_job(job_id)
        if error:
            return error
        if fmt not in export.FORMATS:
            return jsonify(error="Unknown format."), 400
        data = export.export(job.result(), fmt)
        base = os.path.splitext(secure_filename(job.filename) or "transcript")[0]
        return Response(
            data,
            mimetype=export.FORMATS[fmt],
            headers={"Content-Disposition": f'attachment; filename="{base}.{fmt}"'},
        )

    return app


def main():
    parser = argparse.ArgumentParser(description="Transcriber web app")
    parser.add_argument("--host", default="127.0.0.1", help="0.0.0.0 to allow other devices")
    parser.add_argument("--port", type=int, default=7860)
    parser.add_argument("--no-browser", action="store_true", help="do not open a browser tab")
    args = parser.parse_args()

    app = create_app()
    url = f"http://{'127.0.0.1' if args.host == '0.0.0.0' else args.host}:{args.port}"
    print(f"\n  Transcriber is running at {url}  (Ctrl+C to stop)\n")
    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    app.run(host=args.host, port=args.port, threaded=True)


if __name__ == "__main__":
    main()
