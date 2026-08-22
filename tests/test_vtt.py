import unittest

from srtat.parser import SubtitleParseError, at
from srtat.vtt import parse_vtt, parse_vtt_timestamp

SIMPLE = """WEBVTT

1
00:00:01.000 --> 00:00:04.000
Hello there.

2
00:00:05.000 --> 00:00:08.500
General Kenobi.
"""


class VttTimestampParsingTests(unittest.TestCase):

    CASES = [
        ("with hours", "00:00:01.500", 1500),
        ("without hours", "00:01.500", 1500),
        ("single digit millis", "00:00:01.5", 1500),
        ("zero", "00:00:00.000", 0),
        ("hours and minutes", "01:02:03.004", 3_723_004),
    ]

    def test_cases(self):
        for name, raw, expected_ms in self.CASES:
            with self.subTest(name):
                self.assertEqual(parse_vtt_timestamp(raw), expected_ms)

    def test_garbage_raises(self):
        with self.assertRaises(SubtitleParseError):
            parse_vtt_timestamp("not a time")


class ParseVttFilesTests(unittest.TestCase):

    def test_simple_file(self):
        cues = parse_vtt(SIMPLE)
        self.assertEqual(len(cues), 2)
        self.assertEqual(cues[0].text, "Hello there.")
        self.assertEqual(cues[1].text, "General Kenobi.")

    def test_missing_header_raises(self):
        with self.assertRaises(SubtitleParseError):
            parse_vtt(SIMPLE.replace("WEBVTT\n\n", ""))

    def test_header_with_metadata(self):
        text = SIMPLE.replace("WEBVTT\n", "WEBVTT\nKind: captions\nLanguage: en\n")
        cues = parse_vtt(text)
        self.assertEqual(len(cues), 2)

    def test_bom_prefix(self):
        cues = parse_vtt("﻿" + SIMPLE)
        self.assertEqual(len(cues), 2)

    def test_crlf_line_endings(self):
        cues = parse_vtt(SIMPLE.replace("\n", "\r\n"))
        self.assertEqual(len(cues), 2)

    def test_missing_identifier_line(self):
        text = "WEBVTT\n\n00:00:01.000 --> 00:00:04.000\nNo identifier here.\n"
        cues = parse_vtt(text)
        self.assertEqual(len(cues), 1)
        self.assertEqual(cues[0].text, "No identifier here.")

    def test_non_numeric_identifier_falls_back_to_position(self):
        text = "WEBVTT\n\nintro-cue\n00:00:01.000 --> 00:00:04.000\nWeird id.\n"
        cues = parse_vtt(text)
        self.assertEqual(cues[0].index, 1)
        self.assertEqual(cues[0].text, "Weird id.")

    def test_cue_settings_are_ignored(self):
        text = (
            "WEBVTT\n\n"
            "1\n00:00:01.000 --> 00:00:04.000 align:middle line:90%\nStyled cue.\n"
        )
        cues = parse_vtt(text)
        self.assertEqual(cues[0].start_ms, 1000)
        self.assertEqual(cues[0].end_ms, 4000)
        self.assertEqual(cues[0].text, "Styled cue.")

    def test_note_block_is_skipped(self):
        text = (
            "WEBVTT\n\n"
            "NOTE this is a comment\nspanning lines\n\n"
            "1\n00:00:01.000 --> 00:00:04.000\nActual cue.\n"
        )
        cues = parse_vtt(text)
        self.assertEqual(len(cues), 1)
        self.assertEqual(cues[0].text, "Actual cue.")

    def test_style_block_is_skipped(self):
        text = (
            "WEBVTT\n\n"
            "STYLE\n::cue { color: yellow; }\n\n"
            "1\n00:00:01.000 --> 00:00:04.000\nActual cue.\n"
        )
        cues = parse_vtt(text)
        self.assertEqual(len(cues), 1)

    def test_multiline_cue_text(self):
        text = "WEBVTT\n\n1\n00:00:01.000 --> 00:00:04.000\nLine one\nLine two\n"
        cues = parse_vtt(text)
        self.assertEqual(cues[0].text, "Line one\nLine two")


class VttLookupTests(unittest.TestCase):

    def test_lookup_matches_srt_semantics(self):
        cues = parse_vtt(SIMPLE)
        self.assertEqual(len(at(cues, 2000)), 1)
        self.assertEqual(len(at(cues, 4000)), 0)
        self.assertEqual(len(at(cues, 4500)), 0)


if __name__ == "__main__":
    unittest.main()
