import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from srtat import __version__
from srtat.cli import main

SIMPLE = """1
00:00:01,000 --> 00:00:04,000
Hello there.

2
00:00:05,000 --> 00:00:08,500
General Kenobi.
"""

SIMPLE_VTT = """WEBVTT

1
00:00:01.000 --> 00:00:04.000
Hello there.

2
00:00:05.000 --> 00:00:08.500
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


class CliTextFormatTests(unittest.TestCase):

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

    def test_single_time_no_match(self):
        status, out = self._run("100")
        self.assertEqual(status, 0)
        self.assertEqual(out, "(no subtitle at this time)\n")

    def test_range_match(self):
        status, out = self._run("--range", "0", "9")
        self.assertEqual(status, 0)
        self.assertEqual(
            out,
            "#1 00:00:01,000 --> 00:00:04,000\nHello there.\n"
            "#2 00:00:05,000 --> 00:00:08,500\nGeneral Kenobi.\n",
        )

    def test_range_no_match(self):
        status, out = self._run("--range", "4.2", "4.8")
        self.assertEqual(status, 0)
        self.assertEqual(out, "(no subtitles in this range)\n")


class CliErrorHandlingTests(unittest.TestCase):

    def setUp(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        self.tmpdir = tmpdir.name
        self.srt_path = str(Path(self.tmpdir) / "movie.srt")
        Path(self.srt_path).write_text(SIMPLE, encoding="utf-8")

    def _run(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            status = main(list(args))
        return status, out.getvalue(), err.getvalue()

    def test_both_time_and_range_is_an_error(self):
        status, out, err = self._run(self.srt_path, "2.0", "--range", "0", "9")
        self.assertEqual(status, 1)
        self.assertIn("pass either a time or --range, not both", err)

    def test_neither_time_nor_range_is_an_error(self):
        status, out, err = self._run(self.srt_path)
        self.assertEqual(status, 1)
        self.assertIn("a time or --range is required", err)

    def test_missing_file_is_an_error(self):
        missing = str(Path(self.tmpdir) / "nope.srt")
        status, out, err = self._run(missing, "2.0")
        self.assertEqual(status, 1)
        self.assertIn("srtat:", err)

    def test_unparseable_file_is_an_error(self):
        vtt_path = str(Path(self.tmpdir) / "bad.vtt")
        Path(vtt_path).write_text("not a webvtt file\n", encoding="utf-8")
        status, out, err = self._run(vtt_path, "2.0")
        self.assertEqual(status, 1)
        self.assertIn("could not parse", err)

    def test_invalid_single_time_is_an_error(self):
        status, out, err = self._run(self.srt_path, "not-a-time")
        self.assertEqual(status, 1)
        self.assertIn("not a valid time", err)

    def test_invalid_range_time_is_an_error(self):
        status, out, err = self._run(self.srt_path, "--range", "not-a-time", "9")
        self.assertEqual(status, 1)
        self.assertIn("not a valid time range", err)

    def test_range_end_before_start_is_an_error(self):
        status, out, err = self._run(self.srt_path, "--range", "9", "0")
        self.assertEqual(status, 1)
        self.assertIn("--range end must be after start", err)


class CliVersionTests(unittest.TestCase):

    def test_version_flag_prints_version_and_exits_zero(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            with self.assertRaises(SystemExit) as cm:
                main(["--version"])
        self.assertEqual(cm.exception.code, 0)
        self.assertIn(__version__, out.getvalue())


class CliVttDispatchTests(unittest.TestCase):

    def setUp(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        self.vtt_path = str(Path(tmpdir.name) / "movie.vtt")
        Path(self.vtt_path).write_text(SIMPLE_VTT, encoding="utf-8")

    def test_vtt_extension_is_parsed_as_webvtt(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            status = main([self.vtt_path, "2.0"])
        self.assertEqual(status, 0)
        self.assertEqual(out.getvalue(), "#1\nHello there.\n")


if __name__ == "__main__":
    unittest.main()
