import unittest

from srtat.parser import (
    SubtitleParseError,
    at,
    format_timestamp,
    in_range,
    parse,
    parse_timestamp,
)

SIMPLE = """1
00:00:01,000 --> 00:00:04,000
Hello there.

2
00:00:05,000 --> 00:00:08,500
General Kenobi.
"""


class TimestampParsingTests(unittest.TestCase):

    CASES = [
        ("comma millis", "00:00:01,500", 1500),
        ("period millis", "00:00:01.500", 1500),
        ("single digit millis", "00:00:01,5", 1500),
        ("two digit millis", "00:00:01,50", 1500),
        ("zero", "00:00:00,000", 0),
        ("hours and minutes", "01:02:03,004", 3_723_004),
        ("three digit hours", "100:00:00,000", 360_000_000),
    ]

    def test_cases(self):
        for name, raw, expected_ms in self.CASES:
            with self.subTest(name):
                self.assertEqual(parse_timestamp(raw), expected_ms)

    def test_garbage_raises(self):
        with self.assertRaises(SubtitleParseError):
            parse_timestamp("not a time")


class ParseAwkwardFilesTests(unittest.TestCase):

    def test_simple_file(self):
        cues = parse(SIMPLE)
        self.assertEqual(len(cues), 2)
        self.assertEqual(cues[0].text, "Hello there.")

    def test_bom_prefix(self):
        cues = parse("﻿" + SIMPLE)
        self.assertEqual(len(cues), 2)

    def test_crlf_line_endings(self):
        cues = parse(SIMPLE.replace("\n", "\r\n"))
        self.assertEqual(len(cues), 2)
        self.assertEqual(cues[1].text, "General Kenobi.")

    def test_missing_index_line(self):
        text = "00:00:01,000 --> 00:00:04,000\nNo index here.\n"
        cues = parse(text)
        self.assertEqual(len(cues), 1)
        self.assertEqual(cues[0].text, "No index here.")

    def test_non_numeric_index_falls_back_to_position(self):
        text = "x\n00:00:01,000 --> 00:00:04,000\nWeird index.\n"
        cues = parse(text)
        self.assertEqual(cues[0].index, 1)
        self.assertEqual(cues[0].text, "Weird index.")

    def test_multiline_cue_text(self):
        text = "1\n00:00:01,000 --> 00:00:04,000\nLine one\nLine two\n"
        cues = parse(text)
        self.assertEqual(cues[0].text, "Line one\nLine two")

    def test_trailing_blank_lines_ignored(self):
        cues = parse(SIMPLE + "\n\n\n")
        self.assertEqual(len(cues), 2)

    def test_zero_duration_cue(self):
        text = "1\n00:00:01,000 --> 00:00:01,000\nBlink.\n"
        cues = parse(text)
        self.assertEqual(len(cues), 1)
        self.assertEqual(cues[0].start_ms, cues[0].end_ms)

    def test_malformed_timing_line_raises(self):
        text = "1\nnot a timing line\nsomething\n"
        with self.assertRaises(SubtitleParseError):
            parse(text)


class LookupTests(unittest.TestCase):

    def setUp(self):
        self.cues = parse(SIMPLE)

    CASES = [
        ("before first cue", 0, 0),
        ("inside first cue", 2000, 1),
        ("end boundary excluded", 4000, 0),
        ("gap between cues", 4500, 0),
        ("inside second cue", 6000, 1),
        ("after last cue", 9000, 0),
    ]

    def test_lookup_cases(self):
        for name, ms, expected_count in self.CASES:
            with self.subTest(name):
                self.assertEqual(len(at(self.cues, ms)), expected_count)

    def test_overlapping_cues_both_returned(self):
        text = (
            "1\n00:00:01,000 --> 00:00:05,000\nFirst.\n\n"
            "2\n00:00:03,000 --> 00:00:07,000\nSecond, overlapping.\n"
        )
        cues = parse(text)
        matches = at(cues, 4000)
        self.assertEqual(len(matches), 2)


class InRangeTests(unittest.TestCase):

    def setUp(self):
        self.cues = parse(SIMPLE)

    RANGE_CASES = [
        ("range before everything", 0, 500, 0),
        ("range wholly inside first cue", 2000, 3000, 1),
        ("range spans both cues and the gap", 0, 9000, 2),
        ("range touches only the gap", 4200, 4800, 0),
        ("range partially overlaps first cue's tail", 500, 1500, 1),
        ("range starts exactly where second cue ends", 8500, 9000, 0),
    ]

    def test_range_cases(self):
        for name, start_ms, end_ms, expected_count in self.RANGE_CASES:
            with self.subTest(name):
                self.assertEqual(len(in_range(self.cues, start_ms, end_ms)), expected_count)

    def test_zero_duration_cue_never_matches_a_range(self):
        text = "1\n00:00:01,000 --> 00:00:01,000\nBlink.\n"
        cues = parse(text)
        self.assertEqual(in_range(cues, 0, 5000), [])


class FormatTimestampTests(unittest.TestCase):

    def test_round_trips_with_parse_timestamp(self):
        for raw in ("00:00:01,500", "01:02:03,004", "00:00:00,000"):
            with self.subTest(raw):
                self.assertEqual(format_timestamp(parse_timestamp(raw)), raw)

    def test_pads_fields(self):
        self.assertEqual(format_timestamp(61_005), "00:01:01,005")


if __name__ == "__main__":
    unittest.main()
