"""Parsing for WebVTT (.vtt) subtitle files.

WebVTT looks a lot like SRT but differs in a few ways that matter for
parsing: a required "WEBVTT" header, NOTE/STYLE/REGION blocks that aren't
cues, optional (and non-numeric) cue identifiers, cue settings trailing the
timing line, and timestamps that can drop the hours field entirely.
"""

from __future__ import annotations

import re
import warnings

from .parser import Cue, SubtitleParseError, SubtitleParseWarning

# Unlike SRT, WebVTT timestamps may omit the hours field for cues under an
# hour in, so "01:02.500" and "00:01:02.500" both show up in the wild.
_VTT_TIMESTAMP_RE = re.compile(r"(?:(\d+):)?(\d{2}):(\d{2})\.(\d{1,3})")
_ARROW_RE = re.compile(r"-->")
_NON_CUE_PREFIXES = ("NOTE", "STYLE", "REGION")


def parse_vtt_timestamp(raw: str) -> int:
    """Parse a single WebVTT timestamp like '00:01:23.456' or '01:23.456'."""
    match = _VTT_TIMESTAMP_RE.search(raw.strip())
    if not match:
        raise SubtitleParseError(f"not a timestamp: {raw!r}")
    hours, minutes, seconds, millis = match.groups()
    millis = millis.ljust(3, "0")
    return (
        int(hours or 0) * 3_600_000
        + int(minutes) * 60_000
        + int(seconds) * 1_000
        + int(millis)
    )


def parse_vtt(text: str) -> list[Cue]:
    """Parse the contents of a .vtt file into a list of Cue objects, in order.

    A cue block with a malformed timing line is skipped rather than aborting
    the whole file; a SubtitleParseWarning is raised for each one skipped.
    """
    text = text.lstrip("﻿").replace("\r\n", "\n").replace("\r", "\n")
    blocks = re.split(r"\n\s*\n", text.strip())

    if not blocks or not blocks[0].lstrip().startswith("WEBVTT"):
        raise SubtitleParseError("not a WebVTT file: missing WEBVTT header")
    blocks = blocks[1:]

    cues: list[Cue] = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        lines = block.split("\n")

        if lines[0].strip().startswith(_NON_CUE_PREFIXES):
            continue

        if _ARROW_RE.search(lines[0]):
            identifier = None
            timing_line = lines[0]
            body_lines = lines[1:]
        else:
            if len(lines) < 2:
                continue
            if not _ARROW_RE.search(lines[1]):
                warnings.warn(
                    f"skipping cue {lines[0].strip()!r}: no --> in {lines[1]!r}",
                    SubtitleParseWarning,
                )
                continue
            identifier = lines[0].strip()
            timing_line = lines[1]
            body_lines = lines[2:]

        # Cue settings (e.g. "align:middle line:90%") trail the end
        # timestamp on the same line, separated by whitespace; drop them.
        start_raw, rest = timing_line.split("-->", 1)
        end_raw = rest.strip().split(maxsplit=1)[0]
        try:
            start_ms = parse_vtt_timestamp(start_raw)
            end_ms = parse_vtt_timestamp(end_raw)
        except SubtitleParseError as exc:
            label = repr(identifier) if identifier else f"at position {len(cues) + 1}"
            warnings.warn(f"skipping cue {label}: {exc}", SubtitleParseWarning)
            continue

        index = int(identifier) if identifier and identifier.isdigit() else len(cues) + 1
        cues.append(
            Cue(index=index, start_ms=start_ms, end_ms=end_ms, text="\n".join(body_lines))
        )
    return cues
