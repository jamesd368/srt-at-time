"""Command line entry point: report which subtitle cue(s) are on screen at a given time."""

from __future__ import annotations

import argparse
import sys

from .parser import Cue, SubtitleParseError, at, parse, parse_timestamp
from .vtt import parse_vtt


def _parse_query_time(raw: str) -> int:
    raw = raw.strip()
    if ":" in raw:
        return parse_timestamp(raw)
    # Bare number: treat as seconds, decimals allowed (e.g. "83.4").
    return int(round(float(raw) * 1000))


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
        help="timestamp to query: HH:MM:SS,mmm or plain seconds, e.g. 83.4",
    )
    args = parser.parse_args(argv)

    try:
        cues = _load_cues(args.srt_file)
    except OSError as exc:
        print(f"srtat: {exc}", file=sys.stderr)
        return 1
    except SubtitleParseError as exc:
        print(f"srtat: could not parse {args.srt_file}: {exc}", file=sys.stderr)
        return 1

    try:
        query_ms = _parse_query_time(args.time)
    except (SubtitleParseError, ValueError):
        print(f"srtat: not a valid time: {args.time!r}", file=sys.stderr)
        return 1

    matches = at(cues, query_ms)
    if not matches:
        print("(no subtitle at this time)")
        return 0

    for cue in matches:
        print(f"#{cue.index}\n{cue.text}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
