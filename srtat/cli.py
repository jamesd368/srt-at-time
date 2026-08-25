"""Command line entry point: report which subtitle cue(s) are on screen at a given time."""

from __future__ import annotations

import argparse
import json
import sys

from .parser import (
    Cue,
    SubtitleParseError,
    at,
    format_timestamp,
    in_range,
    parse,
    parse_timestamp,
)
from .vtt import parse_vtt


def _parse_query_time(raw: str) -> int:
    raw = raw.strip()
    if ":" in raw:
        return parse_timestamp(raw)
    # Bare number: treat as seconds, decimals allowed (e.g. "83.4").
    return int(round(float(raw) * 1000))


def _cue_to_dict(cue: Cue) -> dict:
    return {
        "index": cue.index,
        "start_ms": cue.start_ms,
        "end_ms": cue.end_ms,
        "start": format_timestamp(cue.start_ms),
        "end": format_timestamp(cue.end_ms),
        "text": cue.text,
    }


def _load_cues(path: str) -> list[Cue]:
    with open(path, encoding="utf-8-sig") as fh:
        text = fh.read()
    if path.lower().endswith(".vtt"):
        return parse_vtt(text)
    return parse(text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="srtat",
        description="Show which subtitle cue is on screen at a given time.",
    )
    parser.add_argument("srt_file", help="path to a .srt or .vtt file")
    parser.add_argument(
        "time",
        nargs="?",
        help="timestamp to query: HH:MM:SS,mmm or plain seconds, e.g. 83.4",
    )
    parser.add_argument(
        "--range",
        nargs=2,
        metavar=("START", "END"),
        help="list every cue overlapping the window between START and END "
        "instead of querying a single instant",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="output format: human-readable text (default) or json",
    )
    args = parser.parse_args(argv)

    if args.range and args.time:
        print("srtat: pass either a time or --range, not both", file=sys.stderr)
        return 1
    if not args.range and not args.time:
        print("srtat: a time or --range is required", file=sys.stderr)
        return 1

    try:
        cues = _load_cues(args.srt_file)
    except OSError as exc:
        print(f"srtat: {exc}", file=sys.stderr)
        return 1
    except SubtitleParseError as exc:
        print(f"srtat: could not parse {args.srt_file}: {exc}", file=sys.stderr)
        return 1

    if args.range:
        try:
            start_ms = _parse_query_time(args.range[0])
            end_ms = _parse_query_time(args.range[1])
        except (SubtitleParseError, ValueError):
            print(f"srtat: not a valid time range: {args.range!r}", file=sys.stderr)
            return 1
        if end_ms <= start_ms:
            print("srtat: --range end must be after start", file=sys.stderr)
            return 1

        matches = in_range(cues, start_ms, end_ms)

        if args.format == "json":
            print(json.dumps([_cue_to_dict(c) for c in matches], ensure_ascii=False))
            return 0

        if not matches:
            print("(no subtitles in this range)")
            return 0

        for cue in matches:
            start = format_timestamp(cue.start_ms)
            end = format_timestamp(cue.end_ms)
            print(f"#{cue.index} {start} --> {end}\n{cue.text}")
        return 0

    try:
        query_ms = _parse_query_time(args.time)
    except (SubtitleParseError, ValueError):
        print(f"srtat: not a valid time: {args.time!r}", file=sys.stderr)
        return 1

    matches = at(cues, query_ms)

    if args.format == "json":
        print(json.dumps([_cue_to_dict(c) for c in matches], ensure_ascii=False))
        return 0

    if not matches:
        print("(no subtitle at this time)")
        return 0

    for cue in matches:
        print(f"#{cue.index}\n{cue.text}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
