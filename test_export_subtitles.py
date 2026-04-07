import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
import stt_routes

app = Flask(__name__)
app.register_blueprint(stt_routes.stt_bp)


class SubtitleExportTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self._saved_jobs = dict(stt_routes.stt_jobs)
        stt_routes.stt_jobs.clear()

    def tearDown(self):
        stt_routes.stt_jobs.clear()
        stt_routes.stt_jobs.update(self._saved_jobs)

    def add_job(self, job_id: str, segments: list, filename: str = "sample.mp4"):
        stt_routes.stt_jobs[job_id] = {
            "job_id": job_id,
            "filename": filename,
            "model_id": "test-model",
            "status": "done",
            "segments": segments,
            "error": None,
            "created_at": 0,
        }

    def test_txt_export_preserves_original_punctuation(self):
        self.add_job(
            "job-txt",
            [
                {"index": 0, "start": 0.0, "end": 1.0, "text": "你好，世界！"},
                {"index": 1, "start": 2.0, "end": 3.0, "text": "Hello, world."},
            ],
        )

        response = self.client.get("/api/stt/export/job-txt?format=txt&lang=zh")

        self.assertEqual(response.status_code, 200)
        content = response.get_data(as_text=True)
        self.assertIn("你好，世界！", content)
        self.assertIn("Hello, world.", content)

    def test_srt_export_normalizes_cjk_and_skips_empty_cues(self):
        self.add_job(
            "job-srt-cjk",
            [
                {"index": 0, "start": 0.0, "end": 1.0, "text": "你好，世界！"},
                {"index": 1, "start": 3.0, "end": 3.2, "text": "。"},
                {"index": 2, "start": 6.0, "end": 7.0, "text": "今天，我们去西安。"},
            ],
        )

        response = self.client.get("/api/stt/export/job-srt-cjk?format=srt&lang=zh")

        self.assertEqual(response.status_code, 200)
        content = response.get_data(as_text=True)
        self.assertIn("你好　世界", content)
        self.assertIn("今天　我们去西安", content)
        self.assertNotIn("你好，世界！", content)
        self.assertNotIn("今天，我们去西安。", content)
        self.assertNotIn("\n。\n", content)
        self.assertIn("1\n00:00:00,000 --> 00:00:01,000\n你好　世界\n", content)
        self.assertIn("2\n00:00:06,000 --> 00:00:07,000\n今天　我们去西安\n", content)

    def test_srt_export_keeps_english_punctuation(self):
        self.add_job(
            "job-srt-en",
            [
                {"index": 0, "start": 0.0, "end": 1.0, "text": "Hello, world."},
                {"index": 1, "start": 2.0, "end": 3.0, "text": "I'm fine."},
            ],
        )

        response = self.client.get("/api/stt/export/job-srt-en?format=srt&lang=en")

        self.assertEqual(response.status_code, 200)
        content = response.get_data(as_text=True)
        self.assertIn("Hello, world.", content)
        self.assertIn("I'm fine.", content)

    def test_vtt_export_applies_same_policy(self):
        self.add_job(
            "job-vtt",
            [
                {"index": 0, "start": 0.0, "end": 1.0, "text": "今天是 Monday，天气不错。"},
                {"index": 1, "start": 3.0, "end": 3.2, "text": "！"},
                {"index": 2, "start": 5.0, "end": 6.0, "text": "Hello, world."},
            ],
        )

        response = self.client.get("/api/stt/export/job-vtt?format=vtt&lang=zh")

        self.assertEqual(response.status_code, 200)
        content = response.get_data(as_text=True)
        self.assertTrue(content.startswith("WEBVTT"))
        self.assertIn("今天是 Monday　天气不错", content)
        self.assertIn("Hello, world.", content)
        self.assertNotIn("今天是 Monday，天气不错。", content)
        self.assertNotIn("\n！\n", content)


if __name__ == "__main__":
    unittest.main()
