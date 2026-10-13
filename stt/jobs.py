"""Background jobs: one worker thread transcribes uploaded files in order.

One worker is deliberate. Whisper already uses every CPU core (or the whole
GPU), so running two files at once is slower than running them one by one.
"""

import os
import queue
import threading
import time
import uuid

from . import engine, summary
from .models import ModelCache

MAX_JOBS_KEPT = 20


class Cancelled(Exception):
    pass


class Job:
    def __init__(self, filename, path, options):
        self.id = uuid.uuid4().hex[:12]
        self.filename = filename
        self.path = path
        self.options = options
        self.status = "queued"  # queued, working, done, error, cancelled
        self.stage = "Waiting in queue"
        self.progress = 0.0
        self.segments = []
        self.duration = 0.0
        self.language = None
        self.elapsed = 0.0
        self.error = None
        self.quick_summary = None
        self.ai_summary = None
        self.ai_status = None  # None, working, done, error
        self.ai_stage = ""
        self.cancel_requested = False
        self.created = time.time()

    def to_dict(self, since=0):
        """State for the browser. `since` skips segments it already has."""
        return {
            "id": self.id,
            "filename": self.filename,
            "options": self.options,
            "status": self.status,
            "stage": self.stage,
            "progress": round(self.progress, 4),
            "duration": self.duration,
            "language": self.language,
            "elapsed": round(self.elapsed, 1),
            "error": self.error,
            "segment_count": len(self.segments),
            "segments": self.segments[since:],
            "since": since,
            "quick_summary": self.quick_summary,
            "ai_summary": self.ai_summary,
            "ai_status": self.ai_status,
            "ai_stage": self.ai_stage,
        }

    def result(self):
        """Everything the exporters need."""
        meta = [
            f"File: {self.filename}",
            f"Length: {_duration_text(self.duration)}",
            f"Model: {self.options.get('model')}",
            f"Language: {engine.LANGUAGES.get(self.options.get('language'), '')}",
            "Created: " + time.strftime("%Y-%m-%d %H:%M", time.localtime(self.created)),
        ]
        summary_data = dict(self.quick_summary or {})
        if self.ai_summary:
            summary_data["ai"] = self.ai_summary
        return {
            "title": os.path.splitext(self.filename)[0],
            "meta": "  |  ".join(meta),
            "filename": self.filename,
            "duration": self.duration,
            "language": self.language,
            "options": self.options,
            "segments": self.segments,
            "summary": summary_data,
        }


def _duration_text(seconds):
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h}h {m}m {s}s" if h else f"{m}m {s}s"


class JobManager:
    def __init__(self, models=None, transcribe_fn=None, load_audio_fn=None):
        # The *_fn arguments let tests swap in a fake engine.
        self.models = models or ModelCache()
        self.transcribe_fn = transcribe_fn or engine.transcribe
        self.load_audio_fn = load_audio_fn or engine.load_audio
        self.jobs = {}
        self.queue = queue.Queue()
        self.lock = threading.Lock()
        threading.Thread(target=self._worker, daemon=True).start()

    def submit(self, filename, path, options):
        job = Job(filename, path, options)
        with self.lock:
            self.jobs[job.id] = job
            self._forget_old_jobs()
        self.queue.put(job)
        return job

    def get(self, job_id):
        return self.jobs.get(job_id)

    def cancel(self, job_id):
        job = self.jobs.get(job_id)
        if job and job.status in ("queued", "working"):
            job.cancel_requested = True

    def _forget_old_jobs(self):
        finished = [j for j in self.jobs.values() if j.status in ("done", "error", "cancelled")]
        finished.sort(key=lambda j: j.created)
        while len(self.jobs) > MAX_JOBS_KEPT and finished:
            self.jobs.pop(finished.pop(0).id, None)

    def _worker(self):
        while True:
            job = self.queue.get()
            try:
                self._run(job)
            except Cancelled:
                job.status, job.stage = "cancelled", "Cancelled"
            except Exception as error:  # show any failure in the UI instead of dying
                job.status, job.stage, job.error = "error", "Failed", str(error)
            finally:
                if os.path.exists(job.path):
                    os.remove(job.path)

    def _run(self, job):
        if job.cancel_requested:
            raise Cancelled()
        job.status = "working"
        started = time.time()
        opts = job.options

        job.stage = "Reading audio"
        audio = self.load_audio_fn(job.path)
        job.duration = round(len(audio) / engine.SAMPLE_RATE, 2)

        job.stage = "Loading model (the first time it downloads, please wait)"
        model = self.models.get(opts["model"])

        job.stage = "Transcribing"
        info, segments = self.transcribe_fn(
            model,
            audio,
            language=opts["language"],
            model_id=opts["model"],
            quality=opts["quality"],
            vocabulary=opts.get("vocabulary", ""),
            device=self.models.device,
        )
        job.language = getattr(info, "language", None)
        for segment, progress in segments:
            if job.cancel_requested:
                raise Cancelled()
            job.segments.append(segment)
            job.progress = progress
            job.elapsed = time.time() - started

        job.quick_summary = summary.quick_summary(job.segments)
        job.progress = 1.0
        job.elapsed = time.time() - started
        job.status, job.stage = "done", "Done"

    def start_ai_summary(self, job, model, language):
        if job.ai_status == "working":
            return
        job.ai_status, job.ai_stage, job.ai_summary = "working", "Starting", None

        def run():
            def on_progress(stage):
                job.ai_stage = stage

            try:
                text = " ".join(s["text"] for s in job.segments)
                job.ai_summary = summary.ollama_summary(text, model, language, on_progress)
                job.ai_status, job.ai_stage = "done", "Done"
            except Exception as error:
                job.ai_status, job.ai_stage = "error", f"Ollama failed: {error}"

        threading.Thread(target=run, daemon=True).start()
