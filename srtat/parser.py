"""Parsing and time-based lookup for SubRip (.srt) subtitle files."""

from __future__ import annotations

import re
from dataclasses import dataclass

# Hours are technically two digits in the SubRip spec, but files produced by
# some encoders (very long streams, DVR captures) go past 99 hours, so accept
# any number of digits there.
_TIMESTAMP_RE = re.compile(r"(\d+):(\d{2}):(\d{2})[.,](\d{1,3})")
_ARROW_RE = re.compile(r"-->")


class SubtitleParseError(ValueError):
    """Raised when a .srt file (or a piece of one) can't be understood."""


@dataclass(frozen=True)
class Cue:
    index: int
    start_ms: int
    end_ms: int
    text: str

    def contains(self, ms: int) -> bool:
        # End time is exclusive so back-to-back cues don't both match the
        # exact millisecond where one ends and the next begins.
        return self.start_ms <= ms < self.end_ms


def parse_timestamp(raw: str) -> int:
    """Parse a single SubRip timestamp like '00:01:23,456' into milliseconds.

    Some files use a period instead of a comma before the milliseconds, and
    some pad the millisecond field to fewer than three digits. Both are
    accepted.
    """
    match = _TIMESTAMP_RE.search(raw.strip())
    if not match:
        raise SubtitleParseError(f"not a timestamp: {raw!r}")
    hours, minutes, seconds, millis = match.groups()
    millis = millis.ljust(3, "0")
    return (
        int(hours) * 3_600_000
        + int(minutes) * 60_000
        + int(seconds) * 1_000
        + int(millis)
    )


def format_timestamp(ms: int) -> str:
    """Format a millisecond offset as an SRT-style timestamp (HH:MM:SS,mmm)."""
    hours, rem = divmod(ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    seconds, millis = divmod(rem, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def parse(text: str) -> list[Cue]:
    """Parse the contents of a .srt file into a list of Cue objects, in order."""
    # A leading BOM and CRLF line endings both show up regularly in the wild;
    # normalize before splitting into blocks.
    text = text.lstrip("﻿").replace("\r\n", "\n").replace("\r", "\n")
    blocks = re.split(r"\n\s*\n", text.strip())

    cues: list[Cue] = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        lines = block.split("\n")

        if _ARROW_RE.search(lines[0]):
            # Some encoders drop the numeric index line entirely.
            timing_line = lines[0]
            body_lines = lines[1:]
            index = len(cues) + 1
        else:
            if len(lines) < 2:
                continue
            try:
                index = int(lines[0].strip())
            except ValueError:
                index = len(cues) + 1
            timing_line = lines[1]
            body_lines = lines[2:]

        if not _ARROW_RE.search(timing_line):
            raise SubtitleParseError(f"cue {index}: no --> in {timing_line!r}")

        start_raw, end_raw = timing_line.split("-->", 1)
        start_ms = parse_timestamp(start_raw)
        end_ms = parse_timestamp(end_raw)
        cues.append(
            Cue(index=index, start_ms=start_ms, end_ms=end_ms, text="\n".join(body_lines))
        )
    return cues


def at(cues: list[Cue], ms: int) -> list[Cue]:
    """Return every cue visible at the given millisecond offset.

    Usually zero or one, but overlapping cues (dueling dialogue, karaoke-style
    files) are common enough that this returns a list rather than assuming.
    """
    return [c for c in cues if c.contains(ms)]


def in_range(cues: list[Cue], start_ms: int, end_ms: int) -> list[Cue]:
    """Return every cue that overlaps the half-open window [start_ms, end_ms).

    A cue overlaps the window if any millisecond of the cue also falls in the
    window. Zero-duration cues never match, same as with `at`, since they
    have no millisecond that's actually on screen.
    """
    return [
        c
        for c in cues
        if c.start_ms < c.end_ms and c.start_ms < end_ms and start_ms < c.end_ms
    ]
