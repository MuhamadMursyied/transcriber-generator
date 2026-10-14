"""Tests for export, summary and option building. Run: python -m unittest -v"""

import io
import unittest
import zipfile

from stt import engine, export, summary

SEGMENTS = [
    {"start": 0.0, "end": 3.2, "text": "Selamat pagi semua, hari ini kita bincang pasal robot UGV."},
    {"start": 3.4, "end": 7.9, "text": "So the robot UGV needs a new navigation stack for the farm."},
    {"start": 8.0, "end": 9.0, "text": "Okay."},
    {"start": 12.5, "end": 17.0, "text": "Kita kena siapkan navigation stack sebelum hujung bulan ni."},
    {"start": 17.2, "end": 21.0, "text": "Hafiz akan test robot UGV di ladang minggu depan."},
]


class ExportTests(unittest.TestCase):
    def test_clock(self):
        self.assertEqual(export.clock(3725.5), "01:02:05.500")
        self.assertEqual(export.clock(1.25, ","), "00:00:01,250")
        self.assertEqual(export.short_clock(65), "1:05")
        self.assertEqual(export.short_clock(3725), "1:02:05")

    def test_srt(self):
        srt = export.to_srt(SEGMENTS[:2])
        self.assertTrue(srt.startswith("1\n00:00:00,000 --> 00:00:03,200\nSelamat pagi"))
        self.assertIn("2\n00:00:03,400 --> 00:00:07,900\n", srt)

    def test_vtt(self):
        self.assertTrue(export.to_vtt(SEGMENTS).startswith("WEBVTT\n\n00:00:00.000 --> "))

    def test_paragraphs_break_on_long_pause(self):
        paras = export.paragraphs(SEGMENTS)
        self.assertEqual(len(paras), 2)  # 9.0 -> 12.5 is a 3.5 s pause
        self.assertEqual(paras[1]["start"], 12.5)

    def test_docx_is_valid_zip_with_text(self):
        data = export.to_docx(
            {"title": "Mesyuarat <1>", "meta": "File: a.mp3", "segments": SEGMENTS,
             "summary": {"ai": "## Ringkasan\nIni **penting**.\n- Satu\n- Dua"}}
        )
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            self.assertIn("word/styles.xml", z.namelist())
            xml = z.read("word/document.xml").decode()
        self.assertIn("Mesyuarat &lt;1&gt;", xml)  # escaped
        self.assertIn("Ringkasan", xml)
        self.assertIn("navigation stack", xml)

    def test_export_unknown_format(self):
        with self.assertRaises(ValueError):
            export.export({"segments": []}, "pdf")


class SummaryTests(unittest.TestCase):
    def test_quick_summary_finds_topic(self):
        result = summary.quick_summary(SEGMENTS, max_points=2)
        self.assertEqual(len(result["key_points"]), 2)
        self.assertIn("robot", result["keywords"])
        self.assertIn("ugv", result["keywords"])
        # Key points stay in the order they were spoken.
        starts = [p["start"] for p in result["key_points"]]
        self.assertEqual(starts, sorted(starts))

    def test_short_fragments_are_joined(self):
        sentences = summary._sentences([{"start": 0, "end": 1, "text": "Okay. So."},
                                        {"start": 1, "end": 4, "text": "We start the robot now today."}])
        self.assertEqual(len(sentences), 1)
        self.assertEqual(sentences[0]["start"], 0)

    def test_empty(self):
        self.assertEqual(summary.quick_summary([]), {"key_points": [], "keywords": []})

    def test_ai_summary_single_pass(self):
        prompts = []

        def generate(prompt, on_text):
            prompts.append(prompt)
            return "## Ringkasan\nOk."

        out = summary.ai_summary("Robot UGV diuji di ladang.", generate, "ms")
        self.assertEqual(out, "## Ringkasan\nOk.")
        self.assertEqual(len(prompts), 1)
        self.assertIn("## Perkara utama", prompts[0])
        self.assertIn("Bahasa Melayu", prompts[0])

    def test_ai_summary_map_reduce_for_long_text(self):
        prompts = []

        def generate(prompt, on_text):
            prompts.append(prompt)
            return f"- note {len(prompts)}"

        text = " ".join(["perkataan"] * 3000)  # ~30k characters -> several parts
        summary.ai_summary(text, generate, "en")
        self.assertGreater(len(prompts), 2)
        self.assertIn("part 1 of", prompts[0])
        self.assertIn("NOTES FROM EACH PART", prompts[-1])
        self.assertIn("- note 1", prompts[-1])
        self.assertIn("## Action items", prompts[-1])

    def test_chunks_cover_all_words(self):
        text = " ".join(f"w{i}" for i in range(5000))
        parts = list(summary._chunks(text, size=1000))
        self.assertGreater(len(parts), 1)
        self.assertEqual(" ".join(parts), text)


class OptionTests(unittest.TestCase):
    def test_mixed_uses_per_segment_detection(self):
        opts = engine.build_options("mixed", "small", "fast")
        self.assertIsNone(opts["language"])
        self.assertTrue(opts["multilingual"])
        self.assertEqual(opts["beam_size"], 1)
        self.assertIn("discuss", opts["initial_prompt"])

    def test_mixed_on_malaysian_model_uses_ms(self):
        opts = engine.build_options("mixed", "malaysian-turbo", "accurate")
        self.assertEqual(opts["language"], "ms")
        self.assertNotIn("multilingual", opts)
        self.assertEqual(opts["beam_size"], 5)

    def test_vocabulary_goes_into_prompt(self):
        opts = engine.build_options("en", "small", "fast", "UMPSA, ROS 2")
        self.assertEqual(opts["language"], "en")
        self.assertEqual(opts["initial_prompt"], "UMPSA, ROS 2")


if __name__ == "__main__":
    unittest.main()
