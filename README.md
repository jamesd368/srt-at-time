# srtat

Given a subtitle file and a timestamp, tell me what's being said right then.

I keep running into this from two directions: writing about a scene in a
video and wanting the exact line without scrubbing back and forth, and
checking whether a subtitle track drifted out of sync partway through a
file. Both come down to the same question: "what cue is on screen at time
T?" Most subtitle tools are editors, players, or format converters. None of
them answer that one question directly from the command line.

## Usage

```
$ srtat movie.srt 00:01:23,500
#42
Come with me if you want to live.

$ srtat movie.srt 83.5
#42
Come with me if you want to live.

$ srtat movie.srt 00:00:05,000
(no subtitle at this time)
```

The time argument accepts either an SRT-style timestamp (`HH:MM:SS,mmm`) or
plain seconds, decimals allowed. If two cues overlap at the given moment,
both are printed.

To list every cue in a stretch of the file instead of a single instant, use
`--range`:

```
$ srtat movie.srt --range 00:01:20,000 00:01:30,000
#42 00:01:23,500 --> 00:01:26,000
Come with me if you want to live.

#43 00:01:27,000 --> 00:01:29,800
Sorry, kid.
```

`--range` takes the same time formats as the single-instant query and lists
any cue that overlaps the window at all, even partially.

Pass `--format json` to get machine-readable output instead, for scripting:

```
$ srtat movie.srt 83.5 --format json
[{"index": 42, "start_ms": 83500, "end_ms": 86000, "start": "00:01:23,500", "end": "00:01:26,000", "text": "Come with me if you want to live."}]
```

It's always a JSON array, even for a single-instant query: empty (`[]`) when
nothing matches, with more than one entry when cues overlap. `--range` uses
the same array shape.

`.vtt` (WebVTT) files work the same way; the format is picked by file
extension:

```
$ srtat movie.vtt 83.5
#42
Come with me if you want to live.
```

As a library:

```python
from srtat import parse, at

with open("movie.srt", encoding="utf-8-sig") as fh:
    cues = parse(fh.read())

for cue in at(cues, ms=83_500):
    print(cue.text)
```

For WebVTT, use `parse_vtt` instead of `parse`.

## What it handles

Real subtitle files are messier than the spec suggests. Right now `srtat`
copes with:

- a leading BOM
- CRLF or LF line endings
- a period instead of a comma before milliseconds (SRT)
- missing or non-numeric index/identifier lines
- multi-line cue text
- overlapping cues
- zero-duration cues

For WebVTT specifically, it also handles the required `WEBVTT` header
(including trailing metadata), `NOTE` and `STYLE` blocks, cue settings
trailing the timing line (`align:middle`, `line:90%`, and so on), and
timestamps that omit the hours field.

Cues with an end time equal to their start time never match a query; a cue
matches from its start time up to (but not including) its end time, so
back-to-back cues don't both claim the boundary millisecond.

A cue block with a garbled timing line or timestamp is skipped rather than
failing the whole file; each one raises a `SubtitleParseWarning` (via the
standard `warnings` module) so you can see what got dropped without losing
the rest of the file over one bad cue.

## Status

Early. `.srt` and `.vtt` are both supported. No dependencies beyond the
Python standard library.

## Running the tests

```
python -m unittest discover tests
```
