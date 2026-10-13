"""Web API tests with a fake speech engine, so no model download is needed."""

import io
import time
import unittest
from types import SimpleNamespace

import numpy as np

from app import create_app
from stt.jobs import JobManager

FAKE_SEGMENTS = [
    {"start": 0.0, "end": 4.0, "text": "Selamat pagi, today we test the robot."},
    {"start": 4.0, "end": 8.0, "text": "Robot ini akan jalan di ladang sawit."},
]


class FakeModels:
    device = "cpu"

    def get(self, model_id):
        return object()


def fake_transcribe(model, audio, language, model_id, quality, vocabulary, device):
    def results():
        for seg in FAKE_SEGMENTS:
            time.sleep(0.05)
            yield dict(seg), seg["end"] / 8.0

    return SimpleNamespace(language="ms"), results()


def fake_load_audio(path):
    return np.zeros(16000 * 8, dtype=np.float32)


class AppTests(unittest.TestCase):
    def setUp(self):
        manager = JobManager(FakeModels(), fake_transcribe, fake_load_audio)
        self.client = create_app(manager).test_client()

    def upload(self, **form):
        data = {"file": (io.BytesIO(b"fake audio"), "mesyuarat.mp3"), **form}
        return self.client.post("/api/jobs", data=data, content_type="multipart/form-data")

    def wait_done(self, job_id):
        for _ in range(100):
            job = self.client.get(f"/api/jobs/{job_id}").get_json()
            if job["status"] not in ("queued", "working"):
                return job
            time.sleep(0.05)
        self.fail("job did not finish")

    def test_index_and_config(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        config = self.client.get("/api/config").get_json()
        self.assertIn("small", [m["id"] for m in config["models"]])
        self.assertIn("mixed", config["languages"])

    def test_full_flow(self):
        res = self.upload(model="small", language="mixed", quality="fast")
        self.assertEqual(res.status_code, 201)
        job_id = res.get_json()["id"]

        job = self.wait_done(job_id)
        self.assertEqual(job["status"], "done")
        self.assertEqual(len(job["segments"]), 2)
        self.assertEqual(job["language"], "ms")
        self.assertEqual(job["duration"], 8.0)
        self.assertTrue(job["quick_summary"]["key_points"])

        # Incremental polling only returns new segments.
        self.assertEqual(self.client.get(f"/api/jobs/{job_id}?since=2").get_json()["segments"], [])

        # Edits are used by exports.
        res = self.client.put(f"/api/jobs/{job_id}/segments", json={"texts": {"1": "Robot ini jalan di ladang."}})
        self.assertEqual(res.status_code, 200)
        srt = self.client.get(f"/api/jobs/{job_id}/export/srt")
        self.assertIn("attachment", srt.headers["Content-Disposition"])
        self.assertIn("Robot ini jalan di ladang.", srt.get_data(as_text=True))

        docx = self.client.get(f"/api/jobs/{job_id}/export/docx")
        self.assertEqual(docx.status_code, 200)
        self.assertEqual(docx.get_data()[:2], b"PK")

    def test_rejects_bad_input(self):
        self.assertEqual(self.client.post("/api/jobs", data={}).status_code, 400)
        self.assertEqual(self.upload(model="nope").status_code, 400)
        self.assertEqual(self.upload(language="fr").status_code, 400)
        self.assertEqual(self.client.get("/api/jobs/missing").status_code, 404)

    def test_cancel(self):
        job_id = self.upload().get_json()["id"]
        self.client.post(f"/api/jobs/{job_id}/cancel")
        job = self.wait_done(job_id)
        self.assertEqual(job["status"], "cancelled")


if __name__ == "__main__":
    unittest.main()
