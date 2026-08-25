import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from srtat.cli import main

SIMPLE = """1
00:00:01,000 --> 00:00:04,000
Hello there.

2
00:00:05,000 --> 00:00:08,500
General Kenobi.
"""


class CliJsonFormatTests(unittest.TestCase):

    def setUp(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        self.srt_path = str(Path(tmpdir.name) / "movie.srt")
        Path(self.srt_path).write_text(SIMPLE, encoding="utf-8")

    def _run(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            status = main([self.srt_path, *args])
        return status, out.getvalue()

    def test_single_time_match(self):
        status, out = self._run("2.0", "--format", "json")
        self.assertEqual(status, 0)
        payload = json.loads(out)
        self.assertEqual(len(payload), 1)
        cue = payload[0]
        self.assertEqual(cue["index"], 1)
        self.assertEqual(cue["start_ms"], 1000)
        self.assertEqual(cue["end_ms"], 4000)
        self.assertEqual(cue["start"], "00:00:01,000")
        self.assertEqual(cue["end"], "00:00:04,000")
        self.assertEqual(cue["text"], "Hello there.")

    def test_single_time_no_match_is_empty_array(self):
        status, out = self._run("100", "--format", "json")
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(out), [])

    def test_range_match(self):
        status, out = self._run("--range", "0", "9", "--format", "json")
        self.assertEqual(status, 0)
        payload = json.loads(out)
        self.assertEqual([cue["index"] for cue in payload], [1, 2])

    def test_range_no_match_is_empty_array(self):
        status, out = self._run("--range", "4.2", "4.8", "--format", "json")
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(out), [])

    def test_default_format_is_text_not_json(self):
        status, out = self._run("2.0")
        self.assertEqual(status, 0)
        self.assertEqual(out, "#1\nHello there.\n")


if __name__ == "__main__":
    unittest.main()
